from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any
from urllib.error import URLError
from urllib.parse import urlparse, urlencode

from app.plugin_http import fetch_json

log = logging.getLogger(__name__)

HTTP_TIMEOUT_S = 8


def _num(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _base_url(value: str) -> str:
    value = (value or "").strip().rstrip("/")
    if not value:
        raise ValueError("empty_url")
    p = urlparse(value)
    if p.scheme not in ("http", "https") or not p.netloc:
        raise ValueError("invalid_url")
    if value.endswith("/api/state"):
        return value[:-10]
    return value


def _get_json(url: str) -> Any:
    return fetch_json(
        url,
        headers={"Accept": "application/json"},
        timeout=HTTP_TIMEOUT_S,
        retries=0,
    )


def _unwrap(data: Any) -> Any:
    if isinstance(data, dict) and isinstance(data.get("result"), (dict, list)):
        return data["result"]
    return data


def _parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        t = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=datetime.now().astimezone().tzinfo)
    return t


def _hhmm(value: Any) -> str:
    t = _parse_ts(value)
    return t.astimezone().strftime("%H:%M") if t else ""


def _energy_kwh(value: Any) -> float | None:
    """evcc session / today / history energy fields are already kWh."""
    if value is None:
        return None
    n = _num(value, -1)
    if n < 0:
        return None
    return round(n, 3)


def _forecast_energy_kwh(value: Any) -> float | None:
    """evcc documents forecast.solar.*.energy in Wh."""
    if value is None:
        return None
    n = _num(value, -1)
    if n < 0:
        return None
    return round(n / 1000.0, 3)


def _solar_forecast(state: dict) -> dict:
    """Compact 15-min PV forecast for today + tomorrow from /api/state."""
    solar = ((state.get("forecast") or {}).get("solar") or {})
    raw = solar.get("timeseries") or []
    now = datetime.now().astimezone()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=2)

    hours: list[float] = []
    watts: list[int] = []
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            t = _parse_ts(item.get("ts") or item.get("time"))
            if t is None:
                continue
            t = t.astimezone(now.tzinfo)
            if t < start or t >= end:
                continue
            hours.append(round((t - start).total_seconds() / 3600.0, 3))
            watts.append(int(round(_num(item.get("val") or item.get("value")))))

    today = solar.get("today") if isinstance(solar.get("today"), dict) else {}
    tomorrow = solar.get("tomorrow") if isinstance(solar.get("tomorrow"), dict) else {}
    after = solar.get("dayAfterTomorrow") if isinstance(solar.get("dayAfterTomorrow"), dict) else {}
    return {
        "pv_forecast_h": hours,
        "pv_forecast_w": watts,
        "pv_forecast_now_h": round(
            now.hour + now.minute / 60.0 + now.second / 3600.0, 3
        ),
        "pv_forecast_today_kwh": _forecast_energy_kwh(today.get("energy")),
        "pv_forecast_tomorrow_kwh": _forecast_energy_kwh(tomorrow.get("energy")),
        "pv_forecast_after_kwh": _forecast_energy_kwh(after.get("energy")),
    }


def _collect_history_numbers(data: Any, *, group: str, field: str) -> list[float]:
    found: list[float] = []
    field_l = field.lower()

    def walk(x: Any, in_group: bool = False):
        if isinstance(x, dict):
            here = in_group or str(x.get("group") or "").lower() == group
            for k, v in x.items():
                if here and str(k).lower() == field_l and isinstance(v, (int, float)):
                    found.append(float(v))
                elif not isinstance(v, (int, float, str, bool)) and v is not None:
                    walk(v, here)
        elif isinstance(x, list):
            for y in x:
                walk(y, in_group)

    walk(data)
    return found


def _sum_history(data: Any, group: str, field: str) -> float | None:
    vals = [
        n
        for n in _collect_history_numbers(data, group=group, field=field)
        if n >= 0 and n == n
    ]
    return round(sum(vals), 3) if vals else None


def _pv_actual_series(data: Any, start: datetime) -> dict:
    """Turn 15-min PV energy buckets into a power curve (W)."""
    hours: list[float] = []
    watts: list[int] = []
    rows = data if isinstance(data, list) else []
    for row in rows:
        if not isinstance(row, dict) or str(row.get("group") or "").lower() != "pv":
            continue
        for pt in row.get("data") or []:
            if not isinstance(pt, dict):
                continue
            t0 = _parse_ts(pt.get("start"))
            t1 = _parse_ts(pt.get("end"))
            if t0 is None:
                continue
            t0 = t0.astimezone(start.tzinfo)
            t1 = t1.astimezone(start.tzinfo) if t1 else t0 + timedelta(minutes=15)
            dt_h = max((t1 - t0).total_seconds() / 3600.0, 1 / 60)
            # Plot at interval start so the curve lines up with forecast sample ts.
            hours.append(round((t0 - start).total_seconds() / 3600.0, 3))
            watts.append(int(round(_num(pt.get("energy")) / dt_h * 1000)))
    return {"pv_actual_h": hours, "pv_actual_w": watts}


def _daily_energy_from_history(base: str) -> dict:
    """One 15-min history call: daily totals plus the actual PV curve."""
    now = datetime.now().astimezone()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    params = {
        "from": start.isoformat(),
        "to": now.isoformat(),
        "aggregate": "15m",
        "grouped": "false",
        "format": "json",
    }
    data = _unwrap(_get_json(base + "/api/history/energy?" + urlencode(params)))

    exported = _sum_history(data, "grid", "returnEnergy")
    if exported is None:
        negatives = [
            abs(v)
            for v in _collect_history_numbers(data, group="grid", field="energy")
            if v < 0
        ]
        exported = round(sum(negatives), 3) if negatives else None

    out = {
        "pv_today_kwh": _sum_history(data, "pv", "energy"),
        "home_today_kwh": _sum_history(data, "home", "energy"),
        "feedin_today_kwh": exported,
        "grid_import_today_kwh": _sum_history(data, "grid", "energy"),
        "battery_charge_today_kwh": _sum_history(data, "battery", "energy"),
        "battery_discharge_today_kwh": _sum_history(data, "battery", "returnEnergy"),
    }
    out.update(_pv_actual_series(data, start))
    return out


def _error_code(exc: BaseException) -> str:
    if isinstance(exc, TimeoutError):
        return "timeout"
    if isinstance(exc, URLError) and "timed out" in str(exc).lower():
        return "timeout"
    return "fetch_failed"


def fetch(options: dict, settings: dict, *, ctx: dict) -> dict:
    del settings, ctx
    try:
        base = _base_url(str(options.get("url", "")))
        state = _unwrap(_get_json(base + "/api/state"))
        if not isinstance(state, dict):
            raise ValueError("unexpected")

        lp_index = max(0, int(options.get("loadpoint", 0) or 0))
        battery = state.get("battery") or {}
        grid = state.get("grid") or {}
        lps = state.get("loadpoints") or []
        lp = lps[lp_index] if isinstance(lps, list) and lp_index < len(lps) and isinstance(lps[lp_index], dict) else {}

        batt_power = _num(battery.get("power"))
        grid_power = _num(grid.get("power"))
        vehicle_soc = _num(lp.get("vehicleSoc"), -1)
        if not lp.get("connected") and vehicle_soc <= 0:
            vehicle_soc = -1
        vehicle_fallback = str(options.get("vehicle_name") or "").strip()

        data = {
            "pv_power": _num(state.get("pvPower")),
            "home_power": _num(state.get("homePower")),
            "grid_power": grid_power,
            "battery_soc": _num(battery.get("soc"), -1),
            "battery_power": batt_power,
            "loadpoint": {
                "title": str(lp.get("vehicleTitle") or lp.get("vehicleName") or vehicle_fallback),
                "connected": bool(lp.get("connected", False)),
                "charging": bool(lp.get("charging", False)),
                "charge_power": _num(lp.get("chargePower")),
                "mode": str(lp.get("mode") or "-"),
                "vehicle_soc": vehicle_soc,
                "vehicle_range": _num(lp.get("vehicleRange"), -1),
                "session_energy": _energy_kwh(lp.get("sessionEnergy") or lp.get("chargedEnergy")),
                "today_energy": _energy_kwh(lp.get("todayEnergy")),
                "plan_time": _hhmm(lp.get("planTime") or lp.get("effectivePlanTime") or lp.get("planProjectedStart")),
                "vehicle_title": str(lp.get("vehicleTitle") or lp.get("vehicleName") or ""),
            },
            "fetched_at": datetime.now().astimezone().strftime("%H:%M"),
        }
        data.update(_solar_forecast(state))

        try:
            data.update(_daily_energy_from_history(base))
        except Exception:
            log.exception("evcc_energy history fetch failed")
            data.setdefault("pv_today_kwh", None)
            data.setdefault("home_today_kwh", None)
            data.setdefault("feedin_today_kwh", None)
            data.setdefault("grid_import_today_kwh", None)
            data.setdefault("battery_charge_today_kwh", None)
            data.setdefault("battery_discharge_today_kwh", None)
            data.setdefault("pv_actual_h", [])
            data.setdefault("pv_actual_w", [])

        now_h = data.get("pv_forecast_now_h")
        actual_h = data.get("pv_actual_h")
        actual_w = data.get("pv_actual_w")
        if (
            isinstance(actual_h, list)
            and isinstance(actual_w, list)
            and isinstance(now_h, (int, float))
        ):
            live = int(round(data.get("pv_power") or 0))
            if not actual_h or now_h > actual_h[-1] + 0.02:
                actual_h.append(round(float(now_h), 3))
                actual_w.append(live)
            else:
                actual_w[-1] = live

        return data

    except ValueError as exc:
        code = str(exc)
        if code in {"empty_url", "invalid_url", "unexpected"}:
            return {"error": code}
        log.warning("evcc_energy fetch failed: %s", exc)
        return {"error": "fetch_failed"}
    except (TimeoutError, URLError) as exc:
        code = _error_code(exc)
        log.warning("evcc_energy fetch %s: %s", code, exc)
        return {"error": code}
    except Exception:
        log.exception("evcc_energy fetch failed")
        return {"error": "fetch_failed"}

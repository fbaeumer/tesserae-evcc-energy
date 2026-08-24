"""evcc_energy fetch() smoke: mocked evcc JSON, no network."""

from __future__ import annotations

from plugins.evcc_energy import server as evcc


_STATE = {
    "pvPower": 1200,
    "homePower": 400,
    "greenShareHome": 1,
    "battery": {"soc": 80, "power": -200},
    "grid": {"power": -800},
    "loadpoints": [
        {
            "vehicleTitle": "Test Car",
            "connected": True,
            "charging": False,
            "chargePower": 0,
            "mode": "pv",
            "vehicleSoc": 64,
            "vehicleRange": 210,
            "sessionEnergy": 0,
            "todayEnergy": 3.2,
        }
    ],
    "forecast": {
        "solar": {
            "today": {"energy": 12.5},
            "tomorrow": {"energy": 20.0},
            "dayAfterTomorrow": {"energy": 8.0},
            "timeseries": [
                {"ts": "2026-08-24T08:00:00+02:00", "val": 1000},
                {"ts": "2026-08-24T12:00:00+02:00", "val": 4000},
                {"ts": "2026-08-25T12:00:00+02:00", "val": 3500},
            ],
        }
    },
}

_HISTORY = [
    {
        "group": "pv",
        "data": [
            {"start": "2026-08-24T07:00:00+02:00", "end": "2026-08-24T07:15:00+02:00", "energy": 0.2},
            {"start": "2026-08-24T07:15:00+02:00", "end": "2026-08-24T07:30:00+02:00", "energy": 0.3},
        ],
    },
    {"group": "home", "data": [{"start": "2026-08-24T07:00:00+02:00", "end": "2026-08-24T07:15:00+02:00", "energy": 0.1}]},
    {"group": "grid", "data": [{"start": "2026-08-24T07:00:00+02:00", "end": "2026-08-24T07:15:00+02:00", "energy": 0, "returnEnergy": 0.05}]},
]


def test_empty_url():
    assert evcc.fetch({"url": ""}, {}, ctx={}) == {"error": "empty_url"}


def test_invalid_url():
    assert evcc.fetch({"url": "evcc.local"}, {}, ctx={}) == {"error": "invalid_url"}


def test_fetch_state(monkeypatch):
    def fake_curl(url: str):
        if url.endswith("/api/state"):
            return _STATE
        if "/api/history/energy" in url:
            return _HISTORY
        raise AssertionError(url)

    monkeypatch.setattr(evcc, "_curl_json", fake_curl)
    out = evcc.fetch({"url": "http://192.168.1.10:7070", "loadpoint": 0}, {}, ctx={})
    assert "error" not in out
    assert out["pv_power"] == 1200
    assert out["loadpoint"]["title"] == "Test Car"
    assert out["pv_forecast_tomorrow_kwh"] == 20.0
    assert out["pv_today_kwh"] == 0.5
    assert out["pv_actual_w"]
    assert out["feedin_today_kwh"] == 0.05


def test_vehicle_name_fallback(monkeypatch):
    state = {**_STATE, "loadpoints": [{"connected": False, "vehicleSoc": 0}]}

    def fake_curl(url: str):
        return state if url.endswith("/api/state") else _HISTORY

    monkeypatch.setattr(evcc, "_curl_json", fake_curl)
    out = evcc.fetch(
        {"url": "http://192.168.1.10:7070", "vehicle_name": "Škoda Enyaq"},
        {},
        ctx={},
    )
    assert out["loadpoint"]["title"] == "Škoda Enyaq"
    assert out["loadpoint"]["connected"] is False


const I18N = {
  de: {
    title: "Energie",
    pv: "PV",
    house: "Haus",
    battery: "Akku",
    grid: "Netz",
    vehicle: "Auto",
    today: "heute",
    tomorrow: "morgen",
    forecast_tomorrow: "PV Prognose morgen",
    forecast_after: "PV Prognose übermorgen",
    charging: "lädt",
    discharging: "entlädt",
    idle: "bereit",
    disconnected: "nicht angeschlossen",
    plan: "Plan",
    session: "Session",
    no_curve: "Keine PV-Kurve",
    mode_off: "aus",
    mode_now: "sofort",
    mode_minpv: "min+pv",
    mode_pv: "pv",
    err_empty_url: "EVCC-URL fehlt.",
    err_invalid_url: "EVCC-URL muss mit http:// oder https:// beginnen.",
    err_timeout: "EVCC Timeout.",
    err_unexpected: "Unerwartete EVCC-Antwort.",
    err_fetch_failed: "EVCC nicht erreichbar.",
  },
  en: {
    title: "Energy",
    pv: "PV",
    house: "Home",
    battery: "Battery",
    grid: "Grid",
    vehicle: "Vehicle",
    today: "today",
    tomorrow: "tomorrow",
    forecast_tomorrow: "PV forecast tomorrow",
    forecast_after: "PV forecast day after",
    charging: "charging",
    discharging: "discharging",
    idle: "idle",
    disconnected: "not connected",
    plan: "plan",
    session: "session",
    no_curve: "No PV curve",
    mode_off: "off",
    mode_now: "fast",
    mode_minpv: "min+pv",
    mode_pv: "pv",
    err_empty_url: "EVCC URL is missing.",
    err_invalid_url: "EVCC URL must start with http:// or https://.",
    err_timeout: "EVCC timed out.",
    err_unexpected: "Unexpected EVCC response.",
    err_fetch_failed: "EVCC is unreachable.",
  },
};

let LANG = "de";
let T = I18N.de;

function useLang(o) {
  LANG = String(o.language || "de").toLowerCase().startsWith("en") ? "en" : "de";
  T = I18N[LANG];
}
function t(key) {
  return T[key] || I18N.en[key] || key;
}
function num(n, digits) {
  const s = Number(n).toFixed(digits);
  return LANG === "de" ? s.replace(".", ",") : s;
}

function esc(v) {
  return String(v ?? "").replaceAll("&","&amp;").replaceAll("<","&lt;")
    .replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#039;");
}
function power(w) {
  const n = Number(w || 0);
  const a = Math.abs(n);
  if (a < 1000) return `${Math.round(a)} W`;
  return `${num(a / 1000, a >= 10000 ? 1 : 2)} kW`;
}
function pct(v) {
  const n = Number(v);
  return Number.isFinite(n) && n >= 0 ? `${Math.round(n)} %` : "–";
}
function kwh(v) {
  if (v == null || v === "") return "–";
  const n = Number(v);
  return Number.isFinite(n) && n >= 0 ? `${num(n, 1)} kWh` : "–";
}
function kwhNum(v) {
  if (v == null || v === "") return "–";
  const n = Number(v);
  return Number.isFinite(n) && n >= 0 ? num(n, 1) : "–";
}
function kwhPair(a, b) {
  if (a == null && b == null) return "";
  return `${kwhNum(a ?? 0)} / ${kwhNum(b ?? 0)} kWh`;
}
function gridSub(d) {
  return kwhPair(d.feedin_today_kwh, d.grid_import_today_kwh);
}
function batterySub(d) {
  const n = Number(d.battery_power || 0);
  if (n < -100) return `${t("charging")} ${power(n)}`;
  if (n > 100) return `${t("discharging")} ${power(n)}`;
  return t("idle");
}
function todaySub(v) {
  return v != null ? `${t("today")} ${kwh(v)}` : "";
}
function modeLabel(v) {
  const key = ({off:"mode_off", now:"mode_now", minpv:"mode_minpv", pv:"mode_pv"})[String(v||"").toLowerCase()];
  return key ? t(key) : String(v || "–").toLowerCase();
}
function vehicleTitle(lp, o) {
  return String(lp.title || o.vehicle_name || t("vehicle")).trim() || t("vehicle");
}
function carSub(lp) {
  if (!lp.connected) return t("disconnected");
  const bits = [];
  if (lp.charging) bits.push(`${t("charging")} ${power(lp.charge_power)}`);
  else bits.push(modeLabel(lp.mode));
  const range = Number(lp.vehicle_range);
  if (Number.isFinite(range) && range > 0) bits.push(`${Math.round(range)} km`);
  if (lp.plan_time) bits.push(`${t("plan")} ${lp.plan_time}`);
  return bits.join(" · ");
}
function carExtra(lp) {
  if (lp.connected) {
    const n = Number(lp.session_energy);
    return Number.isFinite(n) && n > 0 ? `${t("session")} ${kwh(n)}` : "";
  }
  const n = Number(lp.today_energy);
  return Number.isFinite(n) && n > 0 ? `${t("today")} ${kwh(n)}` : "";
}
function carValue(lp) {
  if (lp.charging) return power(lp.charge_power);
  return pct(lp.vehicle_soc);
}
function errText(code) {
  const key = `err_${code}`;
  return T[key] || I18N.en[key] || String(code || "");
}
function showFooter(o) {
  return o.show_forecast !== false && o.show_today !== false;
}

function pathFrom(hs, ws, xOf, yOf) {
  const n = Math.min(hs.length, ws.length);
  let d = "";
  for (let i = 0; i < n; i++) {
    d += `${i ? "L" : "M"}${xOf(hs[i]).toFixed(1)} ${yOf(ws[i]).toFixed(1)} `;
  }
  return { d, n };
}

function forecastChart(d) {
  const hs = Array.isArray(d.pv_forecast_h) ? d.pv_forecast_h : [];
  const ws = Array.isArray(d.pv_forecast_w) ? d.pv_forecast_w : [];
  const ah = Array.isArray(d.pv_actual_h) ? d.pv_actual_h : [];
  const aw = Array.isArray(d.pv_actual_w) ? d.pv_actual_w : [];
  const n = Math.min(hs.length, ws.length);
  const na = Math.min(ah.length, aw.length);

  if (n < 2 && na < 2) {
    return `<div class="evcc-chart-empty">${esc(t("no_curve"))}</div>`;
  }

  const W = 440, H = 230;
  const L = 42, R = 12, T = 20, B = 38;
  const iw = W - L - R, ih = H - T - B;
  const hMax = Math.max(24, n ? hs[n - 1] : 0, na ? ah[na - 1] : 0);
  const wMax = Math.max(800, ...(n ? ws.slice(0, n) : []), ...(na ? aw.slice(0, na) : []));
  const yMax = Math.max(1000, Math.ceil(wMax / 1000) * 1000);
  const xOf = (h) => L + (Math.max(0, Math.min(hMax, h)) / hMax) * iw;
  const yOf = (w) => T + ih - (Math.max(0, w) / yMax) * ih;

  const forecast = pathFrom(hs, ws, xOf, yOf);
  const actual = pathFrom(ah, aw, xOf, yOf);
  const fill = forecast.n > 1
    ? `${forecast.d}L${xOf(hs[forecast.n - 1]).toFixed(1)} ${(T + ih).toFixed(1)} L${xOf(hs[0]).toFixed(1)} ${(T + ih).toFixed(1)} Z`
    : "";

  const yTicks = [0, yMax / 2, yMax].map((w) => {
    const y = yOf(w).toFixed(1);
    const label = w <= 0 ? "0" : `${num(w / 1000, w >= 10000 ? 0 : 1)} kW`;
    return `<line x1="${L}" x2="${L + iw}" y1="${y}" y2="${y}" class="grid-h"/>
      ${w <= 0 ? "" : `<text x="${L - 6}" y="${y}" class="axis-y">${label}</text>`}`;
  }).join("");

  let xTicks = "";
  for (let h = 0; h <= hMax + 0.01; h += 6) {
    const x = xOf(h).toFixed(1);
    const hour = Math.round(h) % 24;
    xTicks += `<text x="${x}" y="${H - 10}" class="axis-x">${hour}</text>`;
  }

  const nowH = Number(d.pv_forecast_now_h);
  let nowMark = "";
  if (Number.isFinite(nowH) && nowH >= 0 && nowH <= hMax) {
    const x = xOf(nowH).toFixed(1);
    nowMark = `<line x1="${x}" x2="${x}" y1="${T}" y2="${T + ih}" class="now"/>`;
  }

  let midnight = "";
  let days = "";
  if (hMax > 24) {
    const x = xOf(24).toFixed(1);
    midnight = `<line x1="${x}" x2="${x}" y1="${T}" y2="${T + ih}" class="midnight"/>`;
    days = `<text x="${xOf(12).toFixed(1)}" y="14" class="day">${esc(t("today"))}</text>
      <text x="${xOf(36).toFixed(1)}" y="14" class="day">${esc(t("tomorrow"))}</text>`;
  }

  let peak = "";
  if (n > 0) {
    let peakI = 0;
    for (let i = 1; i < n; i++) if (ws[i] > ws[peakI]) peakI = i;
    if (ws[peakI] > 80) {
      const px = xOf(hs[peakI]);
      const py = yOf(ws[peakI]);
      peak = `<circle cx="${px.toFixed(1)}" cy="${py.toFixed(1)}" r="3.2" class="peak-dot"/>
       <text x="${Math.min(L + iw - 4, Math.max(L + 28, px + 8)).toFixed(1)}" y="${Math.max(T + 11, py - 6).toFixed(1)}" class="peak">${power(ws[peakI])}</text>`;
    }
  }

  return `
    <svg class="evcc-svg" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" aria-hidden="true">
      <defs>
        <clipPath id="evcc-plot">
          <rect x="${L}" y="${T}" width="${iw}" height="${ih}"/>
        </clipPath>
      </defs>
      ${yTicks}
      ${days}
      <line x1="${L}" x2="${L + iw}" y1="${T + ih}" y2="${T + ih}" class="axis-base"/>
      <g clip-path="url(#evcc-plot)">
        ${midnight}
        ${fill ? `<path d="${fill}" class="area"/>` : ""}
        ${forecast.n > 1 ? `<path d="${forecast.d}" class="line line-forecast"/>` : ""}
        ${actual.n > 1 ? `<path d="${actual.d}" class="line line-actual"/>` : ""}
        ${nowMark}
      </g>
      ${peak}
      ${xTicks}
    </svg>`;
}

export default function render(shadow, ctx) {
  const d = ctx.data || {};
  const o = (ctx.cell && ctx.cell.options) || {};
  useLang(o);
  const title = esc(String(o.title || "").trim() || t("title"));
  const lp = d.loadpoint || {};

  shadow.innerHTML = `
    <link rel="stylesheet" href="/static/style/spectra-widgets.css">
    <link rel="stylesheet" href="/static/icons/phosphor/regular/style.css">
    <link rel="stylesheet" href="/static/icons/phosphor/bold/style.css">
    <link rel="stylesheet" href="/plugins/evcc_energy/client.css">

    <div class="w evcc-widget" data-widget="evcc_energy">
      <div class="evcc-head">
        <div class="evcc-title">${title}</div>
        <div class="evcc-time">${esc(d.fetched_at || "")}</div>
      </div>

      <div class="evcc-main">
        <div class="evcc-chart">
          ${forecastChart(d)}
        </div>

        <div class="evcc-stats">
          ${d.error ? `
          <div class="error-row"><i class="ph-bold ph-warning-circle"></i><span>${esc(errText(d.error))}</span></div>
          ` : `
          <div class="stat"><i class="ph-bold ph-sun"></i><span>${esc(t("pv"))} <small>${esc(todaySub(d.pv_today_kwh))}</small></span><b>${power(d.pv_power)}</b></div>
          <div class="stat"><i class="ph-bold ph-house-line"></i><span>${esc(t("house"))} <small>${esc(todaySub(d.home_today_kwh))}</small></span><b>${power(d.home_power)}</b></div>
          <div class="stat"><i class="ph-bold ph-battery-high"></i><span>${esc(t("battery"))} <small>${esc(batterySub(d))}</small></span><b>${pct(d.battery_soc)}</b></div>
          <div class="stat"><i class="ph-bold ph-lightning"></i><span>${esc(t("grid"))} <small>${esc(gridSub(d))}</small></span><b>${power(d.grid_power)}</b></div>
          `}
        </div>
      </div>

      ${!showFooter(o) ? "" : `
      <div class="today">
        <div class="today-stack">
          <div class="today-item">
            <i class="ph-bold ph-sun"></i>
            <span>${esc(t("forecast_tomorrow"))}</span>
            <b>${kwh(d.pv_forecast_tomorrow_kwh)}</b>
          </div>
          <div class="today-item">
            <i class="ph-bold ph-sun-horizon"></i>
            <span>${esc(t("forecast_after"))}</span>
            <b>${kwh(d.pv_forecast_after_kwh)}</b>
          </div>
        </div>
          ${o.show_car === false ? "" : `
          <div class="today-car">
            <i class="ph-bold ph-car"></i>
            <span>${esc(vehicleTitle(lp, o))} <small>${esc(carSub(lp))}${carExtra(lp) ? ` · ${esc(carExtra(lp))}` : ""}</small></span>
            <b>${esc(carValue(lp))}</b>
          </div>`}
      </div>`}
    </div>`;
}

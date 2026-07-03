"use strict";

const $ = (s) => document.querySelector(s);

const AFFILIATES = [
  { t: T("aff_headsets_t"), d: T("aff_headsets_d"), url: "#" },
  { t: T("aff_courses_t"), d: T("aff_courses_d"), url: "#" },
  { t: T("aff_sims_t"), d: T("aff_sims_d"), url: "#" },
  { t: T("aff_books_t"), d: T("aff_books_d"), url: "#" },
];
$("#aff-grid").innerHTML = AFFILIATES
  .map((a) => `<a class="aff-card" href="${a.url}" rel="sponsored nofollow" target="_blank"><span class="t">${a.t}</span><span class="d">${a.d}</span></a>`)
  .join("");

// ===== Autocomplete de aeroporto (mesmo padrão das outras páginas) ========
function buildAirportAC() {
  const inputEl = $("#wx-airport");
  const acEl = $("#wx-ac");
  let list = [], hl = -1, timer = null;
  function close() { acEl.classList.remove("open"); acEl.innerHTML = ""; hl = -1; }
  function render() {
    acEl.innerHTML = list
      .map((a, i) =>
        `<div data-i="${i}" class="${i === hl ? "hl" : ""}"><span class="code">${a.code}</span> · ${a.icao}` +
        `<div class="nm">${a.city ? a.city + " · " : ""}${a.name} (${a.country})</div></div>`)
      .join("");
    acEl.classList.toggle("open", list.length > 0);
    const _hl = acEl.querySelector(".hl"); if (_hl) _hl.scrollIntoView({ block: "nearest" });
  }
  function pick(a) {
    inputEl.value = `${a.code} · ${a.city || a.name}`;
    close();
    const code = a.icao || a.code;
    loadMetar(code, a);
    loadNowcast(code);
    loadTaf(code);
    loadClima(code);
    renderAlertButton(code);
  }
  inputEl.addEventListener("input", () => {
    const q = inputEl.value.trim();
    clearTimeout(timer);
    if (q.length < 2) return close();
    timer = setTimeout(async () => {
      try { list = (await (await fetch(`/api/airports/search?q=${encodeURIComponent(q)}`)).json()).results || []; hl = -1; render(); }
      catch (_) { close(); }
    }, 160);
  });
  inputEl.addEventListener("keydown", (e) => {
    if (!acEl.classList.contains("open")) return;
    if (e.key === "ArrowDown") { hl = Math.min(hl + 1, list.length - 1); render(); e.preventDefault(); }
    else if (e.key === "ArrowUp") { hl = Math.max(hl - 1, 0); render(); e.preventDefault(); }
    else if (e.key === "Enter" && list[hl >= 0 ? hl : 0]) { pick(list[hl >= 0 ? hl : 0]); e.preventDefault(); }
    else if (e.key === "Escape") close();
  });
  acEl.addEventListener("mousedown", (e) => { const d = e.target.closest("[data-i]"); if (d) pick(list[+d.dataset.i]); });
  inputEl.addEventListener("blur", () => setTimeout(close, 180));
}

// ===== Carrega e renderiza o METAR =======================================
const out = $("#wx-out");

function msg(html) { out.innerHTML = `<div class="wx-msg">${html}</div>`; }

async function loadMetar(icao, ap) {
  out.innerHTML = `<div class="wx-msg">${TF("wx_querying", icao)}</div>`;
  let res, data;
  try {
    res = await fetch(`/api/metar?icao=${encodeURIComponent(icao)}&lang=${window.APP_LANG || "pt"}`);
    data = await res.json().catch(() => ({}));
  } catch (_) {
    return msg(T("wx_conn_fail"));
  }
  if (res.status === 503) {
    return msg(T("wx_503"));
  }
  if (!res.ok) {
    return msg(TF("wx_get_fail", icao, data.detail ? `: ${data.detail}` : "."));
  }
  render(data, ap);
}

function cell(k, v) {
  return v == null || v === "" ? "" : `<div class="wx-cell"><div class="k">${k}</div><div class="v">${v}</div></div>`;
}

function render(d, ap) {
  const c = d.category_info || {};
  const w = d.wind;
  let wind = "—";
  if (w) {
    if (w.vrb) wind = `VRB <small>${w.speed_kt} kt</small>`;
    else if (w.speed_kt === 0) wind = T("wx_calm");
    else wind = `${String(w.dir).padStart(3, "0")}° <small>${w.speed_kt} kt${w.gust_kt ? " G" + w.gust_kt : ""}</small>`;
  }
  const vis = d.cavok ? "CAVOK" : (d.visibility_m == null ? "—" :
    (d.visibility_m >= 9999 ? "≥10 <small>km</small>" :
      (d.visibility_m >= 1000 ? `${Math.round(d.visibility_m / 1000)} <small>km</small>` : `${d.visibility_m} <small>m</small>`)));
  const ceil = d.ceiling_ft == null ? T("wx_noceil") : `${d.ceiling_ft} <small>ft</small>`;
  const temp = d.temp_c == null ? "—" : `${d.temp_c}° <small>/ ${d.dewpoint_c}°</small>`;
  const qnh = d.qnh_hpa == null ? "—" : `${d.qnh_hpa} <small>hPa</small>`;

  const name = (d.airport && (d.airport.name || d.airport.city)) || (ap && (ap.name || ap.city)) || d.station || "";
  const when = d.time_utc ? `${d.time_utc.slice(0, 2)}:${d.time_utc.slice(2, 4)} UTC` : "";

  out.innerHTML =
    `<div class="wx-card">
      <div class="wx-flag" style="background:linear-gradient(90deg,${c.color}22,transparent)">
        <div class="wx-dot" style="background:${c.color}22;border:1px solid ${c.color}">${c.emoji || ""}</div>
        <div class="wx-cat" style="color:${c.color}">${c.label || d.category}<small>${c.desc || ""}</small></div>
        <div class="wx-when">${d.station || ""}${name ? "<br>" + name : ""}${when ? "<br>" + when : ""}</div>
      </div>
      <div class="wx-sum">${d.summary_pt || "—"}</div>
      <div class="wx-grid">
        ${cell(T("wx_wind"), wind)}
        ${cell(T("wx_vis"), vis)}
        ${cell(T("wx_ceil"), ceil)}
        ${cell(T("wx_temp"), temp)}
        ${cell("QNH", qnh)}
        ${cell(T("wx_cat"), `<span style="color:${c.color}">${c.label || d.category}</span>`)}
      </div>
      <div class="wx-raw">${d.raw || ""}</div>
    </div>`;
}

// ===== Alertas push (tempo abaixo de VFR) ================================
const alertEl = document.querySelector("#wx-alert");

function b64ToU8(b64) {
  const pad = "=".repeat((4 - (b64.length % 4)) % 4);
  const s = (b64 + pad).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(s);
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
}

function renderAlertButton(code) {
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) { alertEl.innerHTML = ""; return; }
  alertEl.innerHTML = `<button class="alert-btn" id="alert-btn" type="button">${TF("wx_alert_btn", code)}</button>` +
    `<div class="alert-note">${T("wx_alert_note")}</div>`;
  document.getElementById("alert-btn").addEventListener("click", () => subscribeAlerts(code));
}

async function subscribeAlerts(code) {
  const btn = document.getElementById("alert-btn");
  try {
    const perm = await Notification.requestPermission();
    if (perm !== "granted") return alert(T("wx_perm_denied"));
    const keyRes = await fetch("/api/push/key");
    if (!keyRes.ok) return alert(T("wx_alerts_unavail"));
    const { key } = await keyRes.json();
    const reg = await navigator.serviceWorker.ready;
    const sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64ToU8(key) });
    const r = await fetch("/api/push/subscribe", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ subscription: sub.toJSON(), station: code }),
    });
    if (!r.ok) return alert(T("wx_sub_fail"));
    if (btn) { btn.textContent = TF("wx_alerts_on", code); btn.classList.add("on"); btn.disabled = true; }
  } catch (e) {
    alert(T("wx_alerts_err") + (e && e.message ? e.message : e));
  }
}

// ===== Radar / nowcast (chuva sobre o aeródromo) =========================
const nowcastEl = document.querySelector("#wx-nowcast");

async function loadNowcast(icao) {
  nowcastEl.innerHTML = "";
  let res, d;
  try {
    res = await fetch(`/api/nowcast?icao=${encodeURIComponent(icao)}&lang=${window.APP_LANG || "pt"}`);
    d = await res.json().catch(() => ({}));
  } catch (_) { return; }
  if (!res.ok || !d.summary_pt) return;
  const ic = d.now_level >= 3 ? "⛈️" : d.now_level > 0 ? "🌧️" : "🌤️";
  nowcastEl.innerHTML = `<div class="nowcast"><span class="ic">${ic}</span><span><strong>${T("wx_radar")}</strong> ${d.summary_pt}</span></div>`;
}

// ===== TAF (previsão) =====================================================
const tafEl = document.querySelector("#wx-taf");

async function loadTaf(icao) {
  tafEl.innerHTML = "";
  let res, d;
  try {
    res = await fetch(`/api/taf?icao=${encodeURIComponent(icao)}&lang=${window.APP_LANG || "pt"}`);
    d = await res.json().catch(() => ({}));
  } catch (_) { return; }
  if (!res.ok || !d.periods || !d.periods.length) return; // sem TAF: não mostra nada
  renderTaf(d);
}

function renderTaf(d) {
  const temp = (d.temp_max_c != null || d.temp_min_c != null)
    ? ` · temp ${d.temp_max_c != null ? T("wx_temp_max") + " " + d.temp_max_c + "°" : ""}${d.temp_min_c != null ? " " + T("wx_temp_min") + " " + d.temp_min_c + "°" : ""}`
    : "";
  const periods = d.periods.map((p) => {
    const c = p.category_info || {};
    const known = p.category && p.category !== "UNKNOWN";
    const badge = p.prob != null
      ? `<span class="badge2" style="background:rgba(224,178,32,.18);color:#e0b020">PROB${p.prob}${p.tempo ? " TEMPO" : ""}</span>`
      : (p.type !== "base" && p.type !== "FM" ? `<span class="badge2" style="background:rgba(111,135,168,.18);color:var(--muted)">${p.type}</span>` : "");
    const catChip = known
      ? `<span class="badge2" style="background:${c.color}22;color:${c.color}">${c.emoji} ${c.label}</span>`
      : "";
    return `<div class="taf-p">
      <div class="taf-bar" style="background:${known ? c.color : "#1c3151"}"></div>
      <div>
        <div class="taf-when">${catChip}${badge}${p.type_label}${p.when ? " " + p.when : ""}</div>
        <div class="taf-desc">${p.summary_pt}</div>
      </div>
    </div>`;
  }).join("");
  // Janela de voo: faixa horária da categoria prevista (das próximas horas).
  let tl = "";
  const TL = d.timeline;
  if (TL && TL.hours && TL.hours.length) {
    let anyHist = false;
    const cells = TL.hours.map((h) => {
      const c = h.category_info || {};
      const risk = h.risk ? `<span title="${h.risk.prob ? h.risk.prob + "% " : ""}${TF("wx_risk", h.risk.category_info.label)}">⚠️</span>` : "";
      // Camada climatológica: barra inferior = % VFR histórico daquela hora.
      let hist = "";
      if (h.hist_vfr != null) {
        anyHist = true;
        hist = `<div class="tl-hist" title="${TF("wx_hist", h.hist_vfr, h.hist_n)}"><i style="width:${h.hist_vfr}%"></i></div>`;
      } else {
        hist = `<div class="tl-hist" title="${T("wx_hist_nodata")}"></div>`;
      }
      return `<div class="tl-cell"><div class="tl-bar" style="background:${c.color}">${risk}</div><div class="tl-hr">${h.label}</div>${hist}</div>`;
    }).join("");
    const legend = anyHist
      ? `<div class="tl-legend">${TF("wx_legend_hist", TL.clim_samples)}</div>`
      : `<div class="tl-legend">${T("wx_legend_nohist")}</div>`;
    tl = `<div class="tl-wrap"><div class="tl-sum">${TF("wx_flightwin", TL.summary_pt)}</div><div class="tl-strip">${cells}</div>${legend}</div>`;
  }

  tafEl.innerHTML =
    `<div class="taf">
      <div class="taf-h"><span class="t">${T("wx_taf_title")}</span>
        <span class="v">${TF("wx_taf_meta", d.station || "", d.issued_utc || "?", d.valid_from || "", d.valid_to || "", temp)}</span>
      </div>
      ${tl}
      ${periods}
      <div class="taf-raw">${d.raw || ""}</div>
    </div>`;
}

// ===== Climatologia: melhores horários para voar =========================
const clima = document.querySelector("#wx-clima");

function colorFor(pct) {
  if (pct == null) return "#16263f";
  if (pct >= 80) return "#2fbf71";
  if (pct >= 50) return "#9bc53d";
  if (pct >= 25) return "#e0b020";
  if (pct > 0) return "#e8590c";
  return "#e03131";
}
const hourLabel = (h) => String(h).padStart(2, "0") + "h";

async function loadClima(icao) {
  clima.innerHTML = "";
  let d;
  try {
    d = await (await fetch(`/api/metar/historico?icao=${encodeURIComponent(icao)}`)).json();
  } catch (_) { return; }
  if (!d || !d.samples) return; // sem histórico ainda → não mostra nada
  renderClima(d);
}

function renderClima(d) {
  const bars = d.hours.map((h) => {
    const pct = h.pct_vfr;
    const ht = pct == null ? 0 : Math.max(4, pct);
    const tip = h.total
      ? `${hourLabel(h.hour)} · ${pct}% VFR (${h.total} obs${h.avg_ceiling_ft ? ", " + TF("wx_ceil_avg", h.avg_ceiling_ft) : ""})`
      : `${hourLabel(h.hour)} · ${T("wx_nodata")}`;
    return `<div class="clima-bar ${h.total ? "" : "empty"}" title="${tip}">
      <div class="fill" style="height:${ht}%;background:${colorFor(pct)}"></div></div>`;
  }).join("");

  const axis = d.hours.map((h) => `<span>${h.hour % 6 === 0 ? hourLabel(h.hour) : ""}</span>`).join("");

  const best = (d.best_hours || []).filter((h) => h.pct_vfr != null && h.pct_vfr >= 50).slice(0, 3)
    .map((h) => `<span class="clima-pill good">🟢 ${hourLabel(h.hour)} · ${h.pct_vfr}% VFR</span>`).join("");
  const worst = (d.worst_hours || []).filter((h) => h.pct_vfr != null && h.pct_vfr < 50).slice(0, 1)
    .map((h) => `<span class="clima-pill bad">${TF("wx_avoid", hourLabel(h.hour), h.pct_vfr)}</span>`).join("");

  clima.innerHTML =
    `<div class="clima">
      <div class="clima-h">${T("wx_best_title")}</div>
      <div class="clima-sub">${TF("wx_best_sub", d.samples, d.tz_offset_h >= 0 ? "+" : "", d.tz_offset_h)}</div>
      <div class="clima-best">${best}${worst}</div>
      <div class="clima-chart">${bars}</div>
      <div class="clima-axis">${axis}</div>
      <div class="clima-leg"><i style="background:#2fbf71"></i>${T("wx_leg_vfr")} &nbsp; <i style="background:#e0b020"></i>${T("wx_leg_marginal")} &nbsp; <i style="background:#e8590c"></i>${T("wx_leg_ifr")} &nbsp; <i style="background:#16263f"></i>${T("wx_leg_nodata")}</div>
    </div>`;
}

buildAirportAC();

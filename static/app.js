"use strict";

// ===== Configuração de monetização (afiliados) ===========================
const AFFILIATES = [
  { t: T("aff_headsets_t"), d: T("aff_headsets_d"), url: "#" },
  { t: T("aff_courses_t"), d: T("aff_courses_d"), url: "#" },
  { t: T("aff_sims_t"), d: T("aff_sims_d"), url: "#" },
  { t: T("aff_books_t"), d: T("aff_books_d"), url: "#" },
];

// ===== Mapa (Leaflet, tema claro com oceanos azuis) ======================
const map = L.map("map", { worldCopyJump: true, zoomControl: true }).setView([5, -30], 2);
L.tileLayer("https://basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png", {
  attribution: "© OpenStreetMap, © CARTO",
  maxZoom: 19,
}).addTo(map);
let routeLayer = null;

// ===== Configuração ======================================================
// true: resultados acima do mapa (abaixo dos combos) · false: abaixo do mapa.
const RESULTADO_ACIMA_MAPA = true;

// ===== Utilidades ========================================================
const $ = (s) => document.querySelector(s);

// Container dos resultados conforme a flag (limpa o outro para não duplicar).
function outEl() {
  const top = $("#out-top"), bot = $("#out-bottom");
  if (RESULTADO_ACIMA_MAPA) { if (bot) bot.innerHTML = ""; return top || bot; }
  if (top) top.innerHTML = ""; return bot || top;
}
const norm = (s) =>
  s.toLowerCase().normalize("NFKD").replace(/[̀-ͯ]/g, "");

// ===== Estado ============================================================
let fromCode = "";
let toCode = "";
let selAircraft = "";  // vazio = nenhuma aeronave pré-selecionada
let AIRCRAFT = [];

// ===== Autocomplete de aeroportos (backend, 72k) =========================
function buildAirportAC(inputEl, acEl, setCode) {
  let list = [];
  let hl = -1;
  let timer = null;

  function close() { acEl.classList.remove("open"); acEl.innerHTML = ""; hl = -1; }
  function render() {
    acEl.innerHTML = list
      .map((a, i) =>
        `<div data-i="${i}" class="${i === hl ? "hl" : ""}">` +
        `<span class="code">${a.code}</span> · ${a.icao}` +
        `<div class="nm">${a.city ? a.city + " · " : ""}${a.name} (${a.country})</div></div>`)
      .join("");
    acEl.classList.toggle("open", list.length > 0);
    acScroll(acEl);
  }
  function pick(a) { inputEl.value = a.code; setCode(a.icao || a.iata || a.code); close(); compute(); }

  inputEl.addEventListener("input", () => {
    setCode("");
    const q = inputEl.value.trim();
    clearTimeout(timer);
    if (q.length < 2) return close();
    timer = setTimeout(async () => {
      try {
        const res = await fetch(`/api/airports/search?q=${encodeURIComponent(q)}`);
        list = (await res.json()).results || [];
        hl = -1; render();
      } catch (_) { close(); }
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
buildAirportAC($("#orig"), $("#acOrig"), (c) => (fromCode = c));
buildAirportAC($("#dest"), $("#acDest"), (c) => (toCode = c));

// ===== Inverter origem/destino ===========================================
$("#swap").onclick = () => {
  const o = $("#orig").value, d = $("#dest").value;
  $("#orig").value = d; $("#dest").value = o;
  [fromCode, toCode] = [toCode, fromCode];
  compute();
};

// Recalcula ao mudar a reserva de combustível.
const reserveSel = $("#reserve");
if (reserveSel) reserveSel.addEventListener("change", compute);

// ===== Autocomplete de aeronave (busca por marca/número) =================
function buildAircraftAC() {
  const inputEl = $("#aircraft-input");
  const acEl = $("#acAircraft");
  let list = [];
  let hl = -1;

  function close() { acEl.classList.remove("open"); acEl.innerHTML = ""; hl = -1; }
  function filter(q) {
    const n = norm(q);
    if (!n) return AIRCRAFT.slice(0, 12);
    return AIRCRAFT.filter((a) => norm(a.name).includes(n) || norm(a.category).includes(n) || norm(TCAT(a.category)).includes(n) || norm(a.family || "").includes(n)).slice(0, 12);
  }
  function render() {
    acEl.innerHTML = list
      .map((a, i) =>
        `<div data-i="${i}" class="${i === hl ? "hl" : ""}">` +
        `<span class="code">${a.name}</span>` +
        `<div class="cat">${TCAT(a.category)} · ${a.cruise_kt != null ? a.cruise_kt + " kt" : T("ac_speed_nd")} · ${a.range_nm != null ? T("ac_range") + " " + a.range_nm.toLocaleString(window.I18N_LOCALE) + " nm" : T("ac_range_nd")}</div></div>`)
      .join("");
    acEl.classList.toggle("open", list.length > 0);
    acScroll(acEl);
  }
  function pick(a) { selAircraft = a.key; inputEl.value = a.name; close(); renderAircraftCard(); compute(); }

  inputEl.addEventListener("input", () => { list = filter(inputEl.value); hl = -1; render(); });
  inputEl.addEventListener("focus", () => { list = filter(inputEl.value); hl = -1; render(); });
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

async function loadAircraft() {
  AIRCRAFT = (await (await fetch("/api/aircraft")).json()).aircraft;
  buildAircraftAC();
  const def = AIRCRAFT.find((a) => a.key === selAircraft);
  if (def) $("#aircraft-input").value = def.name;
  renderAircraftCard();
}

// ===== Ficha técnica da aeronave selecionada =============================
function fmtPrice(m) {
  if (m == null) return '<span style="color:var(--muted)">' + T("na") + '</span>';
  if (m < 1) return "US$ " + Math.round(m * 1000).toLocaleString(window.I18N_LOCALE) + " " + T("price_k");
  return "US$ " + m.toLocaleString(window.I18N_LOCALE, { maximumFractionDigits: 1 }) + " " + T("price_m");
}

function renderAircraftCard() {
  const el = $("#aircraft-card");
  if (!el) return;
  const a = AIRCRAFT.find((x) => x.key === selAircraft);
  if (!a) { el.innerHTML = ""; return; }
  const ND = '<span style="color:var(--muted)">' + T("na") + '</span>';
  const f = (n) => Number(n).toLocaleString(window.I18N_LOCALE);
  const frow = (k, v) => `<div class="ficha-row"><span class="fk">${k}</span><span class="fv">${v}</span></div>`;
  const dens = a.density_kg_l || 0.8;
  const cruise = a.cruise_kt == null ? ND : `${f(a.cruise_kt)} kt · ${f(Math.round(a.cruise_kt * 1.852))} km/h`;
  const burn = a.burn_kg_h == null ? ND : `${f(a.burn_kg_h)} kg/h · ${f(Math.round(a.burn_kg_h / dens))} L/h${a.fuel ? " · " + a.fuel : ""}`;
  const range = a.range_nm == null ? ND : `${f(a.range_nm)} nm · ${f(Math.round(a.range_nm * 1.852))} km`;
  el.innerHTML =
    `<div class="ficha-wrap"><div class="ficha">
      <div class="ficha-h"><span class="ficha-dot" style="background:var(--cyan)"></span>
        <div><div class="ficha-name">${a.name}</div><div class="ficha-cat">${TCAT(a.category)}</div></div></div>
      ${frow(T("f_cruise"), cruise)}
      ${frow(T("f_burn"), burn)}
      ${frow(T("f_range"), range)}
      ${frow(T("f_prod"), a.years || "—")}
      ${frow(T("f_price"), fmtPrice(a.price_usd_m))}
    </div></div>`;
}

// ===== Afiliados =========================================================
$("#aff-grid").innerHTML = AFFILIATES
  .map((a) => `<a class="aff-card" href="${a.url}" rel="sponsored nofollow" target="_blank"><span class="t">${a.t}</span><span class="d">${a.d}</span></a>`)
  .join("");

// ===== Cálculo da rota ===================================================
function emptyOut(msg) {
  if (routeLayer) { map.removeLayer(routeLayer); routeLayer = null; }
  outEl().innerHTML = `<div class="empty">${msg}</div>`;
}

async function compute() {
  if (!fromCode || !toCode) return emptyOut(T("empty_od"));
  if (fromCode === toCode) return emptyOut(T("same_od"));
  const hasAc = !!selAircraft;
  const baseQ = `origin=${encodeURIComponent(fromCode)}&dest=${encodeURIComponent(toCode)}`;
  const acQ = hasAc ? `&aircraft=${encodeURIComponent(selAircraft)}` : "";
  const reserveEl = $("#reserve");
  const reserve = reserveEl ? reserveEl.value : "0.85";
  try {
    // distância/proa sempre; tempo/combustível/escalas só com aeronave escolhida.
    const reqs = [fetch(`/api/route?${baseQ}${acQ}`)];
    if (hasAc) reqs.push(fetch(`/api/route/multi?${baseQ}${acQ}&reserve=${reserve}`));
    const arr = await Promise.all(reqs);
    if (!arr[0].ok) {
      const err = await arr[0].json().catch(() => ({}));
      if (window.track) window.track("route_failed", {
        origin: fromCode,
        dest: toCode,
        aircraft: hasAc ? selAircraft : "(nenhuma)",
        reason: "api_error",
        status: arr[0].status,
        detail: (err.detail || "").toString().slice(0, 100) || undefined,
      });
      return emptyOut(err.detail || T("route_fail"));
    }
    const d = await arr[0].json();
    const m = hasAc && arr[1] && arr[1].ok ? await arr[1].json() : null;
    render(d, m, hasAc);
    if (window.track) window.track("route_calculated", {
      origin: fromCode,
      dest: toCode,
      aircraft: hasAc ? selAircraft : "(nenhuma)",
      distance_nm: d.distance ? Math.round(d.distance.nm) : undefined,
      stops: m && m.reachable && !m.direct ? m.num_stops : 0,
      reachable: m ? !!m.reachable : true,
    });
  } catch (_) {
    emptyOut(T("conn_fail"));
    if (window.track) window.track("route_failed", {
      origin: fromCode,
      dest: toCode,
      aircraft: hasAc ? selAircraft : "(nenhuma)",
      reason: "connection",
    });
  }
}

const fmt = (n) => Number(n).toLocaleString(window.I18N_LOCALE);

function planHtml(m) {
  if (!m) return "";
  if (!m.reachable) {
    return `<div class="route-alert warn">⚠️<div><strong>${T("unreach_title")}</strong> ` +
      `${TF("unreach_body", fmt(m.direct_nm), m.aircraft.name, fmt(m.max_leg_nm))}</div></div>`;
  }
  if (m.direct || m.num_stops === 0) return "";
  const legs = m.legs.map((lg, i) =>
    `<div class="leg"><span class="n">${i + 1}</span>` +
    `<span class="rt">${lg.from.code} → ${lg.to.code}</span>` +
    `<span class="meta">${fmt(lg.nm)} nm · ${lg.hm != null ? lg.hm : T("nd")} · ${lg.fuel_kg != null ? fmt(lg.fuel_kg) + " kg" : T("nd")}</span></div>`).join("");
  return `<div class="route-alert info">🛬<div><strong>${TF("stops_title", m.num_stops)}</strong> ` +
    `${TF("stops_body", m.aircraft.name, fmt(m.max_leg_nm))}</div></div><div class="legs">${legs}</div>`;
}

function render(d, m, hasAc) {
  const hasStops = !!(hasAc && m && m.reachable && !m.direct && m.num_stops > 0);
  const br = String(d.bearing_deg).padStart(3, "0");
  // Distância/proa são geométricas (independem de aeronave). Tempo/combustível só com aeronave.
  const distNm = hasStops ? m.totals.nm : d.distance.nm;
  const distKm = hasStops ? m.totals.km : d.distance.km;
  const distLabel = hasStops ? T("r_dist_stops") : T("r_dist");
  const timeVal = hasStops ? m.totals.hm : d.time.block_hm;
  const timeCell = hasAc ? (timeVal != null ? timeVal : T("nd")) : "—";
  const fuelKg = hasStops ? m.totals.fuel_kg : (d.fuel ? d.fuel.total_kg : null);
  const fuelL = !hasStops && d.fuel ? d.fuel.total_l : null;
  const hint = (t) => `<div class="cell amber fuel"><div class="k">${T("r_aircraft")}</div><div class="v" style="font-size:14px;font-family:'Inter',sans-serif;font-weight:500;color:#c3d3e6">${t}</div></div>`;
  let fuelCell;
  if (!hasAc) fuelCell = hint(T("pick_ac"));
  else if (fuelKg == null) fuelCell = hint(TF("burn_na", d.aircraft.name));
  else fuelCell = `<div class="cell amber fuel"><div class="k">${TF("fuel_est", d.aircraft.name)}</div><div class="v">${fmt(fuelKg)}<span class="u">kg</span>${fuelL != null ? ` <span class="u" style="margin-left:10px">${fmt(fuelL)} L</span>` : ""}</div></div>`;
  // Velocidade de cruzeiro da aeronave (base do tempo e do combustível) + km/h.
  const cruiseKt = hasAc && d.aircraft && d.aircraft.cruise_kt != null ? d.aircraft.cruise_kt : null;
  const cruiseKmh = cruiseKt != null ? Math.round(cruiseKt * 1.852) : null;
  const cruiseVal = cruiseKt != null
    ? `${fmt(cruiseKt)}<span class="u">kt</span><span class="u" style="opacity:.75;margin-left:8px">${fmt(cruiseKmh)} km/h</span>`
    : `${hasAc ? "n/d" : "—"}<span class="u">kt</span>`;
  const cruiseCell = `<div class="cell"><div class="k">${T("r_cruise")}</div><div class="v">${cruiseVal}</div></div>`;

  outEl().innerHTML = `
    <div class="readouts">
      <div class="cell cyan"><div class="k">${distLabel}</div><div class="v">${fmt(distNm)}<span class="u">nm</span></div></div>
      <div class="cell"><div class="k">${distLabel}</div><div class="v">${fmt(distKm)}<span class="u">km</span></div></div>
      <div class="cell green"><div class="k">${T("r_block")}</div><div class="v">${timeCell}</div></div>
      ${cruiseCell}
      <div class="cell"><div class="k">${T("r_bearing")}</div><div class="v">${br}<span class="u">°</span></div></div>
      ${fuelCell}
    </div>` + planHtml(m);

  // ----- Mapa -----
  if (routeLayer) map.removeLayer(routeLayer);
  const unreachable = !!(m && !m.reachable);
  const coords = hasStops ? m.path : d.path;
  const layers = [];
  const line = L.polyline(coords, {
    color: unreachable ? "#e03131" : "#1c3faa", weight: 3, opacity: 0.95,
    dashArray: unreachable ? "6 7" : null,
  });
  layers.push(line);
  if (hasStops) {
    m.stops.forEach((s) =>
      layers.push(L.circleMarker([s.lat, s.lon], { radius: 5, weight: 2, color: "#f08c00", fillColor: "#ffd43b", fillOpacity: 1 })
        .bindTooltip(`⛽ ${s.code} · ${s.name}`)));
  }
  layers.push(L.circleMarker([d.origin.lat, d.origin.lon], { radius: 6, color: "#2b8a3e", fillColor: "#2b8a3e", fillOpacity: 1 }).bindTooltip(d.origin.code));
  layers.push(L.circleMarker([d.dest.lat, d.dest.lon], { radius: 6, color: "#e8590c", fillColor: "#e8590c", fillOpacity: 1 }).bindTooltip(d.dest.code));
  routeLayer = L.layerGroup(layers).addTo(map);
  map.fitBounds(line.getBounds(), { padding: [40, 40] });
}

// ===== Início ============================================================
loadAircraft();

const params = new URLSearchParams(location.search);
const pOrig = (params.get("origin") || "").toUpperCase();
const pDest = (params.get("dest") || "").toUpperCase();
if (pOrig && pDest) {
  $("#orig").value = pOrig; fromCode = pOrig;
  $("#dest").value = pDest; toCode = pDest;
  compute();
} else {
  emptyOut(T("empty_od"));
}

"use strict";

const AFFILIATES = [
  { t: T("aff_courses_t"), d: T("aff_courses_d"), url: "#" },
  { t: T("aff_sims_t"), d: T("aff_sims_d"), url: "#" },
  { t: T("aff_books_t"), d: T("aff_books_d"), url: "#" },
];

// Cores dos raios/colunas, uma por aeronave (até 4).
const COLORS = ["#1c7ed6", "#e8590c", "#2b8a3e", "#ae3ec9"];

const $ = (s) => document.querySelector(s);
const norm = (s) => s.toLowerCase().normalize("NFKD").replace(/[̀-ͯ]/g, "");

// Nome abreviado: remove o fabricante (ex.: "Airbus A320neo" -> "A320neo").
const MFG = ["Airbus", "Boeing", "Embraer", "Cessna", "Cirrus", "Diamond", "Mooney",
  "Piper", "Beechcraft", "Pilatus", "Daher", "De Havilland", "Bombardier",
  "Gulfstream", "Dassault"];
function shortName(name) {
  for (const m of MFG) if (name.startsWith(m + " ")) return name.slice(m.length + 1);
  return name;
}
function fmtPrice(m) {
  if (!m) return "—";
  if (m < 1) return "US$ " + Math.round(m * 1000).toLocaleString(window.I18N_LOCALE) + " " + T("price_k");
  return "US$ " + m.toLocaleString(window.I18N_LOCALE, { maximumFractionDigits: 1 }) + " " + T("price_m");
}
const rad = (d) => (d * Math.PI) / 180;
const deg = (r) => (r * 180) / Math.PI;

// ===== Mapa (claro, oceanos azuis) =======================================
const map = L.map("map", { worldCopyJump: true }).setView([-15, -50], 3);
L.tileLayer("https://basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png", {
  attribution: "© OpenStreetMap, © CARTO",
  maxZoom: 19,
}).addTo(map);
let drawLayer = null;

// ===== Estado ============================================================
let AIRCRAFT = [];
let selected = []; // até 4 objetos de aeronave
let airport = null; // {lat, lon, code, name}

// ===== Geodésia: ponto de destino e círculo de alcance ===================
function destPoint(lat, lon, brngDeg, distNm) {
  const R = 3440.065; // raio da Terra em nm
  const d = distNm / R;
  const p1 = rad(lat), l1 = rad(lon), t = rad(brngDeg);
  const p2 = Math.asin(Math.sin(p1) * Math.cos(d) + Math.cos(p1) * Math.sin(d) * Math.cos(t));
  const l2 = l1 + Math.atan2(Math.sin(t) * Math.sin(d) * Math.cos(p1), Math.cos(d) - Math.sin(p1) * Math.sin(p2));
  return [deg(p2), ((deg(l2) + 540) % 360) - 180];
}
function rangeRing(lat, lon, distNm) {
  const pts = [];
  for (let b = 0; b <= 360; b += 5) pts.push(destPoint(lat, lon, b, distNm));
  return pts;
}

// ===== Autocomplete de aeronave ==========================================
function buildAircraftAC() {
  const inputEl = $("#aircraft-input");
  const acEl = $("#acAircraft");
  let list = [];
  let hl = -1;
  function close() { acEl.classList.remove("open"); acEl.innerHTML = ""; hl = -1; }
  function filter(q) {
    const n = norm(q);
    const base = n ? AIRCRAFT.filter((a) => norm(a.name).includes(n) || norm(a.category).includes(n) || norm(TCAT(a.category)).includes(n) || norm(a.family || "").includes(n)) : AIRCRAFT;
    return base.filter((a) => !selected.some((s) => s.key === a.key)).slice(0, 12);
  }
  function render() {
    acEl.innerHTML = list
      .map((a, i) =>
        `<div data-i="${i}" class="${i === hl ? "hl" : ""}"><span class="code">${a.name}</span>` +
        `<div class="cat">${TCAT(a.category)} · ${a.cruise_kt != null ? a.cruise_kt + " kt" : T("ac_speed_nd")} · ${a.range_nm != null ? T("ac_range") + " " + a.range_nm.toLocaleString(window.I18N_LOCALE) + " nm" : T("ac_range_nd")}</div></div>`)
      .join("");
    acEl.classList.toggle("open", list.length > 0);
    acScroll(acEl);
  }
  function pick(a) {
    if (selected.length >= 4) { alert(T("max4")); return; }
    selected.push(a);
    if (window.track) window.track("aircraft_compare", { aircraft: a.key || a.name, count: selected.length });
    inputEl.value = "";
    close();
    renderChips();
    redraw();
  }
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

function renderChips() {
  $("#sel-chips").innerHTML = selected
    .map((a, i) =>
      `<span class="sel-chip" style="border-color:${COLORS[i]};color:${COLORS[i]}" title="${a.name}">` +
      `<span class="dot" style="background:${COLORS[i]}"></span>` +
      `<span class="nm2">${shortName(a.name)}</span>` +
      `<span class="x" data-k="${a.key}" title="${T("remove")}">×</span></span>`)
    .join("");
}
$("#sel-chips").addEventListener("click", (e) => {
  const x = e.target.closest(".x");
  if (!x) return;
  selected = selected.filter((a) => a.key !== x.dataset.k);
  renderChips();
  redraw();
});

// ===== Autocomplete de aeroporto =========================================
function buildAirportAC() {
  const inputEl = $("#airport");
  const acEl = $("#acAirport");
  let list = [];
  let hl = -1;
  let timer = null;
  function close() { acEl.classList.remove("open"); acEl.innerHTML = ""; hl = -1; }
  function render() {
    acEl.innerHTML = list
      .map((a, i) =>
        `<div data-i="${i}" class="${i === hl ? "hl" : ""}"><span class="code">${a.code}</span> · ${a.icao}` +
        `<div class="nm">${a.city ? a.city + " · " : ""}${a.name} (${a.country})</div></div>`)
      .join("");
    acEl.classList.toggle("open", list.length > 0);
    acScroll(acEl);
  }
  function pick(a) { inputEl.value = `${a.code} · ${a.city || a.name}`; airport = a; close(); redraw(); }
  inputEl.addEventListener("input", () => {
    airport = null;
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

// ===== Desenho + tabela ==================================================
function redraw() {
  if (drawLayer) { map.removeLayer(drawLayer); drawLayer = null; }
  const layers = [];

  if (airport) {
    const center = L.circleMarker([airport.lat, airport.lon], { radius: 6, color: "#212529", fillColor: "#212529", fillOpacity: 1 }).bindTooltip(airport.code, { permanent: false });
    // Desenha do MAIOR alcance (embaixo) para o MENOR (em cima): em áreas
    // sobrepostas, o hover mostra sempre o menor alcance que cobre o ponto;
    // ao sair dele, aparece o próximo maior. (No Leaflet, o último fica por cima.)
    selected
      .map((a, i) => ({ a, i }))
      .filter(({ a }) => a.range_nm != null) // sem alcance conhecido: sem círculo
      .sort((x, y) => y.a.range_nm - x.a.range_nm)
      .forEach(({ a, i }) => {
        const ring = rangeRing(airport.lat, airport.lon, a.range_nm);
        layers.push(
          L.polygon(ring, { color: COLORS[i], weight: 2, fillColor: COLORS[i], fillOpacity: 0.07 })
            .bindTooltip(`${a.name} · alcance ${a.range_nm.toLocaleString(window.I18N_LOCALE)} nm`, { sticky: true })
        );
      });
    layers.push(center); // marcador do aeroporto por cima de tudo
  }

  if (layers.length) {
    drawLayer = L.featureGroup(layers).addTo(map);
    map.fitBounds(drawLayer.getBounds(), { padding: [30, 30] });
  }

  renderTable();
}

function renderTable() {
  const out = $("#cmp-out");
  if (selected.length < 1) { out.innerHTML = `<div class="empty">${T("add_ac")}</div>`; return; }
  const head = selected
    .map((a, i) => `<th style="color:${COLORS[i]};padding:10px 8px;border-bottom:1px solid var(--line);text-align:left">${a.name}</th>`)
    .join("");
  const ND = '<span style="color:var(--muted)">' + T("na") + '</span>';
  const nd = (v, fn) => (v == null ? ND : fn(v));
  const rowsDef = [
    [T("f_category"), (a) => TCAT(a.category)],
    [T("f_cruise"), (a) => nd(a.cruise_kt, (v) => `${v} kt`)],
    [T("f_burn"), (a) => nd(a.burn_kg_h, (v) => `${v.toLocaleString(window.I18N_LOCALE)} kg/h`)],
    [T("f_range"), (a) => nd(a.range_nm, (v) => `${v.toLocaleString(window.I18N_LOCALE)} nm`)],
    [T("f_range"), (a) => nd(a.range_nm, (v) => `${Math.round(v * 1.852).toLocaleString(window.I18N_LOCALE)} km`)],
    [T("f_prod"), (a) => a.years || "—"],
    [T("f_price"), (a) => fmtPrice(a.price_usd_m)],
  ];
  const body = rowsDef
    .map(([label, fn]) =>
      `<tr><td style="color:var(--muted);font-family:'JetBrains Mono',monospace;font-size:11px;padding:9px 8px;border-bottom:1px solid var(--line)">${label}</td>` +
      selected.map((a) => `<td style="padding:9px 8px;border-bottom:1px solid var(--line);color:#c3d3e6">${fn(a)}</td>`).join("") +
      `</tr>`)
    .join("");
  // --- Ficha técnica: um cartão por aeronave ---
  const kmh = (kt) => Math.round(kt * 1.852).toLocaleString(window.I18N_LOCALE);
  const frow = (k, v) => `<div class="ficha-row"><span class="fk">${k}</span><span class="fv">${v}</span></div>`;
  const fichas = selected.map((a, i) => {
    const col = COLORS[i];
    const cruise = a.cruise_kt == null ? ND : `${a.cruise_kt} kt · ${kmh(a.cruise_kt)} km/h`;
    const range = a.range_nm == null ? ND : `${a.range_nm.toLocaleString(window.I18N_LOCALE)} nm · ${Math.round(a.range_nm * 1.852).toLocaleString(window.I18N_LOCALE)} km`;
    return `<div class="ficha" style="border-left-color:${col}">
      <div class="ficha-h"><span class="ficha-dot" style="background:${col}"></span>
        <div><div class="ficha-name">${a.name}</div><div class="ficha-cat">${TCAT(a.category)}</div></div></div>
      ${frow(T("f_cruise"), cruise)}
      ${frow(T("f_burn"), nd(a.burn_kg_h, (v) => `${v.toLocaleString(window.I18N_LOCALE)} kg/h · ${Math.round(v / (a.density_kg_l || 0.8)).toLocaleString(window.I18N_LOCALE)} L/h${a.fuel ? " · " + a.fuel : ""}`))}
      ${frow(T("f_range"), range)}
      ${frow(T("f_prod"), a.years || "—")}
      ${frow(T("f_price"), fmtPrice(a.price_usd_m))}
    </div>`;
  }).join("");

  out.innerHTML =
    `<h3 style="font-family:'Chakra Petch',sans-serif;font-size:15px;text-transform:uppercase;letter-spacing:.04em;color:var(--cyan);margin:18px 0 8px">${T("ficha_tecnica")}</h3>` +
    `<div class="ficha-wrap">${fichas}</div>` +
    `<h3 style="font-family:'Chakra Petch',sans-serif;font-size:15px;text-transform:uppercase;letter-spacing:.04em;color:var(--cyan);margin:20px 0 8px">${T("comparativo")}</h3>` +
    `<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:13.5px">` +
    `<thead><tr><th style="padding:10px 8px;border-bottom:1px solid var(--line)"></th>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}

// ===== Início ============================================================
renderAffiliates($("#aff-grid"), AFFILIATES);

(async () => {
  AIRCRAFT = (await (await fetch("/api/aircraft")).json()).aircraft;
  buildAircraftAC();
  buildAirportAC();
  // começa vazio (sem aeronaves pré-selecionadas)
  selected = [];
  renderChips();
  renderTable();
})();

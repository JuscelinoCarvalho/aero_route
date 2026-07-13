/* Aero Jussa · Radar Meteorológico
 * Replica as funcionalidades de um radar de precipitação (estilo IPMET):
 * imagem de radar (células de chuva), animação (loop passado + nowcast),
 * zoom/pan, tela cheia, troca de camada (radar/satélite) e legenda de intensidade.
 *
 * Fonte dos dados: RainViewer (API pública gratuita, cobertura global incluindo
 * o Brasil), servida em tiles compatíveis com Leaflet — o mesmo mapa usado na
 * calculadora. Os dados de radar são atualizados a cada ~10 min.
 */

// Afiliados (mesmo conteúdo do app.js; aqui app.js não é carregado para não
// conflitar com a inicialização do mapa do radar no mesmo elemento #map).
const AFFILIATES = [
  { t: T("aff_headsets_t"), d: T("aff_headsets_d"), url: "#" },
  { t: T("aff_courses_t"), d: T("aff_courses_d"), url: "#" },
  { t: T("aff_sims_t"), d: T("aff_sims_d"), url: "#" },
  { t: T("aff_books_t"), d: T("aff_books_d"), url: "#" },
];
const affGrid = document.getElementById("aff-grid");
if (affGrid) {
  affGrid.innerHTML = AFFILIATES.map(
    (a) =>
      `<a class="aff-card" href="${a.url}" rel="sponsored nofollow" target="_blank"><span class="t">${a.t}</span><span class="d">${a.d}</span></a>`
  ).join("");
}

const API = "https://api.rainviewer.com/public/weather-maps.json";
const SIZE = 512;       // tamanho do tile (256 ou 512)
const COLOR = 4;        // esquema de cores do radar (4 = clássico azul→vermelho)
const OPACITY = 0.78;
const SPEED_MS = 600;   // intervalo entre quadros na animação

// Centro inicial: interior de SP (cobertura clássica dos radares de Bauru/P. Prudente)
const MIN_ZOOM = 3;
const MAX_ZOOM = 18;      // aproximar até nível de bairro/rua
// Zoom nativo máximo de cada camada do RainViewer: acima dele o Leaflet ESTICA o
// último tile (maxNativeZoom) em vez de pedir um que o provedor não tem — senão o
// servidor devolve o tile-placeholder "Zoom Level Not Supported" (fundo cinza com
// texto), que é o que aparecia ao aproximar. Medido empiricamente: o mosaico de
// radar do RainViewer só existe até z=7 (z≥8 já vem placeholder); o satélite
// (infravermelho global) é ainda mais grosseiro.
const RADAR_NATIVE_ZOOM = 7;
const SAT_NATIVE_ZOOM = 6;
const map = L.map("map", {
  zoomControl: true,
  attributionControl: true,
  minZoom: MIN_ZOOM,
  maxZoom: MAX_ZOOM,
}).setView([-22.3, -49.0], 6);

L.tileLayer("https://basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png", {
  attribution:
    '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a> · radar © <a href="https://www.rainviewer.com/">RainViewer</a>',
  maxZoom: MAX_ZOOM,
  minZoom: MIN_ZOOM,
}).addTo(map);

// Estado da animação
let host = "";
let radarPast = [];
let radarNow = [];
let satFrames = [];
let animFrames = [];      // quadros ativos (depende do modo)
let frameLayers = [];     // L.tileLayer por índice (lazy)
let pos = 0;
let playing = false;
let timer = null;
let mode = "radar";       // "radar" | "satellite"

// Elementos da UI
const $ = (id) => document.getElementById(id);
const elPlay = $("r-play");
const elSlider = $("r-slider");
const elTime = $("r-time");
const elTag = $("r-tag");
const elStatus = $("r-status");

function buildUrl(frame) {
  if (mode === "satellite") {
    // satélite (infravermelho): esquema 0, cor sólida
    return `${host}${frame.path}/${SIZE}/{z}/{x}/{y}/0/0_0.png`;
  }
  // radar: esquema de cores + suavização + neve
  return `${host}${frame.path}/${SIZE}/{z}/{x}/{y}/${COLOR}/1_1.png`;
}

function clearLayers() {
  frameLayers.forEach((l) => l && map.removeLayer(l));
  frameLayers = [];
}

function ensureLayer(i) {
  if (!frameLayers[i]) {
    frameLayers[i] = L.tileLayer(buildUrl(animFrames[i]), {
      opacity: 0,
      tileSize: 256,
      zIndex: 300,
      maxZoom: MAX_ZOOM,
      // acima do zoom nativo o Leaflet amplia o último tile (mantém a camada visível
      // ao aproximar e evita o placeholder "ZOOM LEVEL NOT SUPPORTED"); o satélite é
      // bem mais grosseiro que o radar, então usa um nativo menor.
      maxNativeZoom: mode === "satellite" ? SAT_NATIVE_ZOOM : RADAR_NATIVE_ZOOM,
    });
    frameLayers[i].addTo(map);
  }
  return frameLayers[i];
}

function fmtTime(unix) {
  const d = new Date(unix * 1000);
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  const mo = String(d.getMonth() + 1).padStart(2, "0");
  return { hm: `${hh}:${mm}`, full: `${dd}/${mo} ${hh}:${mm}` };
}

function isForecast(i) {
  // No modo radar, quadros após o "passado" são previsão (nowcast)
  return mode === "radar" && i >= radarPast.length;
}

function updateInfo() {
  const f = animFrames[pos];
  if (!f) return;
  const t = fmtTime(f.time);
  elTime.textContent = t.full;
  elSlider.value = String(pos);
  if (mode === "satellite") {
    elTag.textContent = T("rdr_sat");
    elTag.className = "r-pill sat";
  } else if (isForecast(pos)) {
    elTag.textContent = T("rdr_nowcast");
    elTag.className = "r-pill fc";
  } else {
    elTag.textContent = T("rdr_observed");
    elTag.className = "r-pill obs";
  }
}

function showFrame(i) {
  if (!animFrames.length) return;
  pos = (i + animFrames.length) % animFrames.length;
  ensureLayer(pos);
  ensureLayer((pos + 1) % animFrames.length); // pré-carrega o próximo
  frameLayers.forEach((l, idx) => l && l.setOpacity(idx === pos ? OPACITY : 0));
  updateInfo();
}

function loadMode() {
  clearLayers();
  animFrames = mode === "satellite" ? satFrames : radarPast.concat(radarNow);
  if (!animFrames.length) {
    elStatus.textContent = T("rdr_nodata");
    return;
  }
  elStatus.textContent = "";
  frameLayers = new Array(animFrames.length).fill(null);
  elSlider.max = String(animFrames.length - 1);
  // começa no último quadro observado (mais recente real)
  pos = mode === "satellite" ? animFrames.length - 1 : Math.max(0, radarPast.length - 1);
  showFrame(pos);
}

function play() {
  if (playing || animFrames.length < 2) return;
  playing = true;
  elPlay.textContent = "❚❚";
  elPlay.setAttribute("aria-label", T("rdr_pause"));
  timer = setInterval(() => {
    let next = pos + 1;
    // pausa um instante no último quadro antes de reiniciar o loop
    if (next >= animFrames.length) next = 0;
    showFrame(next);
  }, SPEED_MS);
}

function pause() {
  playing = false;
  elPlay.textContent = "▶";
  elPlay.setAttribute("aria-label", T("rdr_play"));
  if (timer) clearInterval(timer);
  timer = null;
}

function togglePlay() {
  playing ? pause() : play();
}

function setMode(m) {
  if (m === mode) return;
  pause();
  mode = m;
  document.querySelectorAll(".r-mode").forEach((b) =>
    b.classList.toggle("on", b.dataset.mode === m)
  );
  $("legend-radar").style.display = m === "radar" ? "" : "none";
  $("legend-sat").style.display = m === "satellite" ? "" : "none";
  loadMode();
}

async function fetchData() {
  elStatus.textContent = T("rdr_loading");
  try {
    const r = await fetch(API, { cache: "no-store" });
    const data = await r.json();
    host = data.host;
    radarPast = (data.radar && data.radar.past) || [];
    radarNow = (data.radar && data.radar.nowcast) || [];
    satFrames = (data.satellite && data.satellite.infrared) || [];
    loadMode();
  } catch (e) {
    elStatus.textContent =
      T("rdr_load_fail");
  }
}

// ----- Controles -----
elPlay.addEventListener("click", togglePlay);
$("r-prev").addEventListener("click", () => {
  pause();
  showFrame(pos - 1);
});
$("r-next").addEventListener("click", () => {
  pause();
  showFrame(pos + 1);
});
elSlider.addEventListener("input", () => {
  pause();
  showFrame(parseInt(elSlider.value, 10));
});
document.querySelectorAll(".r-mode").forEach((b) =>
  b.addEventListener("click", () => setMode(b.dataset.mode))
);
$("r-refresh").addEventListener("click", () => {
  pause();
  fetchData();
});

// Minha localização
$("r-loc").addEventListener("click", () => {
  if (!navigator.geolocation) {
    elStatus.textContent = T("rdr_geo_unsupported");
    return;
  }
  elStatus.textContent = T("rdr_locating");
  navigator.geolocation.getCurrentPosition(
    (p) => {
      elStatus.textContent = "";
      const ll = [p.coords.latitude, p.coords.longitude];
      map.setView(ll, 8);
      L.circleMarker(ll, {
        radius: 6,
        color: "#1fd8e6",
        weight: 2,
        fillColor: "#1fd8e6",
        fillOpacity: 0.6,
      })
        .addTo(map)
        .bindPopup(T("rdr_here"))
        .openPopup();
    },
    () => {
      elStatus.textContent = T("rdr_loc_fail");
    }
  );
});

// Tela cheia
$("r-full").addEventListener("click", () => {
  const el = $("radar-panel");
  if (!document.fullscreenElement) {
    (el.requestFullscreen || el.webkitRequestFullscreen).call(el);
  } else {
    document.exitFullscreen();
  }
});
document.addEventListener("fullscreenchange", () =>
  setTimeout(() => map.invalidateSize(), 120)
);

// Teclado: espaço = play/pause, setas = passo a passo
document.addEventListener("keydown", (e) => {
  if (e.target.tagName === "INPUT") return;
  if (e.code === "Space") {
    e.preventDefault();
    togglePlay();
  } else if (e.code === "ArrowLeft") {
    pause();
    showFrame(pos - 1);
  } else if (e.code === "ArrowRight") {
    pause();
    showFrame(pos + 1);
  }
});

fetchData();

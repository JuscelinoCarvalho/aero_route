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
const affGrid = document.getElementById("aff-grid");
if (affGrid) {
  renderAffiliates(affGrid);
}

const API = "https://api.rainviewer.com/public/weather-maps.json";
const SIZE = 512;       // tamanho do tile (256 ou 512)
const COLOR = 4;        // esquema de cores do radar (4 = clássico azul→vermelho)
const OPACITY = 0.78;
const SPEED_MS = 600;   // intervalo entre quadros na animação

// Satélite: NASA GIBS (GOES-East, infravermelho Band 13 "Clean IR"). O RainViewer
// tirou o satélite do tier gratuito (retorna satellite.infrared: []), então usamos
// o GIBS — grátis, sem chave, cobertura global (inclui o Chile, onde o mosaico de
// radar do RainViewer é vazio). É um único quadro "mais recente" (time=default),
// não uma animação. Zoom nativo máximo do GOES IR: nível 6.
const GIBS_SAT =
  "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/" +
  "GOES-East_ABI_Band13_Clean_Infrared/default/default/" +
  "GoogleMapsCompatible_Level6/{z}/{y}/{x}.png";
// O satélite é filtrado (ver SatFiltered) p/ mostrar só os topos frios de
// convecção (tempestades/CB); a névoa cinza/branca some, então a opacidade
// 0.5 só suaviza os núcleos coloridos sobre o mapa de dia.
const SAT_OPACITY_ALONE = 0.5;   // satélite sozinho
const SAT_OPACITY_UNDER = 0.5;   // satélite por baixo do radar no modo "ambos"

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

// Basemap CLARO (CARTO Voyager, aparência de dia): o satélite entra por cima
// translúcido (ver SAT_OPACITY_ALONE), como um véu — cidades/estradas seguem
// visíveis e os topos de tempestade (coloridos pelo IR) aparecem sobre o mapa.
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
let animFrames = [];      // quadros ativos de radar (passado + nowcast)
let frameLayers = [];     // L.tileLayer por índice (lazy)
let satLayer = null;      // camada única de satélite (GIBS), criada sob demanda
let pos = 0;
let playing = false;
let timer = null;
let mode = "satellite";   // "radar" | "satellite" | "both" — satélite é o padrão

// Elementos da UI
const $ = (id) => document.getElementById(id);
const elPlay = $("r-play");
const elSlider = $("r-slider");
const elTime = $("r-time");
const elTag = $("r-tag");
const elStatus = $("r-status");

function buildUrl(frame) {
  // radar: esquema de cores + suavização + neve
  return `${host}${frame.path}/${SIZE}/{z}/{x}/{y}/${COLOR}/1_1.png`;
}

function clearLayers() {
  frameLayers.forEach((l) => l && map.removeLayer(l));
  frameLayers = [];
}

// ----- Camada de satélite (NASA GIBS), independente da animação de radar -----
// O Clean IR do GIBS coloriza os topos mais frios (convecção profunda / CB) e
// deixa o resto em grayscale. Filtramos cada tile num canvas: pixel COLORIDO
// (saturação alta = topo frio) fica; grayscale (céu limpo + nuvem rasa cinza/
// branca) vira transparente. Assim mostramos só as formações pesadas, sem a
// névoa cobrindo o mapa. GIBS envia CORS (Access-Control-Allow-Origin: *), então
// o canvas não "tainta" e o getImageData funciona.
const SAT_SAT_LO = 24;  // saturação: abaixo disso é grayscale -> transparente
const SAT_SAT_HI = 48;  // acima disso é topo frio pleno -> opaco (borda suave entre os dois)
const SatFiltered = L.TileLayer.extend({
  createTile(coords, done) {
    const tile = document.createElement("canvas");
    const size = this.getTileSize();
    tile.width = size.x;
    tile.height = size.y;
    const ctx = tile.getContext("2d");
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => {
      ctx.drawImage(img, 0, 0, size.x, size.y);
      try {
        const im = ctx.getImageData(0, 0, size.x, size.y);
        const d = im.data;
        for (let i = 0; i < d.length; i += 4) {
          const sat = Math.max(d[i], d[i + 1], d[i + 2]) - Math.min(d[i], d[i + 1], d[i + 2]);
          d[i + 3] =
            sat <= SAT_SAT_LO ? 0
            : sat >= SAT_SAT_HI ? 255
            : Math.round(((sat - SAT_SAT_LO) / (SAT_SAT_HI - SAT_SAT_LO)) * 255);
        }
        ctx.putImageData(im, 0, 0);
      } catch (e) {
        // Sem CORS o canvas fica "tainted": degrada para o tile cru (sem filtro).
      }
      done(null, tile);
    };
    img.onerror = (e) => done(e, tile);
    img.src = this.getTileUrl(coords);
    return tile;
  },
});

function ensureSat() {
  if (!satLayer) {
    satLayer = new SatFiltered(GIBS_SAT, {
      opacity: 0,
      tileSize: 256,
      zIndex: 250, // abaixo dos quadros de radar (zIndex 300)
      maxZoom: MAX_ZOOM,
      maxNativeZoom: SAT_NATIVE_ZOOM,
      attribution:
        'satélite © <a href="https://www.earthdata.nasa.gov/">NASA GIBS</a> · GOES-East',
    });
  }
  return satLayer;
}

function setSat(visible, opacity) {
  if (visible) {
    ensureSat();
    if (!map.hasLayer(satLayer)) satLayer.addTo(map);
    satLayer.setOpacity(opacity);
  } else if (satLayer && map.hasLayer(satLayer)) {
    map.removeLayer(satLayer);
  }
}

// Desliga os controles de animação quando não há quadros de radar (modo satélite).
function setControlsEnabled(on) {
  [elPlay, $("r-prev"), $("r-next"), elSlider].forEach((el) => {
    el.disabled = !on;
    el.style.opacity = on ? "" : "0.4";
    el.style.pointerEvents = on ? "" : "none";
  });
}

function ensureLayer(i) {
  if (!frameLayers[i]) {
    frameLayers[i] = L.tileLayer(buildUrl(animFrames[i]), {
      opacity: 0,
      tileSize: 256,
      zIndex: 300,
      maxZoom: MAX_ZOOM,
      // acima do zoom nativo o Leaflet amplia o último tile (mantém a camada visível
      // ao aproximar e evita o placeholder "ZOOM LEVEL NOT SUPPORTED").
      maxNativeZoom: RADAR_NATIVE_ZOOM,
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
  // Quadros de radar após o "passado" são previsão (nowcast); só há radar
  // nos modos "radar" e "both".
  return mode !== "satellite" && i >= radarPast.length;
}

function updateInfo() {
  const f = animFrames[pos];
  if (!f) return;
  const t = fmtTime(f.time);
  elTime.textContent = t.full;
  elSlider.value = String(pos);
  if (isForecast(pos)) {
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

  // Satélite (GIBS): visível sozinho ou por baixo do radar no modo "both".
  setSat(
    mode === "satellite" || mode === "both",
    mode === "both" ? SAT_OPACITY_UNDER : SAT_OPACITY_ALONE
  );

  if (mode === "satellite") {
    // Sem animação de radar: um único quadro de satélite (mais recente).
    animFrames = [];
    pause();
    setControlsEnabled(false);
    elTag.textContent = T("rdr_sat");
    elTag.className = "r-pill sat";
    elTime.textContent = "—";
    elStatus.textContent = T("rdr_sat_static");
    return;
  }

  // Radar e "both": anima os quadros de radar (por cima do satélite, se houver).
  setControlsEnabled(true);
  elStatus.textContent = "";
  animFrames = radarPast.concat(radarNow);
  if (!animFrames.length) {
    elStatus.textContent = T("rdr_nodata");
    return;
  }
  frameLayers = new Array(animFrames.length).fill(null);
  elSlider.max = String(animFrames.length - 1);
  // começa no último quadro observado (mais recente real)
  pos = Math.max(0, radarPast.length - 1);
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
  $("legend-radar").style.display = m === "radar" || m === "both" ? "" : "none";
  $("legend-sat").style.display = m === "satellite" || m === "both" ? "" : "none";
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
    // Recria a camada de satélite p/ buscar o quadro GIBS mais recente (time=default).
    if (satLayer) {
      map.removeLayer(satLayer);
      satLayer = null;
    }
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

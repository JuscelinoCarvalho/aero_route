/* Aero Jussa · Cartas Aeronáuticas (DECEA/AISWEB)
 * Busca um aeródromo do Brasil, lista as cartas (IAC etc.) e permite
 * visualizar, imprimir, baixar e compartilhar o PDF oficial.
 *
 * Os PDFs são servidos via proxy do próprio backend (/api/carta), mesma origem,
 * o que permite imprimir o iframe e esconde as credenciais do AISWEB.
 */

const $ = (s) => document.querySelector(s);

// Afiliados (mesmo conteúdo das outras páginas)
renderAffiliates($("#aff-grid"));

// Estado
let icao = "";
let current = null; // carta selecionada

// Países com alguma fonte de cartas (embutida BR/US ou deep-link eAIP no resto do mundo).
// Carregado do backend para manter o autocomplete em sincronia com o servidor.
let COVERED = { BR: 1, US: 1 };
fetch("/api/cartas/countries")
  .then((r) => r.json())
  .then((d) => {
    COVERED = {};
    [...(d.embed || []), ...(d.link || [])].forEach((c) => (COVERED[c] = 1));
  })
  .catch(() => {});

const status = $("#c-status");
function setStatus(msg, err) {
  status.textContent = msg;
  status.classList.toggle("err", !!err);
}

// ===== Autocomplete de aeródromo (Brasil + EUA) =====
(function buildAeroAC() {
  const inputEl = $("#aero");
  const acEl = $("#acAero");
  let list = [];
  let hl = -1;
  let timer = null;

  function close() {
    acEl.classList.remove("open");
    acEl.innerHTML = "";
    hl = -1;
  }
  function render() {
    acEl.innerHTML = list
      .map(
        (a, i) =>
          `<div data-i="${i}" class="${i === hl ? "hl" : ""}">` +
          `<span class="code">${a.icao}</span>${a.iata ? " · " + a.iata : ""}` +
          `<div class="nm">${a.city ? a.city + " · " : ""}${a.name}</div></div>`
      )
      .join("");
    acEl.classList.toggle("open", list.length > 0);
    acScroll(acEl); // mantém a opção destacada visível ao navegar com as setas
  }
  function pick(a) {
    inputEl.value = a.icao;
    icao = a.icao;
    close();
    loadCartas();
  }

  inputEl.addEventListener("input", () => {
    icao = "";
    const q = inputEl.value.trim();
    clearTimeout(timer);
    if (q.length < 2) return close();
    timer = setTimeout(async () => {
      try {
        const res = await fetch(`/api/airports/search?q=${encodeURIComponent(q)}`);
        const all = (await res.json()).results || [];
        // Filtra aeródromos com ICAO de 4 letras dos países cobertos
        // (Brasil, EUA e os demais países com eAIP oficial).
        list = all.filter((a) => COVERED[a.country] && a.icao && a.icao.length === 4).slice(0, 10);
        hl = -1;
        render();
      } catch (_) {
        close();
      }
    }, 160);
  });
  inputEl.addEventListener("keydown", (e) => {
    if (!acEl.classList.contains("open")) return;
    if (e.key === "ArrowDown") { hl = Math.min(hl + 1, list.length - 1); render(); e.preventDefault(); }
    else if (e.key === "ArrowUp") { hl = Math.max(hl - 1, 0); render(); e.preventDefault(); }
    else if (e.key === "Enter" && list[hl >= 0 ? hl : 0]) { pick(list[hl >= 0 ? hl : 0]); e.preventDefault(); }
    else if (e.key === "Escape") close();
  });
  acEl.addEventListener("mousedown", (e) => {
    const d = e.target.closest("[data-i]");
    if (d) pick(list[+d.dataset.i]);
  });
  inputEl.addEventListener("blur", () => setTimeout(close, 180));
})();

$("#tipo").addEventListener("change", () => {
  if (icao) loadCartas();
});

// ===== Carrega a lista de cartas =====
async function loadCartas() {
  if (!icao) return;
  const tipo = $("#tipo").value;
  $("#c-list").innerHTML = "";
  $("#c-viewer").style.display = "none";
  current = null;
  setStatus(TF("c_searching", icao), false);
  try {
    const res = await fetch(`/api/cartas?icao=${encodeURIComponent(icao)}&tipo=${encodeURIComponent(tipo)}`);
    const data = await res.json();
    if (!res.ok) {
      setStatus(data.detail || T("c_query_fail"), true);
      return;
    }
    const cartas = data.cartas || [];
    if (!cartas.length) {
      // Sem cartas embutidas: pode ser deep-link (eAIP) ou país sem fonte.
      if (data.link) {
        renderEaipLink(data.link);
        setStatus(TF("c_eaip_status", icao, data.link.provider), false);
      } else if (data.country && !COVERED[data.country]) {
        setStatus(TF("c_nosource", data.country), false);
      } else {
        setStatus(TF("c_none", icao), false);
      }
      return;
    }
    renderList(cartas);
    setStatus(TF("c_found", cartas.length, icao), false);
    openCarta(cartas[0]); // já abre a primeira
  } catch (_) {
    setStatus(T("c_conn_fail"), true);
  }
}

function renderList(cartas) {
  const list = $("#c-list");
  list.innerHTML = "";
  cartas.forEach((c) => {
    const meta = [c.amdt && `AMDT ${c.amdt}`, c.dt].filter(Boolean).join(" · ");
    const el = document.createElement("div");
    el.className = "c-card";
    el.innerHTML =
      `<div><div class="c-nm">${c.nome}</div>${meta ? `<div class="c-meta">${meta}</div>` : ""}</div>` +
      `<span class="c-type">${c.tipo || "—"}</span>`;
    el.addEventListener("click", () => openCarta(c, el));
    list.appendChild(el);
  });
}

// Card de deep-link para o eAIP oficial — não embutimos o PDF.
function renderEaipLink(link) {
  const list = $("#c-list");
  const el = document.createElement("div");
  el.className = "c-eaip";
  el.innerHTML =
    `<div class="c-eaip-h">${T("c_eaip_title")} · <b>${link.provider}</b></div>` +
    `<div class="c-eaip-b">${TF("c_eaip_body", link.provider)}</div>` +
    `<a class="c-eaip-btn" href="${link.url}" target="_blank" rel="nofollow noopener">${T("c_eaip_btn")}</a>`;
  list.appendChild(el);
}

// ===== Visualizar (PDF.js) / imprimir / baixar / compartilhar =====
function pdfUrl(c, dl) {
  const nome = encodeURIComponent(`${icao}-${c.nome}`.replace(/\s+/g, "_"));
  return `/api/carta?t=${encodeURIComponent(c.token)}&nome=${nome}${dl ? "&dl=1" : ""}`;
}

// PDF.js renderiza o PDF num <canvas> — funciona em todo celular sem app externo.
pdfjsLib.GlobalWorkerOptions.workerSrc = "/static/vendor/pdfjs/pdf.worker.min.js";
const DPR = Math.min(window.devicePixelRatio || 1, 2); // nitidez sem estourar memória

let pdfDoc = null; // documento PDF.js atual
let loadTask = null; // task de carregamento (p/ cancelar ao trocar de carta)
let pageNum = 1;
let pageCount = 1;
let zoom = 1; // 1 = ajustado à largura
let rendering = false;
let pendingRender = false; // pedido de re-render enquanto um render corre

function showLoad(on) {
  $("#c-load").hidden = !on;
}

async function renderPage() {
  if (!pdfDoc) return;
  if (rendering) { pendingRender = true; return; } // serializa: canvas não renderiza 2x
  rendering = true;
  try {
    const page = await pdfDoc.getPage(pageNum);
    const wrap = $("#c-view");
    const base = page.getViewport({ scale: 1 });
    const fit = (wrap.clientWidth || base.width) / base.width; // caber na largura
    const vp = page.getViewport({ scale: fit * zoom * DPR });
    const canvas = $("#c-canvas");
    const ctx = canvas.getContext("2d");
    canvas.width = Math.floor(vp.width);
    canvas.height = Math.floor(vp.height);
    canvas.style.width = Math.floor(vp.width / DPR) + "px";
    canvas.style.height = Math.floor(vp.height / DPR) + "px";
    canvas.style.transform = ""; // limpa feedback da pinça
    await page.render({ canvasContext: ctx, viewport: vp }).promise;
    $("#c-page").textContent = `${pageNum} / ${pageCount}`;
    $("#c-zoom").textContent = Math.round(zoom * 100) + "%";
  } finally {
    rendering = false;
    if (pendingRender) { pendingRender = false; renderPage(); }
  }
}

async function openCarta(c, el) {
  current = c;
  if (window.track) window.track("chart_open", { icao: icao, chart_type: c.tipo || undefined, chart_name: c.nome });
  document.querySelectorAll(".c-card").forEach((x) => x.classList.remove("on"));
  if (el) el.classList.add("on");
  $("#c-title").textContent = `${c.tipo ? c.tipo + " · " : ""}${c.nome}`;
  $("#c-viewer").style.display = "";
  $("#c-viewer").scrollIntoView({ behavior: "smooth", block: "nearest" });
  zoom = 1;
  pageNum = 1;
  showLoad(true);
  showStale(null);
  try {
    if (loadTask) { try { await loadTask.destroy(); } catch (_) {} }
    // Busca os bytes por fetch (em vez de dar a URL ao PDF.js) para poder ler o
    // header de defasagem: se a fonte caiu, o proxy serve a última cópia salva.
    const resp = await fetch(pdfUrl(c, false));
    if (!resp.ok) throw new Error("http " + resp.status);
    if (resp.headers.get("X-Chart-Stale") === "1") {
      showStale(resp.headers.get("X-Chart-Cached-At"));
    }
    const buf = await resp.arrayBuffer();
    loadTask = pdfjsLib.getDocument({ data: new Uint8Array(buf) });
    pdfDoc = await loadTask.promise;
    pageCount = pdfDoc.numPages;
    await renderPage();
  } catch (_) {
    setStatus(T("c_render_fail"), true);
  } finally {
    showLoad(false);
  }
}

// Aviso de defasagem: fonte oficial fora do ar, exibindo cópia local de {isoDate}.
function showStale(cachedAtIso) {
  let box = $("#c-stale");
  if (!cachedAtIso) { if (box) box.style.display = "none"; return; }
  if (!box) {
    box = document.createElement("div");
    box.id = "c-stale";
    box.className = "c-stale";
    const viewer = $("#c-viewer");
    viewer.parentNode.insertBefore(box, viewer);
  }
  const d = new Date(cachedAtIso);
  const dateStr = isNaN(d) ? cachedAtIso : d.toLocaleDateString();
  const days = isNaN(d) ? null : Math.floor((Date.now() - d.getTime()) / 86400000);
  const age = days == null ? "" : days <= 0 ? T("c_stale_age_today") : TF("c_stale_age_days", days);
  box.textContent = TF("c_stale", dateStr, age);
  box.style.display = "";
}

// Navegação de páginas
$("#c-prev").addEventListener("click", () => {
  if (pageNum > 1) { pageNum--; renderPage(); }
});
$("#c-next").addEventListener("click", () => {
  if (pageNum < pageCount) { pageNum++; renderPage(); }
});

// Zoom por botões
function setZoom(z) {
  zoom = Math.max(0.5, Math.min(z, 6));
  renderPage();
}
$("#c-zin").addEventListener("click", () => setZoom(zoom + 0.25));
$("#c-zout").addEventListener("click", () => setZoom(zoom - 0.25));
$("#c-zfit").addEventListener("click", () => setZoom(1));

// Pinça (dois dedos) = zoom; um dedo = pan (scroll nativo da área)
(function pinch() {
  const wrap = $("#c-view");
  const canvas = $("#c-canvas");
  let pinching = false;
  let startDist = 0;
  let startZoom = 1;
  let live = 1;
  const dist = (t) => Math.hypot(t[0].clientX - t[1].clientX, t[0].clientY - t[1].clientY);

  wrap.addEventListener("touchstart", (e) => {
    if (e.touches.length === 2) {
      pinching = true;
      startDist = dist(e.touches) || 1;
      startZoom = zoom;
      live = 1;
    }
  }, { passive: true });

  wrap.addEventListener("touchmove", (e) => {
    if (pinching && e.touches.length === 2) {
      e.preventDefault(); // impede o zoom da página; nós tratamos
      const target = Math.max(0.5, Math.min(startZoom * (dist(e.touches) / startDist), 6));
      live = target / zoom;
      canvas.style.transform = `scale(${live})`; // feedback imediato (baixa qualidade)
    }
  }, { passive: false });

  wrap.addEventListener("touchend", () => {
    if (pinching) {
      pinching = false;
      canvas.style.transform = "";
      setZoom(zoom * live); // re-renderiza nítido no novo zoom
      live = 1;
    }
  });
})();

// Duplo-toque/clique: alterna ajuste-à-largura <-> 2x
$("#c-view").addEventListener("dblclick", () => setZoom(zoom > 1 ? 1 : 2));

$("#c-print").addEventListener("click", () => {
  if (!current) return;
  const url = pdfUrl(current, false);
  // Imprime via iframe oculto (mesma origem) — no desktop abre o diálogo direto;
  // no celular cai para abrir a aba, onde o usuário imprime/compartilha.
  const f = document.createElement("iframe");
  f.style.cssText = "position:fixed;right:0;bottom:0;width:0;height:0;border:0";
  f.src = url;
  f.onload = () => {
    try { f.contentWindow.focus(); f.contentWindow.print(); }
    catch (_) { window.open(url, "_blank"); }
  };
  document.body.appendChild(f);
  setTimeout(() => f.remove(), 60000);
});

$("#c-down").addEventListener("click", () => {
  if (!current) return;
  const a = document.createElement("a");
  a.href = pdfUrl(current, true);
  a.download = `${icao}-${current.nome}.pdf`;
  document.body.appendChild(a);
  a.click();
  a.remove();
});

$("#c-open").addEventListener("click", () => {
  if (current) window.open(pdfUrl(current, false), "_blank");
});

$("#c-share").addEventListener("click", async () => {
  if (!current) return;
  const absUrl = location.origin + pdfUrl(current, false);
  const title = `Carta ${current.tipo} ${icao} · ${current.nome}`;
  // 1) tenta compartilhar o arquivo PDF (Web Share API nível 2)
  try {
    const resp = await fetch(pdfUrl(current, false));
    const blob = await resp.blob();
    const file = new File([blob], `${icao}-${current.nome}.pdf`, { type: "application/pdf" });
    if (navigator.canShare && navigator.canShare({ files: [file] })) {
      await navigator.share({ files: [file], title, text: title });
      return;
    }
  } catch (_) {}
  // 2) compartilha o link
  if (navigator.share) {
    try {
      await navigator.share({ title, text: title, url: absUrl });
      return;
    } catch (_) {}
  }
  // 3) fallback: copia o link
  try {
    await navigator.clipboard.writeText(absUrl);
    setStatus(T("c_copied"), false);
  } catch (_) {
    window.open(absUrl, "_blank");
  }
});

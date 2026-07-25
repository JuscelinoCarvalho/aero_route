"use strict";

// ===== Afiliados — curadoria de produtos (Mercado Livre) ===================
// Definido UMA vez e usado por app.js / comparar.js / cartas.js / radar.js /
// tempo.js. Cada link ja carrega a tag de afiliado (matt_tool=47871976); o
// clique e medido automaticamente pelo track.js (a.aff-card / rel="sponsored").
//
// Precos sao aproximados (coletados do ML) — o rotulo "~" e o proprio link
// cobrem variacao/promocao. Nomes de produto ficam neutros de idioma.
window.AFF_HEADSETS = [
  { t: "Headset Eletroleve E-10s",        price: "~R$ 1.460", img: "https://http2.mlstatic.com/D_NQ_NP_653796-MLB87507818141_072025-O.webp", url: "https://meli.la/2yJxo78" },
  { t: "Fone p/ Piloto — Aviação Geral",  price: "~R$ 576",   img: "https://http2.mlstatic.com/D_NQ_NP_926064-MLB105093981704_012026-O.webp", url: "https://meli.la/1AgYDq2" },
  { t: "Headset Supressor de Ruído",      price: "~R$ 3.800", img: "https://http2.mlstatic.com/D_NQ_NP_654070-MLB89889766729_082025-O.webp", url: "https://meli.la/2bcVonB" },
  { t: "Kore Aviation P1 PNR",            price: "~R$ 912",   img: "https://http2.mlstatic.com/D_NQ_NP_885989-CBT110808265425_042026-O.webp", url: "https://meli.la/12bVZEV" },
  { t: "Factem FATG4 — Made in France",   price: "~R$ 3.073", img: "https://http2.mlstatic.com/D_NQ_NP_701837-MLA107195862141_022026-O.webp", url: "https://meli.la/1jJtoGE" },
  { t: "Airvoice PNR c/ cancelamento",    price: "~R$ 1.502", img: "https://http2.mlstatic.com/D_NQ_NP_788188-CBT113500650417_062026-O.webp", url: "https://meli.la/24Xkbws" },
];

function _esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
  });
}

// Renderiza no grid: cards de produto (headsets) seguidos dos cards de
// categoria recebidos (cursos/simuladores/livros). Ambos usam class="aff-card"
// e rel="sponsored", entao o tracking existente cobre tudo.
window.renderAffiliates = function (grid, categories) {
  if (!grid) return;
  var products = window.AFF_HEADSETS.map(function (a) {
    return '<a class="aff-card aff-card--product" href="' + _esc(a.url) + '" rel="sponsored nofollow" target="_blank">' +
      '<img class="aff-thumb" src="' + _esc(a.img) + '" alt="" loading="lazy" width="72" height="72" ' +
      'onerror="this.style.display=\'none\'">' +
      '<span class="t">' + _esc(a.t) + '</span>' +
      '<span class="p">' + _esc(a.price) + '</span></a>';
  }).join("");
  var cats = (categories || []).map(function (a) {
    return '<a class="aff-card" href="' + _esc(a.url) + '" rel="sponsored nofollow" target="_blank">' +
      '<span class="t">' + _esc(a.t) + '</span>' +
      '<span class="d">' + _esc(a.d) + '</span></a>';
  }).join("");
  grid.innerHTML = products + cats;
};

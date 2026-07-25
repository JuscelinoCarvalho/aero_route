"use strict";

// ===== Afiliados — curadoria de produtos ===================================
// Definido UMA vez e renderizado em #aff-grid por todas as paginas via
// renderAffiliates(grid). Cada link ja carrega a tag de afiliado; o clique e
// medido automaticamente pelo track.js (a.aff-card / rel="sponsored").
//
// Dois tipos de card:
//  1) Produto (fisico, Mercado Livre): miniatura + titulo + ~preco.
//  2) Texto (curso/livro/etc): titulo + descricao, trilingue via T().
// Precos sao aproximados (coletados do ML) — o "~" e o link cobrem variacao.

// --- Produtos (Mercado Livre): headsets de aviacao ------------------------
window.AFF_HEADSETS = [
  { t: "Headset Eletroleve E-10s",        price: "~R$ 1.460", img: "https://http2.mlstatic.com/D_NQ_NP_653796-MLB87507818141_072025-O.webp", url: "https://meli.la/2yJxo78" },
  { t: "Fone p/ Piloto — Aviação Geral",  price: "~R$ 576",   img: "https://http2.mlstatic.com/D_NQ_NP_926064-MLB105093981704_012026-O.webp", url: "https://meli.la/1AgYDq2" },
  { t: "Headset Supressor de Ruído",      price: "~R$ 3.800", img: "https://http2.mlstatic.com/D_NQ_NP_654070-MLB89889766729_082025-O.webp", url: "https://meli.la/2bcVonB" },
  { t: "Kore Aviation P1 PNR",            price: "~R$ 912",   img: "https://http2.mlstatic.com/D_NQ_NP_885989-CBT110808265425_042026-O.webp", url: "https://meli.la/12bVZEV" },
  { t: "Factem FATG4 — Made in France",   price: "~R$ 3.073", img: "https://http2.mlstatic.com/D_NQ_NP_701837-MLA107195862141_022026-O.webp", url: "https://meli.la/1jJtoGE" },
  { t: "Airvoice PNR c/ cancelamento",    price: "~R$ 1.502", img: "https://http2.mlstatic.com/D_NQ_NP_788188-CBT113500650417_062026-O.webp", url: "https://meli.la/24Xkbws" },
];

// --- Cards de texto (trilingues) ------------------------------------------
// url:"#" = ainda sem link de afiliado (placeholder ate a curadoria); esses
// sao renderizados como card mudo (sem <a>), pra nao gerar clique morto.
function _affLinks() {
  var T = window.T || function (k) { return k; };
  return [
    { t: T("aff_courses_t"), d: T("aff_courses_d"), url: "https://go.hotmart.com/N106879522K?dp=1" },
    { t: T("aff_sims_t"),    d: T("aff_sims_d"),    url: "#" },
    { t: T("aff_books_t"),   d: T("aff_books_d"),   url: "#" },
  ];
}

function _esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
  });
}

window.renderAffiliates = function (grid) {
  if (!grid) return;
  var products = window.AFF_HEADSETS.map(function (a) {
    return '<a class="aff-card aff-card--product" href="' + _esc(a.url) + '" rel="sponsored nofollow" target="_blank">' +
      '<img class="aff-thumb" src="' + _esc(a.img) + '" alt="" loading="lazy" width="72" height="72" ' +
      'onerror="this.style.display=\'none\'">' +
      '<span class="t">' + _esc(a.t) + '</span>' +
      '<span class="p">' + _esc(a.price) + '</span></a>';
  }).join("");
  var links = _affLinks().map(function (a) {
    var body = '<span class="t">' + _esc(a.t) + '</span><span class="d">' + _esc(a.d) + '</span>';
    // placeholder sem link real → card mudo (nao dispara affiliate_click)
    if (!a.url || a.url === "#") return '<div class="aff-card aff-soon">' + body + '</div>';
    return '<a class="aff-card" href="' + _esc(a.url) + '" rel="sponsored nofollow" target="_blank">' + body + '</a>';
  }).join("");
  grid.innerHTML = products + links;
};

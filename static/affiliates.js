"use strict";

// ===== Afiliados — cards de tema + página dedicada por tema ================
// AFF_CATEGORIES define UMA vez os temas e seus produtos (anuncios).
//
//  - Na home (#aff-grid): renderAffiliates() desenha os 4 cards principais
//    (caixa limpa: titulo + descricao). Cada card LINKA para a pagina do tema
//    /static/afiliados.html?cat=<slug>&lang=<lang> — nao e um link de afiliado.
//  - Na pagina do tema (#aff-page): renderAffiliatePage(host, slug) desenha a
//    "prateleira" com os produtos daquele tema (miniatura + nome + ~preco +
//    link de afiliado real, rel="sponsored", medido pelo track.js).
//
// Titulo/descricao sao trilingues (chaves i18n via T()). Nomes de produto ficam
// neutros de idioma. Precos aproximados — o "~" e o link cobrem variacao.
window.AFF_CATEGORIES = [
  {
    slug: "fones",
    title: "aff_headsets_t",
    desc: "aff_headsets_d",
    items: [
      { t: "Headset Eletroleve E-10s",        price: "~R$ 1.460", img: "https://http2.mlstatic.com/D_NQ_NP_653796-MLB87507818141_072025-O.webp", url: "https://meli.la/2yJxo78" },
      { t: "Fone p/ Piloto — Aviação Geral",  price: "~R$ 576",   img: "https://http2.mlstatic.com/D_NQ_NP_926064-MLB105093981704_012026-O.webp", url: "https://meli.la/1AgYDq2" },
      { t: "Headset Supressor de Ruído",      price: "~R$ 3.800", img: "https://http2.mlstatic.com/D_NQ_NP_654070-MLB89889766729_082025-O.webp", url: "https://meli.la/2bcVonB" },
      { t: "Kore Aviation P1 PNR",            price: "~R$ 912",   img: "https://http2.mlstatic.com/D_NQ_NP_885989-CBT110808265425_042026-O.webp", url: "https://meli.la/12bVZEV" },
      { t: "Factem FATG4 — Made in France",   price: "~R$ 3.073", img: "https://http2.mlstatic.com/D_NQ_NP_701837-MLA107195862141_022026-O.webp", url: "https://meli.la/1jJtoGE" },
      { t: "Airvoice PNR c/ cancelamento",    price: "~R$ 1.502", img: "https://http2.mlstatic.com/D_NQ_NP_788188-CBT113500650417_062026-O.webp", url: "https://meli.la/24Xkbws" },
    ],
  },
  {
    slug: "cursos",
    title: "aff_courses_t",
    desc: "aff_courses_d",
    items: [
      { t: "Teórico Piloto Privado — Céu Livre", price: "~R$ 1.200", img: "https://hotmart.s3.amazonaws.com/product_pictures/0887f948-714c-459d-adeb-2d691e60e8d6/CURSOTERICOCOMPLETOPILOTOPRIVADOAVIOPILOTOAERODESPORTIVO.png", url: "https://go.hotmart.com/N106879522K?dp=1" },
    ],
  },
  { slug: "simuladores", title: "aff_sims_t",  desc: "aff_sims_d",  items: [] },   // sem link ainda
  { slug: "livros",      title: "aff_books_t", desc: "aff_books_d", items: [] },   // sem link ainda
];

function _esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
  });
}

function _catBySlug(slug) {
  var cats = window.AFF_CATEGORIES;
  for (var i = 0; i < cats.length; i++) if (cats[i].slug === slug) return cats[i];
  return null;
}

// Produto na prateleira: imagem grande (full-bleed) + nome + ~preco + link.
function _productTile(a) {
  return '<a class="aff-card aff-card--product" href="' + _esc(a.url) + '" rel="sponsored nofollow" target="_blank">' +
    '<img class="aff-thumb" src="' + _esc(a.img) + '" alt="" loading="lazy" ' +
    'onerror="this.style.visibility=\'hidden\'">' +
    '<span class="aff-prod-body">' +
      '<span class="t">' + _esc(a.t) + '</span>' +
      '<span class="p">' + _esc(a.price) + '</span>' +
    '</span></a>';
}

// Home: 4 cards principais (caixa limpa) que levam a pagina do tema.
window.renderAffiliates = function (grid) {
  if (!grid) return;
  var T = window.T || function (k) { return k; };
  var lang = window.APP_LANG || "pt";
  grid.innerHTML = window.AFF_CATEGORIES.map(function (cat) {
    var href = "/static/afiliados.html?cat=" + encodeURIComponent(cat.slug) +
      "&lang=" + encodeURIComponent(lang);
    return '<a class="aff-card" href="' + href + '">' +
      '<span class="t">' + _esc(T(cat.title)) + '</span>' +
      '<span class="d">' + _esc(T(cat.desc)) + '</span></a>';
  }).join("");
};

// Pagina do tema: cabecalho + prateleira (grid) de produtos daquele tema.
window.renderAffiliatePage = function (host, slug) {
  if (!host) return;
  var T = window.T || function (k) { return k; };
  var lang = window.APP_LANG || "pt";
  var back = lang === "pt" ? "/" : "/" + lang;
  var cat = _catBySlug(slug);
  var title = cat ? T(cat.title) : T("aff_soon");
  document.title = title + " · Aero Jussa";
  var body = cat && cat.items.length
    ? '<div class="aff-page-grid">' + cat.items.map(_productTile).join("") + '</div>'
    : '<div class="aff-cat-empty">' + _esc(T("aff_soon")) + '</div>';
  host.innerHTML =
    '<a class="aff-back" href="' + back + '">' + _esc(T("aff_back")) + '</a>' +
    '<h1 class="aff-page-h">' + _esc(title) + '</h1>' +
    (cat ? '<p class="aff-page-d">' + _esc(T(cat.desc)) + '</p>' : "") +
    '<div class="aff">' + body + '</div>';
};

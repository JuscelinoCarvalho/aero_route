"use strict";

// ===== Eventos GA4 =========================================================
// Helper global usado por app.js, tempo.js, cartas.js e comparar.js. É seguro
// mesmo quando o gtag foi bloqueado por adblock: nunca lança e nunca quebra a
// página. Carregado em TODA página (estáticas e geradas por SEO), depois do
// snippet inline do gtag, então window.gtag já existe aqui.
window.track = function (name, params) {
  try {
    if (typeof gtag === "function") gtag("event", name, params || {});
  } catch (e) { /* nunca quebrar a UX por causa de analytics */ }
};

// Clique em afiliado — delegado no documento, cobre qualquer .aff-card ou link
// marcado rel="sponsored" em todas as páginas de uma vez.
document.addEventListener("click", function (e) {
  var a = e.target.closest && e.target.closest('a.aff-card, a[rel~="sponsored"]');
  if (!a) return;
  window.track("affiliate_click", {
    affiliated_card: (a.textContent || "").trim().slice(0, 80),
    link_url: a.href,
  });
}, true);

// Instalação do PWA na tela inicial.
window.addEventListener("appinstalled", function () {
  window.track("pwa_install", {});
});

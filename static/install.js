/* "Baixar app" — botão de instalação do PWA, presente em todas as páginas.
 *
 * Android/desktop (Chrome/Edge): usa o evento beforeinstallprompt para abrir o
 * diálogo nativo de instalação. iOS/Safari (sem esse evento) e demais casos:
 * mostra as instruções de "Adicionar à Tela de Início". Se o site já estiver
 * rodando instalado (standalone), o botão não aparece.
 */
(function () {
  function isIOS() { return /iphone|ipad|ipod/i.test(navigator.userAgent || ""); }
  function standalone() {
    return window.matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
  }
  if (standalone()) return; // já instalado — nada a fazer

  var deferred = null;

  var btn = document.createElement("button");
  btn.type = "button";
  btn.id = "install-pill";
  btn.textContent = (window.T ? T("install_btn") : "📲 Baixar app");
  btn.style.cssText = [
    "position:fixed", "right:16px", "bottom:16px", "z-index:9999",
    "background:rgba(31,216,230,.14)", "border:1px solid #1fd8e6", "color:#1fd8e6",
    "font-family:'Chakra Petch',sans-serif", "font-weight:600", "letter-spacing:.04em",
    "font-size:13px", "padding:10px 16px", "border-radius:30px", "cursor:pointer",
    "box-shadow:0 8px 24px rgba(0,0,0,.45)"
  ].join(";");

  function mount() { if (!btn.parentNode && document.body) document.body.appendChild(btn); }
  if (document.body) mount(); else window.addEventListener("DOMContentLoaded", mount);

  window.addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault(); deferred = e; mount();
  });
  window.addEventListener("appinstalled", function () {
    deferred = null; if (btn.parentNode) btn.parentNode.removeChild(btn);
  });

  btn.addEventListener("click", function () {
    if (deferred) {
      deferred.prompt();
      deferred.userChoice.then(function () { deferred = null; });
      return;
    }
    if (isIOS()) {
      alert(T("install_ios"));
    } else {
      alert(T("install_other"));
    }
  });
})();

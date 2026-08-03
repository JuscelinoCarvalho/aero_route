/* Service worker do Aero Jussa — cache offline básico.
 *
 * Estratégia:
 *  - Navegações (páginas HTML): network-first, com fallback ao cache e, por fim,
 *    à página offline. Assim o conteúdo fica sempre atual quando há rede.
 *  - Estáticos same-origin (/static/...): stale-while-revalidate (rápido + atualiza).
 *  - /api/* e métodos não-GET: sempre rede, nunca cacheados.
 *  - Recursos cross-origin (fontes, Leaflet, tiles): deixados para o navegador.
 */
const VERSION = "v20";
const STATIC_CACHE = "jussa-static-" + VERSION;
const PAGES_CACHE = "jussa-pages-" + VERSION;

const PRECACHE = [
  "/static/style.css",
  "/static/app.js",
  "/static/i18n.js",
  "/static/track.js",
  "/static/affiliates.js",
  "/static/aerodromo.js",
  "/static/afiliados.html",
  "/static/offline.html",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "/static/vendor/pdfjs/pdf.min.js",
  "/static/vendor/pdfjs/pdf.worker.min.js",
  "/manifest.webmanifest",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) =>
      // addAll falha tudo se um item falhar; usamos add tolerante a falha.
      Promise.allSettled(PRECACHE.map((url) => cache.add(url)))
    ).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => k.startsWith("jussa-") && !k.endsWith(VERSION))
          .map((k) => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;

  const url = new URL(req.url);
  const sameOrigin = url.origin === self.location.origin;

  // Nunca interferir nas APIs.
  if (sameOrigin && url.pathname.startsWith("/api/")) return;

  // Navegações (HTML) e estáticos same-origin → NETWORK-FIRST: sempre busca a
  // versão mais recente quando há rede; cai para o cache só offline. Evita a app
  // instalada ficar "uma versão atrás" do site.
  if (req.mode === "navigate" || (sameOrigin && url.pathname.startsWith("/static/"))) {
    event.respondWith(
      fetch(req)
        .then((res) => {
          if (res && res.status === 200) {
            const copy = res.clone();
            caches.open(PAGES_CACHE).then((c) => c.put(req, copy)).catch(() => {});
          }
          return res;
        })
        .catch(() =>
          caches.match(req).then(
            (hit) => hit || (req.mode === "navigate" ? caches.match("/static/offline.html") : undefined)
          )
        )
    );
  }
});

// --- Web Push: alertas de tempo abaixo de VFR ---------------------------- #
self.addEventListener("push", (event) => {
  let d = {};
  try { d = event.data ? event.data.json() : {}; } catch (e) { d = { body: event.data && event.data.text() }; }
  const title = d.title || "Aero Jussa";
  event.waitUntil(
    self.registration.showNotification(title, {
      body: d.body || "",
      icon: "/static/icons/icon-192.png",
      badge: "/static/icons/favicon-32.png",
      tag: d.tag || "jussa-wx",
      data: { url: d.url || "/tempo" },
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || "/tempo";
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((cls) => {
      for (const c of cls) {
        if ("focus" in c) { c.navigate(url); return c.focus(); }
      }
      return self.clients.openWindow(url);
    })
  );
});

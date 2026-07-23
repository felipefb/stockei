/* Stockei — service worker: cache do shell estático; dados sempre online. */
const CACHE = "stockei-shell-v4";
const SHELL = [
  "/portal/index.html",
  "/portal/demo_portal.html",
  "/portal/dashboard.html",
  "/frontend/camera_styles.css",
  "/frontend/camera_streaming.js?v=6",
  "/portal/manifest.json",
  "/portal/icons/icon-192.png",
  "/portal/icons/icon-512.png",
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  const isShell = e.request.method === "GET" &&
    (url.pathname.startsWith("/portal/") || url.pathname.startsWith("/frontend/"));
  if (!isShell) return; // API sempre online

  // network-first: shell atualizado quando online, cache quando offline
  e.respondWith(
    fetch(e.request)
      .then((resp) => {
        const copy = resp.clone();
        caches.open(CACHE).then((c) => c.put(e.request, copy));
        return resp;
      })
      .catch(() => caches.match(e.request))
  );
});

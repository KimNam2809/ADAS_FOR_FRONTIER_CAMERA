const CACHE = "roadwatch-shell-v4";
const SHELL = ["/", "/app/", "/manifest.json", "/logo.png", "/landing/favicon.svg"];
self.addEventListener("install", (event) => event.waitUntil(
  caches.open(CACHE).then((cache) => cache.addAll(SHELL)).then(() => self.skipWaiting())
));
self.addEventListener("activate", (event) => event.waitUntil(Promise.all([
  self.clients.claim(),
  caches.keys().then((keys) => Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key)))),
])));
self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET" || event.request.url.includes("/api/") || event.request.url.includes("/ws")) return;
  event.respondWith(fetch(event.request).then((response) => {
    const copy = response.clone();
    caches.open(CACHE).then((cache) => cache.put(event.request, copy));
    return response;
  }).catch(() => caches.match(event.request)));
});

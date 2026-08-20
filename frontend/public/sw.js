const CACHE = 'argws-financial-static-v1'
const STATIC = ['/', '/icons/icon.svg', '/icons/icon-192.svg', '/icons/icon-512.svg']
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(STATIC)).then(() => self.skipWaiting()))
})
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()))
})
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url)
  if (event.request.method !== 'GET' || url.pathname.startsWith('/api/') || url.pathname.startsWith('/health')) return
  event.respondWith(fetch(event.request).then(response => {
    const clone = response.clone()
    caches.open(CACHE).then(cache => cache.put(event.request, clone))
    return response
  }).catch(() => caches.match(event.request).then(hit => hit || caches.match('/'))))
})

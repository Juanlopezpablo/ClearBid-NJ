/** Precarga únicamente archivos públicos de la compilación, nunca respuestas de la API. */
import { createHash } from 'node:crypto'
import { readdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import type { Plugin, ResolvedConfig } from 'vite'

export function offlineShell(): Plugin {
  let config: ResolvedConfig
  return {
    name: 'corestream-offline-shell', apply: 'build',
    configResolved(value) { config = value },
    async closeBundle() {
      const root = path.resolve(config.root, config.build.outDir)
      async function collect(dir: string): Promise<string[]> {
        const result: string[] = []
        for (const item of await readdir(dir, { withFileTypes: true })) {
          const file = path.join(dir, item.name)
          if (item.isDirectory()) result.push(...await collect(file))
          else if (/\.(html|js|css|woff2?|png|jpe?g|svg|webp|ico)$/.test(item.name) && item.name !== 'sw.js') result.push(file)
        }
        return result
      }
      const files = (await collect(root)).sort()
      const hash = createHash('sha256')
      for (const file of files) hash.update(await readFile(file))
      const urls = files.map(file => '/' + path.relative(root, file).split(path.sep).map(encodeURIComponent).join('/'))
      await writeFile(path.join(root, 'sw.js'), `
const CACHE = 'corestream-shell-${hash.digest('hex').slice(0, 16)}';
const FILES = ${JSON.stringify(urls)};
self.addEventListener('install', event => event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(FILES))));
self.addEventListener('activate', event => event.waitUntil((async () => {
  for (const key of await caches.keys()) if (key.startsWith('corestream-shell-') && key !== CACHE) await caches.delete(key);
  await self.clients.claim();
})()));
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET' || url.origin !== self.location.origin || url.pathname.startsWith('/api')) return;
  if (event.request.mode === 'navigate') {
    event.respondWith(fetch(event.request).catch(async () => (await caches.open(CACHE)).match('/index.html').then(response => response || new Response('Conéctate para preparar CoreStream sin conexión.', { status: 503 }))));
  } else if (FILES.includes(url.pathname)) {
    event.respondWith(caches.open(CACHE).then(async cache => (await cache.match(url.pathname)) || fetch(event.request)));
  }
});
`)
    },
  }
}

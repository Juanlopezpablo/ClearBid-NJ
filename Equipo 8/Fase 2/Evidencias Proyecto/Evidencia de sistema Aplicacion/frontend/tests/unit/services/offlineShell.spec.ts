import { afterEach, describe, expect, it, vi } from 'vitest'
import { mkdtemp, mkdir, readFile, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import path from 'node:path'
import vm from 'node:vm'
import { offlineShell } from '../../../offlineShell'

let root = ''
afterEach(async () => { if (root) await rm(root, { recursive: true, force: true }) })
describe('Aplicación estática sin conexión', () => {
  it('precarga la compilación, recupera el documento sin red y nunca intercepta la API', async () => {
    root = await mkdtemp(path.join(tmpdir(), 'corestream-shell-'))
    await mkdir(path.join(root, 'dist/assets'), { recursive: true })
    await writeFile(path.join(root, 'dist/index.html'), '<h1>CoreStream</h1>')
    await writeFile(path.join(root, 'dist/assets/app.js'), 'app')
    const plugin = offlineShell()
    await (plugin.configResolved as Function)({ root, build: { outDir: 'dist' } })
    await (plugin.closeBundle as Function)()
    const source = await readFile(path.join(root, 'dist/sw.js'), 'utf8')
    const listeners: Record<string, Function> = {}
    const cached = new Map<string, unknown>()
    const cache = { addAll: async (urls: string[]) => { urls.forEach(url => cached.set(url, { url, body: 'archivo' })) }, match: async (url: string) => cached.get(url) }
    const fetch = vi.fn().mockRejectedValue(new Error('Sin red'))
    vm.runInNewContext(source, { self: { location: { origin: 'https://corestream.test' }, addEventListener: (name: string, callback: Function) => { listeners[name] = callback }, clients: { claim: vi.fn() } }, caches: { open: async () => cache }, URL, Response: class {}, fetch })
    let installing!: Promise<void>
    listeners.install({ waitUntil: (work: Promise<void>) => { installing = work } })
    await installing
    expect([...cached.keys()].sort()).toEqual(['/assets/app.js', '/index.html'])
    let response: Promise<unknown> | undefined
    listeners.fetch({ request: { method: 'GET', url: 'https://corestream.test/', mode: 'navigate' }, respondWith: (work: Promise<unknown>) => { response = work } })
    expect(await response).toEqual({ url: '/index.html', body: 'archivo' })
    const intercept = vi.fn()
    for (const method of ['GET', 'POST']) listeners.fetch({ request: { method, url: 'https://corestream.test/api/tickets/', mode: 'cors' }, respondWith: intercept })
    expect(intercept).not.toHaveBeenCalled()
  })
})

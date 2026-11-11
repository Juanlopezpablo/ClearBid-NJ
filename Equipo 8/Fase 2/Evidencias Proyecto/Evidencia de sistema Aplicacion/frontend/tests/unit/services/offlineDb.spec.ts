import 'fake-indexeddb/auto'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as storage from '@/services/offlineDb'

beforeEach(async () => {
  localStorage.clear()
  for (const id of ['a', 'b']) {
    await storage.clearSnapshots(id)
    for (const item of await storage.pendingComments(id)) await storage.discardComment(id, item.id)
  }
  await storage.forgetProfile()
})
const ticket = { id: 'ticket', title: 'Revisión', description: 'Detalle', status: 'TODO', priority: 'HIGH' }
const pending = (owner = 'a') => ({ id: crypto.randomUUID(), owner, ticketId: 'ticket', title: 'Revisión', body: 'Mi comentario', createdAt: Date.now(), error: '' })

describe('Almacenamiento offline con IndexedDB', () => {
  it('persiste comentarios al volver a importar y separa cuentas', async () => {
    const item = pending()
    await storage.enqueueComment(item)
    vi.resetModules()
    const reopened = await import('@/services/offlineDb')
    expect(await reopened.pendingComments('a')).toEqual([item])
    expect(await reopened.pendingComments('b')).toEqual([])
    await reopened.discardComment('b', item.id)
    expect((await reopened.pendingComments('a')).length).toBe(1)
  })
  it('elimina copias sin perder comentarios pendientes', async () => {
    await storage.cacheTickets('a', [ticket])
    await storage.enqueueComment(pending())
    await storage.clearSnapshots('a')
    expect(await storage.savedTickets('a')).toEqual([])
    expect((await storage.pendingComments('a')).length).toBe(1)
  })
  it('caduca las copias a los siete días y mantiene los pendientes', async () => {
    await storage.cacheTickets('a', [ticket])
    await storage.enqueueComment(pending())
    const now = Date.now()
    const spy = vi.spyOn(Date, 'now').mockReturnValue(now + storage.SNAPSHOT_TTL + 100)
    expect(await storage.savedTickets('a')).toEqual([])
    expect((await storage.pendingComments('a')).length).toBe(1)
    spy.mockRestore()
  })
  it('guarda solo los campos de consulta y limita a 200 copias', async () => {
    await storage.cacheTickets('a', Array.from({ length: 205 }, (_, index) => ({ ...ticket, id: String(index), secret: 'no-guardar' })))
    const copies = await storage.savedTickets('a')
    expect(copies.length).toBe(200)
    expect(JSON.stringify(copies)).not.toContain('no-guardar')
    expect(await storage.savedTickets('b')).toEqual([])
  })
  it('no expone la identidad offline después de cerrar sesión', async () => {
    await storage.saveProfile({ id: 'a', name: 'Ana', savedAt: Date.now() })
    expect((await storage.lastProfile())?.id).toBe('a')
    localStorage.setItem('corestream-offline-logout', '1')
    expect(await storage.lastProfile()).toBeNull()
  })
})

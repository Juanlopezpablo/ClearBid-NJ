import { beforeEach, describe, expect, it, vi } from 'vitest'
const mocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), owner: 'a' as string | null, pending: vi.fn(), discard: vi.fn(), error: vi.fn() }))
vi.mock('@/services/api', () => ({ apiClient: { get: mocks.get, post: mocks.post } }))
vi.mock('@/services/offlineDb', () => ({ getOfflineOwner: () => mocks.owner, pendingComments: mocks.pending, discardComment: mocks.discard, pendingError: mocks.error }))
import { syncComments } from '@/services/offlineSync'
const item = { id: 'operation', owner: 'a', ticketId: 'ticket', body: 'Comentario', error: '' }
beforeEach(() => {
  vi.resetAllMocks(); mocks.owner = 'a'
  vi.spyOn(navigator, 'onLine', 'get').mockReturnValue(true)
  mocks.get.mockResolvedValue({ data: { id: 'a' } })
  mocks.pending.mockResolvedValue([item])
  mocks.post.mockResolvedValue({ data: { id: 'published' } })
})
describe('Sincronización diferida', () => {
  it('envía identidad e ID estables y retira solo el pendiente confirmado', async () => {
    await Promise.all([syncComments(), syncComments()])
    expect(mocks.post).toHaveBeenCalledTimes(1)
    expect(mocks.post).toHaveBeenCalledWith('/tickets/ticket/comments/offline', { client_id: 'operation', author_id: 'a', body: 'Comentario' })
    expect(mocks.discard).toHaveBeenCalledWith('a', 'operation')
  })
  it('conserva el pendiente si se pierde la respuesta', async () => {
    mocks.post.mockRejectedValue(new Error('Sin red'))
    await syncComments()
    expect(mocks.discard).not.toHaveBeenCalled()
    expect(mocks.error).not.toHaveBeenCalled()
  })
  it('detiene el envío con sesión vencida', async () => {
    mocks.get.mockRejectedValue({ response: { status: 401 } })
    await syncComments()
    expect(mocks.post).not.toHaveBeenCalled()
  })
  it('no transmite comentarios desde otra cuenta', async () => {
    mocks.get.mockResolvedValue({ data: { id: 'b' } })
    await syncComments()
    expect(mocks.post).not.toHaveBeenCalled()
  })
  it('retiene un conflicto visible sin borrarlo ni reintentar automáticamente', async () => {
    mocks.post.mockRejectedValue({ response: { status: 404, data: { detail: 'Ticket no encontrado' } } })
    await syncComments()
    expect(mocks.error).toHaveBeenCalledWith(item, 'Ticket no encontrado')
    expect(mocks.discard).not.toHaveBeenCalled()
    mocks.pending.mockResolvedValue([{ ...item, error: 'Ticket no encontrado' }])
    mocks.post.mockClear()
    await syncComments()
    expect(mocks.post).not.toHaveBeenCalled()
  })
})

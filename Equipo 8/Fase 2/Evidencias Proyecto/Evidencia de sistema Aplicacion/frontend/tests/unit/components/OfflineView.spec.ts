import { mount, flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
const mocks = vi.hoisted(() => ({
  auth: { user: null as null | { id: string; fullName: string }, isAuthenticated: false },
  profile: vi.fn(), tickets: vi.fn(), pending: vi.fn(), enqueue: vi.fn(), discard: vi.fn(), clear: vi.fn(), sync: vi.fn(), confirm: vi.fn(),
}))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => mocks.auth }))
vi.mock('@/stores/dialog', () => ({ useDialogStore: () => ({ confirm: mocks.confirm }) }))
vi.mock('@/services/offlineDb', () => ({ lastProfile: mocks.profile, savedTickets: mocks.tickets, pendingComments: mocks.pending, enqueueComment: mocks.enqueue, discardComment: mocks.discard, clearSnapshots: mocks.clear, pendingError: vi.fn() }))
vi.mock('@/services/offlineSync', () => ({ syncComments: mocks.sync, syncingOffline: false, offlineSyncMessage: '' }))
import OfflineView from '@/views/OfflineView.vue'
const render = () => mount(OfflineView, { global: { stubs: { RouterLink: true, AppHeader: true } } })
beforeEach(() => {
  vi.resetAllMocks(); mocks.auth.user = null; mocks.auth.isAuthenticated = false
  vi.spyOn(navigator, 'onLine', 'get').mockReturnValue(false)
  mocks.profile.mockResolvedValue({ id: 'a', name: 'Ana', savedAt: Date.now() })
  mocks.tickets.mockResolvedValue([{ id: 'ticket', title: 'Ticket guardado', description: 'Detalle disponible offline', status: 'TODO', priority: 'HIGH', savedAt: Date.now() }])
  mocks.pending.mockResolvedValue([])
})
describe('Pantalla de consulta offline', () => {
  it('consulta copias sin fingir una sesión y guarda pendientes sin enviarlos', async () => {
    const wrapper = render(); await flushPromises()
    expect(wrapper.text()).toContain('Detalle disponible offline')
    expect(wrapper.text()).toContain('no inicia una sesión')
    await wrapper.get('textarea').setValue('Trabajo realizado sin internet')
    await wrapper.get('form').trigger('submit'); await flushPromises()
    expect(mocks.enqueue).toHaveBeenCalledWith(expect.objectContaining({ owner: 'a', ticketId: 'ticket', body: 'Trabajo realizado sin internet' }))
    expect(mocks.sync).not.toHaveBeenCalled()
    expect(wrapper.get('textarea').element.value).toBe('')
    wrapper.unmount()
  })
  it('conserva el texto si el navegador no puede guardarlo', async () => {
    mocks.enqueue.mockRejectedValue(new Error('Sin espacio'))
    const wrapper = render(); await flushPromises()
    await wrapper.get('textarea').setValue('No perder este comentario')
    await wrapper.get('form').trigger('submit'); await flushPromises()
    expect(wrapper.get('textarea').element.value).toBe('No perder este comentario')
    expect(wrapper.get('[role="alert"]').text()).toContain('Sin espacio')
    wrapper.unmount()
  })
  it('utiliza la cuenta autenticada y no la identidad local anterior', async () => {
    mocks.auth.user = { id: 'b', fullName: 'Bruno' }; mocks.auth.isAuthenticated = true
    const wrapper = render(); await flushPromises()
    expect(mocks.pending).toHaveBeenCalledWith('b')
    expect(wrapper.text()).toContain('Bruno')
    expect(mocks.profile).not.toHaveBeenCalled()
    wrapper.unmount()
  })
})

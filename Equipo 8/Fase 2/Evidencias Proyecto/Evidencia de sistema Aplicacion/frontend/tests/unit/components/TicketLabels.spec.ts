import { mount, flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import TicketLabels from '@/components/shared/TicketLabels.vue'

const mocks = vi.hoisted(() => ({ get: vi.fn(), put: vi.fn(), auth: { userRole: 'DEVELOPER', user: { id: 'yo' } } }))
vi.mock('@/services/api', () => ({ apiClient: mocks }))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => mocks.auth }))

describe('Etiquetas de tickets', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mocks.auth.userRole = 'DEVELOPER'
    mocks.get.mockResolvedValue({ data: { labels: ['web'], assignee_id: 'yo' } })
    mocks.put.mockResolvedValue({ data: { labels: ['web', 'revisión'] } })
  })
  it('permite guardar y quitar etiquetas de un ticket asignado', async () => {
    const wrapper = mount(TicketLabels, { props: { ticketId: 'uno' } })
    await flushPromises()
    await wrapper.get('input').setValue('web, revisión')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(mocks.put).toHaveBeenCalledWith('/tickets/uno', { labels: ['web', 'revisión'] })
    expect(wrapper.text()).toContain('Etiquetas guardadas')
    await wrapper.get('input').setValue('')
    await wrapper.get('form').trigger('submit')
    expect(mocks.put).toHaveBeenLastCalledWith('/tickets/uno', { labels: [] })
  })
  it('muestra solo lectura para un ticket ajeno', async () => {
    mocks.get.mockResolvedValue({ data: { labels: ['web'], assignee_id: 'otra' } })
    const wrapper = mount(TicketLabels, { props: { ticketId: 'uno' } })
    await flushPromises()
    expect(wrapper.text()).toContain('web')
    expect(wrapper.find('form').exists()).toBe(false)
  })
  it('descarta una carga atrasada al cambiar de ticket', async () => {
    let finish!: (value: unknown) => void
    mocks.get.mockImplementationOnce(() => new Promise(resolve => { finish = resolve }))
    const wrapper = mount(TicketLabels, { props: { ticketId: 'uno' } })
    await wrapper.setProps({ ticketId: 'dos' })
    await flushPromises()
    finish({ data: { labels: ['antigua'], assignee_id: 'yo' } })
    await flushPromises()
    expect(wrapper.text()).not.toContain('antigua')
  })
})

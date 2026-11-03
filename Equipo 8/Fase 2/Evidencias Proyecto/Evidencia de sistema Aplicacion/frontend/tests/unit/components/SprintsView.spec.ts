import { mount, flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import SprintsView from '@/views/SprintsView.vue'

const mocks = vi.hoisted(() => ({
  auth: { userRole: 'ADMIN', user: { id: 'yo' } }, confirm: vi.fn(),
  list: vi.fn(), get: vi.fn(), create: vi.fn(), edit: vi.fn(), start: vi.fn(), finish: vi.fn(), tickets: vi.fn(), add: vi.fn(), remove: vi.fn(),
  clientGet: vi.fn(),
}))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => mocks.auth }))
vi.mock('@/stores/dialog', () => ({ useDialogStore: () => ({ confirm: mocks.confirm }) }))
vi.mock('@/services/api', () => ({ apiClient: { get: mocks.clientGet }, api: { tickets: { getById: vi.fn() } } }))
vi.mock('@/services/sprints', () => ({ sprintApi: mocks }))
const sprint = { id: 'sprint', application_id: 'app', name: 'Iteración 1', goal: 'Entregar acceso', start_date: '2026-11-03', end_date: '2026-11-17', status: 'PLANNED', total_tickets: 1, completed_tickets: 0, progress: 0, released_tickets: 0 }
const render = () => mount(SprintsView, { global: { stubs: { AppHeader: true, RouterLink: true, TicketPanel: true } } })
const button = (wrapper: ReturnType<typeof mount>, name: string) => wrapper.findAll('button').find(item => item.text() === name)

describe('Planificación de sprints', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mocks.auth.userRole = 'ADMIN'
    mocks.clientGet.mockResolvedValue({ data: [{ id: 'app', name: 'Aplicación' }] })
    mocks.list.mockResolvedValue({ items: [sprint], total: 1, skip: 0, limit: 25 })
    mocks.get.mockResolvedValue(sprint)
    mocks.tickets.mockImplementation((_id, available) => Promise.resolve({ items: available ? [{ id: 'ticket', title: 'Trabajo asignado', epic_title: 'Épica', status: 'TODO', assignee: { full_name: 'María' } }] : [], total: available ? 1 : 0, skip: 0, limit: 25 }))
    mocks.confirm.mockResolvedValue(true)
  })
  it('permite agregar al sprint trabajo que ya tiene responsable', async () => {
    const wrapper = render()
    await flushPromises()
    expect(wrapper.text()).toContain('María')
    await button(wrapper, 'Agregar')!.trigger('click')
    await flushPromises()
    expect(mocks.add).toHaveBeenCalledWith('sprint', 'ticket')
    expect(wrapper.text()).toContain('Ticket agregado al sprint')
    wrapper.unmount()
  })
  it('ofrece consulta sin acciones de planificación para developer', async () => {
    mocks.auth.userRole = 'DEVELOPER'
    const wrapper = render()
    await flushPromises()
    expect(wrapper.text()).toContain('Iteración 1')
    expect(button(wrapper, 'Nuevo sprint')).toBeUndefined()
    expect(button(wrapper, 'Iniciar sprint')).toBeUndefined()
    expect(button(wrapper, 'Agregar')).toBeUndefined()
    expect(mocks.tickets).toHaveBeenCalledTimes(1)
    wrapper.unmount()
  })
  it('explica el cierre y respeta la cancelación antes de modificarlo', async () => {
    mocks.get.mockResolvedValue({ ...sprint, status: 'ACTIVE' })
    mocks.confirm.mockResolvedValue(false)
    const wrapper = render()
    await flushPromises()
    await button(wrapper, 'Finalizar sprint')!.trigger('click')
    await flushPromises()
    expect(mocks.confirm.mock.calls[0][0]).toContain('conservando su responsable y estado')
    expect(mocks.finish).not.toHaveBeenCalled()
    wrapper.unmount()
  })
  it('muestra el conflicto si otro sprint ya está activo', async () => {
    mocks.start.mockRejectedValue({ response: { data: { detail: 'La aplicación ya tiene un sprint activo' } } })
    const wrapper = render()
    await flushPromises()
    await button(wrapper, 'Iniciar sprint')!.trigger('click')
    await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toContain('ya tiene un sprint activo')
    wrapper.unmount()
  })
  it('conserva el resumen de cierre y oculta la planificación finalizada', async () => {
    mocks.get.mockResolvedValue({ ...sprint, status: 'FINISHED', total_tickets: 5, completed_tickets: 3, progress: 60, released_tickets: 2 })
    const wrapper = render()
    await flushPromises()
    expect(wrapper.text()).toContain('3 de 5 tickets completados')
    expect(wrapper.text()).toContain('2 tickets pendientes volvieron al backlog')
    expect(button(wrapper, 'Editar plan')).toBeUndefined()
    expect(button(wrapper, 'Iniciar sprint')).toBeUndefined()
    expect(wrapper.text()).not.toContain('Backlog disponible')
    wrapper.unmount()
  })
})

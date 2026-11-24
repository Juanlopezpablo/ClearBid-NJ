import { mount, flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import HomeView from '@/views/HomeView.vue'
const mocks = vi.hoisted(() => ({ get: vi.fn(), auth: { userRole: 'ADMIN', user: { fullName: 'Persona de prueba' } } }))
vi.mock('@/services/api', () => ({ apiClient: mocks }))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => mocks.auth }))
const sample = () => ({ role: mocks.auth.userRole, scope: 'general', team_id: null, team_name: null, teams: [{ id: 'equipo-a', name: 'Equipo A' }], generated_at: '2026-11-23T12:00:00Z', metrics: { pending: 3, in_progress: 1, blocked: 1, overdue: 0, upcoming: 1 }, tickets: { total: 0, skip: 0, items: [] }, active_sprints: { total: 0, items: [] }, incidents: { available: true, total: 0, items: [] } })
const render = () => mount(HomeView, { global: { stubs: { AppHeader: true, RouterLink: true } } })
describe('Inicio adaptado por rol', () => {
  beforeEach(() => { vi.resetAllMocks(); mocks.auth.userRole = 'ADMIN'; mocks.get.mockImplementation(() => Promise.resolve({ data: sample() })) })
  it.each([['ADMIN', 'Inicio de administración'], ['TEAM_LEADER', 'Inicio de gestión'], ['DEVELOPER', 'Mi inicio']])('presenta el inicio de %s', async (role, heading) => {
    mocks.auth.userRole = role
    const wrapper = render(); await flushPromises()
    expect(wrapper.get('h1').text()).toBe(heading)
    expect(wrapper.find('select').exists()).toBe(role !== 'DEVELOPER')
    if (role === 'DEVELOPER') expect(wrapper.text()).not.toContain('Gestionar incidencias')
  })
  it('consulta un equipo y aplica la categoría desde el servidor', async () => {
    const wrapper = render(); await flushPromises()
    await wrapper.get('select').setValue('equipo-a'); await flushPromises()
    expect(mocks.get.mock.lastCall?.[1].params).toMatchObject({ team_id: 'equipo-a', focus: 'pending', skip: 0 })
    await wrapper.findAll('button').find(button => button.text().includes('Bloqueados'))!.trigger('click'); await flushPromises()
    expect(mocks.get.mock.lastCall?.[1].params).toMatchObject({ team_id: 'equipo-a', focus: 'blocked' })
  })
  it('explica las incidencias no asociadas a equipos sin mostrar un cero falso', async () => {
    const result = { ...sample(), scope: 'team', team_name: 'Equipo A', incidents: { available: false, total: null, items: [] } }
    mocks.get.mockResolvedValue({ data: result })
    const wrapper = render(); await flushPromises()
    expect(wrapper.text()).toContain('no están asociadas directamente a equipos')
    expect(wrapper.text()).not.toContain('Incidencias abiertas (0)')
  })
  it('muestra un error y permite reintentar', async () => {
    mocks.get.mockRejectedValueOnce(new Error('sin conexión'))
    const wrapper = render(); await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toContain('No se pudo cargar')
    await wrapper.findAll('button').find(button => button.text() === 'Reintentar')!.trigger('click'); await flushPromises()
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
  })
})

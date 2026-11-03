import { mount, flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import TicketSearchView from '@/views/TicketSearchView.vue'

const mocks = vi.hoisted(() => ({ get: vi.fn(), auth: { userRole: 'ADMIN', user: { id: 'yo' } } }))
vi.mock('@/services/api', () => ({ apiClient: mocks }))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => mocks.auth }))
const render = () => mount(TicketSearchView, { global: { stubs: { AppHeader: true, RouterLink: true, TicketLabels: true, TicketComments: true, EvidenceFiles: true } } })
const lastSearch = () => mocks.get.mock.calls.filter(call => call[0] === '/tickets/search').at(-1)![1].params as URLSearchParams

describe('Búsqueda avanzada', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mocks.get.mockImplementation((url: string) => Promise.resolve({ data: url === '/applications/' ? [] : { items: [], total: 0 } }))
  })
  it('envía etiquetas repetidas y combina filtros con el contrato del servidor', async () => {
    const wrapper = render()
    await flushPromises()
    await wrapper.get('input[placeholder="Título, descripción o UUID"]').setValue('acceso')
    await wrapper.get('input[placeholder="interfaz, urgente"]').setValue('web, urgente')
    await wrapper.findAll('select')[0].setValue('TODO')
    await wrapper.findAll('select')[4].setValue('mine')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(lastSearch().getAll('labels')).toEqual(['web', 'urgente'])
    expect(lastSearch().get('assignee_id')).toBe('yo')
    expect(lastSearch().get('status_filter')).toBe('TODO')
    expect(lastSearch().get('q')).toBe('acceso')
  })
  it('valida el rango antes de consultar y permite limpiar los filtros', async () => {
    const wrapper = render()
    await flushPromises()
    const dates = wrapper.findAll('input[type="date"]')
    await dates[0].setValue('2026-11-03')
    await dates[1].setValue('2026-11-01')
    const count = mocks.get.mock.calls.length
    await wrapper.get('form').trigger('submit')
    expect(mocks.get.mock.calls.length).toBe(count)
    expect(wrapper.text()).toContain('La fecha inicial')
    await wrapper.findAll('button').find(button => button.text() === 'Limpiar filtros')!.trigger('click')
    await flushPromises()
    expect(lastSearch().has('created_from')).toBe(false)
  })
  it('mantiene los filtros aplicados al paginar, aunque se edite el formulario', async () => {
    mocks.get.mockImplementation((url: string) => Promise.resolve({ data: url === '/applications/' ? [] : { items: [], total: 26 } }))
    const wrapper = render()
    await flushPromises()
    await wrapper.get('input[placeholder="Título, descripción o UUID"]').setValue('sin aplicar')
    await wrapper.findAll('button').find(button => button.text() === 'Siguiente')!.trigger('click')
    await flushPromises()
    expect(lastSearch().get('skip')).toBe('25')
    expect(lastSearch().has('q')).toBe(false)
  })
})

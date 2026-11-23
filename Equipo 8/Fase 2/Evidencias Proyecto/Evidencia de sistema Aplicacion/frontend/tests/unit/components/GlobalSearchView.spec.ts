import { mount, flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import GlobalSearchView from '@/views/GlobalSearchView.vue'
const mocks = vi.hoisted(() => ({ get: vi.fn() }))
vi.mock('@/services/api', () => ({ apiClient: mocks }))
const render = () => mount(GlobalSearchView, { global: { stubs: { AppHeader: true, TicketComments: true, EvidenceFiles: true } } })
describe('Buscador global', () => {
  beforeEach(() => { vi.resetAllMocks() })
  it('resalta texto y conserva contenido HTML como texto seguro', async () => {
    mocks.get.mockResolvedValue({ data: { total: 1, items: [{ id: '1', kind: 'document', title: 'Manual web', snippet: '<script>web</script>' }] } })
    const wrapper = render()
    await wrapper.get('input').setValue('web')
    await wrapper.get('form').trigger('submit'); await flushPromises()
    expect(wrapper.findAll('mark').map(mark => mark.text())).toEqual(['web', 'web'])
    expect(wrapper.find('script').exists()).toBe(false)
    expect(wrapper.text()).toContain('<script>web</script>')
  })
  it('conserva filtros al paginar aunque se edite el formulario', async () => {
    mocks.get.mockResolvedValue({ data: { total: 26, items: [] } })
    const wrapper = render()
    await wrapper.get('input').setValue('manual'); await wrapper.get('select').setValue('document')
    await wrapper.get('form').trigger('submit'); await flushPromises()
    await wrapper.get('input').setValue('otro')
    await wrapper.findAll('button').find(button => button.text() === 'Siguiente')!.trigger('click'); await flushPromises()
    expect(mocks.get.mock.lastCall?.[1].params).toMatchObject({ q: 'manual', kind: 'document', skip: 25 })
  })
  it('informa errores sin mostrar resultados antiguos', async () => {
    mocks.get.mockRejectedValue(new Error('desconectado'))
    const wrapper = render()
    await wrapper.get('input').setValue('manual'); await wrapper.get('form').trigger('submit'); await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toContain('No se pudo completar')
    expect(wrapper.find('article').exists()).toBe(false)
  })
})

import { mount, flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import TicketComments from '@/components/shared/TicketComments.vue'

const mocks = vi.hoisted(() => ({
  get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn(),
  auth: { user: { id: 'author' }, isAdmin: false },
  confirm: vi.fn(),
}))
vi.mock('@/services/api', () => ({ apiClient: mocks }))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => mocks.auth }))
vi.mock('@/stores/dialog', () => ({ useDialogStore: () => ({ confirm: mocks.confirm }) }))
const recipient = 'b4fe62a0-1304-43ad-828b-62108effe661'
const comment = {
  id: 'comment', ticket_id: 'ticket', author_id: 'author', author_name: 'Autora',
  body: 'Hola @[' + 'María](' + recipient + ')',
  created_at: '2026-10-21T12:00:00Z', updated_at: '2026-10-21T12:00:00Z',
}
async function render() {
  const wrapper = mount(TicketComments, { props: { ticketId: 'ticket' } })
  await flushPromises()
  return wrapper
}
const button = (wrapper: ReturnType<typeof mount>, label: string) =>
  wrapper.findAll('button').find(item => item.text() === label)!

describe('comentarios de tickets', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mocks.auth.user.id = 'author'
    mocks.auth.isAdmin = false
    mocks.get.mockResolvedValue({ data: [comment] })
    mocks.post.mockResolvedValue({ data: comment })
    mocks.patch.mockResolvedValue({ data: comment })
    mocks.delete.mockResolvedValue({})
    mocks.confirm.mockResolvedValue(true)
  })
  it('muestra nombres legibles y permite editar solo el propio comentario', async () => {
    const wrapper = await render()
    expect(wrapper.text()).toContain('Hola @María')
    expect(wrapper.text()).not.toContain(recipient)
    expect(button(wrapper, 'Editar')).toBeTruthy()
    expect(button(wrapper, 'Eliminar')).toBeUndefined()
    await button(wrapper, 'Editar').trigger('click')
    await wrapper.get('textarea').setValue('Texto corregido')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(mocks.patch).toHaveBeenCalledWith('/tickets/ticket/comments/comment', {
      body: 'Texto corregido\n@[María](' + recipient + ')',
    })
    wrapper.unmount()
  })
  it('ADMIN elimina previa confirmación, sin editar comentarios ajenos', async () => {
    mocks.auth.user.id = 'admin'
    mocks.auth.isAdmin = true
    const wrapper = await render()
    expect(button(wrapper, 'Editar')).toBeUndefined()
    await button(wrapper, 'Eliminar').trigger('click')
    await flushPromises()
    expect(mocks.confirm).toHaveBeenCalled()
    expect(mocks.delete).toHaveBeenCalledWith('/tickets/ticket/comments/comment')
    wrapper.unmount()
  })
  it('respeta la cancelación del borrado', async () => {
    mocks.auth.isAdmin = true
    mocks.confirm.mockResolvedValue(false)
    const wrapper = await render()
    await button(wrapper, 'Eliminar').trigger('click')
    await flushPromises()
    expect(mocks.delete).not.toHaveBeenCalled()
    wrapper.unmount()
  })
  it('guarda texto como texto, sin interpretar HTML', async () => {
    mocks.get.mockResolvedValue({ data: [{ ...comment, body: '<img src=x onerror=alert(1)>' }] })
    const wrapper = await render()
    expect(wrapper.find('img').exists()).toBe(false)
    expect(wrapper.text()).toContain('<img src=x onerror=alert(1)>')
    await wrapper.get('textarea').setValue('Nuevo comentario')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(mocks.post).toHaveBeenCalledWith('/tickets/ticket/comments', { body: 'Nuevo comentario' })
    wrapper.unmount()
  })
  it('busca usuarios y guarda sus IDs sin mostrarlos en el editor', async () => {
    const wrapper = await render()
    vi.useFakeTimers()
    mocks.get.mockResolvedValueOnce({ data: [{ id: recipient, full_name: 'María' }] })
    await wrapper.get('input[type=search]').setValue('Mar')
    await vi.advanceTimersByTimeAsync(250)
    await flushPromises()
    await button(wrapper, 'María').trigger('click')
    await wrapper.get('textarea').setValue('Revisa esto')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(mocks.post).toHaveBeenCalledWith('/tickets/ticket/comments', {
      body: 'Revisa esto\n@[María](' + recipient + ')',
    })
    vi.useRealTimers()
    wrapper.unmount()
  })
  it('mantiene el borrador y muestra el error si no se pudo guardar', async () => {
    mocks.post.mockRejectedValue({ response: { data: { detail: 'Usuario inactivo' } } })
    const wrapper = await render()
    await wrapper.get('textarea').setValue('No perder este texto')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(wrapper.get('[role=alert]').text()).toBe('Usuario inactivo')
    expect(wrapper.get('textarea').element.value).toBe('No perder este texto')
    wrapper.unmount()
  })
  it('descarta la respuesta pendiente de otro ticket', async () => {
    let resolveOld: (value: unknown) => void = () => {}
    mocks.get.mockReturnValueOnce(new Promise(resolve => { resolveOld = resolve }))
    const wrapper = mount(TicketComments, { props: { ticketId: 'old' } })
    mocks.get.mockResolvedValueOnce({ data: [{ ...comment, body: 'Comentario actual' }] })
    await wrapper.setProps({ ticketId: 'new' })
    await flushPromises()
    resolveOld({ data: [{ ...comment, body: 'Comentario antiguo' }] })
    await flushPromises()
    expect(wrapper.text()).toContain('Comentario actual')
    expect(wrapper.text()).not.toContain('Comentario antiguo')
    wrapper.unmount()
  })
})


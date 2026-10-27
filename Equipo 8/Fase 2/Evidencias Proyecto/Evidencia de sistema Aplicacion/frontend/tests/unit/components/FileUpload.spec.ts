import { mount, flushPromises } from '@vue/test-utils'
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'
import FileUpload from '@/components/FileUpload.vue'

const mocks = vi.hoisted(() => ({
  list: vi.fn(), upload: vi.fn(), download: vi.fn(), delete: vi.fn(), get: vi.fn(),
  confirm: vi.fn(), fetch: vi.fn(),
  auth: { user: { id: 'autor', role: 'DEVELOPER' }, isAdmin: false },
}))
vi.mock('@/services/api', () => ({
  api: { documents: mocks }, apiClient: { get: mocks.get },
}))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => mocks.auth }))
vi.mock('@/stores/dialog', () => ({ useDialogStore: () => ({ confirm: mocks.confirm }) }))

const documento = {
  id: 'doc', filename: 'captura.png', file_size: 80, mime_type: 'image/png',
  doc_type: 'DOCUMENTATION', ticket_id: 'ticket', uploaded_by_id: 'autor',
  uploaded_by: { full_name: 'Autora de prueba' }, created_at: '2026-10-27T12:00:00Z',
}
async function abrir(props = { ticketId: 'ticket' } as { ticketId?: string; incidentId?: string }) {
  const wrapper = mount(FileUpload, { props })
  await flushPromises()
  return wrapper
}
async function seleccionar(wrapper: Awaited<ReturnType<typeof abrir>>, files: File[]) {
  Object.defineProperty(wrapper.get('input[type=file]').element, 'files', {
    configurable: true, value: files,
  })
  await wrapper.get('input[type=file]').trigger('change')
  await flushPromises()
}
describe('NEW-02: archivos y evidencia', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mocks.auth.user.id = 'autor'
    mocks.auth.user.role = 'DEVELOPER'
    mocks.auth.isAdmin = false
    mocks.list.mockResolvedValue([documento])
    mocks.upload.mockResolvedValue(documento)
    mocks.confirm.mockResolvedValue(true)
    mocks.delete.mockResolvedValue({})
    mocks.get.mockResolvedValue({ data: { url: 'https://storage.example/captura-firmada' } })
    mocks.fetch.mockResolvedValue({ ok: true, blob: async () => new Blob(['imagen'], { type: 'image/png' }) })
    vi.stubGlobal('fetch', mocks.fetch)
    URL.createObjectURL = vi.fn(() => 'blob:captura')
    URL.revokeObjectURL = vi.fn()
  })
  afterEach(() => vi.unstubAllGlobals())

  it('muestra autor, fecha y tamaño del adjunto', async () => {
    const wrapper = await abrir()
    expect(wrapper.text()).toContain('Autora de prueba')
    expect(wrapper.text()).toContain('80 Bytes')
    expect(wrapper.text()).toContain('2026')
    wrapper.unmount()
  })
  it('envía varios archivos a la incidencia seleccionada', async () => {
    const wrapper = await abrir({ incidentId: 'incidencia' })
    await seleccionar(wrapper, [new File(['a'], 'a.txt'), new File(['b'], 'b.png', { type: 'image/png' })])
    expect(mocks.upload).toHaveBeenCalledTimes(2)
    expect(mocks.upload.mock.calls[0][1]).toMatchObject({ incidentId: 'incidencia', ticketId: undefined })
    wrapper.unmount()
  })
  it('rechaza videos, audios y tamaños superiores a 25 MB', async () => {
    const wrapper = await abrir()
    await seleccionar(wrapper, [new File(['v'], 'video.mp4', { type: 'video/mp4' })])
    expect(wrapper.get('[role=alert]').text()).toContain('No se admiten videos ni audios')
    await seleccionar(wrapper, [new File(['a'], 'audio.mp3', { type: 'audio/mpeg' })])
    const grande = new File(['x'], 'grande.pdf')
    Object.defineProperty(grande, 'size', { value: 26 * 1024 * 1024 })
    await seleccionar(wrapper, [grande])
    expect(wrapper.get('[role=alert]').text()).toContain('25 MB')
    expect(mocks.upload).not.toHaveBeenCalled()
    wrapper.unmount()
  })
  it('TEAM_LEADER ajeno no ve eliminar en un ticket; ADMIN sí', async () => {
    mocks.auth.user.id = 'otro'
    mocks.auth.user.role = 'TEAM_LEADER'
    const wrapper = await abrir()
    expect(wrapper.find('button[title=Eliminar]').exists()).toBe(false)
    wrapper.unmount()
    mocks.auth.isAdmin = true
    const admin = await abrir()
    expect(admin.find('button[title=Eliminar]').exists()).toBe(true)
    admin.unmount()
  })
  it('descarga y solicita confirmación antes de eliminar', async () => {
    const wrapper = await abrir()
    await wrapper.get('button[title=Descargar]').trigger('click')
    expect(mocks.download).toHaveBeenCalledWith('doc')
    mocks.confirm.mockResolvedValueOnce(false)
    await wrapper.get('button[title=Eliminar]').trigger('click')
    await flushPromises()
    expect(mocks.delete).not.toHaveBeenCalled()
    await wrapper.get('button[title=Eliminar]').trigger('click')
    await flushPromises()
    expect(mocks.delete).toHaveBeenCalledWith('doc')
    wrapper.unmount()
  })
  it('muestra una captura con URL temporal sin enviar credenciales al almacenamiento', async () => {
    const wrapper = await abrir()
    const ver = wrapper.findAll('button').find(item => item.text() === 'Ver captura')!
    await ver.trigger('click')
    await flushPromises()
    expect(mocks.fetch).toHaveBeenCalledWith('https://storage.example/captura-firmada')
    expect(wrapper.get('img').attributes('src')).toBe('blob:captura')
    wrapper.unmount()
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:captura')
  })
  it('ignora el listado pendiente de otro ticket', async () => {
    let resolver: (value: unknown) => void = () => {}
    mocks.list.mockReturnValueOnce(new Promise(resolve => { resolver = resolve }))
    const wrapper = mount(FileUpload, { props: { ticketId: 'anterior' } })
    mocks.list.mockResolvedValueOnce([{ ...documento, filename: 'actual.txt' }])
    await wrapper.setProps({ ticketId: 'actual' })
    await flushPromises()
    resolver([{ ...documento, filename: 'anterior.txt' }])
    await flushPromises()
    expect(wrapper.text()).toContain('actual.txt')
    expect(wrapper.text()).not.toContain('anterior.txt')
    wrapper.unmount()
  })
})


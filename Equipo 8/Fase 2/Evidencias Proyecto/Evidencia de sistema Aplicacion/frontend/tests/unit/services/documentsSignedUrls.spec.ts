import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

/**
 * Documents go straight to Cloud Storage with signed URLs: the API is only
 * asked for the URL (upload-url / download-url) and to confirm.
 */

const instance: any = vi.fn()
instance.interceptors = { request: { use: vi.fn() }, response: { use: vi.fn() } }
instance.post = vi.fn()
instance.get = vi.fn()

vi.mock('axios', () => ({
  default: { create: vi.fn(() => instance), post: vi.fn() },
}))

const SIGNED = {
  upload_token: 'tok-123',
  url: 'https://storage.googleapis.com/corestream-file/pending/abc?X-Goog-Signature=x',
  method: 'PUT',
  headers: { 'Content-Type': 'text/plain', 'x-goog-content-length-range': '0,26214400' },
  expires_in: 900,
}

describe('api.documents with signed URLs', () => {
  let api: any
  const fetchMock = vi.fn()

  beforeEach(async () => {
    vi.resetModules()
    instance.post.mockReset()
    instance.get.mockReset()
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
    api = (await import('@/services/api')).api
  })

  afterEach(() => vi.unstubAllGlobals())

  it('uploads in three steps and returns the created document', async () => {
    instance.post
      .mockResolvedValueOnce({ data: SIGNED })
      .mockResolvedValueOnce({ data: { id: 'doc-1', filename: 'notas.txt' } })
    fetchMock.mockResolvedValue({ ok: true, status: 200 })
    const file = new File(['hola'], 'notas.txt', { type: 'text/plain' })

    const doc = await api.documents.upload(file, { ticketId: 't-1', docType: 'CODE' })

    expect(instance.post).toHaveBeenNthCalledWith(1, '/documents/upload-url', {
      filename: 'notas.txt',
      size: 4,
      content_type: 'text/plain',
      epic_id: null,
      ticket_id: 't-1',
      doc_type: 'CODE',
    })
    expect(fetchMock).toHaveBeenCalledWith(SIGNED.url, {
      method: 'PUT',
      headers: SIGNED.headers,
      body: file,
    })
    // Our bearer token must never travel to the storage service.
    expect(JSON.stringify(fetchMock.mock.calls[0][1].headers)).not.toMatch(/authorization/i)
    expect(instance.post).toHaveBeenNthCalledWith(2, '/documents/confirm', { upload_token: 'tok-123' })
    expect(doc).toEqual({ id: 'doc-1', filename: 'notas.txt' })
  })

  it('does not confirm when the storage rejects the upload', async () => {
    instance.post.mockResolvedValueOnce({ data: SIGNED })
    fetchMock.mockResolvedValue({ ok: false, status: 400 })
    const file = new File(['x'], 'grande.txt', { type: 'text/plain' })

    await expect(api.documents.upload(file, { epicId: 'e-1' })).rejects.toThrow(/HTTP 400/)
    expect(instance.post).toHaveBeenCalledTimes(1)
  })

  it('shows the backend reason when the API refuses the file', async () => {
    instance.post.mockRejectedValueOnce({
      response: { status: 413, data: { detail: 'El archivo supera el límite de 25 MB' } },
    })
    const file = new File(['x'], 'enorme.pdf', { type: 'application/pdf' })

    await expect(api.documents.upload(file, { epicId: 'e-1' })).rejects.toThrow(
      'El archivo supera el límite de 25 MB'
    )
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('downloads through a short-lived signed URL', async () => {
    instance.get.mockResolvedValueOnce({
      data: { url: 'https://storage.googleapis.com/corestream-file/documents/abc?sig', filename: 'a.pdf' },
    })
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})

    await api.documents.download('doc-9')

    expect(instance.get).toHaveBeenCalledWith('/documents/doc-9/download-url')
    const link = click.mock.contexts[0] as HTMLAnchorElement
    expect(link.href).toBe('https://storage.googleapis.com/corestream-file/documents/abc?sig')
    expect(link.download).toBe('a.pdf')
    click.mockRestore()
  })
})

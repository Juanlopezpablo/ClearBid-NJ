/** Datos locales por cuenta. Nunca se guardan contraseñas ni tokens. */
export interface LocalProfile { id: string; name: string; savedAt: number }
export interface SavedTicket { key: string; owner: string; id: string; title: string; description: string; status: string; priority: string; savedAt: number }
export interface PendingComment { id: string; owner: string; ticketId: string; title: string; body: string; createdAt: number; error: string }
export const SNAPSHOT_TTL = 7 * 24 * 60 * 60 * 1000
let database: Promise<IDBDatabase> | undefined
let owner: string | null = null
export const getOfflineOwner = () => owner
export function setOfflineOwner(id: string | null) { owner = id }
const changed = () => window.dispatchEvent(new Event('offline-data-changed'))

function open(): Promise<IDBDatabase> {
  if (!globalThis.indexedDB) return Promise.reject(new Error('Este navegador no permite guardar datos sin conexión.'))
  if (!database) database = new Promise<IDBDatabase>((resolve, reject) => {
    const request = indexedDB.open('corestream-offline-v1', 1)
    request.onupgradeneeded = () => {
      for (const name of ['profiles', 'tickets', 'outbox']) request.result.createObjectStore(name, { keyPath: name === 'tickets' ? 'key' : 'id' })
    }
    request.onsuccess = () => { request.result.onversionchange = () => { request.result.close(); database = undefined }; resolve(request.result) }
    request.onerror = () => { database = undefined; reject(new Error('No se pudo abrir el almacenamiento local.')) }
    request.onblocked = () => { database = undefined; reject(new Error('Cierra otras pestañas de CoreStream para habilitar el almacenamiento local.')) }
  })
  return database
}
async function readAll<T>(store: string): Promise<T[]> {
  const db = await open()
  return new Promise((resolve, reject) => {
    const request = db.transaction(store).objectStore(store).getAll()
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(new Error('No se pudieron leer los datos locales.'))
  })
}
async function write(store: string, action: (object: IDBObjectStore) => void) {
  const db = await open()
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(store, 'readwrite')
    tx.oncomplete = () => resolve()
    tx.onerror = tx.onabort = () => reject(new Error('No se pudieron guardar los datos locales. Revisa el espacio disponible.'))
    action(tx.objectStore(store))
  })
  changed()
}
export async function saveProfile(profile: LocalProfile) { await write('profiles', store => store.put({ ...profile, id: 'last', ownerId: profile.id })) }
export async function lastProfile(): Promise<LocalProfile | null> {
  if (localStorage.getItem('corestream-offline-logout')) return null
  const profiles = await readAll<LocalProfile & { ownerId: string }>('profiles')
  const value = profiles[0]
  return value && value.savedAt > Date.now() - SNAPSHOT_TTL ? { id: value.ownerId, name: value.name, savedAt: value.savedAt } : null
}
export async function forgetProfile() { await write('profiles', store => store.clear()) }
export async function savedTickets(id: string): Promise<SavedTicket[]> {
  const all = await readAll<SavedTicket>('tickets')
  const cutoff = Date.now() - SNAPSHOT_TTL
  const expired = all.filter(ticket => ticket.savedAt < cutoff)
  if (expired.length) await write('tickets', store => expired.forEach(ticket => store.delete(ticket.key)))
  return all.filter(ticket => ticket.owner === id && ticket.savedAt >= cutoff).sort((a, b) => b.savedAt - a.savedAt)
}
export async function cacheTickets(id: string, raw: unknown) {
  const value = raw as { items?: unknown[] }
  const roots = Array.isArray(raw) ? raw : Array.isArray(value?.items) ? value.items : [raw]
  const list = roots.flatMap(item => Array.isArray(item?.tickets) ? item.tickets : [item])
  const records: SavedTicket[] = []
  for (const item of list) {
    const ticket = item as Record<string, unknown> | null
    if (!ticket || typeof ticket.id !== 'string' || typeof ticket.title !== 'string' || typeof ticket.status !== 'string' || typeof ticket.priority !== 'string') continue
    records.push({ key: `${id}:${ticket.id}`, owner: id, id: ticket.id, title: ticket.title,
      description: typeof ticket.description === 'string' ? ticket.description : '', status: ticket.status,
      priority: ticket.priority, savedAt: Date.now() })
  }
  if (!records.length) return
  await write('tickets', store => records.forEach(record => store.put(record)))
  const all = await savedTickets(id)
  if (all.length > 200) await write('tickets', store => all.slice(200).forEach(ticket => store.delete(ticket.key)))
}
export async function pendingComments(id: string) { return (await readAll<PendingComment>('outbox')).filter(item => item.owner === id).sort((a, b) => a.createdAt - b.createdAt) }
export async function enqueueComment(item: PendingComment) {
  if (!item.body.trim() || item.body.length > 5000) throw new Error('El comentario debe tener entre 1 y 5000 caracteres.')
  const db = await open()
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction('outbox', 'readwrite')
    let reason = 'No se pudo guardar el comentario en este navegador.'
    tx.oncomplete = () => resolve()
    tx.onerror = tx.onabort = () => reject(new Error(reason))
    const store = tx.objectStore('outbox')
    const request = store.getAll()
    request.onsuccess = () => {
      if (request.result.filter((row: PendingComment) => row.owner === item.owner).length >= 200) {
        reason = 'Hay 200 comentarios pendientes. Sincroniza o descarta algunos antes de agregar más.'; tx.abort(); return
      }
      store.add(item)
    }
  })
  changed()
}
export async function pendingError(item: PendingComment, error: string) {
  // No volver a crear una entrada que el usuario haya descartado en otra pestaña.
  await write('outbox', store => {
    const request = store.get(item.id)
    request.onsuccess = () => { if (request.result?.owner === item.owner) store.put({ ...request.result, error }) }
  })
}
export async function discardComment(owner: string, id: string) {
  await write('outbox', store => { const request = store.get(id); request.onsuccess = () => { if (request.result?.owner === owner) store.delete(id) } })
}
export async function clearSnapshots(id: string) {
  const all = await readAll<SavedTicket>('tickets')
  await write('tickets', store => all.filter(ticket => ticket.owner === id).forEach(ticket => store.delete(ticket.key)))
}

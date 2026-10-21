/**
 * Composable useWebSocket.ts
 *
 * Composable de WebSocket para notificaciones en tiempo real en CoreStream.
 * Conecta al servidor FastAPI a través de WebSocket y recibe eventos push.
 * Implementa reconexión automática con backoff exponencial para mayor confiabilidad.
 *
 * DISEÑO — estado a nivel de módulo, no por llamada:
 * Antes, socket/isConnected/reconnectAttempts vivían DENTRO de useWebSocket(),
 * así que cada llamada creaba su propia conexión aislada sin relación con las
 * demás. Nada en la app llamaba nunca a connect() (solo ActionDock.vue
 * importaba el composable sin usarlo), así que ese defecto nunca se notó.
 * Ahora que stores/auth.ts sí llama a connect()/disconnect() en login/logout,
 * hace falta un singleton real: el estado vive a nivel de módulo, y cada
 * useWebSocket() devuelve referencias a la MISMA conexión.
 *
 * Por el mismo motivo se quitó el onUnmounted() que traía antes: solo
 * funciona si el composable se invoca dentro del setup() de un componente,
 * y aquí se invoca desde un store de Pinia. El ciclo de vida de la conexión
 * lo decide quien la abrió (login) y quien la cierra (logout), no el
 * montaje de un componente cualquiera.
 *
 * Autenticación del handshake (plan 3.2):
 * connect(userId) primero cambia el access token actual por un ticket de un
 * solo uso (POST /auth/ws-ticket) y lo manda como ?ticket=... — no el JWT
 * directamente, que quedaría escrito en los logs de acceso de cualquier
 * proxy delante de la app durante toda su vida útil.
 *
 * Corte por inactividad (migración a GCP, plan D13):
 * Un WebSocket abierto mantiene encendida (y facturando) una instancia de
 * Cloud Run. Tras IDLE_PROMPT_AFTER_MS sin actividad del usuario se muestra
 * "¿Sigues ahí?" (components/common/IdlePrompt.vue); si no responde en
 * IDLE_GRACE_MS se cierra el socket con código 4000 y no se reconecta hasta
 * que el usuario pulse "Reconectar". Al reconectar se recargan las
 * notificaciones y se emite 'ws-resync' para que las vistas recarguen lo que
 * pudo cambiar mientras tanto. Mientras hay actividad se avisa al backend
 * con {type: 'activity'} (máx. una vez por minuto); el backend corta por su
 * cuenta si no recibe ninguno en 20 min (routers/websocket.py).
 *
 * Uso:
 * const { isConnected, connect, disconnect, send } = useWebSocket()
 * await connect('user-id-123')
 */

import { ref } from 'vue'
import type { Ref } from 'vue'
import { useNotificationsStore } from '@/stores/notifications'
import { NotificationType } from '@/types'
import { eventBus } from '@/utils/eventBus'
import api from '@/services/api'

interface WebSocketMessage {
  type: 'notification' | 'update' | 'error' | 'ping' | 'pong' | 'connected'
  data?: any
  message?: string
  timestamp?: string
}

// =========================================================================
// ESTADO A NIVEL DE MÓDULO — compartido por todas las llamadas a useWebSocket()
// =========================================================================

const socket: Ref<WebSocket | null> = ref(null)
const isConnected: Ref<boolean> = ref(false)
const reconnectAttempts: Ref<number> = ref(0)
let heartbeatIntervalId: ReturnType<typeof setInterval> | null = null

/** Usuario de la conexión actual, para poder reconectar sin que el caller lo repita. */
let currentUserId: string | null = null

/** Evita reconexiones simultáneas si handleClose se disparase más de una vez. */
let reconnectTimeoutId: ReturnType<typeof setTimeout> | null = null

const maxReconnectAttempts = 10
const baseDelay = 1000
const maxDelay = 30000
const heartbeatInterval = 30000

// Idle handling (see header).
export const WS_CLOSE_IDLE = 4000
export const IDLE_PROMPT_AFTER_MS = 10 * 60 * 1000
export const IDLE_GRACE_MS = 5 * 60 * 1000
const ACTIVITY_REPORT_MS = 60 * 1000
const IDLE_CHECK_MS = 15 * 1000
const ACTIVITY_EVENTS = ['mousemove', 'mousedown', 'keydown', 'wheel', 'touchstart', 'scroll'] as const

/** "¿Sigues ahí?" visible. */
const idlePromptVisible: Ref<boolean> = ref(false)
/** Socket closed for inactivity; waiting for the user to resume. */
const idlePaused: Ref<boolean> = ref(false)
/** Epoch ms when the prompt expires (for the countdown). */
const idleDeadline: Ref<number | null> = ref(null)

let lastActivityAt = Date.now()
let lastActivityReportAt = 0
let idleCheckId: ReturnType<typeof setInterval> | null = null
let activityListening = false
/** True after the first successful open of this session: later opens are reconnections. */
let hasConnectedBefore = false

function calculateBackoffDelay(): number {
  const exponentialDelay = baseDelay * Math.pow(2, reconnectAttempts.value)
  return Math.min(exponentialDelay, maxDelay)
}

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
}

function startHeartbeat(): void {
  if (heartbeatIntervalId) {
    clearInterval(heartbeatIntervalId)
  }

  heartbeatIntervalId = setInterval(() => {
    if (isConnected.value && socket.value) {
      try {
        send({ type: 'ping', timestamp: new Date().toISOString() })
      } catch (error) {
        console.warn('Error enviando heartbeat:', error)
      }
    }
  }, heartbeatInterval)
}

function stopHeartbeat(): void {
  if (heartbeatIntervalId) {
    clearInterval(heartbeatIntervalId)
    heartbeatIntervalId = null
  }
}

function handleMessage(event: MessageEvent): void {
  const notificationStore = useNotificationsStore()

  try {
    const message: WebSocketMessage = JSON.parse(event.data)

    switch (message.type) {
      case 'notification':
        if (message.data) {
          if (message.data.id && message.data.created_at !== undefined) {
            notificationStore.addNotification({
              id: message.data.id,
              userId: '',
              title: message.data.title ?? '',
              message: message.data.message ?? '',
              type: (message.data.type as NotificationType) ?? NotificationType.SYSTEM,
              isRead: message.data.is_read ?? false,
              ticketId: message.data.ticket_id ?? undefined,
              createdAt: message.data.created_at ?? message.timestamp ?? new Date().toISOString(),
            })
          } else {
            const eventType = message.data.eventType || message.data.type
            if (eventType === 'TIMER_SYNC') {
              eventBus.emit('timer-sync', message.data)
            } else {
              notificationStore.addNotification({
                id: message.data.id || generateId(),
                userId: '',
                title: message.data.title || 'Notificación',
                message: message.data.message || '',
                type: (message.data.type as NotificationType) || NotificationType.SYSTEM,
                isRead: false,
                ticketId: message.data.ticketId || message.data.ticket_id || undefined,
                createdAt: message.timestamp || new Date().toISOString(),
              })
            }
          }
        }
        break

      case 'update':
        eventBus.emit('ws-update', message.data)
        break

      case 'ping':
        try {
          send({ type: 'pong' })
        } catch {
          /* ignorar errores de envío del pong */
        }
        break

      case 'pong':
        break

      case 'connected':
        break

      case 'error':
        console.error('Error del servidor WebSocket:', message.message)
        notificationStore.addNotification({
          userId: '',
          id: generateId(),
          title: 'Error',
          message: message.message || 'Error del servidor',
          type: NotificationType.SYSTEM,
          createdAt: message.timestamp || new Date().toISOString(),
          isRead: false
        })
        break

      default:
        console.warn('Tipo de mensaje desconocido:', message.type)
    }
  } catch (error) {
    console.error('Error procesando mensaje WebSocket:', error)
  }
}

function handleClose(event: CloseEvent): void {
  isConnected.value = false
  socket.value = null
  stopHeartbeat()

  // Cierre intencional (disconnect()): no reconectar.
  if (event.code === 1000) return

  // Cierre por inactividad (nuestro o del backend): esperar a que el
  // usuario vuelva, sin reintentos automáticos.
  if (event.code === WS_CLOSE_IDLE) {
    enterIdlePause()
    return
  }

  if (!currentUserId) return

  if (reconnectAttempts.value < maxReconnectAttempts) {
    const delay = calculateBackoffDelay()
    reconnectAttempts.value++

    if (reconnectTimeoutId) clearTimeout(reconnectTimeoutId)
    reconnectTimeoutId = setTimeout(() => {
      if (currentUserId) {
        connect(currentUserId)
      }
    }, delay)
  } else {
    console.error(`No se pudo conectar después de ${maxReconnectAttempts} intentos`)
    useNotificationsStore().addNotification({
      userId: '',
      id: generateId(),
      title: 'Conexión perdida',
      message: 'No se pudo establecer la conexión con el servidor',
      type: NotificationType.SYSTEM,
      createdAt: new Date().toISOString(),
      isRead: false
    })
  }
}

function handleError(event: Event): void {
  console.error('Error de WebSocket:', event)
  useNotificationsStore().addNotification({
    userId: '',
    id: generateId(),
    title: 'Error de conexión',
    message: 'Hubo un error en la conexión WebSocket',
    type: NotificationType.SYSTEM,
    createdAt: new Date().toISOString(),
    isRead: false
  })
}

/**
 * Conecta al servidor WebSocket para `userId`.
 *
 * Cambia el access token actual por un ticket de un solo uso (15s de vida)
 * y lo manda como ?ticket=... — nunca el JWT en claro.
 */
async function connect(userId: string): Promise<void> {
  if (socket.value && isConnected.value) {
    console.warn('Ya hay una conexión WebSocket activa')
    return
  }

  currentUserId = userId

  try {
    const ticket = await api.auth.getWsTicket()

    // Mismo origen que la página, no una URL de backend aparte: /api ya se
    // llama por ruta relativa (ver services/api.ts) porque nginx en
    // producción enruta /api al backend dentro del MISMO dominio — no hay
    // subdominio de API separado. VITE_BACKEND_URL nunca se pasaba como
    // build-arg del Docker de producción, así que esto siempre caía al
    // default "localhost:8000" ahí — jamás conectaba fuera de un dev local
    // sin Docker. En dev con Docker, el proxy de Vite ya reenvía /api
    // (incluido el upgrade de WebSocket, ver vite.config.ts) desde el mismo
    // origen, así que esto funciona igual en ambos casos.
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/api/ws/${userId}?ticket=${encodeURIComponent(ticket)}`

    socket.value = new WebSocket(wsUrl)

    socket.value.addEventListener('open', () => {
      isConnected.value = true
      reconnectAttempts.value = 0
      startHeartbeat()
      startIdleWatch()
      // A reconnection may have missed events: reload what WS feeds.
      if (hasConnectedBefore) resync()
      hasConnectedBefore = true
    })

    socket.value.addEventListener('message', handleMessage)
    socket.value.addEventListener('close', handleClose)
    socket.value.addEventListener('error', handleError)
  } catch (error) {
    console.error('Error al conectar WebSocket:', error)
    isConnected.value = false
  }
}

/**
 * Desconecta del servidor WebSocket. code=1000 le indica a handleClose que
 * es un cierre intencional y no debe disparar reconexión.
 */
function disconnect(): void {
  try {
    currentUserId = null
    if (reconnectTimeoutId) {
      clearTimeout(reconnectTimeoutId)
      reconnectTimeoutId = null
    }
    stopHeartbeat()
    stopIdleWatch()
    idlePromptVisible.value = false
    idlePaused.value = false
    idleDeadline.value = null
    hasConnectedBefore = false

    if (socket.value) {
      socket.value.close(1000, 'Desconexión voluntaria del cliente')
      socket.value = null
    }

    isConnected.value = false
    reconnectAttempts.value = 0
  } catch (error) {
    console.error('Error al desconectar WebSocket:', error)
  }
}

function send(data: any): void {
  if (!socket.value || !isConnected.value) {
    console.error('No hay conexión WebSocket activa')
    return
  }

  try {
    const message = JSON.stringify({
      ...data,
      timestamp: data.timestamp || new Date().toISOString()
    })
    socket.value.send(message)
  } catch (error) {
    console.error('Error enviando mensaje WebSocket:', error)
  }
}

// =========================================================================
// INACTIVIDAD
// =========================================================================

function markActivity(): void {
  // While asking or paused, only the explicit buttons count as an answer.
  if (idlePromptVisible.value || idlePaused.value) return
  const now = Date.now()
  lastActivityAt = now
  if (isConnected.value && now - lastActivityReportAt >= ACTIVITY_REPORT_MS) {
    lastActivityReportAt = now
    send({ type: 'activity' })
  }
}

function handleVisibility(): void {
  if (document.visibilityState === 'visible') markActivity()
}

function checkIdle(): void {
  if (!isConnected.value || idlePaused.value) return
  const now = Date.now()

  if (idlePromptVisible.value) {
    if (idleDeadline.value !== null && now >= idleDeadline.value) pauseForIdle()
    return
  }

  const idleFor = now - lastActivityAt
  if (idleFor >= IDLE_PROMPT_AFTER_MS + IDLE_GRACE_MS) {
    // Tab throttled or laptop asleep past the whole window: nobody could
    // have answered, cut directly.
    pauseForIdle()
  } else if (idleFor >= IDLE_PROMPT_AFTER_MS) {
    idleDeadline.value = now + IDLE_GRACE_MS
    idlePromptVisible.value = true
  }
}

function startIdleWatch(): void {
  lastActivityAt = Date.now()
  lastActivityReportAt = 0
  if (!activityListening) {
    ACTIVITY_EVENTS.forEach((e) =>
      window.addEventListener(e, markActivity, { passive: true, capture: true })
    )
    document.addEventListener('visibilitychange', handleVisibility)
    activityListening = true
  }
  if (!idleCheckId) idleCheckId = setInterval(checkIdle, IDLE_CHECK_MS)
}

function stopIdleWatch(): void {
  if (activityListening) {
    ACTIVITY_EVENTS.forEach((e) =>
      window.removeEventListener(e, markActivity, { capture: true })
    )
    document.removeEventListener('visibilitychange', handleVisibility)
    activityListening = false
  }
  if (idleCheckId) {
    clearInterval(idleCheckId)
    idleCheckId = null
  }
}

function enterIdlePause(): void {
  idlePromptVisible.value = false
  idleDeadline.value = null
  idlePaused.value = true
  stopIdleWatch()
}

/** Closes the socket for inactivity. The session (login) is untouched. */
function pauseForIdle(): void {
  if (reconnectTimeoutId) {
    clearTimeout(reconnectTimeoutId)
    reconnectTimeoutId = null
  }
  enterIdlePause()
  stopHeartbeat()
  const old = socket.value
  if (old) {
    // Detach first: this socket's late 'close' event must not touch the
    // state of a new socket opened by resumeFromIdle().
    old.removeEventListener('message', handleMessage)
    old.removeEventListener('close', handleClose)
    old.removeEventListener('error', handleError)
    old.close(WS_CLOSE_IDLE, 'Inactividad')
  }
  socket.value = null
  isConnected.value = false
}

/** "Sigo aquí": hide the prompt and tell the backend right away. */
function confirmPresence(): void {
  idlePromptVisible.value = false
  idleDeadline.value = null
  const now = Date.now()
  lastActivityAt = now
  lastActivityReportAt = now
  send({ type: 'activity' })
}

/** "Reconectar": open a new socket; resync runs on open. */
async function resumeFromIdle(): Promise<void> {
  if (!currentUserId) return
  idlePaused.value = false
  reconnectAttempts.value = 0
  await connect(currentUserId)
}

/** Reloads what the socket feeds, after any reconnection. */
function resync(): void {
  useNotificationsStore().fetch(1).catch((err: unknown) => {
    console.warn('No se pudieron recargar las notificaciones tras reconectar:', err)
  })
  eventBus.emit('ws-resync')
}

/**
 * Composable para gestionar la conexión WebSocket (singleton a nivel de
 * módulo, ver nota de diseño arriba).
 */
export function useWebSocket() {
  return {
    isConnected,
    reconnectAttempts,
    idlePromptVisible,
    idlePaused,
    idleDeadline,
    connect,
    disconnect,
    send,
    confirmPresence,
    resumeFromIdle,
  }
}

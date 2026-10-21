import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

/**
 * Idle handling of the real-time WebSocket: "are you still there?" after
 * 10 min, close with code 4000 after 5 more, resume + resync on demand.
 */

const fetchNotifications = vi.fn().mockResolvedValue([])
vi.mock('@/stores/notifications', () => ({
  useNotificationsStore: () => ({ fetch: fetchNotifications, addNotification: vi.fn() }),
}))
vi.mock('@/services/api', () => ({
  default: { auth: { getWsTicket: vi.fn().mockResolvedValue('ticket-123') } },
}))

class FakeWebSocket {
  static instances: FakeWebSocket[] = []
  sent: any[] = []
  closedWith: number | null = null
  private listeners: Record<string, Array<(e: any) => void>> = {}

  constructor(public url: string) {
    FakeWebSocket.instances.push(this)
  }
  addEventListener(type: string, fn: (e: any) => void) {
    ;(this.listeners[type] ||= []).push(fn)
  }
  removeEventListener(type: string, fn: (e: any) => void) {
    this.listeners[type] = (this.listeners[type] || []).filter((f) => f !== fn)
  }
  send(data: string) {
    this.sent.push(JSON.parse(data))
  }
  close(code: number) {
    this.closedWith = code
  }
  emit(type: string, event: any = {}) {
    ;(this.listeners[type] || []).forEach((fn) => fn(event))
  }
}

const MIN = 60 * 1000

async function setup() {
  vi.resetModules()
  FakeWebSocket.instances = []
  const mod = await import('@/composables/useWebSocket')
  const { eventBus } = await import('@/utils/eventBus')
  const ws = mod.useWebSocket()
  await ws.connect('user-1')
  const sock = FakeWebSocket.instances[0]
  sock.emit('open')
  return { ws, sock, eventBus }
}

describe('useWebSocket idle handling', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.stubGlobal('WebSocket', FakeWebSocket)
    fetchNotifications.mockClear()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('asks after 10 min without activity and closes with 4000 after 5 more', async () => {
    const { ws, sock } = await setup()

    vi.advanceTimersByTime(9 * MIN)
    expect(ws.idlePromptVisible.value).toBe(false)

    vi.advanceTimersByTime(1.5 * MIN)
    expect(ws.idlePromptVisible.value).toBe(true)
    expect(ws.idleDeadline.value).not.toBeNull()

    vi.advanceTimersByTime(5 * MIN)
    expect(sock.closedWith).toBe(4000)
    expect(ws.idlePaused.value).toBe(true)
    expect(ws.idlePromptVisible.value).toBe(false)
    expect(ws.isConnected.value).toBe(false)

    // No automatic reconnection while paused.
    vi.advanceTimersByTime(60 * MIN)
    expect(FakeWebSocket.instances).toHaveLength(1)
  })

  it('user activity postpones the prompt and is reported at most once a minute', async () => {
    const { ws, sock } = await setup()

    for (let i = 0; i < 12; i++) {
      vi.advanceTimersByTime(MIN)
      window.dispatchEvent(new Event('mousemove'))
      window.dispatchEvent(new Event('keydown'))
    }
    expect(ws.idlePromptVisible.value).toBe(false)
    const activity = sock.sent.filter((m) => m.type === 'activity')
    expect(activity.length).toBe(12)
  })

  it('mouse movement does not answer the prompt; only "I am here" does', async () => {
    const { ws, sock } = await setup()
    vi.advanceTimersByTime(10.5 * MIN)
    expect(ws.idlePromptVisible.value).toBe(true)

    window.dispatchEvent(new Event('mousemove'))
    expect(ws.idlePromptVisible.value).toBe(true)

    ws.confirmPresence()
    expect(ws.idlePromptVisible.value).toBe(false)
    expect(sock.sent.at(-1).type).toBe('activity')

    vi.advanceTimersByTime(9 * MIN)
    expect(ws.idlePromptVisible.value).toBe(false)
    expect(sock.closedWith).toBeNull()
  })

  it('cuts directly when the tab slept past the whole window', async () => {
    const { ws, sock } = await setup()
    // Simulate a throttled/suspended tab: time jumps without interval ticks.
    vi.setSystemTime(Date.now() + 20 * MIN)
    vi.advanceTimersByTime(15 * 1000)
    expect(sock.closedWith).toBe(4000)
    expect(ws.idlePaused.value).toBe(true)
  })

  it('a server-side idle close (4000) pauses without reconnecting', async () => {
    const { ws, sock } = await setup()
    sock.emit('close', { code: 4000 })
    expect(ws.idlePaused.value).toBe(true)
    vi.advanceTimersByTime(10 * MIN)
    expect(FakeWebSocket.instances).toHaveLength(1)
  })

  it('resume opens a new socket and resyncs', async () => {
    const { ws, eventBus } = await setup()
    const onResync = vi.fn()
    eventBus.on('ws-resync', onResync)

    vi.advanceTimersByTime(16 * MIN)
    expect(ws.idlePaused.value).toBe(true)

    await ws.resumeFromIdle()
    const second = FakeWebSocket.instances[1]
    expect(second).toBeDefined()
    second.emit('open')

    expect(ws.idlePaused.value).toBe(false)
    expect(ws.isConnected.value).toBe(true)
    expect(fetchNotifications).toHaveBeenCalledWith(1)
    expect(onResync).toHaveBeenCalledTimes(1)
  })

  it('a network drop reconnects with backoff and resyncs', async () => {
    const { ws, sock, eventBus } = await setup()
    const onResync = vi.fn()
    eventBus.on('ws-resync', onResync)

    sock.emit('close', { code: 1006 })
    expect(ws.idlePaused.value).toBe(false)
    await vi.advanceTimersByTimeAsync(1000)
    const second = FakeWebSocket.instances[1]
    second.emit('open')
    expect(onResync).toHaveBeenCalledTimes(1)
  })

  it('logout clears the idle state', async () => {
    const { ws } = await setup()
    vi.advanceTimersByTime(10.5 * MIN)
    expect(ws.idlePromptVisible.value).toBe(true)
    ws.disconnect()
    expect(ws.idlePromptVisible.value).toBe(false)
    expect(ws.idlePaused.value).toBe(false)
  })
})

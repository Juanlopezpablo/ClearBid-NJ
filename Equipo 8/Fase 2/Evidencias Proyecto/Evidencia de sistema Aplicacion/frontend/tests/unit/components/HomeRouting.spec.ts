import { beforeEach, describe, expect, it, vi } from 'vitest'
const mocks = vi.hoisted(() => ({ auth: { ensureInitialized: vi.fn().mockResolvedValue(undefined), isAuthenticated: true, userRole: 'ADMIN', mustChangePassword: false } }))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => mocks.auth }))
vi.mock('@/views/HomeView.vue', () => ({ default: { render: () => null } }))
vi.mock('@/views/LoginView.vue', () => ({ default: { render: () => null } }))
vi.mock('@/views/shared/SettingsView.vue', () => ({ default: { render: () => null } }))
vi.mock('@/layouts/AdminLayout.vue', () => ({ default: { render: () => null } }))
vi.mock('@/layouts/DeveloperLayout.vue', () => ({ default: { render: () => null } }))
import router from '@/router'
describe('Navegación al inicio', () => {
  beforeEach(async () => { window.scrollTo = vi.fn(); mocks.auth.isAuthenticated = true; mocks.auth.userRole = 'ADMIN'; mocks.auth.mustChangePassword = false; await router.replace('/login') })
  it.each(['ADMIN', 'TEAM_LEADER', 'DEVELOPER'])('dirige %s al inicio desde la raíz', async role => {
    mocks.auth.userRole = role
    await router.push('/')
    expect(router.currentRoute.value.path).toBe('/home')
  })
  it('exige sesión para abrir el panel', async () => {
    mocks.auth.isAuthenticated = false
    await router.push('/home')
    expect(router.currentRoute.value.path).toBe('/login')
    expect(router.currentRoute.value.query.redirect).toBe('/home')
  })
  it('conserva el cambio obligatorio de contraseña', async () => {
    mocks.auth.mustChangePassword = true
    await router.push('/home')
    expect(router.currentRoute.value.path).toBe('/admin/settings')
    expect(router.currentRoute.value.query.forcePasswordChange).toBe('1')
  })
  it('devuelve al inicio al intentar abrir una sección de otro rol', async () => {
    mocks.auth.userRole = 'DEVELOPER'
    await router.push('/admin/team')
    expect(router.currentRoute.value.path).toBe('/home')
  })
})

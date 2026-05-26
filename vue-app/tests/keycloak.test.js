import { describe, it, expect, vi, beforeEach } from 'vitest'

const mockKeycloakInstance = {
  init: vi.fn(),
  token: 'fake-access-token',
  tokenParsed: {},
  idTokenParsed: { preferred_username: 'john.doe' },
  realmAccess: { roles: ['ROLE_ADMIN', 'ROLE_USER'] },
  accountManagement: vi.fn(),
  logout: vi.fn(),
}

const KeycloakMock = vi.fn(() => mockKeycloakInstance)
vi.mock('keycloak-js', () => ({ default: KeycloakMock }))

describe('keycloak.js', () => {
  let keycloakModule

  beforeEach(() => {
    vi.resetModules()
    vi.clearAllMocks()
  })

  describe('getUsername', () => {
    it('should return preferred_username from idTokenParsed', async () => {
      const { getUsername } = await import('../src/keycloak.js')
      expect(getUsername()).toBe('john.doe')
    })

    it('should return Anonymous when idTokenParsed is null', async () => {
      const saved = mockKeycloakInstance.idTokenParsed
      mockKeycloakInstance.idTokenParsed = null
      vi.resetModules()
      const { getUsername } = await import('../src/keycloak.js')
      expect(getUsername()).toBe('Anonymous')
      mockKeycloakInstance.idTokenParsed = saved
    })
  })

  describe('getRoles', () => {
    it('should return realm roles', async () => {
      const { getRoles } = await import('../src/keycloak.js')
      expect(getRoles()).toEqual(['ROLE_ADMIN', 'ROLE_USER'])
    })
  })

  describe('getAccessToken', () => {
    it('should return the access token', async () => {
      const { getAccessToken } = await import('../src/keycloak.js')
      expect(getAccessToken()).toBe('fake-access-token')
    })
  })

  describe('logout', () => {
    it('should call keycloak.logout', async () => {
      const { logout } = await import('../src/keycloak.js')
      logout()
      expect(mockKeycloakInstance.logout).toHaveBeenCalled()
    })
  })

  describe('gotoAccount', () => {
    it('should call keycloak.accountManagement', async () => {
      const { gotoAccount } = await import('../src/keycloak.js')
      gotoAccount()
      expect(mockKeycloakInstance.accountManagement).toHaveBeenCalled()
    })
  })

  describe('login', () => {
    it('should return a promise that resolves on init success', async () => {
      mockKeycloakInstance.init.mockResolvedValue(true)
      const { login } = await import('../src/keycloak.js')
      const result = await login()
      expect(result).toBeUndefined()
      expect(mockKeycloakInstance.init).toHaveBeenCalledWith({
        onLoad: 'login-required',
        checkLoginIframe: false
      })
    })

    it('should reject on init failure', async () => {
      const error = new Error('Init failed')
      mockKeycloakInstance.init.mockRejectedValue(error)
      const { login } = await import('../src/keycloak.js')
      await expect(login()).rejects.toEqual(error)
    })
  })
})

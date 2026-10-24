import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from './client'

function jsonResponse(status: number, body: unknown = {}): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

const fetchMock = vi.fn<typeof fetch>()

beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

function calledPaths(): string[] {
  return fetchMock.mock.calls.map(([url]) => String(url))
}

describe('apiClient refresh handling', () => {
  it('refreshes and retries /auth/me after the access token expires', async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse(401, { detail: 'Not authenticated' }))
      .mockResolvedValueOnce(jsonResponse(200, { message: 'Token refreshed' }))
      .mockResolvedValueOnce(jsonResponse(200, { id: 'user-1' }))

    await expect(apiClient.get('/auth/me')).resolves.toEqual({ id: 'user-1' })
    expect(calledPaths()).toEqual(['/api/auth/me', '/api/auth/refresh', '/api/auth/me'])
  })

  it('shares one refresh between parallel requests that all get 401', async () => {
    let refreshCalls = 0
    let refreshed = false
    fetchMock.mockImplementation(async (input) => {
      const url = String(input)
      if (url === '/api/auth/refresh') {
        refreshCalls += 1
        await new Promise((resolve) => setTimeout(resolve, 10))
        refreshed = true
        return jsonResponse(200, { message: 'Token refreshed' })
      }
      return refreshed ? jsonResponse(200, { url }) : jsonResponse(401, { detail: 'Not authenticated' })
    })

    const results = await Promise.all([apiClient.get('/children/a'), apiClient.get('/children/a/insights')])

    expect(refreshCalls).toBe(1)
    expect(results).toEqual([{ url: '/api/children/a' }, { url: '/api/children/a/insights' }])
  })

  it('does not try to refresh when login itself returns 401', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(401, { detail: 'Invalid email or password' }))

    await expect(apiClient.post('/auth/login', { email: 'a@b.c', password: 'x' })).rejects.toMatchObject({
      status: 401,
      message: 'Invalid email or password',
    })
    expect(calledPaths()).toEqual(['/api/auth/login'])
  })

  it('surfaces the original 401 when the refresh fails', async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse(401, { detail: 'Not authenticated' }))
      .mockResolvedValueOnce(jsonResponse(401, { detail: 'Session expired, please log in again' }))

    await expect(apiClient.get('/children')).rejects.toMatchObject({ status: 401, message: 'Not authenticated' })
  })

  it('does not send logout until an in-flight refresh has settled', async () => {
    let releaseRefresh: (response: Response) => void = () => {}
    fetchMock.mockImplementation((input) => {
      const url = String(input)
      if (url === '/api/auth/refresh') {
        return new Promise<Response>((resolve) => {
          releaseRefresh = resolve
        })
      }
      if (url === '/api/auth/logout') return Promise.resolve(jsonResponse(200, { message: 'Logged out' }))
      return Promise.resolve(jsonResponse(401, { detail: 'Not authenticated' }))
    })

    const pendingRequest = apiClient.get('/children').catch(() => undefined)
    await vi.waitFor(() => expect(calledPaths()).toContain('/api/auth/refresh'))

    const logout = apiClient.post('/auth/logout')
    await new Promise((resolve) => setTimeout(resolve, 20))
    // Logout is queued behind the refresh, so a late refresh response can't
    // re-set cookies after logout cleared them.
    expect(calledPaths()).not.toContain('/api/auth/logout')

    releaseRefresh(jsonResponse(401, { detail: 'Session expired, please log in again' }))
    await expect(logout).resolves.toEqual({ message: 'Logged out' })
    await pendingRequest
    const paths = calledPaths()
    expect(paths.indexOf('/api/auth/logout')).toBeGreaterThan(paths.indexOf('/api/auth/refresh'))
  })
})

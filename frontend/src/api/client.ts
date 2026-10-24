const API_BASE = '/api'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function parseErrorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json()
    return typeof body.detail === 'string' ? body.detail : res.statusText
  } catch {
    return res.statusText
  }
}

// Calls that set or clear the auth cookies.
const AUTH_TRANSITION_PATHS = new Set(['/auth/login', '/auth/register', '/auth/logout'])
// Endpoints whose 401 means "wrong credentials" or "session is over", not "access
// token expired". Every other path, /auth/me included, gets one refresh-and-retry.
const NO_REFRESH_PATHS = new Set([...AUTH_TRANSITION_PATHS, '/auth/refresh'])

// The backend rotates the refresh token on every use and treats a second presentation
// of a rotated token as theft (revoking every session). So cookie-changing calls (refresh,
// login, register, logout) must never overlap: a refresh response landing after a logout
// would otherwise restore a live session. They run one at a time through this queue, and
// the Web Locks API extends that across tabs, which share one cookie jar. Browsers without
// Web Locks get the within-tab guarantee only.
let authQueue: Promise<unknown> = Promise.resolve()

function runAuthExclusive<T>(task: () => Promise<T>): Promise<T> {
  const locked = () => ('locks' in navigator ? navigator.locks.request('auth-session', task) : task())
  const result = authQueue.then(locked, locked)
  authQueue = result.catch(() => undefined)
  return result
}

let refreshInFlight: Promise<boolean> | null = null

async function postRefresh(): Promise<boolean> {
  const res = await fetch(`${API_BASE}/auth/refresh`, { method: 'POST', credentials: 'include' })
  return res.ok
}

// Concurrent 401s in this tab share one in-flight refresh.
function refreshSession(): Promise<boolean> {
  if (!refreshInFlight) {
    refreshInFlight = runAuthExclusive(postRefresh)
      .catch(() => false)
      .finally(() => {
        refreshInFlight = null
      })
  }
  return refreshInFlight
}

async function request<T>(path: string, options: RequestInit = {}, isRetry = false): Promise<T> {
  const send = () =>
    fetch(`${API_BASE}${path}`, {
      ...options,
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    })
  const res = AUTH_TRANSITION_PATHS.has(path) ? await runAuthExclusive(send) : await send()

  if (res.status === 401 && !isRetry && !NO_REFRESH_PATHS.has(path)) {
    if (await refreshSession()) {
      return request<T>(path, options, true)
    }
  }

  if (!res.ok) {
    throw new ApiError(res.status, await parseErrorMessage(res))
  }

  if (res.status === 204) {
    return undefined as T
  }
  return (await res.json()) as T
}

export const apiClient = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'POST', body: body !== undefined ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
}

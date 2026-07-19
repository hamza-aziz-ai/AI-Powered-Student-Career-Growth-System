import { createContext, useCallback, useEffect, useState, type ReactNode } from 'react'
import { authApi, type LoginInput, type RegisterInput } from '../api/auth'
import { ApiError } from '../api/client'
import type { User } from '../api/types'

interface AuthContextValue {
  user: User | null
  status: 'loading' | 'authenticated' | 'unauthenticated'
  login: (data: LoginInput) => Promise<void>
  register: (data: RegisterInput) => Promise<void>
  logout: () => Promise<void>
}

// eslint-disable-next-line react-refresh/only-export-components
export const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [status, setStatus] = useState<'loading' | 'authenticated' | 'unauthenticated'>('loading')

  const refreshSession = useCallback(async () => {
    try {
      const me = await authApi.me()
      setUser(me)
      setStatus('authenticated')
    } catch (err) {
      setUser(null)
      setStatus('unauthenticated')
      if (!(err instanceof ApiError) || err.status !== 401) {
        console.error('Failed to load session', err)
      }
    }
  }, [])

  useEffect(() => {
    void refreshSession()
  }, [refreshSession])

  const login = useCallback(async (data: LoginInput) => {
    const loggedInUser = await authApi.login(data)
    setUser(loggedInUser)
    setStatus('authenticated')
  }, [])

  const register = useCallback(async (data: RegisterInput) => {
    const registeredUser = await authApi.register(data)
    setUser(registeredUser)
    setStatus('authenticated')
  }, [])

  const logout = useCallback(async () => {
    await authApi.logout()
    setUser(null)
    setStatus('unauthenticated')
  }, [])

  return (
    <AuthContext.Provider value={{ user, status, login, register, logout }}>{children}</AuthContext.Provider>
  )
}

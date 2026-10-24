import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { authApi } from '../api/auth'
import { ApiError } from '../api/client'
import type { User } from '../api/types'
import { AuthProvider } from './AuthContext'
import { useAuth } from './useAuth'

vi.mock('../api/auth', () => ({
  authApi: {
    me: vi.fn(),
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  },
}))

const mockedAuthApi = vi.mocked(authApi)

const testUser: User = {
  id: 'user-1',
  email: 'parent@example.com',
  full_name: 'Test Parent',
  is_active: true,
  is_email_verified: false,
  created_at: '2026-01-01T00:00:00Z',
}

function TestConsumer() {
  const { user, status, login, logout } = useAuth()
  return (
    <div>
      <span data-testid="status">{status}</span>
      <span data-testid="user">{user?.full_name ?? 'none'}</span>
      <button onClick={() => void login({ email: testUser.email, password: 'password123' })}>login</button>
      <button onClick={() => void logout()}>logout</button>
    </div>
  )
}

function renderWithProviders(queryClient = new QueryClient()) {
  render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    </QueryClientProvider>,
  )
  return queryClient
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('AuthProvider', () => {
  it('starts loading then becomes unauthenticated when /me fails with 401', async () => {
    mockedAuthApi.me.mockRejectedValue(new ApiError(401, 'Not authenticated'))

    renderWithProviders()

    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('unauthenticated'))
    expect(screen.getByTestId('user')).toHaveTextContent('none')
  })

  it('becomes authenticated when /me succeeds', async () => {
    mockedAuthApi.me.mockResolvedValue(testUser)

    renderWithProviders()

    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('authenticated'))
    expect(screen.getByTestId('user')).toHaveTextContent('Test Parent')
  })

  it('login() transitions state to authenticated with the returned user', async () => {
    mockedAuthApi.me.mockRejectedValue(new ApiError(401, 'Not authenticated'))
    mockedAuthApi.login.mockResolvedValue(testUser)
    const user = userEvent.setup()

    renderWithProviders()

    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('unauthenticated'))

    await user.click(screen.getByText('login'))

    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('authenticated'))
    expect(screen.getByTestId('user')).toHaveTextContent('Test Parent')
  })

  it('logout() clears the user and sets status to unauthenticated', async () => {
    mockedAuthApi.me.mockResolvedValue(testUser)
    mockedAuthApi.logout.mockResolvedValue({ message: 'Logged out' })
    const user = userEvent.setup()

    renderWithProviders()

    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('authenticated'))

    await user.click(screen.getByText('logout'))

    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('unauthenticated'))
    expect(screen.getByTestId('user')).toHaveTextContent('none')
  })

  it('logout() drops cached data so the next parent never sees it', async () => {
    mockedAuthApi.me.mockResolvedValue(testUser)
    mockedAuthApi.logout.mockResolvedValue({ message: 'Logged out' })
    const queryClient = new QueryClient()
    queryClient.setQueryData(['children'], [{ id: 'child-1' }])
    const user = userEvent.setup()

    renderWithProviders(queryClient)
    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('authenticated'))

    await user.click(screen.getByText('logout'))

    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('unauthenticated'))
    expect(queryClient.getQueryData(['children'])).toBeUndefined()
  })

  it('ignores a slow startup session check that finishes after a login', async () => {
    let rejectMe: (err: unknown) => void = () => {}
    mockedAuthApi.me.mockReturnValue(
      new Promise((_, reject) => {
        rejectMe = reject
      }),
    )
    mockedAuthApi.login.mockResolvedValue(testUser)
    const user = userEvent.setup()

    renderWithProviders()
    await user.click(screen.getByText('login'))
    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('authenticated'))

    rejectMe(new ApiError(401, 'Not authenticated'))
    await new Promise((resolve) => setTimeout(resolve, 20))
    expect(screen.getByTestId('status')).toHaveTextContent('authenticated')
    expect(screen.getByTestId('user')).toHaveTextContent('Test Parent')
  })
})

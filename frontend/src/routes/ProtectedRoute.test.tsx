import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { useAuth } from '../auth/useAuth'
import { ProtectedRoute } from './ProtectedRoute'

vi.mock('../auth/useAuth')

const mockedUseAuth = vi.mocked(useAuth)

function renderProtected() {
  return render(
    <MemoryRouter initialEntries={['/dashboard']}>
      <Routes>
        <Route path="/login" element={<div>Login page</div>} />
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<div>Dashboard content</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  )
}

describe('ProtectedRoute', () => {
  it('shows a loading state while auth status is loading', () => {
    mockedUseAuth.mockReturnValue({
      user: null,
      status: 'loading',
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
    })

    renderProtected()

    expect(screen.getByText(/loading/i)).toBeInTheDocument()
    expect(screen.queryByText('Dashboard content')).not.toBeInTheDocument()
  })

  it('redirects to /login when unauthenticated', () => {
    mockedUseAuth.mockReturnValue({
      user: null,
      status: 'unauthenticated',
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
    })

    renderProtected()

    expect(screen.getByText('Login page')).toBeInTheDocument()
    expect(screen.queryByText('Dashboard content')).not.toBeInTheDocument()
  })

  it('renders the protected content when authenticated', () => {
    mockedUseAuth.mockReturnValue({
      user: {
        id: 'user-1',
        email: 'parent@example.com',
        full_name: 'Test Parent',
        is_active: true,
        is_email_verified: false,
        created_at: '2026-01-01T00:00:00Z',
      },
      status: 'authenticated',
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
    })

    renderProtected()

    expect(screen.getByText('Dashboard content')).toBeInTheDocument()
  })
})

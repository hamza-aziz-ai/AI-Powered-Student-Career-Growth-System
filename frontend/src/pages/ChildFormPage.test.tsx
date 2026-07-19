import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { childrenApi } from '../api/children'
import { ChildFormPage } from './ChildFormPage'

vi.mock('../api/children', () => ({
  childrenApi: {
    list: vi.fn(),
    get: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    remove: vi.fn(),
  },
}))

const mockedChildrenApi = vi.mocked(childrenApi)

function renderNewChildForm() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/children/new']}>
        <Routes>
          <Route path="/children/new" element={<ChildFormPage />} />
          <Route path="/dashboard" element={<div>Dashboard page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('ChildFormPage validation', () => {
  it('shows a required-field error and does not submit when first name is empty', async () => {
    const user = userEvent.setup()
    renderNewChildForm()

    await user.click(screen.getByRole('button', { name: /add child/i }))

    expect(await screen.findByText(/first name is required/i)).toBeInTheDocument()
    expect(mockedChildrenApi.create).not.toHaveBeenCalled()
  })

  it('rejects a birth year outside the allowed child age range', async () => {
    const user = userEvent.setup()
    renderNewChildForm()

    await user.type(screen.getByLabelText(/first name/i), 'Alex')
    const birthYearInput = screen.getByLabelText(/birth year/i)
    await user.clear(birthYearInput)
    await user.type(birthYearInput, '1990')

    await user.click(screen.getByRole('button', { name: /add child/i }))

    expect(await screen.findByText(/birth year must be/i)).toBeInTheDocument()
    expect(mockedChildrenApi.create).not.toHaveBeenCalled()
  })

  it('submits successfully with valid data and navigates to the dashboard', async () => {
    mockedChildrenApi.create.mockResolvedValue({
      id: 'child-1',
      parent_id: 'user-1',
      first_name: 'Alex',
      birth_year: 2016,
      grade_level: null,
      interests: [],
      strengths: [],
      favorite_subjects: null,
      notes: null,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    })
    const user = userEvent.setup()
    renderNewChildForm()

    await user.type(screen.getByLabelText(/first name/i), 'Alex')
    const birthYearInput = screen.getByLabelText(/birth year/i)
    await user.clear(birthYearInput)
    await user.type(birthYearInput, '2016')

    await user.click(screen.getByRole('button', { name: /add child/i }))

    await waitFor(() => expect(mockedChildrenApi.create).toHaveBeenCalledTimes(1))
    expect(await screen.findByText('Dashboard page')).toBeInTheDocument()
  })
})

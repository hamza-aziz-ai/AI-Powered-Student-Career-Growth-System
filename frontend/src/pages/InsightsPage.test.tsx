import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { childrenApi } from '../api/children'
import { insightsApi } from '../api/insights'
import type { CareerInsight } from '../api/types'
import { useAuth } from '../auth/useAuth'
import { InsightsPage } from './InsightsPage'

vi.mock('../api/children', () => ({ childrenApi: { get: vi.fn() } }))
vi.mock('../api/insights', () => ({ insightsApi: { list: vi.fn(), generate: vi.fn() } }))
vi.mock('../auth/useAuth')

function insight(overrides: Partial<CareerInsight>): CareerInsight {
  return {
    id: 'insight-1',
    child_id: 'child-1',
    model_name: 'test-model',
    status: 'completed',
    result_text: null,
    result_json: null,
    error_message: null,
    generated_at: null,
    created_at: '2026-10-01T10:00:00Z',
    ...overrides,
  }
}

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/children/child-1/insights']}>
        <Routes>
          <Route path="/children/:childId/insights" element={<InsightsPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(useAuth).mockReturnValue({
    user: null,
    status: 'authenticated',
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  })
  vi.mocked(childrenApi.get).mockResolvedValue({
    id: 'child-1',
    parent_id: 'user-1',
    first_name: 'Riley',
    birth_year: 2016,
    grade_level: null,
    interests: [],
    strengths: [],
    favorite_subjects: null,
    notes: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  })
})

describe('InsightsPage history', () => {
  it('shows a pending insight as still generating', async () => {
    vi.mocked(insightsApi.list).mockResolvedValue([insight({ status: 'pending' })])
    renderPage()
    expect(await screen.findByText(/still generating/i)).toBeInTheDocument()
  })

  it('renders an older malformed result without crashing', async () => {
    // Saved before output validation existed: summary only, no lists.
    const malformed = { summary: 'Loves building things.' } as unknown as CareerInsight['result_json']
    vi.mocked(insightsApi.list).mockResolvedValue([insight({ result_json: malformed })])
    renderPage()
    expect(await screen.findByText('Loves building things.')).toBeInTheDocument()
  })

  it('skips null suggestions and non-text values in an older result', async () => {
    const malformed = {
      summary: { nested: 'object where text belongs' },
      career_suggestions: [null, { title: 'Robotics Engineer', related_subjects: [null, 'science', 42] }],
      growth_areas: 'not a list',
      disclaimer: 'Exploratory only.',
    } as unknown as CareerInsight['result_json']
    vi.mocked(insightsApi.list).mockResolvedValue([insight({ result_json: malformed })])
    renderPage()
    expect(await screen.findByText('Robotics Engineer')).toBeInTheDocument()
    expect(screen.getByText('science')).toBeInTheDocument()
    expect(screen.getByText('Exploratory only.')).toBeInTheDocument()
    expect(screen.queryByText(/object where text belongs/)).not.toBeInTheDocument()
  })
})

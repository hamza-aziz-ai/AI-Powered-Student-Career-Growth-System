import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { childrenApi } from '../api/children'
import { ApiError } from '../api/client'
import { insightsApi } from '../api/insights'
import { AppHeader } from '../components/AppHeader'
import { Spinner } from '../components/Spinner'
// The backend validates new results, but rows saved before that validation existed can
// hold anything (null items, objects where text belongs). Render only values of the
// expected type and skip the rest.
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function asText(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

function asTextList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string' && item !== '') : []
}

function InsightResultView({ result }: { result: unknown }) {
  const data = isRecord(result) ? result : {}
  const summary = asText(data.summary)
  const disclaimer = asText(data.disclaimer)
  const growthAreas = asTextList(data.growth_areas)
  const suggestions = (Array.isArray(data.career_suggestions) ? data.career_suggestions : [])
    .filter(isRecord)
    .map((suggestion) => ({
      title: asText(suggestion.title),
      rationale: asText(suggestion.rationale),
      subjects: asTextList(suggestion.related_subjects),
      activities: asTextList(suggestion.suggested_activities),
    }))
    .filter((suggestion) => suggestion.title || suggestion.rationale)

  return (
    <>
      {summary && <p className="insight-summary">{summary}</p>}
      <div className="career-suggestions">
        {suggestions.map((suggestion, index) => (
          <div key={`${index}-${suggestion.title}`} className="career-suggestion">
            {suggestion.title && <h3>{suggestion.title}</h3>}
            {suggestion.rationale && <p>{suggestion.rationale}</p>}
            {suggestion.subjects.length > 0 && (
              <div className="tag-pills">
                {suggestion.subjects.map((subject) => (
                  <span key={subject} className="tag-pill">
                    {subject}
                  </span>
                ))}
              </div>
            )}
            {suggestion.activities.length > 0 && (
              <ul>
                {suggestion.activities.map((activity) => (
                  <li key={activity}>{activity}</li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>
      {growthAreas.length > 0 && (
        <p className="growth-areas">
          <strong>Growth areas: </strong>
          {growthAreas.join(', ')}
        </p>
      )}
      {disclaimer && <p className="insight-disclaimer">{disclaimer}</p>}
    </>
  )
}

export function InsightsPage() {
  const { childId } = useParams<{ childId: string }>()
  const queryClient = useQueryClient()

  const { data: child } = useQuery({
    queryKey: ['children', childId],
    queryFn: () => childrenApi.get(childId as string),
    enabled: Boolean(childId),
  })

  const { data: insights, isLoading: isLoadingInsights } = useQuery({
    queryKey: ['insights', childId],
    queryFn: () => insightsApi.list(childId as string),
    enabled: Boolean(childId),
  })

  const generateMutation = useMutation({
    mutationFn: () => insightsApi.generate(childId as string),
    // A failed generation is still saved as a `failed` row, so refresh history either way.
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: ['insights', childId] })
    },
  })

  return (
    <>
      <AppHeader backTo={{ to: '/dashboard', label: 'Dashboard' }} />
      <div className="page-container">
        <div className="insights-toolbar">
          <div>
            <h1>{child ? `${child.first_name}'s career insights` : 'Career insights'}</h1>
            <p className="dashboard-subtitle">AI-generated, exploratory career guidance — not a formal assessment.</p>
          </div>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => generateMutation.mutate()}
            disabled={generateMutation.isPending}
          >
            {generateMutation.isPending ? <Spinner label="Generating… up to a minute" /> : '✨ Generate new insight'}
          </button>
        </div>

        {generateMutation.isError && (
          <p className="form-error">
            {generateMutation.error instanceof ApiError
              ? generateMutation.error.message
              : 'Something went wrong generating this insight.'}
          </p>
        )}

        {isLoadingInsights && (
          <p className="page-loading">
            <Spinner label="Loading insight history…" />
          </p>
        )}

        {insights && insights.length === 0 && !generateMutation.isPending && (
          <div className="empty-state card">
            <span className="empty-state-icon" aria-hidden="true">
              ✨
            </span>
            <p>No insights yet.</p>
            <p>Click "Generate new insight" to get started.</p>
          </div>
        )}

        <ul className="insight-list">
          {insights?.map((insight) => (
            <li key={insight.id} className="insight-card card">
              <p className="insight-date">{new Date(insight.created_at).toLocaleString()}</p>

              {insight.status === 'pending' && (
                <p className="dashboard-subtitle">
                  <Spinner label="Still generating… refresh in a minute to see the result." />
                </p>
              )}

              {insight.status === 'failed' && (
                <p className="form-error">{insight.error_message ?? 'This insight could not be generated.'}</p>
              )}

              {insight.status === 'completed' && insight.result_json && <InsightResultView result={insight.result_json} />}
            </li>
          ))}
        </ul>
      </div>
    </>
  )
}

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { childrenApi } from '../api/children'
import { ApiError } from '../api/client'
import { insightsApi } from '../api/insights'
import { AppHeader } from '../components/AppHeader'
import { Spinner } from '../components/Spinner'

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
    onSuccess: () => {
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

              {insight.status === 'failed' && (
                <p className="form-error">{insight.error_message ?? 'This insight could not be generated.'}</p>
              )}

              {insight.status === 'completed' && insight.result_json && (
                <>
                  <p className="insight-summary">{insight.result_json.summary}</p>
                  <div className="career-suggestions">
                    {insight.result_json.career_suggestions.map((suggestion) => (
                      <div key={suggestion.title} className="career-suggestion">
                        <h3>{suggestion.title}</h3>
                        <p>{suggestion.rationale}</p>
                        {suggestion.related_subjects.length > 0 && (
                          <div className="tag-pills">
                            {suggestion.related_subjects.map((subject) => (
                              <span key={subject} className="tag-pill">
                                {subject}
                              </span>
                            ))}
                          </div>
                        )}
                        {suggestion.suggested_activities.length > 0 && (
                          <ul>
                            {suggestion.suggested_activities.map((activity) => (
                              <li key={activity}>{activity}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                    ))}
                  </div>
                  {insight.result_json.growth_areas.length > 0 && (
                    <p className="growth-areas">
                      <strong>Growth areas: </strong>
                      {insight.result_json.growth_areas.join(', ')}
                    </p>
                  )}
                  <p className="insight-disclaimer">{insight.result_json.disclaimer}</p>
                </>
              )}
            </li>
          ))}
        </ul>
      </div>
    </>
  )
}

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { childrenApi } from '../api/children'
import { ApiError } from '../api/client'
import { insightsApi } from '../api/insights'

export function InsightsPage() {
  const { childId } = useParams<{ childId: string }>()
  const queryClient = useQueryClient()

  const { data: child } = useQuery({
    queryKey: ['children', childId],
    queryFn: () => childrenApi.get(childId as string),
    enabled: Boolean(childId),
  })

  const {
    data: insights,
    isLoading: isLoadingInsights,
  } = useQuery({
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
    <div className="dashboard-page">
      <header className="dashboard-header">
        <div>
          <Link to="/dashboard">← Back to dashboard</Link>
          <h1>{child ? `${child.first_name}'s career insights` : 'Career insights'}</h1>
        </div>
        <button type="button" onClick={() => generateMutation.mutate()} disabled={generateMutation.isPending}>
          {generateMutation.isPending ? 'Generating… this can take up to a minute' : 'Generate new insight'}
        </button>
      </header>

      {generateMutation.isError && (
        <p className="form-error">
          {generateMutation.error instanceof ApiError
            ? generateMutation.error.message
            : 'Something went wrong generating this insight.'}
        </p>
      )}

      {isLoadingInsights && <p>Loading insight history…</p>}
      {insights && insights.length === 0 && !generateMutation.isPending && (
        <p>No insights yet — click "Generate new insight" to get started.</p>
      )}

      <ul className="insight-list">
        {insights?.map((insight) => (
          <li key={insight.id} className="insight-card">
            <p className="insight-date">{new Date(insight.created_at).toLocaleString()}</p>

            {insight.status === 'failed' && (
              <p className="form-error">{insight.error_message ?? 'This insight could not be generated.'}</p>
            )}

            {insight.status === 'completed' && insight.result_json && (
              <>
                <p>{insight.result_json.summary}</p>
                <div className="career-suggestions">
                  {insight.result_json.career_suggestions.map((suggestion) => (
                    <div key={suggestion.title} className="career-suggestion">
                      <h3>{suggestion.title}</h3>
                      <p>{suggestion.rationale}</p>
                      {suggestion.related_subjects.length > 0 && (
                        <p className="child-card-tags">Subjects: {suggestion.related_subjects.join(', ')}</p>
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
                  <p className="child-card-tags">Growth areas: {insight.result_json.growth_areas.join(', ')}</p>
                )}
                <p className="insight-disclaimer">{insight.result_json.disclaimer}</p>
              </>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}

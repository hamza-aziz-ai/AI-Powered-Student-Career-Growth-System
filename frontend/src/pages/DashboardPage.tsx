import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { childrenApi } from '../api/children'
import { AppHeader } from '../components/AppHeader'
import { Spinner } from '../components/Spinner'
import { useAuth } from '../auth/useAuth'

export function DashboardPage() {
  const { user } = useAuth()
  const {
    data: children,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['children'],
    queryFn: childrenApi.list,
  })

  return (
    <>
      <AppHeader />
      <div className="page-container">
        <div className="dashboard-toolbar">
          <div>
            <h1>Hi, {user?.full_name.split(' ')[0]} 👋</h1>
            <p className="dashboard-subtitle">Here are the children you're tracking career insights for.</p>
          </div>
          <Link to="/children/new" className="btn btn-primary">
            + Add child
          </Link>
        </div>

        {isLoading && (
          <p className="page-loading">
            <Spinner label="Loading your children…" />
          </p>
        )}
        {isError && <p className="form-error">Couldn't load your children. Please refresh.</p>}

        {children && children.length === 0 && (
          <div className="empty-state card">
            <span className="empty-state-icon" aria-hidden="true">
              🧒
            </span>
            <p>You haven't added a child yet.</p>
            <p>Add one to get started with personalized career insights.</p>
          </div>
        )}

        <ul className="child-card-list">
          {children?.map((child) => (
            <li key={child.id} className="child-card card">
              <div className="child-card-top">
                <span className="child-avatar" aria-hidden="true">
                  {child.first_name.charAt(0).toUpperCase()}
                </span>
                <div>
                  <h2>{child.first_name}</h2>
                  <p className="child-card-grade">{child.grade_level ?? 'Grade not specified'}</p>
                </div>
              </div>
              {child.interests.length > 0 && (
                <div className="tag-pills">
                  {child.interests.slice(0, 4).map((interest) => (
                    <span key={interest} className="tag-pill">
                      {interest}
                    </span>
                  ))}
                </div>
              )}
              <div className="child-card-actions">
                <Link to={`/children/${child.id}/insights`}>View insights</Link>
                <Link to={`/children/${child.id}/edit`}>Edit</Link>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </>
  )
}

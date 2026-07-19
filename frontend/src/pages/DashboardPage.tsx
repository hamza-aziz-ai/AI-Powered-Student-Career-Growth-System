import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { childrenApi } from '../api/children'
import { useAuth } from '../auth/useAuth'

export function DashboardPage() {
  const { user, logout } = useAuth()
  const { data: children, isLoading, isError } = useQuery({
    queryKey: ['children'],
    queryFn: childrenApi.list,
  })

  return (
    <div className="dashboard-page">
      <header className="dashboard-header">
        <h1>Welcome, {user?.full_name}</h1>
        <button type="button" onClick={() => void logout()}>
          Log out
        </button>
      </header>

      <div className="dashboard-toolbar">
        <Link to="/children/new" className="button-link">
          + Add child
        </Link>
      </div>

      {isLoading && <p>Loading your children…</p>}
      {isError && <p className="form-error">Couldn't load your children. Please refresh.</p>}

      {children && children.length === 0 && (
        <p>You haven't added a child yet. Add one to get started with career insights.</p>
      )}

      <ul className="child-card-list">
        {children?.map((child) => (
          <li key={child.id} className="child-card">
            <h2>{child.first_name}</h2>
            <p>{child.grade_level ?? 'Grade not specified'}</p>
            {child.interests.length > 0 && <p className="child-card-tags">Interests: {child.interests.join(', ')}</p>}
            <div className="child-card-actions">
              <Link to={`/children/${child.id}/insights`}>View insights</Link>
              <Link to={`/children/${child.id}/edit`}>Edit</Link>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}

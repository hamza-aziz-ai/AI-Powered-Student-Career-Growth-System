import { Link } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'

interface AppHeaderProps {
  backTo?: { to: string; label: string }
}

export function AppHeader({ backTo }: AppHeaderProps) {
  const { user, logout } = useAuth()

  return (
    <header className="app-header">
      <div className="app-header-left">
        <Link to="/dashboard" className="brand">
          <span className="brand-mark" aria-hidden="true">
            🌱
          </span>
          Career Growth AI
        </Link>
        {backTo && (
          <Link to={backTo.to} className="app-header-back">
            ← {backTo.label}
          </Link>
        )}
      </div>
      <div className="app-header-right">
        {user && <span className="app-header-user">Hi, {user.full_name.split(' ')[0]}</span>}
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => void logout()}>
          Log out
        </button>
      </div>
    </header>
  )
}

import { Navigate, Route, Routes } from 'react-router-dom'
import { ChildFormPage } from '../pages/ChildFormPage'
import { DashboardPage } from '../pages/DashboardPage'
import { InsightsPage } from '../pages/InsightsPage'
import { LoginPage } from '../pages/LoginPage'
import { SignupPage } from '../pages/SignupPage'
import { ProtectedRoute } from './ProtectedRoute'

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />

      <Route element={<ProtectedRoute />}>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/children/new" element={<ChildFormPage />} />
        <Route path="/children/:childId/edit" element={<ChildFormPage />} />
        <Route path="/children/:childId/insights" element={<InsightsPage />} />
      </Route>

      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}

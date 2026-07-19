import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import { ApiError } from '../api/client'
import { Spinner } from '../components/Spinner'
import { loginSchema, type LoginFormValues } from '../schemas/authSchemas'

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [serverError, setServerError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({ resolver: zodResolver(loginSchema) })

  const onSubmit = async (data: LoginFormValues) => {
    setServerError(null)
    try {
      await login(data)
      navigate('/dashboard')
    } catch (err) {
      setServerError(err instanceof ApiError ? 'Invalid email or password.' : 'Something went wrong. Please try again.')
    }
  }

  return (
    <div className="auth-page">
      <div className="card auth-card">
        <span className="auth-brand" aria-hidden="true">
          🌱
        </span>
        <h1>Welcome back</h1>
        <p className="auth-subtitle">Log in to see your children's career insights.</p>
        <form onSubmit={handleSubmit(onSubmit)} noValidate>
          <label>
            Email
            <input type="email" autoComplete="email" {...register('email')} />
            {errors.email && <span className="field-error">{errors.email.message}</span>}
          </label>

          <label>
            Password
            <input type="password" autoComplete="current-password" {...register('password')} />
            {errors.password && <span className="field-error">{errors.password.message}</span>}
          </label>

          {serverError && <p className="form-error">{serverError}</p>}

          <button type="submit" className="btn btn-primary btn-block" disabled={isSubmitting}>
            {isSubmitting ? <Spinner label="Logging in…" /> : 'Log in'}
          </button>
        </form>
        <p className="auth-switch">
          Don't have an account? <Link to="/signup">Sign up</Link>
        </p>
      </div>
    </div>
  )
}

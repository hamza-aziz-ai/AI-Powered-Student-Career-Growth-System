import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import { ApiError } from '../api/client'
import { registerSchema, type RegisterFormValues } from '../schemas/authSchemas'

export function SignupPage() {
  const { register: registerUser } = useAuth()
  const navigate = useNavigate()
  const [serverError, setServerError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormValues>({ resolver: zodResolver(registerSchema) })

  const onSubmit = async (data: RegisterFormValues) => {
    setServerError(null)
    try {
      await registerUser({ email: data.email, password: data.password, full_name: data.full_name })
      navigate('/dashboard')
    } catch (err) {
      setServerError(err instanceof ApiError ? err.message : 'Something went wrong. Please try again.')
    }
  }

  return (
    <div className="auth-page">
      <h1>Create your account</h1>
      <p className="auth-subtitle">
        Parents only — you'll add your child's details after signing up. Your child never needs their own login.
      </p>
      <form onSubmit={handleSubmit(onSubmit)} noValidate>
        <label>
          Your name
          <input type="text" autoComplete="name" {...register('full_name')} />
          {errors.full_name && <span className="field-error">{errors.full_name.message}</span>}
        </label>

        <label>
          Email
          <input type="email" autoComplete="email" {...register('email')} />
          {errors.email && <span className="field-error">{errors.email.message}</span>}
        </label>

        <label>
          Password
          <input type="password" autoComplete="new-password" {...register('password')} />
          {errors.password && <span className="field-error">{errors.password.message}</span>}
        </label>

        <label>
          Confirm password
          <input type="password" autoComplete="new-password" {...register('confirmPassword')} />
          {errors.confirmPassword && <span className="field-error">{errors.confirmPassword.message}</span>}
        </label>

        {serverError && <p className="form-error">{serverError}</p>}

        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Creating account…' : 'Create account'}
        </button>
      </form>
      <p>
        Already have an account? <Link to="/login">Log in</Link>
      </p>
    </div>
  )
}

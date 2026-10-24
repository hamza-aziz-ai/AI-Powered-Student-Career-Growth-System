import { zodResolver } from '@hookform/resolvers/zod'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { useNavigate, useParams } from 'react-router-dom'
import { childrenApi } from '../api/children'
import { ApiError } from '../api/client'
import { AppHeader } from '../components/AppHeader'
import { Spinner } from '../components/Spinner'
import { TagInput } from '../components/TagInput'
import { birthYearBounds, childProfileSchema, type ChildProfileFormValues } from '../schemas/childProfileSchema'
import type { Child } from '../api/types'
import type { FieldError, FieldErrors } from 'react-hook-form'

// Tag-list fields can fail either at the array level (too many entries) or on
// one specific item (an entry too long) — surface whichever fired so a bad
// tag never fails validation silently, which is what happened here before.
function tagListErrorMessage(error: FieldErrors<ChildProfileFormValues>['interests']): string | undefined {
  if (!error) return undefined
  if ((error as FieldError).message) return (error as FieldError).message
  if (Array.isArray(error)) {
    const itemError = error.find((item) => item?.message)
    return itemError?.message
  }
  return undefined
}

function toFormValues(child?: Child): ChildProfileFormValues {
  if (!child) {
    return {
      first_name: '',
      birth_year: birthYearBounds().max,
      grade_level: '',
      interests: [],
      strengths: [],
      favorite_subjects: [],
      notes: '',
    }
  }
  return {
    first_name: child.first_name,
    birth_year: child.birth_year,
    grade_level: child.grade_level ?? '',
    interests: child.interests,
    strengths: child.strengths,
    favorite_subjects: child.favorite_subjects ?? [],
    notes: child.notes ?? '',
  }
}

export function ChildFormPage() {
  const { childId } = useParams<{ childId: string }>()
  const isEditing = Boolean(childId)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [serverError, setServerError] = useState<string | null>(null)
  const yearBounds = birthYearBounds()

  const { data: existingChild, isLoading: isLoadingChild } = useQuery({
    queryKey: ['children', childId],
    queryFn: () => childrenApi.get(childId as string),
    enabled: isEditing,
  })

  const {
    control,
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ChildProfileFormValues>({
    resolver: zodResolver(childProfileSchema),
    defaultValues: toFormValues(),
    values: isEditing && existingChild ? toFormValues(existingChild) : undefined,
  })

  const onSubmit = async (data: ChildProfileFormValues) => {
    setServerError(null)
    const payload = {
      first_name: data.first_name,
      birth_year: data.birth_year,
      grade_level: data.grade_level || null,
      interests: data.interests,
      strengths: data.strengths,
      favorite_subjects: data.favorite_subjects && data.favorite_subjects.length > 0 ? data.favorite_subjects : null,
      notes: data.notes || null,
    }

    try {
      if (isEditing && childId) {
        await childrenApi.update(childId, payload)
      } else {
        await childrenApi.create(payload)
      }
      await queryClient.invalidateQueries({ queryKey: ['children'] })
      navigate('/dashboard')
    } catch (err) {
      setServerError(err instanceof ApiError ? err.message : 'Something went wrong. Please try again.')
    }
  }

  return (
    <>
      <AppHeader backTo={{ to: '/dashboard', label: 'Dashboard' }} />
      <div className="page-container page-container-narrow">
        {isEditing && isLoadingChild ? (
          <p className="page-loading">
            <Spinner label="Loading…" />
          </p>
        ) : (
          <div className="card">
            <h1>{isEditing ? 'Edit child profile' : 'Add a child'}</h1>
            <p className="auth-subtitle">
              Only what's needed to generate helpful, age-appropriate insights — no photos, no school name.
            </p>
            <p className="auth-subtitle">
              To generate insights, the AI service (a cloud-hosted model) receives only an approximate age, the grade,
              interests, strengths and favorite subjects. It never receives your child's name or your notes. Avoid
              putting names or other identifying details in those fields.
            </p>
            <form onSubmit={handleSubmit(onSubmit)} noValidate>
              <div className="field-row">
                <label>
                  First name
                  <input type="text" {...register('first_name')} />
                  {errors.first_name && <span className="field-error">{errors.first_name.message}</span>}
                </label>

                <label>
                  Birth year
                  <input
                    type="number"
                    min={yearBounds.min}
                    max={yearBounds.max}
                    {...register('birth_year', { valueAsNumber: true })}
                  />
                  {errors.birth_year && <span className="field-error">{errors.birth_year.message}</span>}
                </label>
              </div>

              <label>
                Grade level
                <input type="text" placeholder="e.g. 5th grade" {...register('grade_level')} />
              </label>

              <label>
                Interests
                <Controller
                  control={control}
                  name="interests"
                  render={({ field }) => (
                    <TagInput value={field.value ?? []} onChange={field.onChange} placeholder="Type and press Enter" />
                  )}
                />
                {tagListErrorMessage(errors.interests) && (
                  <span className="field-error">{tagListErrorMessage(errors.interests)}</span>
                )}
              </label>

              <label>
                Strengths
                <Controller
                  control={control}
                  name="strengths"
                  render={({ field }) => (
                    <TagInput value={field.value ?? []} onChange={field.onChange} placeholder="Type and press Enter" />
                  )}
                />
                {tagListErrorMessage(errors.strengths) && (
                  <span className="field-error">{tagListErrorMessage(errors.strengths)}</span>
                )}
              </label>

              <label>
                Favorite subjects (optional)
                <Controller
                  control={control}
                  name="favorite_subjects"
                  render={({ field }) => (
                    <TagInput value={field.value ?? []} onChange={field.onChange} placeholder="Type and press Enter" />
                  )}
                />
                {tagListErrorMessage(errors.favorite_subjects) && (
                  <span className="field-error">{tagListErrorMessage(errors.favorite_subjects)}</span>
                )}
              </label>

              <label>
                Private notes (optional, not sent to the AI)
                <textarea rows={3} maxLength={1000} {...register('notes')} />
              </label>

              {serverError && <p className="form-error">{serverError}</p>}

              <button type="submit" className="btn btn-primary btn-block" disabled={isSubmitting}>
                {isSubmitting ? (
                  <Spinner label="Saving…" />
                ) : isEditing ? (
                  'Save changes'
                ) : (
                  'Add child'
                )}
              </button>
            </form>
          </div>
        )}
      </div>
    </>
  )
}

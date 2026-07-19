import { zodResolver } from '@hookform/resolvers/zod'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { useNavigate, useParams } from 'react-router-dom'
import { childrenApi } from '../api/children'
import { ApiError } from '../api/client'
import { TagInput } from '../components/TagInput'
import { childProfileSchema, MAX_BIRTH_YEAR, MIN_BIRTH_YEAR, type ChildProfileFormValues } from '../schemas/childProfileSchema'
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
      birth_year: MAX_BIRTH_YEAR,
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

  if (isEditing && isLoadingChild) {
    return <p className="page-loading">Loading…</p>
  }

  return (
    <div className="auth-page">
      <h1>{isEditing ? 'Edit child profile' : 'Add a child'}</h1>
      <form onSubmit={handleSubmit(onSubmit)} noValidate>
        <label>
          First name
          <input type="text" {...register('first_name')} />
          {errors.first_name && <span className="field-error">{errors.first_name.message}</span>}
        </label>

        <label>
          Birth year
          <input
            type="number"
            min={MIN_BIRTH_YEAR}
            max={MAX_BIRTH_YEAR}
            {...register('birth_year', { valueAsNumber: true })}
          />
          {errors.birth_year && <span className="field-error">{errors.birth_year.message}</span>}
        </label>

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
          Notes for the AI (optional)
          <textarea rows={3} maxLength={1000} {...register('notes')} />
        </label>

        {serverError && <p className="form-error">{serverError}</p>}

        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Saving…' : isEditing ? 'Save changes' : 'Add child'}
        </button>
      </form>
    </div>
  )
}

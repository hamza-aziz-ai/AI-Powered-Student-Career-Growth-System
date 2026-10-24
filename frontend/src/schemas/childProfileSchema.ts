import { z } from 'zod'

// Children are 3-19 years old. Computed on every call, not at module load, so a tab
// left open across New Year doesn't keep last year's window (mirrors the backend).
export function birthYearBounds(): { min: number; max: number } {
  const currentYear = new Date().getFullYear()
  return { min: currentYear - 19, max: currentYear - 3 }
}

const tagList = z
  .array(z.string().min(1).max(200, 'Each entry must be 200 characters or fewer'))
  .max(20, 'No more than 20 entries')

export const childProfileSchema = z.object({
  first_name: z.string().min(1, 'First name is required').max(100),
  birth_year: z
    .number({ error: 'Birth year is required' })
    .int()
    .superRefine((year, ctx) => {
      const { min, max } = birthYearBounds()
      if (year < min) ctx.addIssue({ code: 'custom', message: `Birth year must be ${min} or later` })
      if (year > max) ctx.addIssue({ code: 'custom', message: `Birth year must be ${max} or earlier` })
    }),
  grade_level: z.string().max(50).optional().or(z.literal('')),
  interests: tagList,
  strengths: tagList,
  favorite_subjects: tagList.optional(),
  notes: z.string().max(1000).optional().or(z.literal('')),
})

export type ChildProfileFormValues = z.infer<typeof childProfileSchema>

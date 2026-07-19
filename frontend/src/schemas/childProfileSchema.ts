import { z } from 'zod'

const currentYear = new Date().getFullYear()
export const MIN_BIRTH_YEAR = currentYear - 19
export const MAX_BIRTH_YEAR = currentYear - 3

const tagList = z
  .array(z.string().min(1).max(200, 'Each entry must be 200 characters or fewer'))
  .max(20, 'No more than 20 entries')

export const childProfileSchema = z.object({
  first_name: z.string().min(1, 'First name is required').max(100),
  birth_year: z
    .number({ error: 'Birth year is required' })
    .int()
    .min(MIN_BIRTH_YEAR, `Birth year must be ${MIN_BIRTH_YEAR} or later`)
    .max(MAX_BIRTH_YEAR, `Birth year must be ${MAX_BIRTH_YEAR} or earlier`),
  grade_level: z.string().max(50).optional().or(z.literal('')),
  interests: tagList,
  strengths: tagList,
  favorite_subjects: tagList.optional(),
  notes: z.string().max(1000).optional().or(z.literal('')),
})

export type ChildProfileFormValues = z.infer<typeof childProfileSchema>

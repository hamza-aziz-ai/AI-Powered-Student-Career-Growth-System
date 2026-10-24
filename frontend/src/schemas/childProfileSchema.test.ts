import { afterEach, describe, expect, it, vi } from 'vitest'
import { birthYearBounds, childProfileSchema } from './childProfileSchema'

const validProfile = { first_name: 'Alex', interests: [], strengths: [] }

afterEach(() => {
  vi.useRealTimers()
})

describe('birth year window', () => {
  it('follows the current date instead of the date the module loaded', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2030-06-01T12:00:00Z'))
    expect(birthYearBounds()).toEqual({ min: 2011, max: 2027 })
    expect(childProfileSchema.safeParse({ ...validProfile, birth_year: 2027 }).success).toBe(true)

    vi.setSystemTime(new Date('2031-01-02T12:00:00Z'))
    expect(childProfileSchema.safeParse({ ...validProfile, birth_year: 2011 }).success).toBe(false)
    expect(childProfileSchema.safeParse({ ...validProfile, birth_year: 2028 }).success).toBe(true)
  })
})

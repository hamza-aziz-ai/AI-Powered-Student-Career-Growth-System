export interface User {
  id: string
  email: string
  full_name: string
  is_active: boolean
  is_email_verified: boolean
  created_at: string
}

export interface Child {
  id: string
  parent_id: string
  first_name: string
  birth_year: number
  grade_level: string | null
  interests: string[]
  strengths: string[]
  favorite_subjects: string[] | null
  notes: string | null
  created_at: string
  updated_at: string
}

export type ChildInput = Omit<Child, 'id' | 'parent_id' | 'created_at' | 'updated_at'>

export interface CareerSuggestion {
  title: string
  rationale: string
  related_subjects: string[]
  suggested_activities: string[]
}

export interface InsightResult {
  summary: string
  career_suggestions: CareerSuggestion[]
  growth_areas: string[]
  disclaimer: string
}

export interface CareerInsight {
  id: string
  child_id: string
  model_name: string
  status: 'pending' | 'completed' | 'failed'
  result_text: string | null
  result_json: InsightResult | null
  error_message: string | null
  generated_at: string | null
  created_at: string
}

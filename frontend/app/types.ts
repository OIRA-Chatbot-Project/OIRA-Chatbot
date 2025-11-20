export interface Citation {
  content: string
  source: string
  page: number | null
}

export interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  created_at: string
  feedback?: number // 1 for thumbs up, -1 for thumbs down
}

export interface ChatResponse {
  message_id: number
  answer: string
  citations: Citation[]
  session_id: string
}

export interface MessagesResponse {
  session_id: string
  messages: Message[]
}

export type Theme = 'light' | 'dark'

export interface SessionSummary {
  id: string
  timestamp: number
  title: string
  hasMessages: boolean
  isTemporary?: boolean
}

export interface ParsedCourse {
  course_code: string
  term?: string
  notes?: string
}

export interface ScheduleUploadResponse extends ChatResponse {
  schedule_summary: string
  parsed_courses: ParsedCourse[]
  schedule_message_id: number
}

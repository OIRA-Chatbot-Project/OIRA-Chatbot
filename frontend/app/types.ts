/** A single citation returned by the backend, linking a factual claim to its source document. */
export interface Citation {
  content: string
  source: string
  page: number | null
  url?: string
  filename?: string
  doc_type?: 'catalog' | 'policy' | string
}

/** A single message in a chat conversation, representing either the user or the assistant. */
export interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  follow_ups?: string[]
  created_at: string
  feedback?: number // 1 for thumbs up, -1 for thumbs down
}

/** The full response body returned by the non-streaming `/chat` endpoint. */
export interface ChatResponse {
  message_id: number
  answer: string
  citations: Citation[]
  session_id: string
  follow_ups?: string[]
}

/** The response body for the `/messages` endpoint, containing all messages in a session. */
export interface MessagesResponse {
  session_id: string
  messages: Message[]
}

/** UI color scheme — either light or dark mode. */
export type Theme = 'light' | 'dark'

/** Lightweight summary of a chat session used in the sidebar and local storage. */
export interface SessionSummary {
  id: string
  timestamp: number
  title: string
  hasMessages: boolean
  isTemporary?: boolean
}

/** A single course parsed from an uploaded student schedule file. */
export interface ParsedCourse {
  course_code: string
  term?: string
  notes?: string
}

/** Response body for the `/schedule/upload` endpoint, extending `ChatResponse` with parsed schedule data. */
export interface ScheduleUploadResponse extends ChatResponse {
  schedule_summary: string
  parsed_courses: ParsedCourse[]
  schedule_message_id: number
}

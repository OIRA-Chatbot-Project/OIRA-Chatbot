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

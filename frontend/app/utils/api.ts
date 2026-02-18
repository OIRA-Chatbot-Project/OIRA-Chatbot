import { API_URL } from './config'
import { MessagesResponse } from '../types'

export interface BackendSession {
  session_id: string
  title?: string | null
  created_at: string
  has_messages: boolean
}

export const fetchUserSessions = async (token: string): Promise<BackendSession[]> => {
  const response = await fetch(`${API_URL}/sessions`, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  })

  if (!response.ok) {
    throw new Error('Failed to fetch sessions')
  }

  const data = await response.json()
  return data.sessions
}

export const fetchSessionMessages = async (token: string, sessionId: string): Promise<MessagesResponse> => {
  const response = await fetch(`${API_URL}/messages?session_id=${sessionId}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  })

  if (!response.ok) {
    throw new Error('Failed to fetch messages')
  }

  return response.json()
}

export const initializeUserInBackend = async (
  token: string,
  userId: string,
  email: string,
  name: string | null
): Promise<boolean> => {
  const response = await fetch(`${API_URL}/users`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({
      clerk_user_id: userId,
      email,
      name,
    }),
  })

  return response.ok
}

export const deleteSession = async (token: string, sessionId: string): Promise<boolean> => {
  const response = await fetch(`${API_URL}/sessions/${sessionId}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  })

  return response.ok
}

export const updateSession = async (
  token: string,
  sessionId: string,
  payload: { title?: string }
): Promise<boolean> => {
  const response = await fetch(`${API_URL}/sessions/${sessionId}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  })

  return response.ok
}

// Streaming chat types
export interface StreamMetadataEvent {
  type: 'metadata'
  citations: Array<{
    content: string
    source: string
    page: number | null
    url?: string
    doc_type?: string
  }>
  category: string
}

export interface StreamTokenEvent {
  type: 'token'
  content: string
}

export interface StreamDoneEvent {
  type: 'done'
  message_id: number
  full_answer: string
}

export interface StreamErrorEvent {
  type: 'error'
  message: string
}

export type StreamEvent = StreamMetadataEvent | StreamTokenEvent | StreamDoneEvent | StreamErrorEvent

export interface StreamCallbacks {
  onMetadata: (event: StreamMetadataEvent) => void
  onToken: (token: string) => void
  onDone: (event: StreamDoneEvent) => void
  onError: (error: string) => void
}

/**
 * Send a chat message and stream the response using Server-Sent Events.
 * This provides faster perceived response time by showing tokens as they arrive.
 */
export const sendChatMessageStreaming = async (
  token: string,
  sessionId: string,
  message: string,
  callbacks: StreamCallbacks
): Promise<void> => {
  const response = await fetch(`${API_URL}/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({
      session_id: sessionId,
      message,
    }),
  })

  if (!response.ok) {
    throw new Error(`Failed to send message: ${response.statusText}`)
  }

  const reader = response.body?.getReader()
  if (!reader) {
    throw new Error('Response body is not readable')
  }

  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()

      if (done) {
        break
      }

      buffer += decoder.decode(value, { stream: true })

      // Process complete SSE events
      const lines = buffer.split('\n')
      buffer = lines.pop() || '' // Keep incomplete line in buffer

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const jsonStr = line.slice(6).trim()
          if (jsonStr) {
            try {
              const event: StreamEvent = JSON.parse(jsonStr)

              switch (event.type) {
                case 'metadata':
                  callbacks.onMetadata(event)
                  break
                case 'token':
                  callbacks.onToken(event.content)
                  break
                case 'done':
                  callbacks.onDone(event)
                  break
                case 'error':
                  callbacks.onError(event.message)
                  break
              }
            } catch (e) {
              console.error('Failed to parse SSE event:', e, jsonStr)
            }
          }
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}

/**
 * Fetch follow-up suggestions for a message.
 * Returns empty array if follow-ups are not ready yet.
 */
export const fetchFollowUps = async (
  token: string,
  messageId: number
): Promise<{ follow_ups: string[], ready: boolean }> => {
  const response = await fetch(`${API_URL}/chat/${messageId}/followups`, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  })

  if (!response.ok) {
    return { follow_ups: [], ready: false }
  }

  return response.json()
}

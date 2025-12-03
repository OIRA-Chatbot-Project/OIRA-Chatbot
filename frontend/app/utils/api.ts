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

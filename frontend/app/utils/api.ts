import { API_URL } from './config'
import { MessagesResponse } from '../types'

/** Session data shape returned by the backend `/sessions` endpoint. */
export interface BackendSession {
  session_id: string
  title?: string | null
  created_at: string
  updated_at: string
  has_messages: boolean
}

/**
 * Fetches all sessions belonging to the authenticated user from the backend.
 *
 * @param token - A valid Clerk JWT used to authorize the request.
 * @returns An array of `BackendSession` objects, sorted by the backend's default order.
 * @throws If the request fails or the server returns a non-OK status.
 */
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

/**
 * Fetches all messages for a specific chat session.
 *
 * @param token - A valid Clerk JWT used to authorize the request.
 * @param sessionId - The UUID of the session whose messages should be retrieved.
 * @returns A `MessagesResponse` containing the session ID and its message list.
 * @throws If the request fails or the server returns a non-OK status.
 */
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

/**
 * Creates or upserts a user record in the backend using their Clerk credentials.
 *
 * Safe to call on every login — the backend treats this as an idempotent upsert.
 *
 * @param token - A valid Clerk JWT.
 * @param userId - The Clerk user ID.
 * @param email - The user's primary email address.
 * @param name - The user's full name, or `null` if unavailable.
 * @returns `true` if the request succeeded, `false` otherwise.
 */
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

/**
 * Sends a DELETE request to permanently remove a session and all its messages.
 *
 * @param token - A valid Clerk JWT used to authorize the request.
 * @param sessionId - The UUID of the session to delete.
 * @returns `true` if the deletion succeeded, `false` otherwise.
 */
export const deleteSession = async (token: string, sessionId: string): Promise<boolean> => {
  const response = await fetch(`${API_URL}/sessions/${sessionId}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  })

  return response.ok
}

/**
 * Sends a PATCH request to update session metadata such as the title.
 *
 * @param token - A valid Clerk JWT used to authorize the request.
 * @param sessionId - The UUID of the session to update.
 * @param payload - Partial session fields to update (currently only `title` is supported).
 * @returns `true` if the update succeeded, `false` otherwise.
 */
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

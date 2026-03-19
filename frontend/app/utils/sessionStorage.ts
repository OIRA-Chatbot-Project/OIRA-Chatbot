import { SessionSummary } from '../types'

/**
 * Builds a namespaced localStorage key scoped to a specific user.
 *
 * @param userId - The Clerk user ID.
 * @param key - The logical key to namespace (`sessions` or `currentSessionId`).
 * @returns A combined key string like `sessions_<userId>`.
 */
export const getStorageKey = (userId: string, key: 'sessions' | 'currentSessionId') => {
  return `${key}_${userId}`
}

/**
 * Persists the session list for a user to localStorage.
 *
 * @param userId - The Clerk user ID used to namespace the storage key.
 * @param sessions - The current array of session summaries to serialize.
 */
export const saveSessionsToStorage = (userId: string, sessions: SessionSummary[]) => {
  localStorage.setItem(getStorageKey(userId, 'sessions'), JSON.stringify(sessions))
}

/**
 * Loads the session list for a user from localStorage.
 *
 * @param userId - The Clerk user ID used to namespace the storage key.
 * @returns The parsed array of session summaries, or `null` if nothing is stored.
 */
export const loadSessionsFromStorage = (userId: string): SessionSummary[] | null => {
  const stored = localStorage.getItem(getStorageKey(userId, 'sessions'))
  return stored ? JSON.parse(stored) : null
}

/**
 * Saves the currently active session ID to localStorage so it can be restored on page reload.
 *
 * @param userId - The Clerk user ID used to namespace the storage key.
 * @param sessionId - The ID of the session to mark as active.
 */
export const saveCurrentSessionId = (userId: string, sessionId: string) => {
  localStorage.setItem(getStorageKey(userId, 'currentSessionId'), sessionId)
}

/**
 * Retrieves the last active session ID from localStorage.
 *
 * @param userId - The Clerk user ID used to namespace the storage key.
 * @returns The stored session ID string, or `null` if none is saved.
 */
export const loadCurrentSessionId = (userId: string): string | null => {
  return localStorage.getItem(getStorageKey(userId, 'currentSessionId'))
}

/**
 * Removes legacy (non-namespaced) session keys from localStorage.
 *
 * Should be called once on login to clean up data written by older versions of the app
 * that stored sessions under bare keys (`sessions`, `currentSessionId`) instead of
 * per-user namespaced keys.
 */
export const clearLegacyStorage = () => {
  const oldSessions = localStorage.getItem('sessions')
  const oldSessionId = localStorage.getItem('currentSessionId')

  if (oldSessions || oldSessionId) {
    localStorage.removeItem('sessions')
    localStorage.removeItem('currentSessionId')
  }
}

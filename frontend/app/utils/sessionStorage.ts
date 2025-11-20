import { SessionSummary } from '../types'

export const getStorageKey = (userId: string, key: 'sessions' | 'currentSessionId') => {
  return `${key}_${userId}`
}

export const saveSessionsToStorage = (userId: string, sessions: SessionSummary[]) => {
  localStorage.setItem(getStorageKey(userId, 'sessions'), JSON.stringify(sessions))
}

export const loadSessionsFromStorage = (userId: string): SessionSummary[] | null => {
  const stored = localStorage.getItem(getStorageKey(userId, 'sessions'))
  return stored ? JSON.parse(stored) : null
}

export const saveCurrentSessionId = (userId: string, sessionId: string) => {
  localStorage.setItem(getStorageKey(userId, 'currentSessionId'), sessionId)
}

export const loadCurrentSessionId = (userId: string): string | null => {
  return localStorage.getItem(getStorageKey(userId, 'currentSessionId'))
}

export const clearLegacyStorage = () => {
  const oldSessions = localStorage.getItem('sessions')
  const oldSessionId = localStorage.getItem('currentSessionId')
  
  if (oldSessions || oldSessionId) {
    localStorage.removeItem('sessions')
    localStorage.removeItem('currentSessionId')
  }
}

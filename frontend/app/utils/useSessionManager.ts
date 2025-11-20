import { useState, useEffect, useCallback } from 'react'
import { SessionSummary } from '../types'
import { DEFAULT_SESSION_TITLE, generateSessionTitle, isPlaceholderTitle } from './session'
import { saveSessionsToStorage, loadCurrentSessionId, saveCurrentSessionId } from './sessionStorage'
import { fetchUserSessions, fetchSessionMessages } from './api'

export const useSessionManager = (
  userId: string | undefined,
  getToken: () => Promise<string | null>,
  isLoaded: boolean,
  isSignedIn: boolean
) => {
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const [sessionId, setSessionId] = useState<string>('')
  const [isCreatingSession, setIsCreatingSession] = useState(false)
  const [isTemporarySession, setIsTemporarySession] = useState(false)

  const persistSessions = useCallback(
    (updater: (prev: SessionSummary[]) => SessionSummary[]) => {
      setSessions(prevSessions => {
        const updated = updater(prevSessions)
        if (userId) {
          saveSessionsToStorage(userId, updated)
        }
        return updated
      })
    },
    [userId]
  )

  const updateSessionTitle = useCallback(
    (id: string, newTitle: string) => {
      if (!newTitle || isPlaceholderTitle(newTitle)) return

      persistSessions(prev =>
        prev.map(session => {
          if (session.id !== id || !isPlaceholderTitle(session.title)) {
            return session
          }
          return { ...session, title: newTitle }
        })
      )
    },
    [persistSessions]
  )

  const switchSession = useCallback(
    (id: string) => {
      // When switching away from temporary session, discard it
      setIsTemporarySession(false)
      setSessionId(id)
      if (userId) {
        saveCurrentSessionId(userId, id)
      }
    },
    [userId]
  )

  const markSessionHasMessages = useCallback(
    (id: string) => {
      // If this is a temporary session, make it permanent by adding to sessions list
      if (isTemporarySession && id === sessionId) {
        const tempSession: SessionSummary = {
          id: sessionId,
          timestamp: Date.now(),
          title: DEFAULT_SESSION_TITLE,
          hasMessages: true,
        }
        persistSessions(prev => [tempSession, ...prev])
        setIsTemporarySession(false)
      } else {
        persistSessions(prev =>
          prev.map(session =>
            session.id === id ? { ...session, hasMessages: true } : session
          )
        )
      }
    },
    [persistSessions, isTemporarySession, sessionId]
  )

  const hydrateSessionTitles = useCallback(
    async (sessionsToHydrate: SessionSummary[], isMounted: () => boolean) => {
      const token = await getToken()
      if (!token || !isMounted()) return

      // Process sessions in parallel but without blocking
      // Fire off requests without awaiting (lazy load titles)
      sessionsToHydrate
        .filter(s => isPlaceholderTitle(s.title))
        .forEach(async session => {
          try {
            const data = await fetchSessionMessages(token, session.id)
            const firstUserMessage = data.messages.find(msg => msg.role === 'user')
            
            if (firstUserMessage && isMounted()) {
              updateSessionTitle(session.id, generateSessionTitle(firstUserMessage.content))
            }
          } catch (error) {
            // Silently fail for individual session title hydration
          }
        })
    },
    [getToken, updateSessionTitle]
  )

  const loadUserSessions = useCallback(
    async (startNewChatFallback: () => void) => {
      try {
        const token = await getToken()
        if (!token) return { shouldContinue: false }

        const backendSessions = await fetchUserSessions(token)
        
        if (backendSessions.length === 0) {
          // Create a temporary session instead of calling fallback
          return { shouldContinue: false, createTemporary: true }
        }

        const formattedSessions = backendSessions.map(s => ({
          id: s.session_id,
          timestamp: new Date(s.created_at).getTime(),
          title: DEFAULT_SESSION_TITLE,
          hasMessages: s.has_messages,
        }))

        setSessions(formattedSessions)
        if (userId) {
          saveSessionsToStorage(userId, formattedSessions)
        }

        const savedSessionId = userId ? loadCurrentSessionId(userId) : null
        const activeSessionId = 
          savedSessionId && formattedSessions.find(s => s.id === savedSessionId)
            ? savedSessionId
            : formattedSessions[0].id

        setSessionId(activeSessionId)
        if (userId) {
          saveCurrentSessionId(userId, activeSessionId)
        }

        return { shouldContinue: true, sessions: formattedSessions }
      } catch (error) {
        // On error, create a temporary session
        return { shouldContinue: false, createTemporary: true }
      }
    },
    [getToken, userId]
  )

  return {
    sessions,
    sessionId,
    isCreatingSession,
    isTemporarySession,
    setSessionId,
    setIsCreatingSession,
    setIsTemporarySession,
    persistSessions,
    updateSessionTitle,
    switchSession,
    markSessionHasMessages,
    hydrateSessionTitles,
    loadUserSessions,
  }
}

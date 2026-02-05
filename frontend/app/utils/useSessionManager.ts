import { useState, useEffect, useCallback } from 'react'
import { SessionSummary } from '../types'
import { DEFAULT_SESSION_TITLE, generateSessionTitle, isPlaceholderTitle } from './session'
import { saveSessionsToStorage, loadCurrentSessionId, saveCurrentSessionId, loadSessionsFromStorage } from './sessionStorage'
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

  const renameSessionTitle = useCallback(
    (id: string, newTitle: string) => {
      if (!newTitle.trim()) return
      persistSessions(prev =>
        prev.map(session =>
          session.id === id ? { ...session, title: newTitle.trim() } : session
        )
      )
    },
    [persistSessions]
  )

  const togglePinSession = useCallback(
    (id: string) => {
      persistSessions(prev =>
        prev.map(session =>
          session.id === id ? { ...session, pinned: !session.pinned } : session
        )
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
    async () => {
      try {
        const token = await getToken()
        if (!token) return { shouldContinue: false }

        const backendSessions = await fetchUserSessions(token)
        
        // Backend now only returns sessions with messages
        if (backendSessions.length === 0) {
          return { shouldContinue: false }
        }

        const stored = userId ? loadSessionsFromStorage(userId) : null
        const storedMap = new Map((stored || []).map(s => [s.id, s]))

        const formattedSessions = backendSessions.map(s => {
          const storedSession = storedMap.get(s.session_id)
          const storedTitle = storedSession?.title
          const title =
            storedTitle && !isPlaceholderTitle(storedTitle)
              ? storedTitle
              : s.title || DEFAULT_SESSION_TITLE
          return {
            id: s.session_id,
            timestamp: new Date(s.created_at).getTime(),
            title,
            hasMessages: s.has_messages,
            pinned: storedSession?.pinned ?? false,
          }
        })

        setSessions(formattedSessions)
        if (userId) {
          saveSessionsToStorage(userId, formattedSessions)
        }

        return { shouldContinue: true, sessions: formattedSessions }
      } catch (error) {
        return { shouldContinue: false }
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
    renameSessionTitle,
    togglePinSession,
  }
}

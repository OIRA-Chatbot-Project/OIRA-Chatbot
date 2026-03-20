import { useState, useEffect, useCallback } from 'react'
import { SessionSummary } from '../types'
import { DEFAULT_SESSION_TITLE, generateSessionTitle, isPlaceholderTitle } from './session'
import { saveSessionsToStorage, loadCurrentSessionId, saveCurrentSessionId, loadSessionsFromStorage } from './sessionStorage'
import { fetchUserSessions, fetchSessionMessages } from './api'

/**
 * Deduplicates a session list by ID, merging duplicate entries.
 *
 * When two entries share the same ID the merge strategy is:
 * - Keep whichever title is non-placeholder; fall back to the incoming entry's title.
 * - Set `hasMessages` to `true` if either entry has messages.
 * - Use the larger of the two timestamps.
 *
 * Returns the deduplicated list sorted by timestamp descending (most recent first).
 *
 * @param sessions - A flat array of sessions that may contain duplicates.
 * @returns A deduplicated, sorted array of `SessionSummary` objects.
 */
const dedupeSessions = (sessions: SessionSummary[]): SessionSummary[] => {
  const sessionMap = new Map<string, SessionSummary>()

  for (const session of sessions) {
    const existing = sessionMap.get(session.id)
    if (!existing) {
      sessionMap.set(session.id, session)
      continue
    }

    sessionMap.set(session.id, {
      ...existing,
      ...session,
      title:
        !isPlaceholderTitle(session.title) || isPlaceholderTitle(existing.title)
          ? session.title
          : existing.title,
      hasMessages: existing.hasMessages || session.hasMessages,
      timestamp: Math.max(existing.timestamp, session.timestamp),
    })
  }

  return Array.from(sessionMap.values()).sort((a, b) => b.timestamp - a.timestamp)
}

/**
 * Manages the full lifecycle of chat sessions for the authenticated user.
 *
 * Handles session creation, switching, renaming, deletion, persistence to localStorage,
 * hydration of session titles from the backend, and initial load from the backend.
 *
 * @param userId - The Clerk user ID, or `undefined` while auth is loading.
 * @param getToken - Async function that resolves to a Clerk JWT, or `null` if unavailable.
 * @param isLoaded - Whether the Clerk auth state has finished loading.
 * @param isSignedIn - Whether the user is currently signed in.
 * @returns An object containing session state and callbacks for all session operations.
 */
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

  /**
   * Applies an updater function to the session list, deduplicates the result,
   * and persists it to localStorage.
   */
  const persistSessions = useCallback(
    (updater: (prev: SessionSummary[]) => SessionSummary[]) => {
      setSessions(prevSessions => {
        const updated = dedupeSessions(updater(prevSessions))
        if (userId) {
          saveSessionsToStorage(userId, updated)
        }
        return updated
      })
    },
    [userId]
  )

  /**
   * Replaces the title of a session only if it currently holds a placeholder title.
   * No-ops if the new title is itself a placeholder.
   */
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

  /**
   * Unconditionally renames a session title (used for user-initiated rename actions).
   * No-ops if the new title is blank after trimming.
   */
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

  /**
   * Switches the active session, discarding any in-progress temporary session,
   * and saves the new active session ID to localStorage.
   */
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

  /**
   * Marks a session as having messages.
   *
   * If the session is currently temporary, it is promoted to a permanent session
   * by adding it to the session list. Otherwise the existing entry's `hasMessages`
   * flag is flipped to `true`.
   */
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

  /**
   * Lazily fetches and backfills titles for sessions that still have placeholder titles.
   *
   * Fires parallel requests without blocking the caller. Silently ignores individual
   * failures so that a single slow/failing session doesn't block the rest.
   *
   * @param sessionsToHydrate - The session list to scan for placeholder titles.
   * @param isMounted - A callback that returns `false` once the component has unmounted,
   *   used to prevent state updates after cleanup.
   */
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

  /**
   * Loads all sessions from the backend, merges them with any locally cached data,
   * deduplicates, and persists the result.
   *
   * @returns An object with `shouldContinue` indicating whether any sessions were found,
   *   and optionally the merged `sessions` array.
   */
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
          // Use updated_at for ordering (most recent activity first) and fall back
          // to created_at. Both may arrive as naive UTC strings (no 'Z') from SQLite,
          // so we append 'Z' to force UTC interpretation instead of local time.
          const toUtcMs = (dt: string) =>
            new Date(dt.endsWith('Z') || dt.includes('+') ? dt : dt + 'Z').getTime()
          const timestamp = toUtcMs(s.updated_at ?? s.created_at)
          return {
            id: s.session_id,
            timestamp,
            title,
            hasMessages: s.has_messages,
          }
        })

        // Merge backend sessions with any locally-added sessions that haven't
        // been confirmed by the backend yet (e.g. first message still in-flight).
        // Sessions present in the backend response take precedence; local-only
        // sessions are preserved so they don't disappear during the async window.
        const backendIds = new Set(formattedSessions.map(s => s.id))
        setSessions(prevSessions => {
          const localOnly = prevSessions.filter(s => !backendIds.has(s.id))
          const merged = dedupeSessions([...formattedSessions, ...localOnly])
          if (userId) {
            saveSessionsToStorage(userId, merged)
          }
          return merged
        })

        // Return the backend-only deduplicated list for hydrateSessionTitles.
        // Local-only sessions don't need title hydration (they were just created).
        const dedupedSessions = dedupeSessions(formattedSessions)

        return { shouldContinue: true, sessions: dedupedSessions }
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
  }
}

'use client'

import { useState, useEffect, useCallback } from 'react'
import { useAuth, useUser } from '@clerk/nextjs'
import { v4 as uuidv4 } from 'uuid'
import ChatInterface from './components/ChatInterface'
import Sidebar from './components/Sidebar'
import { MessagesResponse, SessionSummary, Theme } from './types'
import { API_URL } from './utils/config'
import {
  DEFAULT_SESSION_TITLE,
  generateSessionTitle,
  isPlaceholderTitle,
} from './utils/session'

export default function Home() {
  const { getToken, isLoaded, isSignedIn } = useAuth()
  const { user } = useUser()
  const [sessionId, setSessionId] = useState<string>('')
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const [theme, setTheme] = useState<Theme>('light')
  const [isCreatingSession, setIsCreatingSession] = useState(false)
  const [isCurrentSessionEmpty, setIsCurrentSessionEmpty] = useState(false)
  const [isInitialized, setIsInitialized] = useState(false)

  useEffect(() => {
    if (typeof window === 'undefined') return
    const savedTheme = localStorage.getItem('theme') as Theme | null
    if (savedTheme) {
      setTheme(savedTheme)
      return
    }

    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      setTheme('dark')
    }
  }, [])

  useEffect(() => {
    if (typeof document === 'undefined') return
    document.documentElement.dataset.theme = theme
    document.body.dataset.theme = theme
    localStorage.setItem('theme', theme)
  }, [theme])

  const toggleTheme = useCallback(() => {
    setTheme(prev => (prev === 'light' ? 'dark' : 'light'))
  }, [])

  const persistSessions = useCallback(
    (updater: (prev: SessionSummary[]) => SessionSummary[]) => {
      setSessions(prevSessions => {
        const updated = updater(prevSessions)
        console.log('persistSessions - updated sessions:', updated)
        if (user?.id) {
          localStorage.setItem(`sessions_${user.id}`, JSON.stringify(updated))
        }
        return updated
      })
    },
    [user]
  )

  // Separate effect to update isCurrentSessionEmpty when sessionId or sessions change
  useEffect(() => {
    const current = sessions.find(session => session.id === sessionId)
    console.log('Checking current session:', sessionId, current)
    setIsCurrentSessionEmpty(current ? !current.hasMessages : false)
  }, [sessionId, sessions])

  const updateSessionTitle = useCallback(
    (id: string, newTitle: string) => {
      if (!newTitle || isPlaceholderTitle(newTitle)) {
        return
      }

      persistSessions(prev =>
        prev.map(session => {
          if (session.id !== id) {
            return session
          }

          if (!isPlaceholderTitle(session.title) && session.title === newTitle) {
            return session
          }

          if (!isPlaceholderTitle(session.title)) {
            return session
          }

          return { ...session, title: newTitle }
        })
      )
    },
    [persistSessions]
  )

  const startNewChat = useCallback(() => {
    console.log('startNewChat called, isCreatingSession:', isCreatingSession)
    if (isCreatingSession) {
      console.log('Already creating session, returning')
      return
    }
    setIsCreatingSession(true)
    const newSessionId = uuidv4()
    console.log('Creating new session:', newSessionId)
    
    const newSession: SessionSummary = {
      id: newSessionId,
      timestamp: Date.now(),
      title: DEFAULT_SESSION_TITLE,
      hasMessages: false,
    }

    console.log('About to persist new session:', newSession)
    
    // Update sessions first
    persistSessions(prev => {
      console.log('Previous sessions:', prev)
      return [newSession, ...prev]
    })
    
    // Then set the new session as active
    setSessionId(newSessionId)
    if (user?.id) {
      localStorage.setItem(`currentSessionId_${user.id}`, newSessionId)
    }
    
    setIsCreatingSession(false)
  }, [isCreatingSession, persistSessions, user])

  const switchSession = useCallback(
    (id: string) => {
      setSessionId(id)
      if (user?.id) {
        localStorage.setItem(`currentSessionId_${user.id}`, id)
      }
      const current = sessions.find(session => session.id === id)
      setIsCurrentSessionEmpty(current ? !current.hasMessages : false)
    },
    [sessions, user]
  )

  const deleteSession = useCallback(
    (id: string) => {
      persistSessions(prev => prev.filter(session => session.id !== id))

      if (id === sessionId) {
        startNewChat()
      }
    },
    [persistSessions, sessionId, startNewChat]
  )

  const markSessionHasMessages = useCallback((id: string) => {
    persistSessions(prev =>
      prev.map(session =>
        session.id === id ? { ...session, hasMessages: true } : session
      )
    )
  }, [persistSessions])

  // Session initialization - fetch from backend for user-scoped sessions
  useEffect(() => {
    if (!isLoaded || !isSignedIn || !user) return

    let isMounted = true

    async function loadUserSessions() {
      try {
        const token = await getToken()
        if (!token || !isMounted) return

        // Fetch sessions from backend
        const response = await fetch(`${API_URL}/sessions`, {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        })

        if (!isMounted) return

        if (response.ok) {
          const data = await response.json()
          
          // Convert backend sessions to frontend format
          const backendSessions = data.sessions.map((s: any) => ({
            id: s.session_id,
            timestamp: new Date(s.updated_at).getTime(),
            title: DEFAULT_SESSION_TITLE,
            hasMessages: true,
          }))

          if (backendSessions.length > 0) {
            setSessions(backendSessions)
            if (user?.id) {
              localStorage.setItem(`sessions_${user.id}`, JSON.stringify(backendSessions))
            }
            
            // Load saved session ID for this user or use most recent
            const savedSessionId = user?.id ? localStorage.getItem(`currentSessionId_${user.id}`) : null
            
            if (savedSessionId && backendSessions.find((s: SessionSummary) => s.id === savedSessionId)) {
              setSessionId(savedSessionId)
            } else {
              // Use most recent session
              setSessionId(backendSessions[0].id)
              if (user?.id) {
                localStorage.setItem(`currentSessionId_${user.id}`, backendSessions[0].id)
              }
            }

            // Hydrate titles for sessions
            const token = await getToken()
            if (!token || !isMounted) return

            await Promise.all(
              backendSessions.filter((s: SessionSummary) => isPlaceholderTitle(s.title)).map(async (session: SessionSummary) => {
                try {
                  const response = await fetch(`${API_URL}/messages?session_id=${session.id}`, {
                    headers: {
                      'Authorization': `Bearer ${token}`,
                    },
                  })
                  if (!response.ok || !isMounted) return
                  
                  const data: MessagesResponse = await response.json()
                  const firstUserMessage = data.messages.find(message => message.role === 'user')
                  if (firstUserMessage && isMounted) {
                    updateSessionTitle(session.id, generateSessionTitle(firstUserMessage.content))
                  }
                } catch (error) {
                  console.error('Failed to derive session title', error)
                }
              })
            )
          } else {
            // No sessions exist, create a new one
            startNewChat()
          }
        } else {
          // Error fetching sessions, start fresh
          startNewChat()
        }
      } catch (error) {
        console.error('Failed to load user sessions:', error)
        startNewChat()
      }
    }

    loadUserSessions()

    return () => {
      isMounted = false
    }
  }, [isLoaded, isSignedIn, user, getToken, updateSessionTitle, startNewChat])

  // Initialize user in backend when signed in
  useEffect(() => {
    async function initializeUser() {
      if (!isLoaded || !isSignedIn || !user) return
      
      // Clear old non-user-scoped localStorage data
      const oldSessions = localStorage.getItem('sessions')
      const oldSessionId = localStorage.getItem('currentSessionId')
      if (oldSessions || oldSessionId) {
        localStorage.removeItem('sessions')
        localStorage.removeItem('currentSessionId')
      }
      
      try {
        const token = await getToken()
        if (!token) return

        const response = await fetch(`${API_URL}/users`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify({
            clerk_user_id: user.id,
            email: user.primaryEmailAddress?.emailAddress || '',
            name: user.fullName,
          }),
        })

        if (response.ok) {
          setIsInitialized(true)
        }
      } catch (error) {
        console.error('Failed to initialize user:', error)
      }
    }

    initializeUser()
  }, [isLoaded, isSignedIn, user, getToken])

  // Show loading state while auth is loading
  if (!isLoaded) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-lg">Loading...</div>
      </div>
    )
  }

  // If not signed in, middleware will redirect to sign-in page
  if (!isSignedIn) {
    return null
  }

  return (
    <div
      className={`flex h-screen overflow-hidden ${
        theme === 'dark'
          ? 'text-gray-100 bg-transparent'
          : 'text-gray-900 bg-transparent'
      }`}
    >
      <Sidebar
        sessions={sessions}
        currentSessionId={sessionId}
        onNewChat={startNewChat}
        onSelectSession={switchSession}
        onDeleteSession={deleteSession}
        theme={theme}
        disableNewChat={isCreatingSession}
      />
      <main className="flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 flex justify-center px-4 sm:px-6 lg:px-10 py-6 overflow-hidden">
          {sessionId && (
          <ChatInterface
            key={sessionId}
            sessionId={sessionId}
            onSessionTitleUpdate={updateSessionTitle}
            onSessionHasMessages={markSessionHasMessages}
            theme={theme}
            onToggleTheme={toggleTheme}
          />
          )}
        </div>
      </main>
    </div>
  )
}

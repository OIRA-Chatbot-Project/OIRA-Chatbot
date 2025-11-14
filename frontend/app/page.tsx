'use client'

import { useState, useEffect, useCallback } from 'react'
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
  const [sessionId, setSessionId] = useState<string>('')
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const [theme, setTheme] = useState<Theme>('light')
  const [isCreatingSession, setIsCreatingSession] = useState(false)
  const [isCurrentSessionEmpty, setIsCurrentSessionEmpty] = useState(false)

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
        localStorage.setItem('sessions', JSON.stringify(updated))
        const current = updated.find(session => session.id === sessionId)
        setIsCurrentSessionEmpty(current ? !current.hasMessages : false)
        return updated
      })
    },
    [setSessions, sessionId]
  )

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

  const hydrateSessionTitles = useCallback(
    async (sessionList: SessionSummary[]) => {
      const sessionsNeedingTitles = sessionList.filter(session => isPlaceholderTitle(session.title))
      if (sessionsNeedingTitles.length === 0) {
        return
      }

      await Promise.all(
        sessionsNeedingTitles.map(async session => {
          try {
            const response = await fetch(`${API_URL}/messages?session_id=${session.id}`)
            if (!response.ok) {
              return
            }
            const data: MessagesResponse = await response.json()
            const firstUserMessage = data.messages.find(message => message.role === 'user')
            if (firstUserMessage) {
              updateSessionTitle(session.id, generateSessionTitle(firstUserMessage.content))
            }
          } catch (error) {
            console.error('Failed to derive session title', error)
          }
        })
      )
    },
    [updateSessionTitle]
  )

  const startNewChat = useCallback(() => {
    if (isCreatingSession || isCurrentSessionEmpty) {
      return
    }
    setIsCreatingSession(true)
    const newSessionId = uuidv4()
    setSessionId(newSessionId)
    localStorage.setItem('currentSessionId', newSessionId)

    const newSession: SessionSummary = {
      id: newSessionId,
      timestamp: Date.now(),
      title: DEFAULT_SESSION_TITLE,
      hasMessages: false,
    }

    persistSessions(prev => [newSession, ...prev])
    setIsCreatingSession(false)
    setIsCurrentSessionEmpty(true)
  }, [isCreatingSession, isCurrentSessionEmpty, persistSessions, setSessionId])

  useEffect(() => {
    const savedSessionId = localStorage.getItem('currentSessionId')
    const savedSessions = localStorage.getItem('sessions')

    if (savedSessions) {
      try {
        const parsedSessions: SessionSummary[] = JSON.parse(savedSessions)
        const normalizedSessions = parsedSessions.map(session => ({
          ...session,
          title: session.title || DEFAULT_SESSION_TITLE,
          hasMessages: session.hasMessages ?? true,
        }))
        setSessions(normalizedSessions)
        localStorage.setItem('sessions', JSON.stringify(normalizedSessions))
        void hydrateSessionTitles(normalizedSessions)
        const current = normalizedSessions.find(session => session.id === (savedSessionId || sessionId))
        setIsCurrentSessionEmpty(current ? !current.hasMessages : false)
      } catch (error) {
        console.error('Failed to parse saved sessions', error)
      }
    }

    if (savedSessionId) {
      setSessionId(savedSessionId)
    } else {
      startNewChat()
    }
  }, [hydrateSessionTitles, startNewChat])

  const switchSession = useCallback(
    (id: string) => {
      setSessionId(id)
      localStorage.setItem('currentSessionId', id)
      const current = sessions.find(session => session.id === id)
      setIsCurrentSessionEmpty(current ? !current.hasMessages : false)
    },
    [sessions]
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
        disableNewChat={isCurrentSessionEmpty || isCreatingSession}
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

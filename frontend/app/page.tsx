'use client'

import { useState, useEffect } from 'react'
import ChatInterface from './components/ChatInterface'
import Sidebar from './components/Sidebar'
import { v4 as uuidv4 } from 'uuid'

export default function Home() {
  const [sessionId, setSessionId] = useState<string>('')
  const [sessions, setSessions] = useState<{ id: string; timestamp: number }[]>([])

  useEffect(() => {
    // Load session from localStorage or create new one
    const savedSessionId = localStorage.getItem('currentSessionId')
    const savedSessions = localStorage.getItem('sessions')
    
    if (savedSessions) {
      setSessions(JSON.parse(savedSessions))
    }

    if (savedSessionId) {
      setSessionId(savedSessionId)
    } else {
      startNewChat()
    }
  }, [])

  const startNewChat = () => {
    const newSessionId = uuidv4()
    setSessionId(newSessionId)
    localStorage.setItem('currentSessionId', newSessionId)
    
    // Add to sessions list
    const newSession = { id: newSessionId, timestamp: Date.now() }
    const updatedSessions = [newSession, ...sessions]
    setSessions(updatedSessions)
    localStorage.setItem('sessions', JSON.stringify(updatedSessions))
  }

  const switchSession = (id: string) => {
    setSessionId(id)
    localStorage.setItem('currentSessionId', id)
  }

  const deleteSession = (id: string) => {
    const updatedSessions = sessions.filter(s => s.id !== id)
    setSessions(updatedSessions)
    localStorage.setItem('sessions', JSON.stringify(updatedSessions))
    
    // If we deleted the current session, create a new one
    if (id === sessionId) {
      startNewChat()
    }
  }

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar
        sessions={sessions}
        currentSessionId={sessionId}
        onNewChat={startNewChat}
        onSelectSession={switchSession}
        onDeleteSession={deleteSession}
      />
      <main className="flex-1 flex flex-col">
        {sessionId && <ChatInterface key={sessionId} sessionId={sessionId} />}
      </main>
    </div>
  )
}

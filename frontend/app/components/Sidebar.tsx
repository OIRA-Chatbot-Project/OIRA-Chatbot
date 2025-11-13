'use client'

import { useState } from 'react'

interface Session {
  id: string
  timestamp: number
}

interface SidebarProps {
  sessions: Session[]
  currentSessionId: string
  onNewChat: () => void
  onSelectSession: (id: string) => void
  onDeleteSession: (id: string) => void
}

export default function Sidebar({
  sessions,
  currentSessionId,
  onNewChat,
  onSelectSession,
  onDeleteSession,
}: SidebarProps) {
  const [isCollapsed, setIsCollapsed] = useState(false)

  const formatDate = (timestamp: number) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24))

    if (diffDays === 0) {
      return 'Today'
    } else if (diffDays === 1) {
      return 'Yesterday'
    } else if (diffDays < 7) {
      return `${diffDays} days ago`
    } else {
      return date.toLocaleDateString()
    }
  }

  if (isCollapsed) {
    return (
      <div className="w-16 bg-white border-r border-gray-200 flex flex-col items-center py-4">
        <button
          onClick={() => setIsCollapsed(false)}
          className="p-2 hover:bg-gray-100 rounded-lg mb-4"
          title="Expand sidebar"
        >
          ☰
        </button>
        <button
          onClick={onNewChat}
          className="p-2 hover:bg-gray-100 rounded-lg"
          title="New chat"
        >
          ➕
        </button>
      </div>
    )
  }

  return (
    <div className="w-64 bg-white border-r border-gray-200 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold text-gray-700">Chat History</h2>
          <button
            onClick={() => setIsCollapsed(true)}
            className="text-gray-500 hover:text-gray-700"
            title="Collapse sidebar"
          >
            ◀
          </button>
        </div>
        <button
          onClick={onNewChat}
          className="w-full bg-primary text-white py-2 px-4 rounded-lg hover:bg-opacity-90 transition-colors flex items-center justify-center gap-2"
        >
          <span>➕</span>
          <span>New Chat</span>
        </button>
      </div>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto p-2 scrollbar-thin">
        {sessions.length === 0 ? (
          <div className="text-center text-gray-500 text-sm mt-8">
            No chat history yet
          </div>
        ) : (
          <div className="space-y-1">
            {sessions.map((session) => (
              <div
                key={session.id}
                className={`group relative rounded-lg p-3 cursor-pointer transition-colors ${
                  session.id === currentSessionId
                    ? 'bg-primary bg-opacity-10 border border-primary'
                    : 'hover:bg-gray-100'
                }`}
                onClick={() => onSelectSession(session.id)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-700 truncate">
                      Chat Session
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      {formatDate(session.timestamp)}
                    </p>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      if (confirm('Delete this chat session?')) {
                        onDeleteSession(session.id)
                      }
                    }}
                    className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-600 transition-all ml-2"
                    title="Delete session"
                  >
                    🗑️
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-gray-200 text-xs text-gray-500">
        <div className="flex items-center gap-2 mb-2">
          <span className="w-2 h-2 bg-green-400 rounded-full"></span>
          <span>Backend connected</span>
        </div>
        <p>Session ID: {currentSessionId.slice(0, 8)}...</p>
      </div>
    </div>
  )
}

'use client'

import { useState, useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import { UserButton, useUser } from '@clerk/nextjs'
import Image from 'next/image'
import { SessionSummary, Theme } from '../types'
import { API_URL } from '../utils/config'

interface SidebarProps {
  sessions: SessionSummary[]
  currentSessionId: string
  onNewChat: () => void
  onSelectSession: (id: string) => void
  onDeleteSession: (id: string) => void
  onRenameSession: (id: string, title: string) => void
  theme: Theme
  disableNewChat?: boolean
}

/**
 * Formats a timestamp as a short, locale-aware date string (e.g., "Jan 15, 2024").
 *
 * @param timestamp - A Unix millisecond timestamp, ISO date string, or `undefined`.
 * @returns A formatted date string, or an empty string for missing/invalid input.
 */
const formatDate = (timestamp: number | string | undefined): string => {
  if (timestamp === undefined) return ''
  const date = new Date(timestamp)
  if (isNaN(date.getTime())) return ''
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

/**
 * Left navigation panel for the chat application.
 *
 * Displays the session history list with per-session rename/delete menus, a new-chat
 * button, a full-text search overlay (with lazy indexing), and a collapsible icon-only
 * mode. The search panel is portalled to `document.body` so it renders above all content.
 */
export default function Sidebar({
  sessions,
  currentSessionId,
  onNewChat,
  onSelectSession,
  onDeleteSession,
  onRenameSession,
  theme,
  disableNewChat = false,
}: SidebarProps) {
  const { user } = useUser()
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [isSearchOpen, setIsSearchOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchCache, setSearchCache] = useState<Record<string, { fullText: string; lowerText: string; preview: string }>>({})
  const [isSearchLoading, setIsSearchLoading] = useState(false)
  const [searchError, setSearchError] = useState<string | null>(null)
  const searchCacheRef = useRef(searchCache)
  const [isClient, setIsClient] = useState(false)
  const [openMenuSessionId, setOpenMenuSessionId] = useState<string | null>(null)
  const [menuPosition, setMenuPosition] = useState<{ top: number; left: number } | null>(null)
  const menuContainerRef = useRef<HTMLDivElement | null>(null)
  const menuPortalRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    searchCacheRef.current = searchCache
  }, [searchCache])

  useEffect(() => {
    setIsClient(true)
  }, [])

  useEffect(() => {
    if (!openMenuSessionId) return
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node
      if (menuPortalRef.current && menuPortalRef.current.contains(target)) {
        return
      }
      if (menuContainerRef.current && !menuContainerRef.current.contains(target)) {
        setOpenMenuSessionId(null)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [openMenuSessionId])

  useEffect(() => {
    if (!isSearchOpen) return
    const sessionsToFetch = sessions.filter(session => !searchCacheRef.current[session.id])
    if (sessionsToFetch.length === 0) {
      setIsSearchLoading(false)
      return
    }

    let cancelled = false
    setIsSearchLoading(true)
    setSearchError(null)

    const fetchSessions = async () => {
      await Promise.all(
        sessionsToFetch.map(async session => {
          try {
            const response = await fetch(`${API_URL}/messages?session_id=${session.id}`)
            if (!response.ok) {
              throw new Error('Failed to load conversation')
            }
            const data: { messages: { content: string }[] } = await response.json()
            const messages = data.messages || []
            const fullText = messages.map((msg) => msg.content).join(' ')
            const preview =
              messages.length > 0
                ? messages[messages.length - 1].content
                : session.title || 'No messages yet'

            if (!cancelled) {
              setSearchCache(prev => ({
                ...prev,
                [session.id]: {
                  fullText,
                  lowerText: fullText.toLowerCase(),
                  preview,
                },
              }))
            }
          } catch (error) {
            console.error('Search indexing failed', error)
            if (!cancelled) {
              setSearchError('Unable to index some conversations.')
            }
          }
        })
      )

      if (!cancelled) {
        setIsSearchLoading(false)
      }
    }

    void fetchSessions()

    return () => {
      cancelled = true
    }
  }, [isSearchOpen, sessions])

  const normalizedQuery = searchQuery.trim().toLowerCase()

  /**
   * Returns a context-aware preview snippet for a session in the search panel.
   *
   * When a search query is active it extracts a ±60-character window around the first
   * match in the full conversation text. Falls back to the last message preview when
   * there is no query or no match. Returns an indexing placeholder while the session
   * is still being fetched.
   *
   * @param sessionId - The ID of the session to generate a snippet for.
   * @returns A short preview string, possibly prefixed/suffixed with `…`.
   */
  const getSnippet = (sessionId: string) => {
    const entry = searchCache[sessionId]
    if (!entry) {
      return 'Indexing conversation...'
    }

    if (!normalizedQuery) {
      return entry.preview || ''
    }

    const index = entry.lowerText.indexOf(normalizedQuery)
    if (index === -1) {
      return entry.preview || ''
    }

    const radius = 60
    const start = Math.max(0, index - radius)
    const end = Math.min(entry.fullText.length, index + normalizedQuery.length + radius)
    let snippet = entry.fullText.slice(start, end).trim()
    if (start > 0) {
      snippet = '…' + snippet
    }
    if (end < entry.fullText.length) {
      snippet = snippet + '…'
    }
    return snippet || entry.preview || ''
  }

  const visibleSearchSessions = normalizedQuery
    ? sessions.filter(session => {
        const entry = searchCache[session.id]
        const titleMatch = session.title?.toLowerCase().includes(normalizedQuery)
        const contentMatch = entry ? entry.lowerText.includes(normalizedQuery) : false
        return Boolean(titleMatch || contentMatch)
      })
    : sessions.slice(0, 6)

  /** Closes the search overlay and resets all search state (query, loading, error). */
  const closeSearch = () => {
    setIsSearchOpen(false)
    setSearchQuery('')
    setIsSearchLoading(false)
    setSearchError(null)
  }

  /**
   * Switches to the selected session, closes the search overlay, and expands the sidebar
   * if it was collapsed.
   *
   * @param id - The session ID to activate.
   */
  const handleSearchSessionClick = (id: string) => {
    onSelectSession(id)
    closeSearch()
    setIsCollapsed(false)
  }

  const searchPanelLeft = isCollapsed ? '100px' : '300px'

  if (isCollapsed) {
    return (
      <div
        className={`w-16 border-r flex flex-col items-center py-4 backdrop-blur-2xl ${
          theme === 'dark'
            ? 'bg-slate-900/80 border-slate-800 text-gray-200'
            : 'bg-white/80 border-white/60 text-gray-600'
        }`}
      >
        <button
          onClick={() => setIsCollapsed(false)}
          className={`p-2 rounded-xl mb-4 transition-colors ${
            theme === 'dark' ? 'hover:bg-slate-800 text-white' : 'hover:bg-white/70'
          }`}
          title="Expand sidebar"
        >
          <span className="material-symbols-outlined text-[20px]">menu</span>
        </button>
        <button
          onClick={() => {
            setIsCollapsed(false)
            setIsSearchOpen(true)
          }}
          className={`p-2 rounded-xl mb-4 transition-colors ${
            theme === 'dark' ? 'hover:bg-slate-800 text-white' : 'hover:bg-white/70'
          }`}
          title="Search chats"
        >
          <span className="material-symbols-outlined text-[20px]">search</span>
        </button>
        <button
          onClick={disableNewChat ? undefined : onNewChat}
          disabled={disableNewChat}
          className={`p-2 rounded-xl transition-colors ${
            disableNewChat
              ? 'text-gray-500 cursor-not-allowed'
              : theme === 'dark'
                ? 'hover:bg-slate-800 text-white'
                : 'hover:bg-white/70'
          }`}
          title="New chat"
        >
          <span className="material-symbols-outlined text-[20px]">add</span>
        </button>
      </div>
    )
  }

  const searchOverlay =
    isClient && isSearchOpen
      ? createPortal(
          <>
            <div
              className="fixed inset-0 z-[150] bg-black/40 backdrop-blur-sm"
              onClick={closeSearch}
              aria-hidden="true"
            ></div>
            <div
              className={`fixed z-[200] w-96 rounded-3xl border shadow-2xl p-5 backdrop-blur-xl ${
                theme === 'dark'
                  ? 'bg-slate-900/90 text-gray-100 border-slate-800/80'
                  : 'bg-white/90 text-gray-900 border-white/80'
              }`}
              style={{ left: searchPanelLeft, top: '80px' }}
            >
              <div className="flex items-center justify-between mb-4">
                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-primary">Search</p>
                  <h3 className="text-lg font-semibold">Find past chats</h3>
                </div>
                <button
                  onClick={closeSearch}
                  className={`h-8 w-8 rounded-full border text-lg transition-colors ${
                    theme === 'dark'
                      ? 'border-slate-700 hover:bg-slate-800'
                      : 'border-white/70 hover:bg-white'
                  }`}
                  title="Close search"
                >
                  <span className="material-symbols-outlined text-[18px]">close</span>
                </button>
              </div>

              <div className="space-y-3">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search conversations..."
                  className={`w-full rounded-2xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-primary ${
                    theme === 'dark'
                      ? 'bg-slate-900 border border-slate-700 placeholder:text-gray-500 text-gray-100'
                      : 'bg-gray-50 border border-gray-200 placeholder:text-gray-500 text-gray-900'
                  }`}
                />

                {searchError && (
                  <p className="text-xs text-red-500">{searchError}</p>
                )}

                <div className="max-h-80 overflow-y-auto space-y-2 scrollbar-thin">
                  {isSearchLoading && (
                    <p className="text-xs text-gray-500">Indexing conversations...</p>
                  )}
                  {!isSearchLoading && visibleSearchSessions.length === 0 && normalizedQuery && (
                    <p className="text-sm text-gray-500">No conversations matched “{searchQuery}”.</p>
                  )}
                  {!isSearchLoading && !normalizedQuery && visibleSearchSessions.length === 0 && (
                    <p className="text-sm text-gray-500">No conversations yet.</p>
                  )}
                  {visibleSearchSessions.map(session => (
                    <button
                      key={session.id}
                      onClick={() => handleSearchSessionClick(session.id)}
                      className={`w-full text-left rounded-2xl border px-4 py-3 transition-colors ${
                        theme === 'dark'
                          ? 'border-slate-800 hover:border-slate-600 hover:bg-slate-900/60'
                          : 'border-gray-200 hover:border-gray-400 hover:bg-gray-50'
                      }`}
                    >
                      <p className="text-sm font-semibold truncate">
                        {session.title || 'New Chat'}
                      </p>
                      <p
                        className={`text-xs mt-1 line-clamp-2 ${
                          theme === 'dark' ? 'text-gray-400' : 'text-gray-500'
                        }`}
                      >
                        {getSnippet(session.id) || 'No preview available'}
                      </p>
                      <p
                        className={`text-[11px] mt-2 ${
                          theme === 'dark' ? 'text-gray-500' : 'text-gray-400'
                        }`}
                      >
                        {formatDate(session.timestamp)}
                      </p>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </>,
          document.body
        )
      : null

  return (
    <>
      <div
        className={`w-72 flex-shrink-0 flex flex-col border-r backdrop-blur-2xl ${
          theme === 'dark'
            ? 'bg-slate-900/70 border-slate-800 text-slate-100'
            : 'bg-white/70 border-white/60 text-slate-900 shadow-[0_0_45px_rgba(15,23,42,0.08)]'
        }`}
      >
      {/* Header */}
      <div
        className={`p-5 border-b ${
          theme === 'dark' ? 'border-slate-800/80' : 'border-white/70'
        }`}
      >
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className="relative w-28 h-8">
              <Image
                src={theme === 'dark' ? '/bulogo_orange.png' : '/bulogo_blue.png'}
                alt="Bucknell University"
                fill
                className="object-contain"
                priority
                sizes="112px"
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <UserButton 
              appearance={{
                elements: {
                  avatarBox: "w-8 h-8"
                }
              }}
            />
            <button
              onClick={() => setIsCollapsed(true)}
              className={`transition-colors ${
                theme === 'dark' ? 'text-gray-500 hover:text-white' : 'text-gray-400 hover:text-gray-700'
              }`}
              title="Collapse sidebar"
            >
              <span className="material-symbols-outlined text-[20px]">chevron_left</span>
            </button>
          </div>
        </div>
        <div className="flex gap-2 mt-2">
          <button
            onClick={onNewChat}
            disabled={disableNewChat}
            className={`flex-1 py-2 px-3 rounded-xl text-sm font-semibold transition-colors flex items-center justify-center gap-2 ${
              disableNewChat
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : theme === 'dark'
                  ? 'bg-gradient-to-r from-orange-400 to-pink-500 text-white hover:from-orange-300 hover:to-pink-400'
                  : 'bg-primary text-white hover:bg-secondary'
            }`}
          >
            <span className="material-symbols-outlined text-[18px]">add</span>
            <span>New Chat</span>
          </button>
          <button
            onClick={() => {
              setIsSearchOpen(true)
              setSearchQuery('')
              setSearchError(null)
            }}
            className={`w-12 rounded-xl flex items-center justify-center border transition-colors ${
              theme === 'dark'
                ? 'border-slate-700 text-gray-200 hover:border-slate-500 hover:bg-slate-900/60'
                : 'border-white/60 text-gray-700 hover:border-gray-300 hover:bg-white'
            }`}
            title="Search chats"
          >
            <span className="material-symbols-outlined text-[20px]">search</span>
          </button>
        </div>
      </div>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto p-4 scrollbar-thin space-y-0">
        {sessions.length === 0 ? (
          <div
            className={`text-center text-sm mt-8 ${
              theme === 'dark' ? 'text-gray-500' : 'text-gray-500'
            }`}
          >
            No chat history yet
          </div>
        ) : (
          sessions.map((session) => (
            <div
              key={session.id}
              className={`group relative rounded-2xl p-1.5 cursor-pointer transition-all border backdrop-blur ${
                session.id === currentSessionId
                  ? theme === 'dark'
                    ? 'bg-gradient-to-r from-slate-900 to-slate-800 border-indigo-500/40 shadow-lg shadow-indigo-900/40'
                    : 'bg-gradient-to-r from-white to-orange-50 border-primary/40 shadow-md'
                  : theme === 'dark'
                    ? 'border-slate-900/80 hover:border-slate-700 hover:bg-slate-900/40'
                    : 'border-white/40 hover:border-gray-200 hover:bg-white/80'
              }`}
              onClick={() => onSelectSession(session.id)}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0 pr-2">
                  <p
                    className={`text-sm font-medium truncate whitespace-nowrap leading-snug ${
                      theme === 'dark' ? 'text-white' : 'text-slate-800'
                    }`}
                    title={session.title || 'New Chat'}
                  >
                    {session.title || 'New Chat'}
                  </p>
                </div>
                <div ref={openMenuSessionId === session.id ? menuContainerRef : null} className="relative ml-2">
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      const nextOpen = openMenuSessionId === session.id ? null : session.id
                      setOpenMenuSessionId(nextOpen)
                      if (nextOpen) {
                        const rect = (e.currentTarget as HTMLButtonElement).getBoundingClientRect()
                        setMenuPosition({
                          top: rect.top + window.scrollY,
                          left: rect.right + window.scrollX + 8,
                        })
                      } else {
                        setMenuPosition(null)
                      }
                    }}
                    className={`opacity-0 group-hover:opacity-100 transition-all px-2 py-1 rounded-md ${
                      theme === 'dark'
                        ? 'text-slate-500 hover:text-slate-200 hover:bg-slate-800/60'
                        : 'text-slate-500 hover:text-slate-800 hover:bg-white'
                    }`}
                    title="More options"
                    aria-label="More options"
                  >
                    <span className="material-symbols-outlined text-[18px]">more_horiz</span>
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Footer */}
      <div
        className={`p-4 border-t text-xs ${
          theme === 'dark' ? 'border-slate-800 text-slate-500' : 'border-white/60 text-slate-500'
        }`}
      >
        <div className="flex items-center gap-2 mb-2">
          <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>
          <span>Backend connected</span>
        </div>
        <p className="tracking-wide uppercase text-[11px]">
          Session {currentSessionId.slice(0, 8)}…
        </p>
      </div>
    </div>
      {searchOverlay}
      {isClient && openMenuSessionId && menuPosition
        ? createPortal(
            (() => {
              const activeMenuSessionId = openMenuSessionId as string
              const activeSession = sessions.find(s => s.id === activeMenuSessionId)
              return (
                <div
                  ref={menuPortalRef}
                  className={`fixed z-[9999] w-40 rounded-xl border shadow-lg ${
                    theme === 'dark'
                      ? 'bg-slate-900 border-slate-800 text-slate-200'
                      : 'bg-white border-gray-200 text-slate-700'
                  }`}
                  style={{ top: menuPosition.top, left: menuPosition.left }}
                >
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  setOpenMenuSessionId(null)
                  setMenuPosition(null)
                  if (confirm('Delete this chat session?')) {
                    onDeleteSession(activeMenuSessionId)
                  }
                }}
                className={`w-full text-left px-3 py-2 text-sm rounded-t-xl ${
                  theme === 'dark' ? 'hover:bg-slate-800' : 'hover:bg-gray-50'
                }`}
              >
                Delete
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  setOpenMenuSessionId(null)
                  setMenuPosition(null)
                  const nextTitle = window.prompt('Rename chat', activeSession?.title || '')
                  if (nextTitle !== null) {
                    onRenameSession(activeMenuSessionId, nextTitle)
                  }
                }}
                className={`w-full text-left px-3 py-2 text-sm rounded-b-xl ${
                  theme === 'dark' ? 'hover:bg-slate-800' : 'hover:bg-gray-50'
                }`}
              >
                Rename
              </button>
            </div>
              )
            })(),
            document.body
          )
        : null}
    </>
  )
}

'use client'

import { useState, useEffect, useRef, ChangeEvent, useCallback } from 'react'
import { useAuth } from '@clerk/nextjs'
import MessageList from './MessageList'
import MessageInput from './MessageInput'
import { Message, Theme, ScheduleUploadResponse, Citation } from '../types'
import { API_URL } from '../utils/config'
import { generateSessionTitle } from '../utils/session'
import {
  sendChatMessageStreaming,
  fetchFollowUps,
  StreamMetadataEvent,
  StreamDoneEvent
} from '../utils/api'

interface ChatInterfaceProps {
  sessionId: string
  onSessionTitleUpdate?: (sessionId: string, title: string) => void
  onSessionHasMessages?: (sessionId: string) => void
  theme: Theme
  onToggleTheme: () => void
}

export default function ChatInterface({
  sessionId,
  onSessionTitleUpdate,
  onSessionHasMessages,
  theme,
  onToggleTheme,
}: ChatInterfaceProps) {
  const { getToken } = useAuth()
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const [seenMessageIds, setSeenMessageIds] = useState<Set<number>>(new Set())
  const [animateMessageId, setAnimateMessageId] = useState<number | undefined>(undefined)
  const [showSettings, setShowSettings] = useState(false)
  const [animationEnabled, setAnimationEnabled] = useState<boolean>(() => {
    try {
      const v = localStorage.getItem('word_animation_enabled')
      return v === null ? true : v === 'true'
    } catch {
      return true
    }
  })
  const [isUploadingSchedule, setIsUploadingSchedule] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const streamingMessageRef = useRef<{ id: number; content: string; citations: Citation[] }>({
    id: 0,
    content: '',
    citations: []
  })

  useEffect(() => {
    // Load conversation history when session changes
    loadConversationHistory()
    setUploadError(null)
    setIsUploadingSchedule(false)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }, [sessionId])

  useEffect(() => {
    // Scroll to bottom when messages change
    scrollToBottom()
  }, [messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const loadConversationHistory = async () => {
    try {
      const token = await getToken()
      if (!token) {
        setError('Authentication required')
        return
      }

      const response = await fetch(`${API_URL}/messages?session_id=${sessionId}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      })
      if (response.ok) {
        const data = await response.json()
        setMessages(data.messages)
        setSeenMessageIds(new Set((data.messages || []).map((m: Message) => m.id)))
        setAnimateMessageId(undefined)
        if (data.messages && data.messages.length > 0) {
          onSessionHasMessages?.(sessionId)
        }

        const firstUserMessage: Message | undefined = data.messages?.find(
          (msg: Message) => msg.role === 'user'
        )
        if (firstUserMessage) {
          notifySessionTitle(firstUserMessage.content)
          onSessionHasMessages?.(sessionId)
        }
      }
    } catch (err) {
      console.error('Failed to load conversation history:', err)
    }
  }

  const notifySessionTitle = async (content: string) => {
    if (!content) return
    
    try {
      // Call backend to generate AI-powered title
      const token = await getToken()
      if (!token) return
      
      const response = await fetch(`${API_URL}/sessions/generate-title`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          first_message: content
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        onSessionTitleUpdate?.(sessionId, data.title)
      } else {
        // Fallback to simple title generation
        const title = generateSessionTitle(content)
        onSessionTitleUpdate?.(sessionId, title)
      }
    } catch (error) {
      console.error('Failed to generate AI title, using fallback:', error)
      // Fallback to simple title generation
      const title = generateSessionTitle(content)
      onSessionTitleUpdate?.(sessionId, title)
    }
  }

  // Poll for follow-ups after streaming completes
  const pollFollowUps = useCallback(async (messageId: number, maxAttempts: number = 5) => {
    const token = await getToken()
    if (!token) return

    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      // Wait before polling (increasing delay)
      await new Promise(resolve => setTimeout(resolve, 500 + attempt * 300))

      try {
        const result = await fetchFollowUps(token, messageId)
        if (result.ready && result.follow_ups.length > 0) {
          // Update the message with follow-ups
          setMessages(prev =>
            prev.map(msg =>
              msg.id === messageId ? { ...msg, follow_ups: result.follow_ups } : msg
            )
          )
          return
        }
      } catch (e) {
        console.error('Failed to fetch follow-ups:', e)
      }
    }
  }, [getToken])

  const sendMessage = async (content: string) => {
    // Add user message to UI
    const userMessage: Message = {
      id: Date.now(),
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    }
    setMessages(prev => [...prev, userMessage])
    setSeenMessageIds(prev => {
      const next = new Set(prev)
      next.add(userMessage.id)
      return next
    })
    setIsLoading(true)
    setIsStreaming(true)
    setError(null)
    const hasExistingUserMessage = messages.some(msg => msg.role === 'user')
    const isFirstMessage = !hasExistingUserMessage

    // Initialize streaming message ref
    const tempId = Date.now() + 1
    streamingMessageRef.current = { id: tempId, content: '', citations: [] }

    // Add placeholder assistant message for streaming
    const placeholderMessage: Message = {
      id: tempId,
      role: 'assistant',
      content: '',
      citations: [],
      follow_ups: [],
      created_at: new Date().toISOString(),
    }
    setMessages(prev => [...prev, placeholderMessage])

    try {
      const token = await getToken()
      if (!token) {
        setError('Authentication required')
        setIsLoading(false)
        setIsStreaming(false)
        return
      }

      let finalMessageId = tempId

      await sendChatMessageStreaming(token, sessionId, content, {
        onMetadata: (event: StreamMetadataEvent) => {
          // Update citations immediately
          streamingMessageRef.current.citations = event.citations as Citation[]
          setMessages(prev =>
            prev.map(msg =>
              msg.id === tempId
                ? { ...msg, citations: event.citations as Citation[] }
                : msg
            )
          )
        },

        onToken: (tokenContent: string) => {
          // Append token to streaming content
          streamingMessageRef.current.content += tokenContent
          setMessages(prev =>
            prev.map(msg =>
              msg.id === tempId
                ? { ...msg, content: streamingMessageRef.current.content }
                : msg
            )
          )
        },

        onDone: (event: StreamDoneEvent) => {
          finalMessageId = event.message_id
          // Update with final message ID and content
          setMessages(prev =>
            prev.map(msg =>
              msg.id === tempId
                ? {
                    ...msg,
                    id: event.message_id,
                    content: event.full_answer,
                  }
                : msg
            )
          )
          setSeenMessageIds(prev => {
            const next = new Set(prev)
            next.add(event.message_id)
            return next
          })

          // Poll for follow-ups in background
          pollFollowUps(event.message_id)
        },

        onError: (errorMsg: string) => {
          setError(errorMsg || 'Failed to get response. Please try again.')
          // Remove placeholder message on error
          setMessages(prev => prev.filter(msg => msg.id !== tempId))
        },
      })

      // Only save session after successful first exchange
      if (isFirstMessage) {
        notifySessionTitle(content)
        onSessionHasMessages?.(sessionId)
      }
    } catch (err) {
      setError('Failed to get response. Please try again.')
      console.error('Error sending message:', err)
      // Remove placeholder message on error
      setMessages(prev => prev.filter(msg => msg.id === userMessage.id || msg.role !== 'assistant' || msg.content !== ''))
    } finally {
      setIsLoading(false)
      setIsStreaming(false)
    }
  }

  const submitFeedback = async (messageId: number, rating: number, note?: string) => {
    try {
      const token = await getToken()
      if (!token) {
        console.error('Authentication required for feedback')
        return
      }

      const response = await fetch(`${API_URL}/feedback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          session_id: sessionId,
          message_id: messageId,
          rating,
          note,
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to submit feedback')
      }

      // Update message to show feedback was submitted
      setMessages(prev =>
        prev.map(msg =>
          msg.id === messageId ? { ...msg, feedback: rating } : msg
        )
      )
    } catch (err) {
      console.error('Error submitting feedback:', err)
    }
  }

  const triggerScheduleUpload = () => {
    if (isUploadingSchedule) return
    fileInputRef.current?.click()
  }

  const handleScheduleUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return
    setIsUploadingSchedule(true)
    setUploadError(null)

    try {
      const token = await getToken()
      if (!token) {
        setUploadError('Authentication required')
        setIsUploadingSchedule(false)
        return
      }

      const formData = new FormData()
      formData.append('session_id', sessionId)
      formData.append('file', file)

      const response = await fetch(`${API_URL}/schedule/upload`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      })

      let payload: ScheduleUploadResponse | { detail?: string }
      try {
        payload = await response.json()
      } catch {
        payload = { detail: undefined }
      }
      if (!response.ok) {
        let detail: string | undefined
        if (payload && typeof payload === 'object' && 'detail' in payload) {
          detail = (payload as { detail?: string }).detail
        }
        throw new Error(detail || 'Failed to process schedule')
      }

      const data = payload as ScheduleUploadResponse

      const scheduleMessage: Message = {
        id: data.schedule_message_id,
        role: 'user',
        content: `Schedule uploaded:\n${data.schedule_summary}`,
        created_at: new Date().toISOString(),
      }

      const assistantMessage: Message = {
        id: data.message_id,
        role: 'assistant',
        content: data.answer,
        citations: data.citations,
        follow_ups: data.follow_ups || [],
        created_at: new Date().toISOString(),
      }

      setMessages(prev => [...prev, scheduleMessage, assistantMessage])
      setSeenMessageIds(prev => {
        const next = new Set(prev)
        next.add(scheduleMessage.id)
        next.add(assistantMessage.id)
        return next
      })
      const shouldAnimateAssistant = animationEnabled && !seenMessageIds.has(assistantMessage.id)
      setAnimateMessageId(shouldAnimateAssistant ? assistantMessage.id : undefined)
      onSessionHasMessages?.(sessionId)
      setUploadError(null)
    } catch (err) {
      console.error('Failed to upload schedule:', err)
      const fallback =
        'Failed to analyze the schedule. Please try again with a clearer image or text export.'
      if (err instanceof Error && err.message) {
        setUploadError(err.message)
      } else if (typeof err === 'string' && err.trim().length > 0) {
        setUploadError(err)
      } else {
        setUploadError(fallback)
      }
    } finally {
      setIsUploadingSchedule(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  return (
    <>
      {/* Header */}
      <header
        className={`px-4 sm:px-6 md:px-8 py-4 border-b flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between flex-shrink-0 ${
          theme === 'dark'
            ? 'border-slate-800/80 bg-gradient-to-r from-slate-950/80 to-slate-900/50'
            : 'border-white/70 bg-white/60'
        }`}
      >
        <div className="min-w-0">
          <p className="text-xs uppercase tracking-[0.3em] text-primary">Bucknell</p>
          <h1
            className={`text-2xl sm:text-3xl font-semibold ${
              theme === 'dark' ? 'text-white' : 'text-secondary'
            }`}
          >
            Course Catalog Assistant
          </h1>
        </div>
        <div className="flex items-center gap-3">
          <span
            className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${
              theme === 'dark' ? 'bg-green-500/10 text-green-300' : 'bg-green-100 text-green-800'
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full mr-2 ${
                theme === 'dark' ? 'bg-green-300' : 'bg-green-500'
              }`}
            ></span>
            Connected
          </span>
          <div className="relative">
            <input
              ref={fileInputRef}
              type="file"
              accept=".png,.jpg,.jpeg,.bmp,.tiff,.tif,.gif,.txt,.csv"
              className="hidden"
              onChange={handleScheduleUpload}
            />
            <button
              onClick={triggerScheduleUpload}
              disabled={isUploadingSchedule}
              className={`h-11 px-4 rounded-2xl border text-sm font-medium transition-colors ${
                isUploadingSchedule
                  ? 'border-gray-300 text-gray-400 cursor-not-allowed'
                  : theme === 'dark'
                    ? 'border-slate-700/80 text-gray-100 hover:border-slate-400'
                    : 'border-white/70 text-gray-700 hover:border-gray-300'
              }`}
            >
              {isUploadingSchedule ? 'Uploading…' : 'Upload Schedule'}
            </button>
          </div>
          <button
            onClick={() => setShowSettings(prev => !prev)}
            className={`h-11 w-11 rounded-2xl border transition-colors ${
              theme === 'dark'
                ? 'border-slate-700/80 bg-slate-900/60 hover:border-slate-400'
                : 'border-white/70 bg-white/70 hover:border-gray-300'
            }`}
            title="Settings"
          >
            <span className="text-lg">⚙️</span>
          </button>
        </div>
      </header>

      {uploadError && (
        <div
          className={`mx-4 sm:mx-6 md:mx-8 mt-3 rounded-2xl border px-4 py-2.5 text-sm flex-shrink-0 ${
            theme === 'dark'
              ? 'border-red-400/40 bg-red-500/10 text-red-100'
              : 'border-red-200 bg-red-50 text-red-700'
          }`}
        >
          {uploadError}
        </div>
      )}

      {/* Settings Panel */}
      {showSettings && (
        <>
          <div
            className="fixed inset-0 z-10 bg-black/30 backdrop-blur"
            onClick={() => setShowSettings(false)}
            aria-hidden="true"
          ></div>
          <div
            className={`absolute right-4 sm:right-6 md:right-8 top-24 z-20 w-72 rounded-3xl border shadow-2xl p-5 ${
              theme === 'dark'
                ? 'bg-slate-900/95 border-slate-700 text-gray-100'
                : 'bg-white/95 border-white/80 text-gray-900'
            }`}
          >
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold">Appearance</h3>
                <p className="text-xs text-gray-500">Switch between light and dark themes.</p>
              </div>
              <button
                onClick={onToggleTheme}
                className={`relative inline-flex h-7 w-14 items-center rounded-full transition-colors ${
                  theme === 'dark' ? 'bg-indigo-500/60' : 'bg-gray-300'
                }`}
              >
                <span
                  className={`inline-block h-5 w-5 transform rounded-full bg-white shadow-lg transition-transform ${
                    theme === 'dark' ? 'translate-x-7' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
            <div className="mt-4 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold">Playback</h3>
                <p className="text-xs text-gray-500">Show responses character-by-character.</p>
              </div>
              <button
                onClick={() => {
                  setAnimationEnabled(prev => {
                    const next = !prev
                    try { localStorage.setItem('word_animation_enabled', String(next)) } catch {}
                    return next
                  })
                }}
                className={`relative inline-flex h-7 w-14 items-center rounded-full transition-colors ${
                  animationEnabled ? 'bg-indigo-500/60' : 'bg-gray-300'
                }`}
              >
                <span
                  className={`inline-block h-5 w-5 transform rounded-full bg-white shadow-lg transition-transform ${
                    animationEnabled ? 'translate-x-7' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
          </div>
        </>
      )}

      {/* Messages */}
      <div
        className={`flex-1 min-h-0 overflow-y-auto px-4 sm:px-6 md:px-8 lg:px-10 py-4 sm:py-6 scrollbar-thin ${
          theme === 'dark'
            ? 'bg-gradient-to-b from-transparent via-slate-950/20 to-slate-950/60'
            : 'bg-gradient-to-b from-white/60 to-slate-50'
        }`}
      >
        {messages.length === 0 && !isLoading && (
          <div className="flex flex-col items-center justify-center min-h-full text-center py-8">
            <div className="max-w-lg px-4">
              <h2
                className={`text-xl sm:text-2xl font-semibold mb-3 ${
                  theme === 'dark' ? 'text-gray-100' : 'text-gray-700'
                }`}
              >
                Welcome to the Bucknell Course Catalog Assistant! 👋
              </h2>
              <p className={`mb-4 text-sm sm:text-base ${theme === 'dark' ? 'text-gray-400' : 'text-gray-600'}`}>
                I can help you find information about courses, majors, prerequisites, and academic planning.
              </p>
              <div
                className={`text-left rounded-2xl p-5 space-y-2 ${
                  theme === 'dark'
                    ? 'bg-slate-900/60 text-gray-100 border border-slate-800'
                    : 'bg-white text-gray-700 border border-gray-100 shadow'
                }`}
              >
                <p className="text-sm font-medium">Try asking:</p>
                <ul className="text-sm space-y-1">
                  <li>• "What are the requirements for a Computer Science major?"</li>
                  <li>• "Tell me about CSCI 204"</li>
                  <li>• "What courses should I take as a first-year student?"</li>
                  <li>• "What are the prerequisites for upper-level math courses?"</li>
                </ul>
              </div>
            </div>
          </div>
        )}
        
        <MessageList
          messages={messages}
          onFeedback={submitFeedback}
          theme={theme}
          animationEnabled={animationEnabled}
          animateMessageId={animateMessageId}
          onFollowupClick={(text: string) => sendMessage(text)}
        />
        
        {/* Show loading indicator only when loading but not streaming (streaming shows content directly) */}
        {isLoading && !isStreaming && (
          <div className="flex items-start gap-3 mb-4">
            <div
              className={`w-10 h-10 rounded-2xl flex items-center justify-center flex-shrink-0 ${
                theme === 'dark' ? 'bg-slate-800 text-orange-200' : 'bg-primary text-white'
              }`}
            >
              🤖
            </div>
            <div
              className={`flex-1 rounded-2xl p-4 ${
                theme === 'dark'
                  ? 'bg-slate-900/60 border border-slate-800'
                  : 'bg-white shadow border border-gray-100'
              }`}
            >
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200"></div>
              </div>
            </div>
          </div>
        )}

        {error && (
          <div
            className={`px-4 py-3 rounded-2xl mb-4 border ${
              theme === 'dark'
                ? 'bg-red-500/10 border-red-500/40 text-red-200'
                : 'bg-red-50 border-red-200 text-red-700'
            }`}
          >
            {error}
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div
        className={`border-t px-4 sm:px-6 md:px-8 lg:px-10 py-4 backdrop-blur flex-shrink-0 ${
          theme === 'dark'
            ? 'bg-slate-950/80 border-slate-800/80'
            : 'bg-white/70 border-white/80'
        }`}
      >
        <MessageInput onSend={sendMessage} disabled={isLoading} theme={theme} />
      </div>
    </>
  )
}

'use client'

import { useState, useEffect, useRef, ChangeEvent } from 'react'
import { useAuth } from '@clerk/nextjs'
import MessageList from './MessageList'
import MessageInput from './MessageInput'
import { Message, Theme, ScheduleUploadResponse } from '../types'
import { API_URL } from '../utils/config'
import { generateSessionTitle } from '../utils/session'

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
  const [isRegenerating, setIsRegenerating] = useState(false)
  const [isLoadingHistory, setIsLoadingHistory] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showJumpToLatest, setShowJumpToLatest] = useState(false)
  const messageScrollRef = useRef<HTMLDivElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const shouldAutoScrollRef = useRef(true)
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
    // Preserve user-controlled scrolling while streaming.
    if (shouldAutoScrollRef.current) {
      scrollToBottom('auto')
    }
  }, [messages])

  const isNearBottom = () => {
    const container = messageScrollRef.current
    if (!container) return true

    const distanceFromBottom =
      container.scrollHeight - (container.scrollTop + container.clientHeight)

    return distanceFromBottom <= 120
  }

  const handleMessagesScroll = () => {
    const nearBottom = isNearBottom()
    shouldAutoScrollRef.current = nearBottom
    setShowJumpToLatest(!nearBottom && messages.length > 0)
  }

  const enableAutoScroll = () => {
    shouldAutoScrollRef.current = true
    setShowJumpToLatest(false)
  }

  const scrollToBottom = (behavior: ScrollBehavior = 'smooth') => {
    messagesEndRef.current?.scrollIntoView({ behavior })
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
    } finally {
      setIsLoadingHistory(false)
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

  const ENABLE_STREAMING = true

  const streamAssistantMessage = async (
    url: string,
    body: Record<string, unknown>,
    placeholderId: number,
    token: string,
    userPlaceholderId?: number
  ) => {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      throw new Error('Failed to send message')
    }

    const reader = response.body?.getReader()
    if (!reader) throw new Error('No response body')

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      // Parse SSE events from buffer
      const lines = buffer.split('\n')
      buffer = lines.pop() || '' // Keep incomplete line in buffer

      let eventType = ''
      for (const line of lines) {
        if (line.startsWith('event: ')) {
          eventType = line.slice(7).trim()
        } else if (line.startsWith('data: ') && eventType) {
          try {
            const data = JSON.parse(line.slice(6))

            switch (eventType) {
              case 'metadata':
                // Set citations and category on the placeholder message
                setMessages(prev => prev.map(msg =>
                  msg.id === placeholderId
                    ? { ...msg, citations: data.citations || [] }
                    : msg
                ))
                break

              case 'user':
                if (userPlaceholderId && data.message_id) {
                  setMessages(prev => prev.map(msg =>
                    msg.id === userPlaceholderId
                      ? { ...msg, id: data.message_id }
                      : msg
                  ))
                  setSeenMessageIds(prev => {
                    const next = new Set(prev)
                    next.delete(userPlaceholderId)
                    next.add(data.message_id)
                    return next
                  })
                }
                break

              case 'token':
                // Append token to the placeholder message content
                setMessages(prev => prev.map(msg =>
                  msg.id === placeholderId
                    ? { ...msg, content: msg.content + (data.token || '') }
                    : msg
                ))
                break

              case 'followups':
                setMessages(prev => prev.map(msg =>
                  msg.id === placeholderId
                    ? { ...msg, follow_ups: data.follow_ups || [] }
                    : msg
                ))
                break

              case 'saved':
                // Update the placeholder ID with the real DB message ID
                if (data.message_id) {
                  setMessages(prev => prev.map(msg =>
                    msg.id === placeholderId
                      ? { ...msg, id: data.message_id }
                      : msg
                  ))
                  setSeenMessageIds(prev => {
                    const next = new Set(prev)
                    next.delete(placeholderId)
                    next.add(data.message_id)
                    return next
                  })
                }
                break

              case 'error':
                throw new Error(data.error || 'Stream error')

              case 'done':
                // Stream complete
                break
            }
          } catch (parseErr) {
            // Skip malformed JSON lines
            if (eventType === 'error') throw parseErr
          }
          eventType = ''
        }
      }
    }

    // Disable animation for streamed messages (tokens already arrive progressively)
    setAnimateMessageId(undefined)
  }

  const sendMessageNonStreaming = async (content: string, token: string, isFirstMessage: boolean, userPlaceholderId: number) => {
    const response = await fetch(`${API_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({
        session_id: sessionId,
        message: content,
      }),
    })

    if (!response.ok) {
      throw new Error('Failed to send message')
    }

    const data = await response.json()

    if (data.user_message_id) {
      setMessages(prev => prev.map(msg =>
        msg.id === userPlaceholderId
          ? { ...msg, id: data.user_message_id }
          : msg
      ))
      setSeenMessageIds(prev => {
        const next = new Set(prev)
        next.delete(userPlaceholderId)
        next.add(data.user_message_id)
        return next
      })
    }

    const assistantMessage: Message = {
      id: data.message_id,
      role: 'assistant',
      content: data.answer,
      citations: data.citations,
      follow_ups: data.follow_ups || [],
      created_at: new Date().toISOString(),
    }
    setMessages(prev => [...prev, assistantMessage])
    setSeenMessageIds(prev => {
      const next = new Set(prev)
      next.add(assistantMessage.id)
      return next
    })
    const shouldAnimateAssistant = animationEnabled && !seenMessageIds.has(assistantMessage.id)
    setAnimateMessageId(shouldAnimateAssistant ? assistantMessage.id : undefined)

    if (isFirstMessage) {
      notifySessionTitle(content)
      onSessionHasMessages?.(sessionId)
    }
  }

  const sendMessage = async (content: string) => {
    enableAutoScroll()

    // Add user message to UI
    const userPlaceholderId = Date.now()
    const userMessage: Message = {
      id: userPlaceholderId,
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
    setError(null)
    const hasExistingUserMessage = messages.some(msg => msg.role === 'user')
    const isFirstMessage = !hasExistingUserMessage

    try {
      const token = await getToken()
      if (!token) {
        setError('Authentication required')
        setIsLoading(false)
        return
      }

      if (ENABLE_STREAMING) {
        // Create a placeholder assistant message for progressive rendering
        const placeholderId = Date.now() + 1
        const placeholderMessage: Message = {
          id: placeholderId,
          role: 'assistant',
          content: '',
          citations: [],
          follow_ups: [],
          created_at: new Date().toISOString(),
        }
        setMessages(prev => [...prev, placeholderMessage])
        setSeenMessageIds(prev => {
          const next = new Set(prev)
          next.add(placeholderId)
          return next
        })
        // Disable animation — streaming tokens are already progressive
        setAnimateMessageId(undefined)
        setIsLoading(false) // Hide bouncing dots, the placeholder message is visible

        await streamAssistantMessage(
          `${API_URL}/chat/stream`,
          { session_id: sessionId, message: content },
          placeholderId,
          token,
          userPlaceholderId
        )
        if (isFirstMessage) {
          notifySessionTitle(content)
          onSessionHasMessages?.(sessionId)
        }
      } else {
        await sendMessageNonStreaming(content, token, isFirstMessage, userPlaceholderId)
      }
    } catch (err) {
      setError('Failed to get response. Please try again.')
      console.error('Error sending message:', err)
    } finally {
      setIsLoading(false)
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

  const removeMessagesAfter = (messageId: number) => {
    setMessages(prev => prev.filter(msg => msg.id <= messageId))
    setSeenMessageIds(prev => {
      const next = new Set(prev)
      for (const id of Array.from(next)) {
        if (id > messageId) next.delete(id)
      }
      return next
    })
  }

  const regenerateAnswer = async (userMessageId: number, options?: { skipLoading?: boolean }) => {
    enableAutoScroll()
    const skipLoading = options?.skipLoading === true
    setIsRegenerating(true)
    setError(null)
    try {
      const token = await getToken()
      if (!token) {
        setError('Authentication required')
        return
      }

      removeMessagesAfter(userMessageId)

      // Create a placeholder assistant message for progressive rendering
      const placeholderId = Date.now() + 1
      const placeholderMessage: Message = {
        id: placeholderId,
        role: 'assistant',
        content: '',
        citations: [],
        follow_ups: [],
        created_at: new Date().toISOString(),
      }
      setMessages(prev => [...prev, placeholderMessage])
      setSeenMessageIds(prev => {
        const next = new Set(prev)
        next.add(placeholderId)
        return next
      })
      setAnimateMessageId(undefined)

      await streamAssistantMessage(
        `${API_URL}/chat/regenerate/stream`,
        { session_id: sessionId, user_message_id: userMessageId },
        placeholderId,
        token
      )
    } catch (err) {
      console.error('Error regenerating response:', err)
      setError('Failed to regenerate response. Please try again.')
    } finally {
      setIsRegenerating(false)
    }
  }

  const editQuestionAndRegenerate = async (messageId: number, content: string) => {
    if (!content.trim()) return
    setIsRegenerating(true)
    setError(null)
    try {
      const token = await getToken()
      if (!token) {
        setError('Authentication required')
        return
      }

      const response = await fetch(`${API_URL}/messages/edit`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          session_id: sessionId,
          message_id: messageId,
          content,
        }),
      })

      if (!response.ok) {
        const detail = await response.text()
        console.error('Edit message failed', {
          url: `${API_URL}/messages/edit`,
          status: response.status,
          detail
        })
        throw new Error(`Failed to edit message (${response.status})`)
      }

      const data = await response.json()
      const deletedIds: number[] = data.deleted_message_ids || []

      setMessages(prev =>
        prev
          .map(msg => (msg.id === messageId ? { ...msg, content } : msg))
          .filter(msg => !deletedIds.includes(msg.id))
      )
      setSeenMessageIds(prev => {
        const next = new Set(prev)
        deletedIds.forEach(id => next.delete(id))
        return next
      })

      await regenerateAnswer(messageId, { skipLoading: true })
    } catch (err) {
      console.error('Error editing message:', err)
      setError('Failed to edit message. Please try again.')
    } finally {
      setIsRegenerating(false)
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
            <span className="material-symbols-outlined text-[20px]">settings</span>
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
        ref={messageScrollRef}
        onScroll={handleMessagesScroll}
        className={`flex-1 min-h-0 overflow-y-auto px-4 sm:px-6 md:px-8 lg:px-10 py-4 sm:py-6 scrollbar-thin ${
          theme === 'dark'
            ? 'bg-gradient-to-b from-transparent via-slate-950/20 to-slate-950/60'
            : 'bg-gradient-to-b from-white/60 to-slate-50'
        }`}
      >
        {messages.length === 0 && !isLoading && !isLoadingHistory && (
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
          isLoading={isLoading}
          isRegenerating={isRegenerating}
          onEditQuestion={editQuestionAndRegenerate}
          onFollowupClick={(text: string) => sendMessage(text)}
        />
        
        {isLoading && (
          <div className="flex items-start gap-3 mb-4">
            <div
              className={`w-10 h-10 rounded-2xl flex items-center justify-center flex-shrink-0 ${
                theme === 'dark' ? 'bg-slate-800 text-orange-200' : 'bg-primary text-white'
              }`}
            >
              <span className="material-symbols-outlined text-[22px]">smart_toy</span>
            </div>
            <div
              className={`flex-1 rounded-2xl p-4 ${
                theme === 'dark'
                  ? 'bg-slate-900/60 border border-slate-800'
                  : 'bg-white shadow border border-gray-100'
              }`}
            >
              <div className="flex items-center gap-1.5 px-1">
                <div className="thinking-dot w-2.5 h-2.5 rounded-full bg-gray-400"></div>
                <div className="thinking-dot w-2.5 h-2.5 rounded-full bg-gray-400"></div>
                <div className="thinking-dot w-2.5 h-2.5 rounded-full bg-gray-400"></div>
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

        {showJumpToLatest && (
          <div className="sticky bottom-4 z-10 flex justify-end pointer-events-none">
            <button
              type="button"
              onClick={() => {
                enableAutoScroll()
                scrollToBottom('smooth')
              }}
              className={`pointer-events-auto inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium shadow-lg transition-colors ${
                theme === 'dark'
                  ? 'bg-slate-800 text-gray-100 hover:bg-slate-700 border border-slate-600'
                  : 'bg-white text-gray-800 hover:bg-gray-50 border border-gray-200'
              }`}
            >
              <span className="material-symbols-outlined text-[18px]">south</span>
              Jump to latest
            </button>
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

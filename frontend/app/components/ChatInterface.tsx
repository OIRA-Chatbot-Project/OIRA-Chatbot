'use client'

import { useState, useEffect, useRef, ChangeEvent } from 'react'
import { useAuth } from '@clerk/nextjs'
import { createPortal } from 'react-dom'
import MessageList from './MessageList'
import MessageInput from './MessageInput'
import { Message, Theme, ScheduleUploadResponse } from '../types'
import { API_URL } from '../utils/config'
import { generateSessionTitle } from '../utils/session'
import { SUGGESTED_QUESTION_GROUPS } from '../utils/suggestedQuestions'

/**
 * Returns a new array with the same elements in a random order (Fisher-Yates shuffle).
 *
 * @param items - The array to shuffle. The original array is not mutated.
 * @returns A new shuffled array.
 */
const shuffle = <T,>(items: T[]): T[] => {
  const next = [...items]
  for (let i = next.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[next[i], next[j]] = [next[j], next[i]]
  }
  return next
}

/**
 * Builds a shuffled list of suggested questions by picking one random question from
 * each category in `SUGGESTED_QUESTION_GROUPS`, then shuffling the category order.
 *
 * @returns An array of question strings, one per category, in random order.
 */
const buildSuggestedQuestions = () => {
  return shuffle((Object.values(SUGGESTED_QUESTION_GROUPS) as unknown as string[][]).map(group => {
    const [question] = shuffle([...group])
    return question
  }))
}

interface ChatInterfaceProps {
  sessionId: string
  onSessionTitleUpdate?: (sessionId: string, title: string) => void
  onSessionHasMessages?: (sessionId: string) => void
  theme: Theme
  onToggleTheme: () => void
}

/**
 * Main chat interface component managing the full conversation lifecycle.
 *
 * Responsibilities:
 * - Loading and displaying conversation history for the active session.
 * - Sending user messages via streaming SSE (`/chat/stream`) or non-streaming (`/chat`).
 * - Progressively rendering streaming tokens into a placeholder message bubble.
 * - Regenerating assistant responses and supporting inline message editing.
 * - Submitting thumbs up/down feedback.
 * - Handling schedule file uploads and displaying parsed course information.
 * - Notifying the parent of session title updates and first-message events.
 */
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
  const [isLinksOpen, setIsLinksOpen] = useState(false)
  const [isClient, setIsClient] = useState(false)
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
  const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>(() => buildSuggestedQuestions())
  const fileInputRef = useRef<HTMLInputElement>(null)

  /**
   * Filters a message array to remove duplicate entries, keeping the first occurrence
   * of each message ID.
   *
   * @param items - The message array, potentially containing duplicates.
   * @returns A new array with duplicates removed.
   */
  const dedupeMessagesById = (items: Message[]) => {
    const seen = new Set<string>()
    return items.filter((item) => {
      const key = String(item.id)
      if (seen.has(key)) return false
      seen.add(key)
      return true
    })
  }

  useEffect(() => {
    setIsClient(true)
  }, [])

  useEffect(() => {
    // Load conversation history when session changes
    loadConversationHistory()
    setSuggestedQuestions(buildSuggestedQuestions())
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

  /** Returns `true` if the message scroll container is within 120 px of its bottom edge. */
  const isNearBottom = () => {
    const container = messageScrollRef.current
    if (!container) return true

    const distanceFromBottom =
      container.scrollHeight - (container.scrollTop + container.clientHeight)

    return distanceFromBottom <= 120
  }

  /** Scroll event handler — updates `shouldAutoScrollRef` and shows/hides the jump-to-latest button. */
  const handleMessagesScroll = () => {
    const nearBottom = isNearBottom()
    shouldAutoScrollRef.current = nearBottom
    setShowJumpToLatest(!nearBottom && messages.length > 0)
  }

  /** Re-enables automatic scrolling and hides the jump-to-latest button. */
  const enableAutoScroll = () => {
    shouldAutoScrollRef.current = true
    setShowJumpToLatest(false)
  }

  /**
   * Scrolls the message list to the bottom sentinel element.
   *
   * @param behavior - The scroll animation style (`'smooth'` by default, `'auto'` for instant).
   */
  const scrollToBottom = (behavior: ScrollBehavior = 'smooth') => {
    messagesEndRef.current?.scrollIntoView({ behavior })
  }

  /**
   * Fetches and renders the full message history for the current session.
   *
   * Also notifies the parent of any existing session title derived from the first
   * user message, and marks the session as having messages when history is non-empty.
   */
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
        setMessages(dedupeMessagesById(data.messages || []))
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

  /**
   * Requests an AI-generated session title from the backend and forwards it to the parent.
   *
   * Falls back to `generateSessionTitle` (a local heuristic) if the backend call fails
   * or returns an error response.
   *
   * @param content - The text of the first user message used as the title source.
   */
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

  /**
   * Consumes a Server-Sent Events stream from the backend and progressively updates
   * the in-progress assistant message placeholder.
   *
   * Handled event types:
   * - `metadata` — sets citations on the placeholder.
   * - `user` — swaps the temporary user message ID for the real DB ID.
   * - `token` — appends the token string to the placeholder's content.
   * - `followups` — attaches follow-up question suggestions.
   * - `saved` — swaps the placeholder assistant ID for the real DB ID.
   * - `error` — throws so the caller can surface the failure.
   * - `done` — marks the stream as complete (no state change needed).
   *
   * @param url - The streaming endpoint URL.
   * @param body - JSON-serializable request body.
   * @param placeholderId - The temporary ID of the assistant message placeholder.
   * @param token - A valid Clerk JWT.
   * @param userPlaceholderId - Optional temporary ID of the user message placeholder,
   *   used to apply the real ID returned via the `user` event.
   */
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
                  setMessages(prev =>
                    dedupeMessagesById(
                      prev.map(msg =>
                        msg.id === userPlaceholderId
                          ? { ...msg, id: data.message_id }
                          : msg
                      )
                    )
                  )
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
                  setMessages(prev =>
                    dedupeMessagesById(
                      prev.map(msg =>
                        msg.id === placeholderId
                          ? { ...msg, id: data.message_id }
                          : msg
                      )
                    )
                  )
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

  /**
   * Sends a message using the non-streaming `/chat` endpoint and appends the full
   * assistant response once the request completes.
   *
   * Used as a fallback when `ENABLE_STREAMING` is false.
   *
   * @param content - The user's message text.
   * @param token - A valid Clerk JWT.
   * @param isFirstMessage - Whether this is the first user message in the session.
   * @param userPlaceholderId - The temporary ID assigned to the user message placeholder.
   */
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
    setMessages(prev => dedupeMessagesById([...prev, assistantMessage]))
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

  /**
   * Main message submission handler.
   *
   * Optimistically appends the user message to the UI, then either opens an SSE stream
   * (streaming mode) or awaits the full response (non-streaming mode). Updates session
   * state on the first message of a session.
   *
   * @param content - The trimmed user message text.
   */
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
    setMessages(prev => dedupeMessagesById([...prev, userMessage]))
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
        setMessages(prev => dedupeMessagesById([...prev, placeholderMessage]))
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

  /**
   * Submits a thumbs up/down rating (and optional note) for an assistant message.
   *
   * On success, updates the local message state to reflect the submitted feedback
   * so the feedback controls are hidden and the indicator is shown.
   *
   * @param messageId - The DB ID of the message being rated.
   * @param rating - `1` for thumbs up, `-1` for thumbs down.
   * @param note - Optional free-text elaboration (used for thumbs-down reports).
   */
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

  /**
   * Removes all messages with an ID greater than `messageId` from local state.
   *
   * Used before regenerating a response to clear the stale assistant reply and any
   * messages that follow it.
   *
   * @param messageId - The ID of the anchor message to preserve (inclusive).
   */
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

  /**
   * Regenerates the assistant response for a given user message.
   *
   * Removes all messages after `userMessageId`, inserts a new streaming placeholder,
   * and calls the `/chat/regenerate/stream` endpoint.
   *
   * @param userMessageId - The DB ID of the user message to regenerate a response for.
   * @param options.skipLoading - When `true`, skips setting `isRegenerating` to `true`
   *   (used when called from `editQuestionAndRegenerate` which manages its own loading state).
   */
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
      setMessages(prev => dedupeMessagesById([...prev, placeholderMessage]))
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

  /**
   * Updates the content of a user message and regenerates the assistant response.
   *
   * Sends a PATCH to `/messages/edit` which returns the IDs of any downstream messages
   * that were deleted server-side. The local state is updated to reflect both the new
   * content and the deletions before streaming begins.
   *
   * @param messageId - The DB ID of the user message to edit.
   * @param content - The new message content (must be non-empty after trimming).
   */
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

  /** Programmatically opens the hidden file input dialog to start a schedule upload. No-ops while an upload is in progress. */
  const triggerScheduleUpload = () => {
    if (isUploadingSchedule) return
    fileInputRef.current?.click()
  }

  /**
   * Handles a schedule file selected via the hidden file input.
   *
   * Uploads the file to `/schedule/upload`, then appends both a user-side schedule
   * summary message and the assistant's parsed-courses response to the conversation.
   * Sets `uploadError` with a user-friendly message on failure.
   *
   * @param event - The `change` event fired by the file input element.
   */
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

      setMessages(prev => dedupeMessagesById([...prev, scheduleMessage, assistantMessage]))
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

      {isClient && isLinksOpen
        ? createPortal(
            <div className="fixed inset-0 z-[9998]">
              <div
                className="absolute inset-0 bg-black/30 backdrop-blur"
                onClick={() => setIsLinksOpen(false)}
                aria-hidden="true"
              ></div>
              <div
                className={`absolute left-1/2 top-1/2 w-[92vw] max-w-sm -translate-x-1/2 -translate-y-1/2 rounded-2xl border shadow-2xl ${
                  theme === 'dark'
                    ? 'bg-slate-900 border-slate-800 text-slate-100'
                    : 'bg-white border-gray-200 text-slate-800'
                }`}
              >
                <div className="flex items-center justify-between border-b px-4 py-3 text-sm font-semibold">
                  <span>Important Links & Files</span>
                  <button
                    onClick={() => setIsLinksOpen(false)}
                    className={`rounded-lg px-2 py-1 text-xs ${
                      theme === 'dark'
                        ? 'text-slate-400 hover:text-slate-100 hover:bg-slate-800'
                        : 'text-slate-500 hover:text-slate-900 hover:bg-slate-100'
                    }`}
                  >
                    Close
                  </button>
                </div>
                <div className="px-4 py-3 space-y-4 text-sm">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Links</p>
                    <ul className="mt-2 space-y-2">
                      <li>
                        <a
                          href="https://pubapps.bucknell.edu/CourseInformation/#/lookup"
                          target="_blank"
                          rel="noreferrer"
                          className="underline underline-offset-2 hover:text-primary"
                        >
                          Course Information Page (Public)
                        </a>
                      </li>
                      <li>
                        <a
                          href="https://banner.ban.bucknell.edu/StudentRegistrationSsb/ssb/registration/registration"
                          target="_blank"
                          rel="noreferrer"
                          className="underline underline-offset-2 hover:text-primary"
                        >
                          Course Registration (Banner Self Service)
                        </a>
                      </li>
                      <li>
                        <a
                          href="https://banner.ban.bucknell.edu/BannerExtensibility/customPage/page/BucknellAPR?type=STUD"
                          target="_blank"
                          rel="noreferrer"
                          className="underline underline-offset-2 hover:text-primary"
                        >
                          Academic Progress Report
                        </a>
                      </li>
                    </ul>
                  </div>
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Files</p>
                    <ul className="mt-2 space-y-2">
                      <li>
                        <a
                          href="https://drive.google.com/file/d/1gaUCs_WZl0jLeS41y6cCVwHXiLeeejDA/view?usp=sharing"
                          target="_blank"
                          rel="noreferrer"
                          className="underline underline-offset-2 hover:text-primary"
                        >
                          Course Catalog (PDF)
                        </a>
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>,
            document.body
          )
        : null}

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
            <div className="max-w-2xl px-4">
              <h2
                className={`text-xl sm:text-2xl font-semibold mb-3 ${
                  theme === 'dark' ? 'text-gray-100' : 'text-gray-700'
                }`}
              >
                Welcome to the Bucknell Course Catalog Assistant! 👋
              </h2>
              <p className={`mb-4 text-sm sm:text-base ${theme === 'dark' ? 'text-gray-400' : 'text-gray-600'}`}>
                I can help with Bucknell course catalog details and official academic policies.
              </p>
              <div
                className={`text-left rounded-2xl p-5 space-y-2 ${
                  theme === 'dark'
                    ? 'bg-slate-900/60 text-gray-100 border border-slate-800'
                    : 'bg-white text-gray-700 border border-gray-100 shadow'
                }`}
              >
                <p className="text-sm font-semibold">Try asking one of these:</p>
                <div className="grid gap-2">
                  {suggestedQuestions.map((question) => (
                    <button
                      key={question}
                      type="button"
                      onClick={() => sendMessage(question)}
                      className={`w-full rounded-2xl border px-4 py-3 text-left text-sm transition-colors ${
                        theme === 'dark'
                          ? 'border-slate-700 bg-slate-950/40 hover:border-slate-500 hover:bg-slate-900'
                          : 'border-gray-200 bg-white hover:border-gray-300 hover:bg-slate-50'
                      }`}
                    >
                      {question}
                    </button>
                  ))}
                </div>
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
        <input
          ref={fileInputRef}
          type="file"
          accept=".png,.jpg,.jpeg,.bmp,.tiff,.tif,.gif,.txt,.csv"
          className="hidden"
          onChange={handleScheduleUpload}
        />
        <MessageInput
          onSend={sendMessage}
          onUploadSchedule={triggerScheduleUpload}
          onOpenImportantLinks={() => setIsLinksOpen(true)}
          isUploadingSchedule={isUploadingSchedule}
          disabled={isLoading}
          theme={theme}
        />
      </div>
    </>
  )
}

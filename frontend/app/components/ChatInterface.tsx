'use client'

import { useState, useEffect, useRef, ChangeEvent } from 'react'
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
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const [showSettings, setShowSettings] = useState(false)
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
    // Scroll to bottom when messages change
    scrollToBottom()
  }, [messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const loadConversationHistory = async () => {
    try {
      const response = await fetch(`${API_URL}/messages?session_id=${sessionId}`)
      if (response.ok) {
        const data = await response.json()
        setMessages(data.messages)
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

  const notifySessionTitle = (content: string) => {
    if (!content) return
    const title = generateSessionTitle(content)
    onSessionTitleUpdate?.(sessionId, title)
  }

  const sendMessage = async (content: string) => {
    // Add user message to UI
    const userMessage: Message = {
      id: Date.now(),
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    }
    setMessages(prev => [...prev, userMessage])
    setIsLoading(true)
    setError(null)
    const hasExistingUserMessage = messages.some(msg => msg.role === 'user')
    if (!hasExistingUserMessage) {
      notifySessionTitle(content)
      onSessionHasMessages?.(sessionId)
    }

    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
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

      // Add assistant message to UI
      const assistantMessage: Message = {
        id: data.message_id,
        role: 'assistant',
        content: data.answer,
        citations: data.citations,
        created_at: new Date().toISOString(),
      }
      setMessages(prev => [...prev, assistantMessage])
    } catch (err) {
      setError('Failed to get response. Please try again.')
      console.error('Error sending message:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const submitFeedback = async (messageId: number, rating: number, note?: string) => {
    try {
      const response = await fetch(`${API_URL}/feedback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
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
      const formData = new FormData()
      formData.append('session_id', sessionId)
      formData.append('file', file)

      const response = await fetch(`${API_URL}/schedule/upload`, {
        method: 'POST',
        body: formData,
      })

      let payload: ScheduleUploadResponse | { detail?: string }
      try {
        payload = await response.json()
      } catch {
        payload = { detail: undefined } as ScheduleUploadResponse
      }
      if (!response.ok) {
        throw new Error(payload?.detail || 'Failed to process schedule')
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
        created_at: new Date().toISOString(),
      }

      setMessages(prev => [...prev, scheduleMessage, assistantMessage])
      onSessionHasMessages?.(sessionId)
      setUploadError(null)
    } catch (err) {
      console.error('Failed to upload schedule:', err)
      setUploadError('Failed to analyze the schedule. Please try again with a clearer image or text export.')
    } finally {
      setIsUploadingSchedule(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  return (
    <div
      className={`relative flex flex-col h-full w-full ${
        theme === 'dark' ? 'text-gray-100' : 'text-gray-900'
      }`}
    >
      {/* Header */}
      <header
        className={`px-8 py-6 border-b flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between ${
          theme === 'dark'
            ? 'border-slate-800/80 bg-gradient-to-r from-slate-950/80 to-slate-900/50'
            : 'border-white/70 bg-white/60'
        }`}
      >
        <div>
          <p className="text-xs uppercase tracking-[0.4em] text-primary">Bucknell</p>
          <h1
            className={`text-3xl font-semibold ${
              theme === 'dark' ? 'text-white' : 'text-secondary'
            }`}
          >
            Course Catalog Assistant
          </h1>
          <p
            className={`text-sm mt-2 ${
              theme === 'dark' ? 'text-gray-400' : 'text-gray-600'
            }`}
          >
            Modern answers powered by your catalog, presented in a focused workspace.
          </p>
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
          className={`mx-8 mt-4 rounded-2xl border px-4 py-3 text-sm ${
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
            className={`absolute right-8 top-28 z-20 w-72 rounded-3xl border shadow-2xl p-5 ${
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
          </div>
        </>
      )}

      {/* Messages */}
      <div
        className={`flex-1 overflow-y-auto px-6 sm:px-10 py-8 scrollbar-thin ${
          theme === 'dark'
            ? 'bg-gradient-to-b from-transparent via-slate-950/20 to-slate-950/60'
            : 'bg-gradient-to-b from-white/60 to-slate-50'
        }`}
      >
        {messages.length === 0 && !isLoading && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="max-w-md">
              <h2
                className={`text-xl font-semibold mb-3 ${
                  theme === 'dark' ? 'text-gray-100' : 'text-gray-700'
                }`}
              >
                Welcome to the Bucknell Course Catalog Assistant! 👋
              </h2>
              <p className={`mb-4 ${theme === 'dark' ? 'text-gray-400' : 'text-gray-600'}`}>
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
        />
        
        {isLoading && (
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
        className={`border-t px-6 sm:px-10 py-5 backdrop-blur ${
          theme === 'dark'
            ? 'bg-slate-950/80 border-slate-800/80'
            : 'bg-white/70 border-white/80'
        }`}
      >
        <MessageInput onSend={sendMessage} disabled={isLoading} theme={theme} />
      </div>
    </div>
  )
}

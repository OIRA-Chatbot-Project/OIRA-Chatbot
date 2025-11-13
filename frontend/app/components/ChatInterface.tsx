'use client'

import { useState, useEffect, useRef } from 'react'
import MessageList from './MessageList'
import MessageInput from './MessageInput'
import { Message, Citation } from '../types'

interface ChatInterfaceProps {
  sessionId: string
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function ChatInterface({ sessionId }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // Load conversation history when session changes
    loadConversationHistory()
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
      }
    } catch (err) {
      console.error('Failed to load conversation history:', err)
    }
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

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-secondary">
              Bucknell Course Catalog Assistant
            </h1>
            <p className="text-sm text-gray-600 mt-1">
              Ask me anything about courses, majors, and requirements
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
              <span className="w-2 h-2 bg-green-400 rounded-full mr-2"></span>
              Connected
            </span>
          </div>
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 scrollbar-thin">
        {messages.length === 0 && !isLoading && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="max-w-md">
              <h2 className="text-xl font-semibold text-gray-700 mb-3">
                Welcome to the Bucknell Course Catalog Assistant! 👋
              </h2>
              <p className="text-gray-600 mb-4">
                I can help you find information about courses, majors, prerequisites, and academic planning.
              </p>
              <div className="text-left bg-gray-50 rounded-lg p-4 space-y-2">
                <p className="text-sm font-medium text-gray-700">Try asking:</p>
                <ul className="text-sm text-gray-600 space-y-1">
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
        />
        
        {isLoading && (
          <div className="flex items-start gap-3 mb-4">
            <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-white flex-shrink-0">
              🤖
            </div>
            <div className="flex-1 bg-white rounded-lg shadow-sm p-4">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200"></div>
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">
            {error}
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 bg-white px-6 py-4">
        <MessageInput onSend={sendMessage} disabled={isLoading} />
      </div>
    </div>
  )
}

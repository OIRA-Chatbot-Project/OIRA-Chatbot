'use client'

import { useState } from 'react'
import { Message } from '../types'

interface MessageItemProps {
  message: Message
  onFeedback: (messageId: number, rating: number, note?: string) => void
}

export default function MessageItem({ message, onFeedback }: MessageItemProps) {
  const [showFeedbackNote, setShowFeedbackNote] = useState(false)
  const [feedbackNote, setFeedbackNote] = useState('')
  const [pendingRating, setPendingRating] = useState<number | null>(null)

  const isUser = message.role === 'user'

  const handleFeedback = (rating: number) => {
    if (rating === -1) {
      // Show note input for negative feedback
      setPendingRating(rating)
      setShowFeedbackNote(true)
    } else {
      // Submit positive feedback immediately
      onFeedback(message.id, rating)
    }
  }

  const submitFeedbackWithNote = () => {
    if (pendingRating !== null) {
      onFeedback(message.id, pendingRating, feedbackNote || undefined)
      setShowFeedbackNote(false)
      setFeedbackNote('')
      setPendingRating(null)
    }
  }

  const cancelFeedbackNote = () => {
    setShowFeedbackNote(false)
    setFeedbackNote('')
    setPendingRating(null)
  }

  // Format message content with basic markdown-like rendering
  const formatContent = (content: string) => {
    // Split by double newlines for paragraphs
    const paragraphs = content.split('\n\n')
    
    return paragraphs.map((paragraph, i) => {
      // Check if it's a list
      if (paragraph.trim().startsWith('•') || paragraph.trim().startsWith('-')) {
        const items = paragraph.split('\n').filter(line => line.trim())
        return (
          <ul key={i} className="list-disc list-inside space-y-1 mb-3">
            {items.map((item, j) => (
              <li key={j}>{item.replace(/^[•\-]\s*/, '')}</li>
            ))}
          </ul>
        )
      }
      
      // Check if it's a header (starts with **)
      if (paragraph.trim().startsWith('**')) {
        const text = paragraph.replace(/\*\*/g, '')
        return (
          <h3 key={i} className="font-semibold text-lg mb-2 mt-3">
            {text}
          </h3>
        )
      }
      
      // Regular paragraph
      return (
        <p key={i} className="mb-3">
          {paragraph}
        </p>
      )
    })
  }

  return (
    <div className={`flex items-start gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-white flex-shrink-0">
          🤖
        </div>
      )}
      
      <div className={`flex flex-col max-w-3xl ${isUser ? 'items-end' : 'items-start'}`}>
        <div
          className={`rounded-lg px-4 py-3 ${
            isUser
              ? 'bg-secondary text-white'
              : 'bg-white shadow-sm border border-gray-200'
          }`}
        >
          <div className="markdown-content">
            {formatContent(message.content)}
          </div>
          
          {message.citations && message.citations.length > 0 && (
            <div className="mt-4 pt-3 border-t border-gray-200">
              <p className="text-xs font-semibold text-gray-600 mb-2">
                📚 References ({message.citations.length}):
              </p>
              <div className="space-y-2">
                {message.citations.map((citation, idx) => (
                  <div key={idx} className="text-xs text-gray-600 bg-gray-50 rounded p-2">
                    <div className="font-medium">
                      [{citation.source}, p. {citation.page}]
                    </div>
                    <div className="text-gray-500 mt-1 line-clamp-2">
                      {citation.content}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {!isUser && !message.feedback && (
          <div className="mt-2 flex items-center gap-2">
            {!showFeedbackNote ? (
              <>
                <button
                  onClick={() => handleFeedback(1)}
                  className="text-gray-400 hover:text-green-600 transition-colors p-1"
                  title="Helpful"
                >
                  👍
                </button>
                <button
                  onClick={() => handleFeedback(-1)}
                  className="text-gray-400 hover:text-red-600 transition-colors p-1"
                  title="Not helpful"
                >
                  👎
                </button>
              </>
            ) : (
              <div className="bg-white border border-gray-200 rounded-lg p-3 shadow-sm">
                <p className="text-xs text-gray-600 mb-2">
                  What could be improved?
                </p>
                <textarea
                  value={feedbackNote}
                  onChange={(e) => setFeedbackNote(e.target.value)}
                  placeholder="Optional feedback..."
                  className="w-full text-sm border border-gray-300 rounded px-2 py-1 mb-2 focus:outline-none focus:ring-2 focus:ring-primary"
                  rows={2}
                />
                <div className="flex gap-2">
                  <button
                    onClick={submitFeedbackWithNote}
                    className="text-xs bg-secondary text-white px-3 py-1 rounded hover:bg-opacity-90"
                  >
                    Submit
                  </button>
                  <button
                    onClick={cancelFeedbackNote}
                    className="text-xs text-gray-600 px-3 py-1 rounded hover:bg-gray-100"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {message.feedback && (
          <div className="mt-2 text-xs text-gray-500">
            {message.feedback === 1 ? '👍 Marked as helpful' : '👎 Feedback submitted'}
          </div>
        )}

        <div className="text-xs text-gray-400 mt-1">
          {new Date(message.created_at).toLocaleTimeString()}
        </div>
      </div>

      {isUser && (
        <div className="w-8 h-8 rounded-full bg-gray-300 flex items-center justify-center flex-shrink-0">
          👤
        </div>
      )}
    </div>
  )
}

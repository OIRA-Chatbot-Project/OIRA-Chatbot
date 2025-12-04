'use client'

import { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Message, Theme } from '../types'

interface MessageItemProps {
  message: Message
  onFeedback: (messageId: number, rating: number, note?: string) => void
  theme: Theme
  animationEnabled?: boolean
  animate?: boolean
}

export default function MessageItem({ message, onFeedback, theme, animationEnabled = false, animate = false }: MessageItemProps) {
  const [displayedCount, setDisplayedCount] = useState(0)
  const [animationComplete, setAnimationComplete] = useState(false)

  const isAssistant = message.role === 'assistant'
  const shouldAnimate = animationEnabled && animate && isAssistant

  const citationRegex = /\[[^\]]+?,\s*p\.\s*\d+\]/gi
  const rawContent = message.content || ''
  const cleanedContent = rawContent.replace(citationRegex, '').replace(/ {2,}/g, ' ')
  const words = cleanedContent ? cleanedContent.split(/(\s+)/) : []

  useEffect(() => {
    if (!shouldAnimate) {
      setDisplayedCount(words.length)
      setAnimationComplete(true)
      return
    }

    setDisplayedCount(0)
    setAnimationComplete(false)
    let i = 0
    const delayPerUnit = 40
    const id = setInterval(() => {
      i += 1
      setDisplayedCount(i)
      if (i >= words.length) {
        clearInterval(id)
        setAnimationComplete(true)
      }
    }, delayPerUnit)

    return () => clearInterval(id)
  }, [message.id, animationEnabled, animate])

  const [showFeedbackNote, setShowFeedbackNote] = useState(false)
  const [feedbackNote, setFeedbackNote] = useState('')
  const [pendingRating, setPendingRating] = useState<number | null>(null)
  const [isCopied, setIsCopied] = useState(false)
  const [showFlagFeedback, setShowFlagFeedback] = useState(false)
  const [flagReason, setFlagReason] = useState('')
  const [flagComment, setFlagComment] = useState('')

  const isUser = message.role === 'user'

  const handleFeedback = (rating: number) => {
    if (rating === -1) {
      setPendingRating(rating)
      setShowFeedbackNote(true)
    } else {
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

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(message.content)
      setIsCopied(true)
      setTimeout(() => setIsCopied(false), 2000)
    } catch (error) {
      console.error('Failed to copy message', error)
    }
  }

  const handleFlagSubmit = (reason: string, note?: string) => {
    onFeedback(message.id, -1, `${reason}${note ? `: ${note}` : ''}`)
    setShowFlagFeedback(false)
    setFlagReason('')
    setFlagComment('')
  }

  const toggleFlagFeedback = () => {
    setShowFlagFeedback(prev => {
      const next = !prev
      if (!next) {
        setFlagReason('')
        setFlagComment('')
      }
      return next
    })
  }

  return (
    <div className={`flex items-start gap-4 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div
          className={`w-10 h-10 rounded-2xl flex items-center justify-center flex-shrink-0 ${
            theme === 'dark' ? 'bg-slate-800 text-orange-200' : 'bg-primary text-white'
          }`}
        >
          🤖
        </div>
      )}
      
      <div className={`flex flex-col max-w-3xl ${isUser ? 'items-end' : 'items-start'}`}>
        <span
          className={`text-[11px] uppercase tracking-[0.3em] mb-2 ${
            isUser
              ? theme === 'dark'
                ? 'text-orange-200'
                : 'text-secondary'
              : theme === 'dark'
                ? 'text-gray-500'
                : 'text-gray-500'
          }`}
        >
          {isUser ? 'You' : 'Assistant'}
        </span>

        <div
          className={`rounded-[22px] px-5 py-4 backdrop-blur ${
            isUser
              ? theme === 'dark'
                ? 'bg-gradient-to-r from-indigo-500 via-blue-500 to-sky-500 text-white shadow-lg shadow-blue-900/40'
                : 'bg-gradient-to-r from-secondary to-blue-500 text-white shadow-xl shadow-blue-200/50'
              : theme === 'dark'
                ? 'bg-slate-900/60 text-gray-100 shadow-xl shadow-black/40 border border-slate-800'
                : 'bg-white/90 text-gray-900 shadow-lg shadow-gray-200/60 border border-white/70'
          }`}
        >
          <div className={`markdown-content ${isUser ? 'text-white' : theme === 'dark' ? 'text-gray-100' : 'text-gray-900'}`}>
            {shouldAnimate && !animationComplete ? (
              <div className="animated-text whitespace-pre-wrap">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {words.slice(0, displayedCount).join('')}
                </ReactMarkdown>
                <span className="inline-block animate-pulse ml-1">▌</span>
              </div>
            ) : (
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {cleanedContent}
              </ReactMarkdown>
            )}
          </div>
          
          {message.citations && message.citations.length > 0 && (animationComplete || !shouldAnimate) && (
            <div
              className={`mt-4 pt-3 border-t ${
                theme === 'dark' ? 'border-slate-700/80' : 'border-gray-200/80'
              }`}
            >
              <p
                className={`text-xs font-semibold mb-2 ${
                  theme === 'dark' ? 'text-gray-300' : 'text-gray-600'
                }`}
              >
                📚 References ({message.citations.length}):
              </p>
              <div className="space-y-2">
                {message.citations.map((citation, idx) => (
                  <div
                    key={idx}
                    className={`text-xs rounded-2xl p-3 border ${
                      theme === 'dark'
                        ? 'bg-slate-900/60 text-gray-200 border-slate-800'
                        : 'bg-white text-gray-600 border-gray-200'
                    }`}
                  >
                    {/* 🔗 FIXED: Dynamic PDF link */}
                    <div className="font-medium">
                      <a
                        href={`${typeof window !== 'undefined' ? window.location.origin : ''}/catalog.pdf#page=${citation.page}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="underline text-blue-500 hover:text-blue-600"
                      >
                        [{citation.source}, p. {citation.page}]
                      </a>
                    </div>

                    <div
                      className={`mt-1 line-clamp-2 ${
                        theme === 'dark' ? 'text-gray-400' : 'text-gray-500'
                      }`}
                    >
                      {citation.content}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {!isUser && !message.feedback && (
          <div className="mt-2 flex flex-col gap-2 w-full">
            <div className="flex items-center gap-2 text-xs">
              <button
                onClick={copyToClipboard}
                className={`px-2 py-1 rounded-full border transition-colors ${
                  theme === 'dark'
                    ? 'border-slate-700 text-gray-200 hover:bg-slate-800'
                    : 'border-gray-200 text-gray-600 hover:bg-gray-100'
                }`}
              >
                {isCopied ? 'Copied!' : 'Copy'}
              </button>

              <button
                onClick={toggleFlagFeedback}
                className={`px-2 py-1 rounded-full border transition-colors ${
                  theme === 'dark'
                    ? 'border-slate-700 text-gray-200 hover:bg-slate-800'
                    : 'border-gray-200 text-gray-600 hover:bg-gray-100'
                }`}
              >
                🚩
              </button>

              <div className={`w-px h-4 ${theme === 'dark' ? 'bg-slate-700' : 'bg-gray-300'} opacity-60`}></div>

              <button
                onClick={() => handleFeedback(1)}
                className="text-gray-400 hover:text-green-500 transition-colors p-1"
              >
                👍
              </button>
              <button
                onClick={() => handleFeedback(-1)}
                className="text-gray-400 hover:text-red-500 transition-colors p-1"
              >
                👎
              </button>
            </div>

            {showFeedbackNote && (
              <div
                className={`rounded-2xl p-3 shadow-lg border ${
                  theme === 'dark'
                    ? 'bg-slate-900 text-gray-100 border-slate-700'
                    : 'bg-white text-gray-700 border-gray-200'
                }`}
              >
                <p className={`text-xs mb-2 ${theme === 'dark' ? 'text-gray-400' : 'text-gray-600'}`}>
                  What could be improved?
                </p>

                <textarea
                  value={feedbackNote}
                  onChange={(e) => setFeedbackNote(e.target.value)}
                  className={`w-full text-sm rounded px-2 py-1 mb-2 focus:outline-none focus:ring-2 focus:ring-primary ${
                    theme === 'dark'
                      ? 'bg-slate-900 text-gray-100 placeholder:text-gray-500 border border-slate-700'
                      : 'bg-white text-gray-900 placeholder:text-gray-500 border border-gray-300'
                  }`}
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
                    className={`text-xs px-3 py-1 rounded ${
                      theme === 'dark' ? 'text-gray-400 hover:bg-slate-800' : 'text-gray-500 hover:bg-gray-100'
                    }`}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}

            {showFlagFeedback && (
              <div
                className={`rounded-2xl p-3 shadow-lg border ${
                  theme === 'dark'
                    ? 'bg-slate-900 text-gray-100 border-slate-700'
                    : 'bg-white text-gray-700 border-gray-200'
                }`}
              >
                <p className="text-xs font-semibold mb-2">Report an issue</p>

                <div className="flex flex-wrap gap-2 mb-3">
                  {['Wrong information', 'Formatting issue', 'Poor tone', 'Other'].map(option => (
                    <button
                      key={option}
                      onClick={() => setFlagReason(option)}
                      className={`px-3 py-1 rounded-full text-xs border transition-colors ${
                        flagReason === option
                          ? 'bg-primary text-white border-primary'
                          : theme === 'dark'
                            ? 'border-slate-700 text-gray-300 hover:border-slate-500'
                            : 'border-gray-300 text-gray-600 hover:border-gray-500'
                      }`}
                    >
                      {option}
                    </button>
                  ))}
                </div>

                {flagReason && (
                  <>
                    <textarea
                      value={flagComment}
                      onChange={(e) => setFlagComment(e.target.value)}
                      className={`w-full text-sm rounded px-3 py-2 mb-2 focus:outline-none focus:ring-2 focus:ring-primary ${
                        theme === 'dark'
                          ? 'bg-slate-900 text-gray-100 placeholder:text-gray-500 border border-slate-700'
                          : 'bg-white text-gray-900 placeholder:text-gray-500 border border-gray-300'
                      }`}
                      rows={3}
                    />

                    <div className="flex gap-2">
                      <button
                        onClick={() => handleFlagSubmit(flagReason, flagComment)}
                        className="text-xs bg-primary text-white px-3 py-1 rounded hover:bg-secondary"
                      >
                        Submit report
                      </button>

                      <button
                        onClick={() => {
                          setFlagReason('')
                          setFlagComment('')
                          setShowFlagFeedback(false)
                        }}
                        className={`text-xs px-3 py-1 rounded ${
                          theme === 'dark' ? 'text-gray-400 hover:bg-slate-800' : 'text-gray-500 hover:bg-gray-100'
                        }`}
                      >
                        Close
                      </button>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        )}

        {message.feedback && (
          <div className="mt-2 text-xs text-gray-500">
            {message.feedback === 1 ? '👍 Marked as helpful' : '👎 Feedback submitted'}
          </div>
        )}

        <div className={`text-[11px] mt-2 tracking-wide uppercase ${theme === 'dark' ? 'text-gray-500' : 'text-gray-400'}`}>
          {new Date(message.created_at).toLocaleTimeString()}
        </div>
      </div>

      {isUser && (
        <div
          className={`w-10 h-10 rounded-2xl flex items-center justify-center flex-shrink-0 ${
            theme === 'dark' ? 'bg-slate-700 text-white' : 'bg-gray-200'
          }`}
        >
          👤
        </div>
      )}
    </div>
  )
}

'use client'

import { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Message, Theme } from '../types'

interface MessageItemProps {
  message: Message
  onFeedback: (messageId: number, rating: number, note?: string) => void
  theme: Theme
  animationEnabled?: boolean
  animate?: boolean
  isLoading?: boolean
  isRegenerating?: boolean
  isLastUser?: boolean
  onEditQuestion?: (messageId: number, content: string) => void
  onFollowupClick?: (text: string) => void
}

const THINKING_MESSAGES = [
  'Thinking...',
  'Searching knowledge base...',
  'Fetching details...',
  'Reviewing course information...',
  'Almost there...',
]

export default function MessageItem({
  message,
  onFeedback,
  theme,
  animationEnabled = false,
  animate = false,
  isLoading = false,
  isRegenerating = false,
  isLastUser = false,
  onEditQuestion,
  onFollowupClick
}: MessageItemProps) {
  const [displayedCount, setDisplayedCount] = useState(0)
  const [animationComplete, setAnimationComplete] = useState(false)
  const [thinkingIndex, setThinkingIndex] = useState(0)
  const [thinkingVisible, setThinkingVisible] = useState(true)

  const isAssistant = message.role === 'assistant'
  const shouldAnimate = animationEnabled && animate && isAssistant

  const citationRegex = /\[[^\]]+?,\s*p\.\s*\d+\]/gi
  const rawContent = message.content || ''
  const cleanedContent = rawContent
    .replace(citationRegex, '')
    .replace(/\s+([,.;:!?])/g, '$1')
    .replace(/(?<=\S) {2,}/g, ' ')

  const totalChars = cleanedContent.length
  const displayedContent = shouldAnimate ? cleanedContent.slice(0, displayedCount) : cleanedContent

  // Run the character-by-character reveal
  useEffect(() => {
    if (!shouldAnimate) {
      setDisplayedCount(totalChars)
      setAnimationComplete(true)
      return
    }

    setDisplayedCount(0)
    setAnimationComplete(false)
    let i = 0
    let intervalId: number | null = null
    const startDelay = 120 // allow full message render before playback
    const delayPerUnit = 5 // ms per character

    const startTimer = window.setTimeout(() => {
      intervalId = window.setInterval(() => {
        i += 1
        setDisplayedCount(i)
        if (i >= totalChars) {
          if (intervalId !== null) clearInterval(intervalId)
          setAnimationComplete(true)
        }
      }, delayPerUnit)
    }, startDelay)

    return () => {
      clearTimeout(startTimer)
      if (intervalId !== null) clearInterval(intervalId)
    }
  }, [message.id, animationEnabled, animate, totalChars, shouldAnimate])

  const isThinking = isAssistant && !message.content?.trim()

  // Cycle through thinking messages while waiting for first token
  useEffect(() => {
    if (!isThinking) return
    setThinkingIndex(0)
    setThinkingVisible(true)

    const cycle = setInterval(() => {
      // Fade out, then swap text, then fade in
      setThinkingVisible(false)
      setTimeout(() => {
        setThinkingIndex(prev => (prev + 1) % THINKING_MESSAGES.length)
        setThinkingVisible(true)
      }, 300)
    }, 2200)

    return () => clearInterval(cycle)
  }, [isThinking])

  const [showFeedbackNote, setShowFeedbackNote] = useState(false)
  const [feedbackNote, setFeedbackNote] = useState('')
  const [pendingRating, setPendingRating] = useState<number | null>(null)
  const [isCopied, setIsCopied] = useState(false)
  const [showFlagFeedback, setShowFlagFeedback] = useState(false)
  const [flagReason, setFlagReason] = useState('')
  const [flagComment, setFlagComment] = useState('')
  const [citationsOpen, setCitationsOpen] = useState(false)
  const markdownContentRef = useRef<HTMLDivElement>(null)
  const [isEditing, setIsEditing] = useState(false)
  const [draft, setDraft] = useState(message.content || '')

  const isUser = message.role === 'user'
  const isBusy = isLoading || isRegenerating

  useEffect(() => {
    setDraft(message.content || '')
    setIsEditing(false)
  }, [message.id, message.content])

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

  const stripMarkdown = (markdown: string): string => {
    return markdown
      // Remove bold (**text** -> text)
      .replace(/\*\*(.+?)\*\*/g, '$1')
      // Remove italic (*text* -> text)
      .replace(/\*(.+?)\*/g, '$1')
      // Remove headers (# Header -> Header)
      .replace(/^#+\s+/gm, '')
      // Remove links ([text](url) -> text)
      .replace(/\[(.+?)\]\(.+?\)/g, '$1')
      // Remove code blocks (```code``` -> code)
      .replace(/```[\s\S]*?```/g, (match) => {
        return match.replace(/```/g, '').trim()
      })
      // Remove inline code (`code` -> code)
      .replace(/`(.+?)`/g, '$1')
      // Remove horizontal rules (---, ***, ___)
      .replace(/^\s*([-*_])\s*\1\s*\1+\s*$/gm, '')
      // Remove blockquotes (> text -> text)
      .replace(/^\s*>\s+/gm, '')
      // Remove list markers (-, *, +, digits.)
      .replace(/^\s*[-*+]\s+/gm, '')
      .replace(/^\s*\d+\.\s+/gm, '')
      // Clean up extra whitespace
      .replace(/\n\n+/g, '\n\n')
      .trim()
  }

  const copyToClipboard = async () => {
    try {
      if (markdownContentRef.current) {
        const htmlContent = markdownContentRef.current.innerHTML
        const plainText = stripMarkdown(message.content)
        
        const blob = new Blob([htmlContent], { type: 'text/html' })
        const data = [
          new ClipboardItem({
            'text/html': blob,
            'text/plain': new Blob([plainText], { type: 'text/plain' })
          })
        ]
        
        await navigator.clipboard.write(data)
      } else {
        // Fallback to plain text if ref is not available
        const plainText = stripMarkdown(message.content)
        await navigator.clipboard.writeText(plainText)
      }
      
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

  useEffect(() => {
    setCitationsOpen(false)
  }, [message.id])

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
          <span className="material-symbols-outlined text-[22px]">smart_toy</span>
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
          {/* Show cycling status text while waiting for first streaming token */}
          {isThinking ? (
            <span
              className={`text-sm italic transition-opacity duration-300 ${
                thinkingVisible ? 'opacity-100' : 'opacity-0'
              } ${theme === 'dark' ? 'text-gray-400' : 'text-gray-500'}`}
            >
              {THINKING_MESSAGES[thinkingIndex]}
            </span>
          ) : (
            /* Renders the list syntax (sections, bullets, numbered lists) to become HTML with nested hierarchy. */
            <div ref={markdownContentRef} className={`markdown-content relative ${isUser ? 'text-white' : theme === 'dark' ? 'text-gray-100' : 'text-gray-900'}`}>
              {isUser && isEditing ? (
                <div>
                  <textarea
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    className={`w-full text-sm rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary ${
                      theme === 'dark'
                        ? 'bg-slate-900 text-gray-100 placeholder:text-gray-500 border border-slate-700'
                        : 'bg-white text-gray-900 placeholder:text-gray-500 border border-gray-300'
                    }`}
                    rows={3}
                  />
                  <div className="mt-2 flex gap-2">
                    <button
                      onClick={() => {
                        if (!onEditQuestion || !draft.trim()) return
                        setIsEditing(false)
                        onEditQuestion(message.id, draft.trim())
                      }}
                      disabled={isBusy || !draft.trim()}
                      className={`text-xs px-3 py-1 rounded ${
                        isBusy || !draft.trim()
                          ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                          : 'bg-secondary text-white hover:bg-opacity-90'
                      }`}
                    >
                      Save & Regenerate
                    </button>
                    <button
                      onClick={() => {
                        setDraft(message.content || '')
                        setIsEditing(false)
                      }}
                      className={`text-xs px-3 py-1 rounded ${
                        theme === 'dark' ? 'text-gray-300 hover:bg-slate-800' : 'text-gray-600 hover:bg-gray-100'
                      }`}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <div className="leading-normal">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {displayedContent}
                    </ReactMarkdown>
                  </div>
                  {shouldAnimate && !animationComplete && (
                    <span className="inline-block animate-pulse ml-1">▌</span>
                  )}
                </>
              )}
            </div>
          )}
          
          {message.citations && message.citations.length > 0 && (animationComplete || !shouldAnimate) && (
            <div
              className={`mt-4 pt-3 border-t ${
                theme === 'dark' ? 'border-slate-700/80' : 'border-gray-200/80'
              }`}
            >
              <button
                type="button"
                onClick={() => setCitationsOpen(prev => !prev)}
                className={`w-full flex items-center justify-between gap-2 text-xs font-semibold ${
                  theme === 'dark'
                    ? 'text-gray-300 hover:text-white'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
                aria-expanded={citationsOpen}
              >
                <div className="flex items-center gap-2">
                  <span
                    className={`material-symbols-outlined text-[18px] transform transition-transform ${citationsOpen ? 'rotate-90' : ''}`}
                  >
                    chevron_right
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="material-symbols-outlined text-[16px]">menu_book</span>
                    References ({message.citations.length})
                  </span>
                </div>
                <span className="text-[11px] uppercase tracking-wide">
                  {citationsOpen ? 'Hide' : 'Show'}
                </span>
              </button>

              {citationsOpen && (
                <div className="space-y-2 mt-2">
                  {message.citations.map((citation, idx) => (
                    <div
                      key={idx}
                      className={`text-xs rounded-2xl p-3 border ${
                        theme === 'dark'
                          ? 'bg-slate-900/60 text-gray-200 border-slate-800'
                          : 'bg-white text-gray-600 border-gray-200'
                      }`}
                    >
                      {/* 🔗 Link to source document (PDF or Google Doc) */}
                      <div className="font-medium">
                        {citation.doc_type === 'policy' ? (
                          citation.url ? (
                            <a
                              href={citation.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="underline text-blue-500 hover:text-blue-600"
                            >
                              [{citation.source}, p. {citation.page}]
                            </a>
                          ) : (
                            <span>[{citation.source}, p. {citation.page}]</span>
                          )
                        ) : (
                          <a
                            href={
                              citation.url
                                ? citation.url
                                : `${typeof window !== 'undefined' ? window.location.origin : ''}/${encodeURIComponent(
                                    // Use filename when available; fall back to friendly source label
                                    (citation.filename || citation.source)
                                  )}#page=${citation.page}`
                            }
                            target="_blank"
                            rel="noopener noreferrer"
                            className="underline text-blue-500 hover:text-blue-600"
                          >
                            [{citation.source}, p. {citation.page}]
                          </a>
                        )}
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
              )}
            </div>
          )}

            {message.follow_ups && message.follow_ups.length > 0 && (animationComplete || !shouldAnimate) && (
              <div className="mt-4 pt-3 border-t">
                <div className="text-sm font-semibold mb-2">Suggested follow-up questions</div>
                <div className="flex flex-wrap gap-2">
                  {message.follow_ups.map((s, idx) => (
                    <button
                      key={idx}
                      onClick={() => onFollowupClick && onFollowupClick(s)}
                      className={`px-3 py-1 rounded-full text-sm border transition-colors ${
                        theme === 'dark' ? 'border-slate-700 text-gray-200 hover:bg-slate-800' : 'border-gray-200 text-gray-700 hover:bg-gray-100'
                      }`}
                    >
                      {s}
                    </button>
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
                <span className="material-symbols-outlined text-[18px]">flag</span>
              </button>

              <div className={`w-px h-4 ${theme === 'dark' ? 'bg-slate-700' : 'bg-gray-300'} opacity-60`}></div>

              <button
                onClick={() => handleFeedback(1)}
                className="text-gray-400 hover:text-green-500 transition-colors p-1"
              >
                <span className="material-symbols-outlined text-[18px]">thumb_up</span>
              </button>
              <button
                onClick={() => handleFeedback(-1)}
                className="text-gray-400 hover:text-red-500 transition-colors p-1"
              >
                <span className="material-symbols-outlined text-[18px]">thumb_down</span>
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
            {message.feedback === 1
            ? <span className="flex items-center gap-1"><span className="material-symbols-outlined text-[14px]">thumb_up</span> Marked as helpful</span>
            : <span className="flex items-center gap-1"><span className="material-symbols-outlined text-[14px]">thumb_down</span> Feedback submitted</span>
          }
          </div>
        )}

        {isUser && isLastUser && !isEditing && onEditQuestion && (
          <div className="mt-2 flex items-center gap-2 text-xs">
            <button
              onClick={() => setIsEditing(true)}
              disabled={isBusy}
              className={`px-2 py-1 rounded-full border transition-colors ${
                isBusy
                  ? 'border-gray-300 text-gray-400 cursor-not-allowed'
                  : theme === 'dark'
                    ? 'border-slate-700 text-gray-200 hover:bg-slate-800'
                    : 'border-gray-200 text-gray-600 hover:bg-gray-100'
              }`}
            >
              Edit
            </button>
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
          <span className="material-symbols-outlined text-[22px]">person</span>
        </div>
      )}
    </div>
  )
}

'use client'

import { useState, KeyboardEvent, useEffect, useRef } from 'react'
import { Theme } from '../types'

interface MessageInputProps {
  onSend: (message: string) => void
  onUploadSchedule?: () => void
  onOpenImportantLinks?: () => void
  isUploadingSchedule?: boolean
  disabled?: boolean
  theme?: Theme
}

export default function MessageInput({
  onSend,
  onUploadSchedule,
  onOpenImportantLinks,
  isUploadingSchedule = false,
  disabled,
  theme = 'light',
}: MessageInputProps) {
  const [input, setInput] = useState('')
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!isMenuOpen) return

    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node
      if (menuRef.current && !menuRef.current.contains(target)) {
        setIsMenuOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isMenuOpen])

  const handleSend = () => {
    if (input.trim() && !disabled) {
      onSend(input.trim())
      setInput('')
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div
      className={`flex items-end gap-3 rounded-3xl border px-4 py-3 ${
        theme === 'dark'
          ? 'bg-slate-900/70 border-slate-800 text-gray-100'
          : 'bg-white/90 border-white/80 shadow-inner shadow-white/40'
      }`}
    >
      <div ref={menuRef} className="relative flex-shrink-0">
        <button
          type="button"
          onClick={() => setIsMenuOpen(prev => !prev)}
          className={`flex h-11 w-11 items-center justify-center rounded-2xl border transition-colors ${
            theme === 'dark'
              ? 'border-slate-700 bg-slate-950/50 text-gray-100 hover:border-slate-500'
              : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300 hover:bg-slate-50'
          }`}
          title="More actions"
          aria-label="More actions"
        >
          <span className="material-symbols-outlined text-[20px]">add</span>
        </button>
        {isMenuOpen && (
          <div
            className={`absolute bottom-14 left-0 z-20 w-56 rounded-2xl border p-2 shadow-xl ${
              theme === 'dark'
                ? 'border-slate-700 bg-slate-900 text-gray-100'
                : 'border-gray-200 bg-white text-gray-800'
            }`}
          >
            <button
              type="button"
              onClick={() => {
                setIsMenuOpen(false)
                onUploadSchedule?.()
              }}
              disabled={isUploadingSchedule}
              className={`flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left text-sm transition-colors ${
                isUploadingSchedule
                  ? 'cursor-not-allowed opacity-60'
                  : theme === 'dark'
                    ? 'hover:bg-slate-800'
                    : 'hover:bg-slate-50'
              }`}
            >
              <span className="material-symbols-outlined text-[18px]">upload_file</span>
              <span>{isUploadingSchedule ? 'Uploading…' : 'Upload Schedule'}</span>
            </button>
            <button
              type="button"
              onClick={() => {
                setIsMenuOpen(false)
                onOpenImportantLinks?.()
              }}
              className={`flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left text-sm transition-colors ${
                theme === 'dark' ? 'hover:bg-slate-800' : 'hover:bg-slate-50'
              }`}
            >
              <span className="material-symbols-outlined text-[18px]">link</span>
              <span>Important Links</span>
            </button>
          </div>
        )}
      </div>
      <textarea
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask about courses, majors, prerequisites..."
        disabled={disabled}
        className={`flex-1 resize-none bg-transparent border-none px-1 py-1 text-base placeholder:text-gray-500 focus:outline-none disabled:cursor-not-allowed ${
          theme === 'dark' ? 'text-gray-100' : 'text-gray-900'
        }`}
        rows={1}
        style={{ minHeight: '48px', maxHeight: '150px' }}
        onInput={(e) => {
          const target = e.target as HTMLTextAreaElement
          target.style.height = 'auto'
          target.style.height = target.scrollHeight + 'px'
        }}
      />
      <button
        onClick={handleSend}
        disabled={disabled || !input.trim()}
        className={`px-6 py-3 rounded-2xl font-semibold transition-all disabled:opacity-60 disabled:cursor-not-allowed ${
          theme === 'dark'
            ? 'bg-gradient-to-r from-orange-400 to-pink-500 text-white hover:shadow-[0_10px_25px_rgba(236,72,153,0.35)]'
            : 'bg-gradient-to-r from-primary to-secondary text-white shadow-[0_10px_30px_rgba(3,56,101,0.25)] hover:translate-y-[-1px]'
        }`}
      >
        Send
      </button>
    </div>
  )
}

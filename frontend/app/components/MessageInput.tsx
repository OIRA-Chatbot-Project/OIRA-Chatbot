'use client'

import { useState, KeyboardEvent } from 'react'
import { Theme } from '../types'

interface MessageInputProps {
  onSend: (message: string) => void
  disabled?: boolean
  theme?: Theme
}

export default function MessageInput({ onSend, disabled, theme = 'light' }: MessageInputProps) {
  const [input, setInput] = useState('')

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

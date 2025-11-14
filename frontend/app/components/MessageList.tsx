'use client'

import { Message, Theme } from '../types'
import MessageItem from './MessageItem'

interface MessageListProps {
  messages: Message[]
  onFeedback: (messageId: number, rating: number, note?: string) => void
  theme: Theme
}

export default function MessageList({ messages, onFeedback, theme }: MessageListProps) {
  return (
    <div className="space-y-6">
      {messages.map((message) => (
        <MessageItem
          key={message.id}
          message={message}
          onFeedback={onFeedback}
          theme={theme}
        />
      ))}
    </div>
  )
}

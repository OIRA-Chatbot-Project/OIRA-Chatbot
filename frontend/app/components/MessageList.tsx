'use client'

import { Message } from '../types'
import MessageItem from './MessageItem'

interface MessageListProps {
  messages: Message[]
  onFeedback: (messageId: number, rating: number, note?: string) => void
}

export default function MessageList({ messages, onFeedback }: MessageListProps) {
  return (
    <div className="space-y-4">
      {messages.map((message) => (
        <MessageItem
          key={message.id}
          message={message}
          onFeedback={onFeedback}
        />
      ))}
    </div>
  )
}

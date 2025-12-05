'use client'

import { Message, Theme } from '../types'
import MessageItem from './MessageItem'

interface MessageListProps {
  messages: Message[]
  onFeedback: (messageId: number, rating: number, note?: string) => void
  theme: Theme
  animationEnabled?: boolean
  animateMessageId?: number
}

export default function MessageList({ messages, onFeedback, theme, animationEnabled, animateMessageId }: MessageListProps) {
  return (
    <div className="space-y-3">
      {messages.map((message) => (
        <MessageItem
          key={message.id}
          message={message}
          onFeedback={onFeedback}
          theme={theme}
          animationEnabled={!!animationEnabled}
          animate={animateMessageId === message.id}
        />
      ))}
    </div>
  )
}

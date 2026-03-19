'use client'

import { Message, Theme } from '../types'
import MessageItem from './MessageItem'

interface MessageListProps {
  messages: Message[]
  onFeedback: (messageId: number, rating: number, note?: string) => void
  theme: Theme
  animationEnabled?: boolean
  animateMessageId?: number
  isLoading?: boolean
  isRegenerating?: boolean
  onEditQuestion?: (messageId: number, content: string) => void
  onFollowupClick?: (text: string) => void
}

/**
 * Renders the full list of chat messages in the current session.
 *
 * Identifies the last user message so that `MessageItem` can show the edit control
 * only on that message. All other interaction callbacks are forwarded to each item.
 */
export default function MessageList({ messages, onFeedback, theme, animationEnabled, animateMessageId, isLoading, isRegenerating, onEditQuestion, onFollowupClick }: MessageListProps) {
  const lastUserIndex = [...messages].reverse().findIndex(msg => msg.role === 'user')
  const resolvedLastUserIndex = lastUserIndex === -1 ? -1 : messages.length - 1 - lastUserIndex
  return (
    <div className="space-y-3">
      {messages.map((message, index) => {
        const isLastUser = index === resolvedLastUserIndex

        return (
          <MessageItem
            key={message.id}
            message={message}
            onFeedback={onFeedback}
            theme={theme}
            animationEnabled={!!animationEnabled}
            animate={animateMessageId === message.id}
            isLoading={!!isLoading}
            isRegenerating={!!isRegenerating}
            isLastUser={isLastUser}
            onEditQuestion={onEditQuestion}
            onFollowupClick={onFollowupClick}
          />
        )
      })}
    </div>
  )
}

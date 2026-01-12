import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import MessageItem from '../app/components/MessageItem'
import { Message } from '../app/types'

describe('MessageItem follow-up suggestions', () => {
  const baseMessage: Message = {
    id: 1,
    role: 'assistant',
    content: 'This is an answer.',
    citations: [],
    follow_ups: ['What are the prerequisites?', 'Can you recommend courses?'] ,
    created_at: new Date().toISOString(),
  }

  it('renders follow-up suggestion buttons and calls handler when clicked', () => {
    const onFeedback = jest.fn()
    const onFollowup = jest.fn()

    render(
      <MessageItem
        message={baseMessage}
        onFeedback={onFeedback}
        theme={'light'}
        animationEnabled={false}
        animate={false}
        onFollowupClick={onFollowup}
      />
    )

    // Expect suggestion headings and buttons
    expect(screen.getByText('Suggested follow-up questions')).toBeInTheDocument()
    const btn = screen.getByText('What are the prerequisites?')
    expect(btn).toBeInTheDocument()

    fireEvent.click(btn)
    expect(onFollowup).toHaveBeenCalledWith('What are the prerequisites?')
  })
})

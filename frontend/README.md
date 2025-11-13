# OIRA Chatbot Frontend

Next.js frontend for the Bucknell University course catalog chatbot.

## Features

- 💬 Real-time chat interface with the course catalog AI
- 📚 Citation display for all answers
- 👍👎 Feedback system for rating responses
- 💾 Session management with localStorage
- 📱 Responsive design with Tailwind CSS
- 🎨 Bucknell branding (orange and blue)

## Getting Started

### Prerequisites

- Node.js 18+ installed
- Backend API running on `http://localhost:8000`

### Installation

```bash
npm install
```

### Configuration

The frontend is configured via `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Development

Run the development server:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Production Build

```bash
npm run build
npm start
```

## Project Structure

```
frontend/
├── app/
│   ├── components/
│   │   ├── ChatInterface.tsx    # Main chat container
│   │   ├── MessageList.tsx      # Message list wrapper
│   │   ├── MessageItem.tsx      # Individual message display
│   │   ├── MessageInput.tsx     # Message input field
│   │   └── Sidebar.tsx          # Session history sidebar
│   ├── types.ts                 # TypeScript interfaces
│   ├── layout.tsx               # Root layout
│   ├── page.tsx                 # Main page
│   └── globals.css              # Global styles
├── public/                      # Static assets
├── .env.local                   # Environment variables
├── package.json                 # Dependencies
├── tsconfig.json                # TypeScript config
├── tailwind.config.ts           # Tailwind CSS config
└── next.config.js               # Next.js config
```

## Features Explained

### Session Management

- Each chat session has a unique UUID
- Sessions are stored in `localStorage`
- Click "New Chat" to start a fresh conversation
- Previous sessions can be accessed from the sidebar

### Message Flow

1. User types a question and clicks "Send"
2. Message is sent to `POST /chat` endpoint
3. Backend retrieves relevant course info from ChromaDB
4. OpenAI generates an answer with citations
5. Answer is displayed with expandable references

### Feedback System

- Click 👍 for helpful answers (submits immediately)
- Click 👎 for unhelpful answers (prompts for optional note)
- Feedback is sent to `POST /feedback` endpoint
- Stored in SQLite for analytics

### Citations

- Each assistant message includes source citations
- Citations show: filename, page number, and text excerpt
- Helps users verify information and find more details

## Customization

### Colors

Bucknell branding colors are defined in `tailwind.config.ts`:

```typescript
colors: {
  primary: '#E87722',   // Bucknell Orange
  secondary: '#003865', // Bucknell Blue
}
```

### API Endpoint

Change the backend URL in `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://your-backend-url:8000
```

## Troubleshooting

**"Failed to fetch" errors**
- Ensure backend is running on `http://localhost:8000`
- Check CORS settings in backend allow `http://localhost:3000`

**Empty chat history**
- Check browser console for API errors
- Verify session_id is being generated and stored

**Citations not displaying**
- Backend should return citations in the response
- Check network tab in browser DevTools

## Development Notes

- Built with Next.js 14 (App Router)
- Uses TypeScript for type safety
- Styled with Tailwind CSS
- State management with React hooks
- No external state library needed (uses localStorage + React state)

## Next Steps

- Add user authentication
- Implement chat export functionality
- Add dark mode support
- Mobile app version
- Advanced search filters
- Multi-language support

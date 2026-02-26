# OIRA Chatbot Frontend

Next.js frontend for the Bucknell University course catalog chatbot.

## Tech stack
- Next.js (App Router)
- React
- Tailwind CSS
- Clerk authentication (`@clerk/nextjs`)
- Jest for tests

## Prerequisites
- Node.js 18+
- Backend running (default: `http://localhost:8000`)

## Setup

### 1) Install dependencies
```bash
npm install
```

### 2) Configure environment
Copy the example file:
```bash
cp .env.example .env.local
```

Edit `.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000

# Clerk Authentication (required if auth is enabled)
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=...
CLERK_SECRET_KEY=...

NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/
```

### 3) Run in development
```bash
npm run dev
```

Open http://localhost:3000

## Scripts
- `npm run dev` - local dev server
- `npm run build` - production build
- `npm start` - run production build
- `npm run test` - run Jest tests

## Project structure (high level)
```
frontend/
  app/                # routes + UI
  public/             # static assets
  middleware.ts       # Next.js middleware (often used with Clerk)
  tailwind.config.ts  # theme/styling config
```

## How it talks to the backend
The frontend calls the backend API configured by `NEXT_PUBLIC_API_URL`.
If you see `Failed to fetch`:
- verify backend is running
- verify CORS in backend `.env` allows `http://localhost:3000`
- verify `NEXT_PUBLIC_API_URL` is correct
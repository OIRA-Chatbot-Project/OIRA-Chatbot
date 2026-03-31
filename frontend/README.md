# OIRA Chatbot Frontend

Next.js frontend for the Bucknell University course catalog chatbot.

## Tech stack

- Next.js App Router
- React
- Tailwind CSS
- Clerk authentication
- Jest for component tests

## Prerequisites

- Node.js 18+
- Backend API running at `http://localhost:8000` or another configured URL

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

Then update `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000

# Clerk
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

Open `http://localhost:3000`.

## Scripts

- `npm run dev` starts the local dev server
- `npm run build` creates a production build
- `npm run start` serves the production build
- `npm run lint` runs Next.js linting
- `npm run test` runs Jest tests

## Current structure

```text
frontend/
  app/           # routes, page layout, UI components, utilities
  __tests__/     # frontend tests
  public/        # static assets
  proxy.ts       # route protection / auth matcher
  tailwind.config.ts
  jest.config.cjs
```

## How it talks to the backend

- Backend requests use `NEXT_PUBLIC_API_URL`
- Default local backend URL is `http://localhost:8000`
- The frontend expects backend CORS to allow `http://localhost:3000`

## Auth routes

- Sign-in page: `/sign-in`
- Sign-up page: `/sign-up`
- Protected route matching is configured in `proxy.ts`

## Troubleshooting

- `Failed to fetch` errors:
  Check that the backend is running and `NEXT_PUBLIC_API_URL` is correct.
- CORS errors:
  Ensure backend `ALLOWED_ORIGINS` includes `http://localhost:3000`.
- Clerk errors:
  Confirm the Clerk keys in `.env.local` are set correctly.

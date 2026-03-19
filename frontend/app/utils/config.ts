/** Base URL for all backend API requests. Reads from `NEXT_PUBLIC_API_URL` or falls back to `http://localhost:8000`. */
export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

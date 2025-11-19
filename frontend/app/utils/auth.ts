/**
 * Utility functions for making authenticated API calls
 */

export async function authenticatedFetch(
  url: string,
  getToken: () => Promise<string | null>,
  options: RequestInit = {}
): Promise<Response> {
  const token = await getToken()
  
  if (!token) {
    throw new Error('No authentication token available')
  }

  const headers = new Headers(options.headers || {})
  headers.set('Authorization', `Bearer ${token}`)

  return fetch(url, {
    ...options,
    headers,
  })
}

export async function createOrGetUser(
  getToken: () => Promise<string | null>,
  clerkUserId: string,
  email: string,
  name?: string
): Promise<any> {
  const response = await authenticatedFetch(
    `${process.env.NEXT_PUBLIC_API_URL}/users`,
    getToken,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        clerk_user_id: clerkUserId,
        email,
        name,
      }),
    }
  )

  if (!response.ok) {
    throw new Error(`Failed to create/get user: ${response.statusText}`)
  }

  return response.json()
}

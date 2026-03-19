/** Default title assigned to a session before the user sends their first message. */
export const DEFAULT_SESSION_TITLE = 'New Chat'

const PLACEHOLDER_TITLES = new Set(['New Chat', 'Chat Session'])

/**
 * Returns true if the given title is a generic placeholder that has not been customized yet.
 *
 * @param title - The session title to check.
 * @returns Whether the title is a placeholder or absent.
 */
export const isPlaceholderTitle = (title?: string | null) => {
  if (!title) return true
  return PLACEHOLDER_TITLES.has(title.trim())
}

/**
 * Generates a concise, human-readable session title from the user's first message.
 *
 * Strips markdown syntax and truncates to 60 characters with an ellipsis if needed.
 * Falls back to `DEFAULT_SESSION_TITLE` if the content is empty or results in blank text.
 *
 * @param content - Raw message content, potentially containing markdown.
 * @returns A trimmed title string no longer than 60 characters.
 */
export const generateSessionTitle = (content: string) => {
  if (!content) {
    return DEFAULT_SESSION_TITLE
  }

  const cleaned = content
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1') // strip markdown links
    .replace(/[#>*_`]/g, '')
    .replace(/\s+/g, ' ')
    .trim()

  if (!cleaned) {
    return DEFAULT_SESSION_TITLE
  }

  return cleaned.length > 60 ? `${cleaned.slice(0, 57).trim()}...` : cleaned
}

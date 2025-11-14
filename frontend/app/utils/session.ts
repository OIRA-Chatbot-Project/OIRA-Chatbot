export const DEFAULT_SESSION_TITLE = 'New Chat'

const PLACEHOLDER_TITLES = new Set(['New Chat', 'Chat Session'])

export const isPlaceholderTitle = (title?: string | null) => {
  if (!title) return true
  return PLACEHOLDER_TITLES.has(title.trim())
}

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

import { useEffect } from 'react'

/**
 * Sets document.title to `title — Forest IDS` while the component is mounted.
 */
export function useDocumentTitle(title) {
  useEffect(() => {
    const prev = document.title
    document.title = title ? `${title} — Forest IDS` : 'Forest IDS'
    return () => { document.title = prev }
  }, [title])
}

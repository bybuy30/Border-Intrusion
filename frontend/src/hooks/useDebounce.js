import { useState, useEffect } from 'react'

/**
 * Returns a debounced copy of `value` that only updates after `delay` ms
 * of inactivity. Useful for search inputs that drive API calls.
 */
export function useDebounce(value, delay = 300) {
  const [debounced, setDebounced] = useState(value)

  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(id)
  }, [value, delay])

  return debounced
}

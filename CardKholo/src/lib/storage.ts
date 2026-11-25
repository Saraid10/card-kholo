// localStorage can throw (Safari private mode, blocked storage, quota). Fall back to memory.
const memory = new Map<string, string>()

export function readJSON<T>(key: string): T | null {
  let raw: string | null = null
  try {
    raw = window.localStorage.getItem(key)
  } catch {
    raw = memory.get(key) ?? null
  }
  if (raw == null) raw = memory.get(key) ?? null
  if (raw == null) return null
  try {
    return JSON.parse(raw) as T
  } catch {
    return null
  }
}

export function writeJSON(key: string, value: unknown): void {
  const raw = JSON.stringify(value)
  memory.set(key, raw)
  try {
    window.localStorage.setItem(key, raw)
  } catch {
    /* memory copy is enough */
  }
}

export function remove(key: string): void {
  memory.delete(key)
  try {
    window.localStorage.removeItem(key)
  } catch {
    /* ignore */
  }
}

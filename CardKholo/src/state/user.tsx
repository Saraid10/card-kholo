import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import type { Lang, Role } from '../api/types'
import { dict, type StringKey } from '../i18n/strings'
import { readJSON, remove, writeJSON } from '../lib/storage'

export interface StoredUser {
  user_id: string
  name: string
  lang: Lang
  role: Role
  beta: boolean
  pair_link: string | null
  /** Display name of the linked child, once known. */
  linked_name?: string | null
}

const USER_KEY = 'cardkholo_user'
const LANG_KEY = 'cardkholo_lang' // language chosen before identify

interface Ctx {
  user: StoredUser | null
  lang: Lang
  setLang: (l: Lang) => void
  saveUser: (u: StoredUser) => void
  patchUser: (p: Partial<StoredUser>) => void
  clearUser: () => void
  t: (k: StringKey) => string
}

const UserCtx = createContext<Ctx | null>(null)
const isLang = (v: unknown): v is Lang => v === 'hi' || v === 'kn' || v === 'en'

export function UserProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<StoredUser | null>(() => {
    const u = readJSON<StoredUser>(USER_KEY)
    return u && typeof u.user_id === 'string' ? u : null
  })
  const [prefLang, setPrefLang] = useState<Lang>(() => {
    const l = readJSON<string>(LANG_KEY)
    return isLang(l) ? l : 'en'
  })
  const lang: Lang = user && isLang(user.lang) ? user.lang : prefLang

  useEffect(() => {
    document.documentElement.lang = lang
  }, [lang])

  const setLang = useCallback((l: Lang) => {
    setPrefLang(l)
    writeJSON(LANG_KEY, l)
    setUser((u) => {
      if (!u) return u
      const next = { ...u, lang: l }
      writeJSON(USER_KEY, next)
      return next
    })
  }, [])

  const saveUser = useCallback((u: StoredUser) => {
    writeJSON(USER_KEY, u)
    writeJSON(LANG_KEY, u.lang)
    setPrefLang(u.lang)
    setUser(u)
  }, [])

  const patchUser = useCallback((p: Partial<StoredUser>) => {
    setUser((u) => {
      if (!u) return u
      const next = { ...u, ...p }
      writeJSON(USER_KEY, next)
      return next
    })
  }, [])

  const clearUser = useCallback(() => {
    remove(USER_KEY)
    setUser(null)
  }, [])

  const t = useCallback((k: StringKey) => dict[lang][k] ?? dict.en[k], [lang])

  const value = useMemo(
    () => ({ user, lang, setLang, saveUser, patchUser, clearUser, t }),
    [user, lang, setLang, saveUser, patchUser, clearUser, t],
  )
  return <UserCtx.Provider value={value}>{children}</UserCtx.Provider>
}

// eslint-disable-next-line react/only-export-components
export function useUser(): Ctx {
  const c = useContext(UserCtx)
  if (!c) throw new Error('useUser must be used inside UserProvider')
  return c
}

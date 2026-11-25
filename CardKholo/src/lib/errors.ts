import { ApiError } from '../api'
import type { StringKey } from '../i18n/strings'

export function errorKey(e: unknown): StringKey {
  if (e instanceof ApiError) {
    if (e.kind === 'timeout') return 'errTimeout'
    if (e.kind === 'network') return 'errNetwork'
  }
  return 'errServer'
}

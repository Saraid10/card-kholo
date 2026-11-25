// Single entry point for every backend call. Mock or real is decided by USE_MOCKS.
import { USE_MOCKS, resolveUrl } from '../lib/env'
import { request, TIMEOUT } from './http'
import * as m from './mocks'
import type {
  ExperimentEvent, FeedbackRes, IdentifyReq, IdentifyRes, OpenedRes,
  InviteRes, PairingRes, ScanRes, StatusRes, VoiceRes, WeddingReq, WeddingRes,
} from './types'

export * from './types'
export { ApiError } from './http'

async function mock<T>(fn: () => T): Promise<T> {
  await m.sleep(m.MOCK_DELAY)
  return fn()
}

export const api = {
  identify(body: IdentifyReq): Promise<IdentifyRes> {
    if (USE_MOCKS) return mock(() => m.mockIdentify(body))
    return request('/api/identify', { method: 'POST', json: body })
  },

  /** Sends the file with its ORIGINAL filename (the backend checks extensions). */
  scanFile(file: File, userId: string): Promise<ScanRes> {
    if (USE_MOCKS) return mock(() => m.mockScan({ filename: file.name }))
    const form = new FormData()
    form.append('file', file, file.name)
    form.append('user_id', userId)
    return request('/api/scan', { method: 'POST', form, timeoutMs: TIMEOUT.scan })
  },

  scanText(text: string, userId: string): Promise<ScanRes> {
    if (USE_MOCKS) return mock(() => m.mockScan({ text }))
    return request('/api/scan', { method: 'POST', json: { user_id: userId, text }, timeoutMs: TIMEOUT.scan })
  },

  opened(scanId: string): Promise<OpenedRes> {
    if (USE_MOCKS) return mock(() => m.mockOpened())
    return request('/api/opened', { method: 'POST', json: { scan_id: scanId } })
  },

  feedback(scanId: string): Promise<FeedbackRes> {
    if (USE_MOCKS) return mock(() => m.mockFeedback(scanId))
    return request('/api/feedback', { method: 'POST', json: { scan_id: scanId, real_invite: true } })
  },

  /** Fire-and-forget. Never throws; the endpoint is optional and may 404. */
  event(scanId: string, event: ExperimentEvent): void {
    if (USE_MOCKS) {
      m.mockEvent(scanId, event)
      return
    }
    request('/api/events', { method: 'POST', json: { scan_id: scanId, event }, timeoutMs: TIMEOUT.events }).catch(() => {})
  },

  status(): Promise<StatusRes> {
    if (USE_MOCKS) return mock(() => m.mockStatus())
    return request('/api/status')
  },

  /** Absolute URL for the .ics download, or null. */
  icsUrl(icsPath: string | null | undefined): string | null {
    return resolveUrl(icsPath)
  },

  createWedding(body: WeddingReq): Promise<WeddingRes> {
    if (USE_MOCKS) return mock(() => m.mockWedding(body))
    return request('/api/invites/wedding', { method: 'POST', json: body })
  },

  voiceInvite(audio: Blob, userId: string): Promise<VoiceRes> {
    if (USE_MOCKS) return mock(() => m.mockVoice())
    const form = new FormData()
    const ext = /webm/.test(audio.type) ? 'webm' : /ogg/.test(audio.type) ? 'ogg' : /mp4|aac/.test(audio.type) ? 'm4a' : 'wav'
    form.append('audio', audio, `invite.${ext}`)
    form.append('user_id', userId)
    return request('/api/invites/voice', { method: 'POST', form, timeoutMs: TIMEOUT.scan })
  },

  /** Verified invite for /i/:id. Falls back to the demo invite if the backend lacks this endpoint. */
  async invite(inviteId: string): Promise<InviteRes> {
    if (USE_MOCKS) return mock(() => m.mockInvite(inviteId))
    try {
      return await request<InviteRes>(`/api/invites/${encodeURIComponent(inviteId)}`)
    } catch {
      return m.mockInvite(inviteId)
    }
  },

  /** Optional route. Throws on 404 / network so callers can stop polling quietly. */
  pairing(userId: string): Promise<PairingRes> {
    if (USE_MOCKS) return mock(() => m.mockPairing(userId))
    return request(`/api/pairing/${encodeURIComponent(userId)}`, { timeoutMs: TIMEOUT.events })
  },

  health(): Promise<{ ok: boolean }> {
    if (USE_MOCKS) return mock(() => ({ ok: true }))
    return request('/health', { timeoutMs: TIMEOUT.wake })
  },
}

import type { SVGProps } from 'react'

type P = SVGProps<SVGSVGElement> & { size?: number }

function Base({ size = 22, children, ...rest }: P & { children: React.ReactNode }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...rest}>
      {children}
    </svg>
  )
}

export const IArrowLeft = (p: P) => <Base {...p}><path d="M19 12H5" /><path d="m12 19-7-7 7-7" /></Base>
export const IArrowRight = (p: P) => <Base {...p}><path d="M5 12h14" /><path d="m12 5 7 7-7 7" /></Base>
export const IClose = (p: P) => <Base {...p}><path d="M18 6 6 18" /><path d="m6 6 12 12" /></Base>
export const IUpload = (p: P) => <Base {...p}><path d="M12 16V4" /><path d="m6 10 6-6 6 6" /><path d="M4 20h16" /></Base>
export const ICalPlus = (p: P) => <Base {...p}><rect x="3" y="4.5" width="18" height="16" rx="3" /><path d="M3 9.5h18M8 2.5v4M16 2.5v4M12 12.5v5M9.5 15h5" /></Base>
export const IPin = (p: P) => <Base {...p}><path d="M12 21s-7-6.2-7-11.5a7 7 0 0 1 14 0C19 14.8 12 21 12 21Z" /><circle cx="12" cy="9.5" r="2.5" /></Base>
export const IPhone = (p: P) => <Base {...p}><path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2" /></Base>
export const IPlay = (p: P) => <Base {...p}><path d="M7 4.5v15l12.5-7.5Z" fill="currentColor" stroke="none" /></Base>
export const IPause = (p: P) => <Base {...p}><rect x="6" y="4.5" width="4" height="15" rx="1" fill="currentColor" stroke="none" /><rect x="14" y="4.5" width="4" height="15" rx="1" fill="currentColor" stroke="none" /></Base>
export const IVolume = (p: P) => <Base {...p}><path d="M11 5 6 9H3v6h3l5 4z" /><path d="M15.5 8.5a5 5 0 0 1 0 7M18.5 5.5a9 9 0 0 1 0 13" /></Base>
export const ICheck = (p: P) => <Base {...p}><path d="m5 12.5 4.5 4.5L19 7.5" /></Base>
export const IX = (p: P) => <Base {...p}><path d="M17 7 7 17M7 7l10 10" /></Base>
export const IAlert = (p: P) => <Base {...p}><path d="M12 3 2 20h20Z" /><path d="M12 10v4.5M12 17.5v.01" /></Base>
export const ICopy = (p: P) => <Base {...p}><rect x="8" y="8" width="13" height="13" rx="2.5" /><path d="M16 8V5.5A2.5 2.5 0 0 0 13.5 3h-8A2.5 2.5 0 0 0 3 5.5v8A2.5 2.5 0 0 0 5.5 16H8" /></Base>
export const IMic = (p: P) => <Base {...p}><rect x="9" y="2.5" width="6" height="12" rx="3" /><path d="M5 11a7 7 0 0 0 14 0M12 18v3.5" /></Base>
export const IChevron = (p: P) => <Base {...p}><path d="m9 6 6 6-6 6" /></Base>
export const IDownload = (p: P) => <Base {...p}><path d="M12 4v12" /><path d="m6 10 6 6 6-6" /><path d="M4 20h16" /></Base>
export const IPlane = (p: P) => <Base {...p}><path d="M10.5 21 12 16l-7 1.5L4 16l7-4.5V5a1.5 1.5 0 0 1 3 0v6.5l7 4.5-1 1.5-7-1.5 1.5 5Z" /></Base>
export const IBank = (p: P) => <Base {...p}><path d="M3 10 12 4l9 6M5 10v8M9.5 10v8M14.5 10v8M19 10v8M3 20.5h18" /></Base>
export const IGlobe = (p: P) => <Base {...p}><circle cx="12" cy="12" r="9" /><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18" /></Base>
export const ITrash = (p: P) => <Base {...p}><path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3" /></Base>
export const IEdit = (p: P) => <Base {...p}><path d="M4 20h4L19 9l-4-4L4 16Z" /><path d="m13.5 6.5 4 4" /></Base>
export const IShield = (p: P) => <Base {...p}><path d="M12 3 4.5 6v5.5c0 4.6 3.2 8.4 7.5 9.5 4.3-1.1 7.5-4.9 7.5-9.5V6Z" /><path d="m8.5 12 2.5 2.5 4.5-5" /></Base>
export const IClock = (p: P) => <Base {...p}><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></Base>
export const ICar = (p: P) => <Base {...p}><path d="M4 16v-4l2-5h12l2 5v4M3 16h18v3h-3v-1.5H6V19H3Z" /><circle cx="7.5" cy="13" r=".8" fill="currentColor" /><circle cx="16.5" cy="13" r=".8" fill="currentColor" /></Base>
export const IAuto = (p: P) => <Base {...p}><path d="M3 15V9a4 4 0 0 1 4-4h7l5 5v5H3Z" /><path d="M10 5v10M14 5l1 5h4" /><circle cx="7" cy="17" r="2" /><circle cx="17" cy="17" r="2" /></Base>
export const ITrain = (p: P) => <Base {...p}><rect x="5" y="3" width="14" height="13" rx="3" /><path d="M5 10h14M8 20l2-4M16 20l-2-4" /><circle cx="9" cy="13" r=".8" fill="currentColor" /><circle cx="15" cy="13" r=".8" fill="currentColor" /></Base>
export const IWalk = (p: P) => <Base {...p}><circle cx="13" cy="4" r="1.8" /><path d="m9 21 2.5-7L14 16v5M8 11l3-4 3 1 2 3 2 1M11 7l-1 5" /></Base>
export const ISend = (p: P) => <Base {...p}><path d="M21 3 10 14" /><path d="m21 3-7 18-4-7-7-4Z" /></Base>
export const IFile = (p: P) => <Base {...p}><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8Z" /><path d="M14 3v5h5" /></Base>
export const IQr = (p: P) => <Base {...p}><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><path d="M14 14h3v3M21 14v.01M14 21h7v-4" /></Base>
export const ILink = (p: P) => <Base {...p}><path d="M10 14a4.5 4.5 0 0 0 6.4 0l3-3a4.5 4.5 0 0 0-6.4-6.4l-1 1" /><path d="M14 10a4.5 4.5 0 0 0-6.4 0l-3 3a4.5 4.5 0 0 0 6.4 6.4l1-1" /></Base>

export const IWhatsApp = ({ size = 22, ...p }: P) => (
  <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true" {...p}>
    <path fill="currentColor" d="M12 2.2a9.7 9.7 0 0 0-8.3 14.8L2.4 21.6l4.7-1.2A9.7 9.7 0 1 0 12 2.2Zm0 17.7c-1.5 0-3-.4-4.2-1.1l-.3-.2-2.8.7.8-2.7-.2-.3A8 8 0 1 1 12 19.9Zm4.4-6c-.2-.1-1.4-.7-1.7-.8-.2-.1-.4-.1-.5.1l-.8 1c-.1.2-.3.2-.5.1a6.6 6.6 0 0 1-3.3-2.9c-.2-.4.2-.4.7-1.3.1-.2 0-.3 0-.4l-.8-1.8c-.2-.5-.4-.4-.5-.4h-.5a.9.9 0 0 0-.7.3 2.8 2.8 0 0 0-.9 2.1c0 1.2.9 2.4 1 2.6.1.2 1.8 2.7 4.3 3.8 1.6.7 2.2.7 3 .6.5-.1 1.4-.6 1.6-1.1.2-.6.2-1 .1-1.1l-.5-.3Z" />
  </svg>
)
export const ITelegram = ({ size = 22, ...p }: P) => (
  <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true" {...p}>
    <path fill="currentColor" d="M21.4 4.2 18.3 19c-.2 1-.8 1.3-1.7.8l-4.6-3.4-2.2 2.1c-.2.2-.5.5-1 .5l.3-4.8 8.7-7.9c.4-.3-.1-.5-.6-.2L6.5 12.9 1.9 11.5c-1-.3-1-1 .2-1.5L20.1 3c.8-.3 1.6.2 1.3 1.2Z" />
  </svg>
)

import { Link } from 'react-router-dom'
import AppShell from '../components/AppShell'
import { btnClass, Seal } from '../components/ui'
import { useUser } from '../state/user'

export default function NotFound({ message }: { message?: string }) {
  const { t } = useUser()
  return (
    <AppShell back="/" footer={<Link to="/check" className={btnClass('primary', 'lg', 'w-full')}>{t('checkCard')}</Link>}>
      <div className="flex flex-1 flex-col items-center justify-center gap-4 text-center animate-rise">
        <Seal size={64} />
        <h1 className="display-md">{message ?? t('notFoundTitle')}</h1>
        <Link to="/" className="font-medium text-wine underline underline-offset-4">{t('goHome')}</Link>
      </div>
    </AppShell>
  )
}

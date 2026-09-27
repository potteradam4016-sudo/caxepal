import type { ReactNode } from 'react'
import { AppProvider } from './AppContext'
import { AuthProvider, useAuth } from './AuthContext'

function UserBoundAppProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const stateKey = user?.id ?? 'guest'
  return <AppProvider key={stateKey}>{children}</AppProvider>
}

export function AppProviders({ children }: { children: ReactNode }) {
  return <AuthProvider><UserBoundAppProvider>{children}</UserBoundAppProvider></AuthProvider>
}

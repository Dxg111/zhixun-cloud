import { Navigate, useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'
import { getToken } from '../services/api'

interface RequireAuthProps {
  children: ReactNode
}

export default function RequireAuth({ children }: RequireAuthProps) {
  const token = getToken()
  const location = useLocation()

  if (!token) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  return <>{children}</>
}

import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { authApi, getErrorMessage } from '@/api'
import { STORAGE_KEYS } from '@/lib/constants'
import type { User, LoginCredentials, RegisterCredentials, AuthState } from '@/types'
import { toast } from 'sonner'

interface AuthContextType extends AuthState {
  login: (credentials: LoginCredentials) => Promise<void>
  register: (credentials: RegisterCredentials) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    token: localStorage.getItem(STORAGE_KEYS.TOKEN),
    isAuthenticated: false,
    isLoading: true,
  })

  const navigate = useNavigate()
  const location = useLocation()

  // Check if token exists and fetch user data
  const refreshUser = useCallback(async () => {
    const token = localStorage.getItem(STORAGE_KEYS.TOKEN)
    
    if (!token) {
      setState({
        user: null,
        token: null,
        isAuthenticated: false,
        isLoading: false,
      })
      return
    }

    try {
      const user = await authApi.getMe()
      localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(user))
      setState({
        user,
        token,
        isAuthenticated: true,
        isLoading: false,
      })
    } catch {
      // Token is invalid, clear it
      localStorage.removeItem(STORAGE_KEYS.TOKEN)
      localStorage.removeItem(STORAGE_KEYS.USER)
      setState({
        user: null,
        token: null,
        isAuthenticated: false,
        isLoading: false,
      })
    }
  }, [])

  useEffect(() => {
    refreshUser()
  }, [refreshUser])

  const login = async (credentials: LoginCredentials) => {
    setState(prev => ({ ...prev, isLoading: true }))
    
    try {
      const { access_token } = await authApi.login(credentials)
      localStorage.setItem(STORAGE_KEYS.TOKEN, access_token)
      
      const user = await authApi.getMe()
      localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(user))
      
      setState({
        user,
        token: access_token,
        isAuthenticated: true,
        isLoading: false,
      })

      toast.success('Welcome back!')
      
      // Redirect to the page they were trying to access, or dashboard
      const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/'
      navigate(from, { replace: true })
    } catch (error) {
      setState(prev => ({ ...prev, isLoading: false }))
      toast.error(getErrorMessage(error))
      throw error
    }
  }

  const register = async (credentials: RegisterCredentials) => {
    setState(prev => ({ ...prev, isLoading: true }))
    
    try {
      await authApi.register(credentials)
      toast.success('Account created! Please log in.')
      navigate('/login')
    } catch (error) {
      setState(prev => ({ ...prev, isLoading: false }))
      toast.error(getErrorMessage(error))
      throw error
    }
  }

  const logout = () => {
    localStorage.removeItem(STORAGE_KEYS.TOKEN)
    localStorage.removeItem(STORAGE_KEYS.USER)
    
    setState({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,
    })
    
    toast.success('Logged out successfully')
    navigate('/login')
  }

  return (
    <AuthContext.Provider
      value={{
        ...state,
        login,
        register,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

// Protected route component
export function RequireAuth({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      navigate('/login', { state: { from: location }, replace: true })
    }
  }, [isAuthenticated, isLoading, location, navigate])

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return null
  }

  return <>{children}</>
}

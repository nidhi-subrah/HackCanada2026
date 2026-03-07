"use client"
import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from "react"
import { useRouter } from "next/navigation"
import axios from "axios"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

interface User {
  email: string
  name: string
  picture: string
}

interface AuthContextType {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  login: (token: string, user: User) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  token: null,
  isAuthenticated: false,
  login: () => {},
  logout: () => {},
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter()
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)

  // Auto-restore session: when user info is loaded, check if they have existing graph data
  const restoreSession = useCallback(async (email: string) => {
    try {
      const res = await axios.get(`${API_URL}/api/graph/session`, {
        params: { auth_email: email },
      })
      if (res.data.found) {
        localStorage.setItem("user_id", res.data.user_id)
        localStorage.setItem("user_name", res.data.user_name)
      }
    } catch (e) {
      console.error("Failed to restore session:", e)
    }
  }, [])

  useEffect(() => {
    const storedToken = localStorage.getItem("auth_token")
    const storedUser = localStorage.getItem("auth_user")

    if (storedToken && storedUser) {
      try {
        setToken(storedToken)
        const parsedUser = JSON.parse(storedUser)
        setUser(parsedUser)
        // Restore graph session if user_id is missing
        if (!localStorage.getItem("user_id") && parsedUser.email) {
          restoreSession(parsedUser.email)
        }
      } catch {
        localStorage.removeItem("auth_token")
        localStorage.removeItem("auth_user")
      }
    }
  }, [restoreSession])

  const login = useCallback(async (newToken: string, newUser: User) => {
    localStorage.setItem("auth_token", newToken)
    localStorage.setItem("auth_user", JSON.stringify(newUser))
    setToken(newToken)
    setUser(newUser)
    // Try to restore their graph session
    if (newUser.email) {
      await restoreSession(newUser.email)
    }
  }, [restoreSession])

  const logout = useCallback(() => {
    localStorage.removeItem("auth_token")
    localStorage.removeItem("auth_user")
    localStorage.removeItem("user_id")
    localStorage.removeItem("user_name")
    setToken(null)
    setUser(null)
    router.push("/login")
  }, [router])

  return (
    <AuthContext.Provider value={{ user, token, isAuthenticated: !!token, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}

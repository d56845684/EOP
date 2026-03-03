'use client'

import { useState, useEffect, useCallback, createContext, useContext, type ReactNode } from 'react'
import { authApi } from '../api/auth'

interface User {
    id: string
    email: string
    role?: string
}

interface UserProfile {
    id: string
    role: 'admin' | 'teacher' | 'student' | 'employee'
    full_name: string
    email: string
    phone?: string
    avatar_url?: string
    must_change_password?: boolean
}

interface AuthContextValue {
    user: User | null
    profile: UserProfile | null
    loading: boolean
    mustChangePassword: boolean
    signIn: (email: string, password: string) => Promise<any>
    signOut: () => Promise<any>
    refreshUser: () => Promise<void>
    isAdmin: boolean
    isTeacher: boolean
    isStudent: boolean
    isEmployee: boolean
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null)
    const [profile, setProfile] = useState<UserProfile | null>(null)
    const [loading, setLoading] = useState(true)

    const fetchCurrentUser = useCallback(async () => {
        try {
            const { user: u, profile: p, error } = await authApi.getCurrentUserAndProfile()
            if (error || !u) {
                setUser(null)
                setProfile(null)
                return
            }
            setUser(u)
            setProfile(p)
        } catch {
            setUser(null)
            setProfile(null)
        }
    }, [])

    useEffect(() => {
        fetchCurrentUser().finally(() => {
            setLoading(false)
        })
    }, [fetchCurrentUser])

    const signIn = useCallback(async (email: string, password: string) => {
        setLoading(true)
        const result = await authApi.signIn(email, password)

        if (result.data?.user) {
            // 登入成功後重新 fetch 一次取得完整資料
            await fetchCurrentUser()
        }

        setLoading(false)
        return result
    }, [fetchCurrentUser])

    const signOut = useCallback(async () => {
        setLoading(true)
        const result = await authApi.signOut()
        setUser(null)
        setProfile(null)
        setLoading(false)
        return result
    }, [])

    const value: AuthContextValue = {
        user,
        profile,
        loading,
        mustChangePassword: profile?.must_change_password || false,
        signIn,
        signOut,
        refreshUser: fetchCurrentUser,
        isAdmin: profile?.role === 'admin',
        isTeacher: profile?.role === 'teacher',
        isStudent: profile?.role === 'student',
        isEmployee: profile?.role === 'employee',
    }

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
    const ctx = useContext(AuthContext)
    if (!ctx) {
        throw new Error('useAuth must be used within an AuthProvider')
    }
    return ctx
}

'use client'

import { useState, useEffect, useCallback, createContext, useContext, type ReactNode } from 'react'
import { authApi } from '../api/auth'
import { permissionsApi } from '../api/permissions'

interface User {
    id: string
    email: string
    role?: string
}

interface UserProfile {
    id: string
    role: string
    role_id?: string
    full_name: string
    email: string
    phone?: string
    avatar_url?: string
    must_change_password?: boolean
    teacher_id?: string
    student_id?: string
    employee_id?: string
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
    pageKeys: string[]
    hasPage: (key: string) => boolean
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null)
    const [profile, setProfile] = useState<UserProfile | null>(null)
    const [loading, setLoading] = useState(true)
    const [pageKeys, setPageKeys] = useState<string[]>([])

    const fetchPermissions = useCallback(async () => {
        try {
            const { data, error } = await permissionsApi.getMyPermissions()
            if (!error && data) {
                setPageKeys(data.page_keys)
            }
        } catch {
            // 權限取得失敗不影響登入流程
        }
    }, [])

    const fetchCurrentUser = useCallback(async () => {
        try {
            const { user: u, profile: p, error } = await authApi.getCurrentUserAndProfile()
            if (error || !u) {
                setUser(null)
                setProfile(null)
                setPageKeys([])
                return
            }
            setUser(u)
            setProfile(p)
            await fetchPermissions()
        } catch {
            setUser(null)
            setProfile(null)
            setPageKeys([])
        }
    }, [fetchPermissions])

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
        setPageKeys([])
        setLoading(false)
        return result
    }, [])

    const hasPage = useCallback((key: string) => pageKeys.includes(key), [pageKeys])

    const value: AuthContextValue = {
        user,
        profile,
        loading,
        mustChangePassword: profile?.must_change_password || false,
        signIn,
        signOut,
        refreshUser: fetchCurrentUser,
        isAdmin: profile?.employee_id != null && (profile?.role === 'admin' || (profile as any)?.permission_level >= 100),
        isTeacher: profile?.teacher_id != null,
        isStudent: profile?.student_id != null,
        isEmployee: profile?.employee_id != null,
        pageKeys,
        hasPage,
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

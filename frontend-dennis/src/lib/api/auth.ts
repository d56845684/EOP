// Use backend API for authentication instead of direct Supabase calls
// This avoids CORS issues with the Supabase client

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

interface AuthResponse {
    success: boolean
    message: string
    user?: {
        id: string
        email: string
        role: string
        email_confirmed: boolean
    }
    tokens?: {
        access_token: string
        refresh_token: string
        token_type: string
        expires_in: number
    }
}

interface UserProfile {
    id: string
    role: string
    full_name: string
    email: string
    phone?: string
    avatar_url?: string
}

export type RoleType = 'student' | 'teacher' | 'employee'
export type EmployeeType = 'admin' | 'full_time' | 'part_time' | 'intern'

export interface RegisterData {
    email: string
    password: string
    name: string
    role: RoleType
    phone?: string
    address?: string
    // Student fields
    birth_date?: string
    emergency_contact_name?: string
    emergency_contact_phone?: string
    // Teacher fields
    bio?: string
    // Employee fields
    employee_type?: EmployeeType
}

export const authApi = {
    async register(data: RegisterData): Promise<{ success: boolean, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/auth/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            })

            const result = await response.json()

            if (!response.ok || !result.success) {
                return { success: false, error: { message: result.message || '註冊失敗' } }
            }

            return { success: true, error: null }
        } catch (err) {
            return { success: false, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async signIn(email: string, password: string) {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify({ email, password }),
            })

            const result: AuthResponse = await response.json()

            if (!response.ok || !result.success) {
                return {
                    data: null,
                    error: { message: result.message || '登入失敗' }
                }
            }

            // Store tokens in localStorage for the app to use
            if (result.tokens) {
                localStorage.setItem('access_token', result.tokens.access_token)
                localStorage.setItem('refresh_token', result.tokens.refresh_token)
            }

            return {
                data: {
                    user: result.user,
                    session: result.tokens
                },
                error: null
            }
        } catch (err) {
            return {
                data: null,
                error: { message: '網路錯誤，請稍後再試' }
            }
        }
    },

    async signOut() {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/auth/logout`, {
                method: 'POST',
                credentials: 'include',
            })

            // Clear local storage
            localStorage.removeItem('access_token')
            localStorage.removeItem('refresh_token')

            if (!response.ok) {
                return { error: { message: '登出失敗' } }
            }

            return { error: null }
        } catch (err) {
            // Still clear storage on error
            localStorage.removeItem('access_token')
            localStorage.removeItem('refresh_token')
            return { error: null }
        }
    },

    async getCurrentUserAndProfile(): Promise<{
        user: { id: string; email: string; role: string } | null
        profile: UserProfile | null
        error: any
    }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
                method: 'GET',
                credentials: 'include',
            })

            if (!response.ok) {
                return { user: null, profile: null, error: { message: '未登入' } }
            }

            const result = await response.json()
            const userData = result.data || result.user || result

            const user = userData ? {
                id: userData.id,
                email: userData.email,
                role: userData.role,
            } : null

            const profile: UserProfile | null = userData ? {
                id: userData.id,
                role: userData.role || 'student',
                full_name: userData.name || userData.full_name || userData.email || '',
                email: userData.email || '',
                phone: userData.phone,
                avatar_url: userData.avatar_url,
            } : null

            return { user, profile, error: null }
        } catch (err) {
            return { user: null, profile: null, error: { message: '無法取得用戶資訊' } }
        }
    },
}

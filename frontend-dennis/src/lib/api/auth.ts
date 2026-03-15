// Use backend API for authentication instead of direct Supabase calls
// This avoids CORS issues with the Supabase client

import { fetchWithAuth } from './fetchWithAuth'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

interface AuthResponse {
    success: boolean
    message: string
    user?: {
        id: string
        email: string
        role: string
        email_confirmed: boolean
        must_change_password?: boolean
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
    role_id?: string
    full_name: string
    email: string
    phone?: string
    avatar_url?: string
    must_change_password?: boolean
}

export const authApi = {
    // 公開註冊已關閉，所有帳號建立請走 invite 流程（/accept-invite）

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

            if (!response.ok) {
                return { error: { message: '登出失敗' } }
            }

            return { error: null }
        } catch (err) {
            return { error: null }
        }
    },

    async getCurrentUserAndProfile(): Promise<{
        user: { id: string; email: string; role: string } | null
        profile: UserProfile | null
        error: any
    }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/auth/me`, {
                method: 'GET',
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
                role_id: userData.role_id,
                full_name: userData.name || userData.full_name || userData.email || '',
                email: userData.email || '',
                phone: userData.phone,
                avatar_url: userData.avatar_url,
                must_change_password: userData.must_change_password || false,
                teacher_id: userData.teacher_id,
                student_id: userData.student_id,
                employee_id: userData.employee_id,
            } : null

            return { user, profile, error: null }
        } catch (err) {
            return { user: null, profile: null, error: { message: '無法取得用戶資訊' } }
        }
    },

    async changePassword(currentPassword: string, newPassword: string): Promise<{ success: boolean, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/auth/password/change`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    current_password: currentPassword,
                    new_password: newPassword,
                }),
            })

            const result = await response.json()

            if (!response.ok || !result.success) {
                return { success: false, error: { message: result.detail || result.message || '密碼變更失敗' } }
            }

            return { success: true, error: null }
        } catch (err) {
            return { success: false, error: { message: '網路錯誤，請稍後再試' } }
        }
    },
}

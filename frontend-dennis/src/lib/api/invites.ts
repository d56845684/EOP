import { API_BASE_URL } from './config'
import { apiPost } from './client'

export interface GenerateInviteResponse {
    invite_url: string
    expires_at: string
}

export interface AcceptInviteResponse {
    success: boolean
    message: string
}

export const invitesApi = {
    generate: (entityType: 'student' | 'teacher' | 'employee', entityId: string, roleId?: string) => {
        const body: Record<string, unknown> = { entity_type: entityType, entity_id: entityId }
        if (roleId) body.role_id = roleId
        return apiPost<GenerateInviteResponse>('/api/v1/invites/generate', body, '產生邀請連結失敗', { extractData: false })
    },

    /** accept 不需要 auth cookie（公開端點），直接用 fetch */
    async accept(token: string, password: string): Promise<{ data: AcceptInviteResponse | null, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/invites/accept`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token, password }),
            })

            if (!response.ok) {
                const error = await response.json()
                const detail = error.detail
                const message = typeof detail === 'string' ? detail
                    : Array.isArray(detail) && detail.length > 0 ? (detail[0]?.msg || '').replace(/^Value error,\s*/, '')
                    : '建立帳號失敗'
                return { data: null, error: { message } }
            }

            const result: AcceptInviteResponse = await response.json()
            return { data: result, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

export interface GenerateInviteResponse {
    invite_url: string
    expires_at: string
}

export interface AcceptInviteResponse {
    success: boolean
    message: string
}

function parseErrorDetail(detail: unknown): string {
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && detail.length > 0) {
        const msg = detail[0]?.msg || ''
        return msg.replace(/^Value error,\s*/, '')
    }
    return ''
}

export const invitesApi = {
    async generate(entityType: 'student' | 'teacher', entityId: string): Promise<{ data: GenerateInviteResponse | null, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/invites/generate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ entity_type: entityType, entity_id: entityId }),
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '產生邀請連結失敗' } }
            }

            const result: GenerateInviteResponse = await response.json()
            return { data: result, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async accept(token: string, password: string): Promise<{ data: AcceptInviteResponse | null, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/invites/accept`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token, password }),
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '建立帳號失敗' } }
            }

            const result: AcceptInviteResponse = await response.json()
            return { data: result, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },
}

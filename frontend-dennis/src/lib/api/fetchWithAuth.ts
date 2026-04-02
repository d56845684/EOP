const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

let refreshPromise: Promise<boolean> | null = null

async function refreshTokens(): Promise<boolean> {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
    })
    return response.ok
}

/** 從 401 response body 判斷登出原因 */
function detectLogoutReason(detail: string): string {
    if (detail.includes('閒置超時')) return 'idle'
    if (detail.includes('其他裝置')) return 'replaced'
    return 'expired'
}

export async function fetchWithAuth(
    url: string,
    options: RequestInit = {}
): Promise<Response> {
    options.credentials = 'include'

    let response = await fetch(url, options)

    if (response.status === 401) {
        // 先取得原始錯誤訊息（clone 以避免 body consumed）
        const errClone = response.clone()
        let reason = 'expired'
        try {
            const errBody = await errClone.json()
            reason = detectLogoutReason(errBody.detail || '')
        } catch { /* ignore parse errors */ }

        // Mutex: 同一時間只有一個 refresh 請求
        if (!refreshPromise) {
            refreshPromise = refreshTokens().finally(() => {
                refreshPromise = null
            })
        }

        const refreshed = await refreshPromise

        if (refreshed) {
            // 重試原始請求
            response = await fetch(url, options)
        } else {
            // refresh 也失敗 → 導向登入頁（避免在 /login 頁面無限迴圈）
            if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
                window.location.href = `/login?reason=${reason}`
            }
        }
    }

    return response
}

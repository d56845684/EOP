const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

let refreshPromise: Promise<boolean> | null = null

async function refreshTokens(): Promise<boolean> {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
    })
    return response.ok
}

export async function fetchWithAuth(
    url: string,
    options: RequestInit = {}
): Promise<Response> {
    options.credentials = 'include'

    let response = await fetch(url, options)

    if (response.status === 401) {
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
            // refresh 也失敗 → 導向登入頁
            window.location.href = '/login'
        }
    }

    return response
}

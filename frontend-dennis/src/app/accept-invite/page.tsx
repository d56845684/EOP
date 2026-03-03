'use client'

import { useState, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { invitesApi } from '@/lib/api/invites'

function AcceptInviteForm() {
    const router = useRouter()
    const searchParams = useSearchParams()
    const token = searchParams.get('token') || ''

    const [password, setPassword] = useState('')
    const [confirmPassword, setConfirmPassword] = useState('')
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)
    const [success, setSuccess] = useState(false)

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError('')

        if (!token) {
            setError('邀請連結無效，缺少 token')
            return
        }

        if (password.length < 6) {
            setError('密碼至少需要 6 個字元')
            return
        }

        if (password !== confirmPassword) {
            setError('兩次輸入的密碼不一致')
            return
        }

        setLoading(true)
        try {
            const { data, error: apiError } = await invitesApi.accept(token, password)
            if (apiError) {
                setError(apiError.message)
            } else {
                setSuccess(true)
            }
        } catch {
            setError('發生錯誤，請稍後再試')
        } finally {
            setLoading(false)
        }
    }

    if (!token) {
        return (
            <div className="min-h-screen flex items-center justify-center p-4">
                <div className="card w-full max-w-md text-center py-12">
                    <h2 className="text-xl font-bold text-gray-900 mb-2">邀請連結無效</h2>
                    <p className="text-gray-600 mb-6">缺少必要的 token 參數</p>
                    <button onClick={() => router.push('/login')} className="btn-primary">
                        前往登入頁面
                    </button>
                </div>
            </div>
        )
    }

    if (success) {
        return (
            <div className="min-h-screen flex items-center justify-center p-4">
                <div className="card w-full max-w-md text-center py-12">
                    <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                        <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                    </div>
                    <h2 className="text-xl font-bold text-gray-900 mb-2">帳號建立成功</h2>
                    <p className="text-gray-600 mb-6">您現在可以使用 email 和密碼登入系統</p>
                    <button onClick={() => router.push('/login')} className="btn-primary">
                        前往登入
                    </button>
                </div>
            </div>
        )
    }

    return (
        <div className="min-h-screen flex items-center justify-center p-4">
            <div className="card w-full max-w-md">
                <div className="p-6">
                    <h1 className="text-2xl font-bold text-gray-900 mb-2 text-center">設定您的密碼</h1>
                    <p className="text-gray-600 text-center mb-6">
                        請設定登入密碼以完成帳號註冊
                    </p>

                    {error && (
                        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                            {error}
                        </div>
                    )}

                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                密碼 <span className="text-red-500">*</span>
                            </label>
                            <input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="input-field"
                                placeholder="至少 6 個字元"
                                required
                                minLength={6}
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                確認密碼 <span className="text-red-500">*</span>
                            </label>
                            <input
                                type="password"
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                className="input-field"
                                placeholder="再次輸入密碼"
                                required
                                minLength={6}
                            />
                        </div>
                        <button
                            type="submit"
                            className="btn-primary w-full"
                            disabled={loading}
                        >
                            {loading ? (
                                <span className="flex items-center justify-center">
                                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                                    建立中...
                                </span>
                            ) : '建立帳號'}
                        </button>
                    </form>
                </div>
            </div>
        </div>
    )
}

export default function AcceptInvitePage() {
    return (
        <Suspense fallback={
            <div className="min-h-screen flex items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
        }>
            <AcceptInviteForm />
        </Suspense>
    )
}

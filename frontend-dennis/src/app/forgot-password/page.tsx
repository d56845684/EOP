'use client'

import { useState } from 'react'
import Link from 'next/link'
import { authApi } from '@/lib/api/auth'

export default function ForgotPasswordPage() {
    const [email, setEmail] = useState('')
    const [loading, setLoading] = useState(false)
    const [sent, setSent] = useState(false)
    const [error, setError] = useState('')

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError('')
        setLoading(true)

        const { error } = await authApi.requestPasswordReset(email)
        if (error) {
            setError(error.message)
        } else {
            setSent(true)
        }

        setLoading(false)
    }

    return (
        <div className="min-h-screen flex items-center justify-center p-4">
            <div className="card w-full max-w-md">
                <h1 className="text-2xl font-bold text-center mb-2">重設密碼</h1>
                <p className="text-center text-sm text-gray-500 mb-6">
                    輸入您的 Email，我們將寄送重設密碼連結
                </p>

                {sent ? (
                    <div className="text-center">
                        <div className="bg-green-50 text-green-700 p-4 rounded-lg mb-6 text-sm border border-green-200">
                            如果該 Email 已註冊，您將收到重設密碼郵件。請檢查您的信箱（含垃圾郵件資料夾）。
                        </div>
                        <Link
                            href="/login"
                            className="btn-primary inline-block"
                        >
                            返回登入
                        </Link>
                    </div>
                ) : (
                    <>
                        {error && (
                            <div className="bg-red-50 text-red-600 p-3 rounded-lg mb-4 text-sm">
                                {error}
                            </div>
                        )}

                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Email
                                </label>
                                <input
                                    type="email"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    className="input-field"
                                    placeholder="your@email.com"
                                    required
                                />
                            </div>

                            <button
                                type="submit"
                                disabled={loading}
                                className="btn-primary w-full disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {loading ? '發送中...' : '發送重設連結'}
                            </button>
                        </form>

                        <p className="text-center text-sm text-gray-500 mt-6">
                            <Link href="/login" className="text-primary-600 hover:underline">
                                返回登入
                            </Link>
                        </p>
                    </>
                )}
            </div>
        </div>
    )
}

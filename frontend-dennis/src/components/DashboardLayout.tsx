'use client'

import { useEffect, useState } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { useAuth } from '@/lib/hooks/useAuth'
import { authApi } from '@/lib/api/auth'
import Sidebar from './Sidebar'
import { Lock, ChevronRight, Home } from 'lucide-react'

interface DashboardLayoutProps {
  children: React.ReactNode
}

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  const router = useRouter()
  const { user, loading, mustChangePassword, refreshUser } = useAuth()

  // Password change modal state
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [pwError, setPwError] = useState<string | null>(null)
  const [pwSubmitting, setPwSubmitting] = useState(false)

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login')
    }
  }, [loading, user, router])

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault()
    setPwError(null)

    if (newPassword.length < 6) {
      setPwError('新密碼至少需要 6 個字元')
      return
    }
    if (newPassword !== confirmPassword) {
      setPwError('兩次輸入的新密碼不一致')
      return
    }

    setPwSubmitting(true)
    const { success, error } = await authApi.changePassword(currentPassword, newPassword)
    if (error) {
      setPwError(error.message)
    } else if (success) {
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      await refreshUser()
    }
    setPwSubmitting(false)
  }

  const pathname = usePathname()

  // 路由 → 麵包屑標籤
  const pageLabels: Record<string, string> = {
    '/profile': '個人設定',
    '/courses': '課程管理',
    '/bookings': '預約管理',
    '/teacher-slots': '教師時段',
    '/my-contracts': '我的合約',
    '/student-courses': '學生選課',
    '/student-contracts': '學生合約',
    '/teacher-contracts': '教師合約',
    '/teacher-bonus': '教師獎金',
    '/student-overview': '學生總覽',
    '/students': '學生管理',
    '/teachers': '教師管理',
    '/employees': '員工管理',
    '/zoom-accounts': 'Zoom 帳號',
    '/line-testing': 'LINE 測試',
    '/accounts': '帳號管理',
    '/role-permissions': '角色權限',
  }

  const currentPageLabel = pageLabels[pathname] || ''

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: 'var(--ep-bg-color-page)' }}>
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 rounded-full border-2 border-primary-200 border-t-primary-500 animate-spin"></div>
          <span className="text-sm text-slate-400">載入中...</span>
        </div>
      </div>
    )
  }

  if (!user) {
    return null
  }

  return (
    <div className="min-h-screen flex" style={{ backgroundColor: 'var(--ep-bg-color-page)' }}>
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        {/* Header — breadcrumb bar */}
        <header className="h-14 flex items-center px-6 shrink-0 bg-white"
          style={{ borderBottom: '1px solid var(--ep-border-color)' }}>
          <nav className="flex items-center text-sm gap-1.5">
            <Home className="w-4 h-4 text-slate-400" />
            <span className="text-slate-400 font-medium cursor-pointer hover:text-primary-500 transition-colors">
              首頁
            </span>
            {currentPageLabel && (
              <>
                <ChevronRight className="w-3.5 h-3.5 text-slate-300" />
                <span className="text-slate-700 font-medium">{currentPageLabel}</span>
              </>
            )}
          </nav>
        </header>

        {/* Main content */}
        <main className="flex-1 overflow-auto p-6">
          {children}
        </main>

        {/* Footer */}
        <footer className="h-10 flex items-center justify-center shrink-0 text-xs text-slate-400"
          style={{ borderTop: '1px solid var(--ep-border-color-light)' }}>
          &copy; 2024 EOP System
        </footer>
      </div>

      {/* Forced Password Change Modal */}
      {mustChangePassword && (
        <div className="modal-overlay">
          <div className="modal-panel max-w-md p-6 mx-4">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-11 h-11 rounded-xl bg-amber-50 flex items-center justify-center">
                <Lock className="w-5 h-5 text-amber-500" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-slate-900">首次登入密碼變更</h2>
                <p className="text-sm text-slate-500 mt-0.5">為確保帳號安全，請變更您的初始密碼</p>
              </div>
            </div>

            <form onSubmit={handlePasswordChange} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">當前密碼</label>
                <input
                  type="password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  className="input-field w-full"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">新密碼</label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="input-field w-full"
                  required
                  minLength={6}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">確認新密碼</label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="input-field w-full"
                  required
                  minLength={6}
                />
              </div>

              {pwError && (
                <div className="text-sm text-red-600 bg-red-50 border border-red-100 p-3 rounded-lg">{pwError}</div>
              )}

              <button
                type="submit"
                disabled={pwSubmitting}
                className="btn-primary w-full"
              >
                {pwSubmitting ? '變更中...' : '變更密碼'}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

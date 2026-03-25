'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { User, BookOpen, Home, Settings, LogOut, Calendar, FileText, Users, Clock, GraduationCap, DollarSign, Video, Shield, MessageSquare } from 'lucide-react'
import { useAuth } from '@/lib/hooks/useAuth'
import { useRouter } from 'next/navigation'

interface NavItem {
  href: string
  label: string
  icon: React.ReactNode
  pageKey?: string  // 對應後端 pages.key，未設定則永遠顯示
}

const navItems: NavItem[] = [
  { href: '/profile', label: '個人設定', icon: <User className="w-5 h-5" />, pageKey: 'profile' },
  { href: '/courses', label: '課程管理', icon: <BookOpen className="w-5 h-5" />, pageKey: 'courses' },
  { href: '/bookings', label: '預約管理', icon: <Calendar className="w-5 h-5" />, pageKey: 'bookings' },
  { href: '/teacher-slots', label: '教師時段', icon: <Clock className="w-5 h-5" />, pageKey: 'teachers.slots' },
  { href: '/my-contracts', label: '我的合約', icon: <FileText className="w-5 h-5" />, pageKey: 'students.contracts|teachers.contracts' },
  { href: '/student-courses', label: '學生選課', icon: <BookOpen className="w-5 h-5" />, pageKey: 'students.edit' },
  { href: '/student-contracts', label: '學生合約', icon: <FileText className="w-5 h-5" />, pageKey: 'students.list' },
  { href: '/teacher-contracts', label: '教師合約', icon: <Users className="w-5 h-5" />, pageKey: 'teachers.contracts' },
  { href: '/teacher-bonus', label: '教師獎金', icon: <DollarSign className="w-5 h-5" />, pageKey: 'teachers.bonus' },
  { href: '/student-overview', label: '學生總覽', icon: <GraduationCap className="w-5 h-5" />, pageKey: 'students.list' },
  { href: '/students', label: '學生管理', icon: <GraduationCap className="w-5 h-5" />, pageKey: 'students.list' },
  { href: '/teachers', label: '教師管理', icon: <Users className="w-5 h-5" />, pageKey: 'teachers.list' },
  { href: '/employees', label: '員工管理', icon: <Users className="w-5 h-5" />, pageKey: 'employees.list' },
  { href: '/zoom-accounts', label: 'Zoom 帳號', icon: <Video className="w-5 h-5" />, pageKey: 'employees.list' },
  { href: '/line-testing', label: 'LINE 測試', icon: <MessageSquare className="w-5 h-5" />, pageKey: 'employees.list' },
  { href: '/accounts', label: '帳號管理', icon: <Shield className="w-5 h-5" />, pageKey: 'permissions.users' },
  { href: '/role-permissions', label: '角色權限', icon: <Settings className="w-5 h-5" />, pageKey: 'permissions.roles' },
]

export default function Sidebar() {
  const pathname = usePathname()
  const router = useRouter()
  const { user, profile, signOut, pageKeys } = useAuth()

  const handleSignOut = async () => {
    await signOut()
    router.push('/login')
  }

  const roleLabels: Record<string, string> = {
    admin: '管理員',
    teacher: '老師',
    student: '學生',
    employee: '員工',
  }

  return (
    <aside className="w-60 bg-white border-r flex flex-col" style={{ borderColor: 'var(--ep-border-color)', minHeight: '100vh' }}>
      {/* Avatar + User Info (top section) */}
      {user && (
        <div className="py-5 px-4 text-center" style={{ borderBottom: '1px solid var(--ep-border-color)' }}>
          <div className="w-12 h-12 rounded-full bg-primary-100 flex items-center justify-center mx-auto mb-2">
            {profile?.avatar_url ? (
              <img
                src={profile.avatar_url}
                alt="Avatar"
                className="w-12 h-12 rounded-full object-cover"
              />
            ) : (
              <User className="w-6 h-6 text-primary-500" />
            )}
          </div>
          <p className="text-sm font-medium truncate" style={{ color: 'var(--ep-text-color-primary)' }}>
            {profile?.full_name || user.email}
          </p>
          {profile?.role && (
            <span className="inline-block mt-1 px-2 py-0.5 text-xs rounded"
              style={{
                backgroundColor: 'var(--ep-color-primary)',
                color: '#fff',
                borderRadius: 'var(--ep-border-radius-small)',
              }}>
              {roleLabels[profile.role] || profile.role}
            </span>
          )}
        </div>
      )}

      {/* Navigation Menu */}
      <nav className="flex-1 overflow-y-auto py-2">
        <ul className="space-y-0.5 px-2">
          {navItems
            .filter((item) => {
              if (!item.pageKey) return true
              const keys = item.pageKey.split('|')
              return keys.some((k) => pageKeys.includes(k))
            })
            .map((item) => {
              const isActive = pathname === item.href
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className="flex items-center gap-3 px-3 py-2 text-sm transition-colors"
                    style={{
                      borderRadius: 'var(--ep-border-radius)',
                      color: isActive ? 'var(--ep-color-primary)' : 'var(--ep-text-color-primary)',
                      backgroundColor: isActive ? 'var(--ep-color-primary, #409eff)10' : 'transparent',
                      fontWeight: isActive ? 500 : 400,
                    }}
                    onMouseEnter={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.backgroundColor = 'var(--ep-bg-color-page)'
                        e.currentTarget.style.color = 'var(--ep-color-primary)'
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.backgroundColor = 'transparent'
                        e.currentTarget.style.color = 'var(--ep-text-color-primary)'
                      }
                    }}
                  >
                    {item.icon}
                    {item.label}
                  </Link>
                </li>
              )
            })}
        </ul>
      </nav>

      {/* Bottom — Logout */}
      <div className="px-4 py-4" style={{ borderTop: '1px solid var(--ep-border-color)' }}>
        <button
          onClick={handleSignOut}
          className="flex items-center justify-center gap-2 w-full py-2 text-sm font-medium transition-colors"
          style={{
            color: 'var(--ep-color-danger)',
            border: '1px solid var(--ep-color-danger)',
            borderRadius: 'var(--ep-border-radius)',
            backgroundColor: 'transparent',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = 'var(--ep-color-danger)'
            e.currentTarget.style.color = '#fff'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = 'transparent'
            e.currentTarget.style.color = 'var(--ep-color-danger)'
          }}
        >
          <LogOut className="w-4 h-4" />
          登出
        </button>
      </div>
    </aside>
  )
}

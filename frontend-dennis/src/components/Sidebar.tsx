'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { User, BookOpen, Settings, LogOut, Calendar, FileText, Users, Clock, GraduationCap, DollarSign, Video, Shield, MessageSquare, Bell } from 'lucide-react'
import { useAuth } from '@/lib/hooks/useAuth'
import { useRouter } from 'next/navigation'

interface NavItem {
  href: string
  label: string
  icon: React.ReactNode
  pageKey?: string  // 對應後端 pages.key，未設定則永遠顯示
}

interface SidebarProps {
  isOpen?: boolean
  onClose?: () => void
}

const navItems: NavItem[] = [
  { href: '/profile', label: '個人設定', icon: <User className="w-[18px] h-[18px]" />, pageKey: 'profile' },
  { href: '/courses', label: '課程管理', icon: <BookOpen className="w-[18px] h-[18px]" />, pageKey: 'courses' },
  { href: '/bookings', label: '預約管理', icon: <Calendar className="w-[18px] h-[18px]" />, pageKey: 'bookings' },
  { href: '/teacher-slots', label: '教師時段', icon: <Clock className="w-[18px] h-[18px]" />, pageKey: 'teachers.slots' },
  { href: '/my-contracts', label: '我的合約', icon: <FileText className="w-[18px] h-[18px]" />, pageKey: 'students.contracts|teachers.contracts' },
  { href: '/student-courses', label: '學生選課', icon: <BookOpen className="w-[18px] h-[18px]" />, pageKey: 'students.edit' },
  { href: '/student-contracts', label: '學生合約', icon: <FileText className="w-[18px] h-[18px]" />, pageKey: 'students.list' },
  { href: '/teacher-contracts', label: '教師合約', icon: <Users className="w-[18px] h-[18px]" />, pageKey: 'teachers.contracts' },
  { href: '/teacher-bonus', label: '教師獎金', icon: <DollarSign className="w-[18px] h-[18px]" />, pageKey: 'teachers.bonus' },
  { href: '/student-overview', label: '學生總覽', icon: <GraduationCap className="w-[18px] h-[18px]" />, pageKey: 'students.list' },
  { href: '/students', label: '學生管理', icon: <GraduationCap className="w-[18px] h-[18px]" />, pageKey: 'students.list' },
  { href: '/teacher-overview', label: '教師總覽', icon: <Users className="w-[18px] h-[18px]" />, pageKey: 'teachers.list' },
  { href: '/teachers', label: '教師管理', icon: <Users className="w-[18px] h-[18px]" />, pageKey: 'teachers.list' },
  { href: '/employees', label: '員工管理', icon: <Users className="w-[18px] h-[18px]" />, pageKey: 'employees.list' },
  { href: '/zoom-accounts', label: 'Zoom 帳號', icon: <Video className="w-[18px] h-[18px]" />, pageKey: 'employees.list' },
  { href: '/line-testing', label: 'LINE 測試', icon: <MessageSquare className="w-[18px] h-[18px]" />, pageKey: 'employees.list' },
  { href: '/accounts', label: '帳號管理', icon: <Shield className="w-[18px] h-[18px]" />, pageKey: 'permissions.users' },
  { href: '/role-permissions', label: '角色權限', icon: <Settings className="w-[18px] h-[18px]" />, pageKey: 'permissions.roles' },
  { href: '/system-alerts', label: '系統告警', icon: <Bell className="w-[18px] h-[18px]" />, pageKey: 'dashboard.alerts' },
]

export default function Sidebar({ isOpen = false, onClose }: SidebarProps) {
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

  const roleBadgeColors: Record<string, { bg: string; text: string }> = {
    admin: { bg: '#fef3c7', text: '#92400e' },
    teacher: { bg: '#dbeafe', text: '#1e40af' },
    student: { bg: '#dcfce7', text: '#166534' },
    employee: { bg: '#eef2ff', text: '#3730a3' },
  }

  return (
    <aside className={`
      w-[248px] bg-white flex flex-col shrink-0
      fixed md:relative inset-y-0 left-0 z-40
      transform transition-transform duration-200 ease-in-out
      ${isOpen ? 'translate-x-0' : '-translate-x-full'} md:translate-x-0
    `}
      style={{
        minHeight: '100vh',
        borderRight: '1px solid var(--ep-border-color)',
        boxShadow: '1px 0 0 var(--ep-border-color-light)',
      }}>
      {/* Brand + User Info */}
      {user && (
        <div className="px-5 pt-6 pb-5">
          {/* Brand */}
          <div className="flex items-center gap-2.5 mb-5">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center text-white text-sm font-bold"
              style={{ background: 'linear-gradient(135deg, #4f6ef7, #7b93fa)' }}>
              E
            </div>
            <span className="text-[15px] font-semibold tracking-tight" style={{ color: 'var(--ep-text-color-primary)' }}>
              EOP System
            </span>
          </div>

          {/* User card */}
          <div className="flex items-center gap-3 p-3 rounded-lg"
            style={{ backgroundColor: 'var(--ep-bg-color-page)' }}>
            <div className="w-9 h-9 rounded-full flex items-center justify-center shrink-0 overflow-hidden"
              style={{ background: 'linear-gradient(135deg, #c7d2fe, #e0e7ff)' }}>
              {profile?.avatar_url ? (
                <img src={profile.avatar_url} alt="Avatar" className="w-9 h-9 rounded-full object-cover" />
              ) : (
                <User className="w-4 h-4 text-primary-600" />
              )}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium truncate" style={{ color: 'var(--ep-text-color-primary)' }}>
                {profile?.full_name || user.email}
              </p>
              {profile?.role && (
                <span className="inline-block mt-0.5 px-1.5 py-px text-[11px] font-medium rounded"
                  style={{
                    backgroundColor: roleBadgeColors[profile.role]?.bg || '#f1f5f9',
                    color: roleBadgeColors[profile.role]?.text || '#475569',
                  }}>
                  {roleLabels[profile.role] || profile.role}
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Navigation Menu */}
      <nav className="flex-1 overflow-y-auto px-3 pb-2">
        <ul className="space-y-0.5">
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
                    onClick={onClose}
                    className={`
                      flex items-center gap-2.5 px-3 py-2 text-[13px] rounded-lg
                      transition-all duration-150
                      ${isActive
                        ? 'bg-primary-50 text-primary-600 font-medium shadow-sm'
                        : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                      }
                    `}
                  >
                    <span className={isActive ? 'text-primary-500' : 'text-slate-400'}>{item.icon}</span>
                    {item.label}
                  </Link>
                </li>
              )
            })}
        </ul>
      </nav>

      {/* Bottom — Logout */}
      <div className="px-3 py-4" style={{ borderTop: '1px solid var(--ep-border-color-light)' }}>
        <button
          onClick={handleSignOut}
          className="flex items-center justify-center gap-2 w-full py-2 text-sm font-medium rounded-lg
            text-slate-500 hover:text-red-600 hover:bg-red-50
            transition-all duration-150"
        >
          <LogOut className="w-4 h-4" />
          登出
        </button>
      </div>
    </aside>
  )
}

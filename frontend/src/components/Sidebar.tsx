'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { User, BookOpen, Home, Settings, LogOut, Calendar, FileText, Users, Clock } from 'lucide-react'
import { useAuth } from '@/lib/hooks/useAuth'
import { useRouter } from 'next/navigation'

interface NavItem {
  href: string
  label: string
  icon: React.ReactNode
}

interface NavItemWithRoles extends NavItem {
  roles?: string[]  // If defined, only show for these roles
}

const navItems: NavItemWithRoles[] = [
  { href: '/profile', label: '個人設定', icon: <User className="w-5 h-5" /> },
  { href: '/courses', label: '課程管理', icon: <BookOpen className="w-5 h-5" /> },
  { href: '/bookings', label: '預約管理', icon: <Calendar className="w-5 h-5" /> },
  { href: '/teacher-slots', label: '教師時段', icon: <Clock className="w-5 h-5" />, roles: ['admin', 'employee', 'teacher'] },
  { href: '/my-contracts', label: '我的合約', icon: <FileText className="w-5 h-5" />, roles: ['student', 'teacher'] },
  { href: '/student-courses', label: '學生選課', icon: <BookOpen className="w-5 h-5" />, roles: ['admin', 'employee'] },
  { href: '/student-contracts', label: '學生合約', icon: <FileText className="w-5 h-5" />, roles: ['admin', 'employee'] },
  { href: '/teacher-contracts', label: '教師合約', icon: <Users className="w-5 h-5" />, roles: ['admin', 'employee'] },
]

export default function Sidebar() {
  const pathname = usePathname()
  const router = useRouter()
  const { user, profile, signOut } = useAuth()

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
    <aside className="w-64 bg-white border-r border-gray-200 min-h-screen flex flex-col">
      {/* Logo / Title */}
      <div className="p-4 border-b border-gray-200">
        <h1 className="text-xl font-bold text-gray-800">教學管理系統</h1>
      </div>

      {/* User Info */}
      {user && (
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
              {profile?.avatar_url ? (
                <img
                  src={profile.avatar_url}
                  alt="Avatar"
                  className="w-10 h-10 rounded-full object-cover"
                />
              ) : (
                <User className="w-5 h-5 text-blue-600" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">
                {profile?.full_name || user.email}
              </p>
              {profile?.role && (
                <span className="inline-block px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded">
                  {roleLabels[profile.role] || profile.role}
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Navigation */}
      <nav className="flex-1 p-4">
        <ul className="space-y-1">
          {navItems
            .filter((item) => {
              // If no roles specified, show to everyone
              if (!item.roles) return true
              // Otherwise, check if user's role is in the allowed roles
              return profile?.role && item.roles.includes(profile.role)
            })
            .map((item) => {
              const isActive = pathname === item.href
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
                      isActive
                        ? 'bg-blue-50 text-blue-700 font-medium'
                        : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                    }`}
                  >
                    {item.icon}
                    {item.label}
                  </Link>
                </li>
              )
            })}
        </ul>
      </nav>

      {/* Sign Out Button */}
      <div className="p-4 border-t border-gray-200">
        <button
          onClick={handleSignOut}
          className="flex items-center gap-3 w-full px-3 py-2 text-gray-600 hover:bg-gray-50 hover:text-gray-900 rounded-lg transition-colors"
        >
          <LogOut className="w-5 h-5" />
          登出
        </button>
      </div>
    </aside>
  )
}

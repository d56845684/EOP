'use client'

import { useState } from 'react'
import Link from 'next/link'
import { authApi, RoleType, EmployeeType } from '@/lib/api/auth'

const ROLES: { value: RoleType; label: string; description: string }[] = [
  { value: 'student', label: '學生', description: '報名課程、預約上課' },
  { value: 'teacher', label: '教師', description: '管理課程、排定時段' },
  { value: 'employee', label: '員工', description: '系統管理、行政作業' },
]

const EMPLOYEE_TYPES: { value: EmployeeType; label: string }[] = [
  { value: 'intern', label: '實習生' },
  { value: 'part_time', label: '兼職' },
  { value: 'full_time', label: '全職' },
  { value: 'admin', label: '管理員' },
]

export default function RegisterPage() {
  const [role, setRole] = useState<RoleType | null>(null)
  const [form, setForm] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
    phone: '',
    address: '',
    // Student
    birth_date: '',
    emergency_contact_name: '',
    emergency_contact_phone: '',
    // Teacher
    bio: '',
    // Employee
    employee_type: '' as EmployeeType | '',
  })
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [loading, setLoading] = useState(false)

  const updateField = (field: string, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!role) {
      setError('請選擇角色')
      return
    }

    if (form.password !== form.confirmPassword) {
      setError('密碼不一致')
      return
    }

    if (form.password.length < 6) {
      setError('密碼至少需要 6 個字元')
      return
    }

    if (role === 'employee' && !form.employee_type) {
      setError('請選擇員工類型')
      return
    }

    setLoading(true)

    const data: Parameters<typeof authApi.register>[0] = {
      email: form.email,
      password: form.password,
      name: form.name,
      role,
      ...(form.phone && { phone: form.phone }),
      ...(form.address && { address: form.address }),
      ...(role === 'student' && form.birth_date && { birth_date: form.birth_date }),
      ...(role === 'student' && form.emergency_contact_name && { emergency_contact_name: form.emergency_contact_name }),
      ...(role === 'student' && form.emergency_contact_phone && { emergency_contact_phone: form.emergency_contact_phone }),
      ...(role === 'teacher' && form.bio && { bio: form.bio }),
      ...(role === 'employee' && form.employee_type && { employee_type: form.employee_type as EmployeeType }),
    }

    try {
      const { success: ok, error: err } = await authApi.register(data)
      if (ok) {
        setSuccess(true)
      } else {
        setError(err?.message || '註冊失敗')
      }
    } catch {
      setError('註冊失敗，請稍後再試')
    } finally {
      setLoading(false)
    }
  }

  // Success screen
  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="card w-full max-w-md text-center">
          <div className="text-green-500 text-5xl mb-4">&#10003;</div>
          <h1 className="text-2xl font-bold mb-2">註冊成功</h1>
          <p className="text-gray-600 mb-6">請檢查您的郵箱進行驗證，驗證後即可登入。</p>
          <Link href="/login" className="btn-primary inline-block w-full text-center">
            前往登入
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="card w-full max-w-md">
        <h1 className="text-2xl font-bold text-center mb-6">註冊帳號</h1>

        {error && (
          <div className="bg-red-50 text-red-600 p-3 rounded-lg mb-4 text-sm">
            {error}
          </div>
        )}

        {/* Step 1: Role Selection */}
        {!role && (
          <div className="space-y-3">
            <p className="text-sm text-gray-600 text-center mb-4">請選擇您的角色</p>
            {ROLES.map((r) => (
              <button
                key={r.value}
                onClick={() => setRole(r.value)}
                className="w-full p-4 border-2 border-gray-200 rounded-lg text-left hover:border-blue-500 hover:bg-blue-50 transition-colors"
              >
                <div className="font-medium">{r.label}</div>
                <div className="text-sm text-gray-500">{r.description}</div>
              </button>
            ))}
            <p className="text-center text-sm text-gray-500 mt-6">
              已有帳號？{' '}
              <Link href="/login" className="text-blue-600 hover:underline">
                前往登入
              </Link>
            </p>
          </div>
        )}

        {/* Step 2: Registration Form */}
        {role && (
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Role badge + back button */}
            <div className="flex items-center justify-between mb-2">
              <button
                type="button"
                onClick={() => setRole(null)}
                className="text-sm text-gray-500 hover:text-gray-700"
              >
                &larr; 返回選擇角色
              </button>
              <span className="text-sm bg-blue-100 text-blue-700 px-2 py-1 rounded">
                {ROLES.find((r) => r.value === role)?.label}
              </span>
            </div>

            {/* Common fields */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                姓名 <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => updateField('name', e.target.value)}
                className="input-field"
                placeholder="您的姓名"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Email <span className="text-red-500">*</span>
              </label>
              <input
                type="email"
                value={form.email}
                onChange={(e) => updateField('email', e.target.value)}
                className="input-field"
                placeholder="your@email.com"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                密碼 <span className="text-red-500">*</span>
              </label>
              <input
                type="password"
                value={form.password}
                onChange={(e) => updateField('password', e.target.value)}
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
                value={form.confirmPassword}
                onChange={(e) => updateField('confirmPassword', e.target.value)}
                className="input-field"
                placeholder="再次輸入密碼"
                required
                minLength={6}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                電話
              </label>
              <input
                type="tel"
                value={form.phone}
                onChange={(e) => updateField('phone', e.target.value)}
                className="input-field"
                placeholder="09xx-xxx-xxx"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                地址
              </label>
              <input
                type="text"
                value={form.address}
                onChange={(e) => updateField('address', e.target.value)}
                className="input-field"
                placeholder="通訊地址"
              />
            </div>

            {/* Student-specific fields */}
            {role === 'student' && (
              <>
                <hr className="border-gray-200" />
                <p className="text-xs text-gray-500">學生資料（選填）</p>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    生日
                  </label>
                  <input
                    type="date"
                    value={form.birth_date}
                    onChange={(e) => updateField('birth_date', e.target.value)}
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    緊急聯絡人姓名
                  </label>
                  <input
                    type="text"
                    value={form.emergency_contact_name}
                    onChange={(e) => updateField('emergency_contact_name', e.target.value)}
                    className="input-field"
                    placeholder="緊急聯絡人"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    緊急聯絡人電話
                  </label>
                  <input
                    type="tel"
                    value={form.emergency_contact_phone}
                    onChange={(e) => updateField('emergency_contact_phone', e.target.value)}
                    className="input-field"
                    placeholder="緊急聯絡人電話"
                  />
                </div>
              </>
            )}

            {/* Teacher-specific fields */}
            {role === 'teacher' && (
              <>
                <hr className="border-gray-200" />
                <p className="text-xs text-gray-500">教師資料（選填）</p>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    自我介紹
                  </label>
                  <textarea
                    value={form.bio}
                    onChange={(e) => updateField('bio', e.target.value)}
                    className="input-field"
                    rows={3}
                    placeholder="簡述您的教學經歷與專長"
                  />
                </div>
              </>
            )}

            {/* Employee-specific fields */}
            {role === 'employee' && (
              <>
                <hr className="border-gray-200" />
                <p className="text-xs text-gray-500">員工資料</p>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    員工類型 <span className="text-red-500">*</span>
                  </label>
                  <select
                    value={form.employee_type}
                    onChange={(e) => updateField('employee_type', e.target.value)}
                    className="input-field"
                    required
                  >
                    <option value="">請選擇</option>
                    {EMPLOYEE_TYPES.map((t) => (
                      <option key={t.value} value={t.value}>
                        {t.label}
                      </option>
                    ))}
                  </select>
                </div>
              </>
            )}

            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? '註冊中...' : '註冊'}
            </button>

            <p className="text-center text-sm text-gray-500">
              已有帳號？{' '}
              <Link href="/login" className="text-blue-600 hover:underline">
                前往登入
              </Link>
            </p>
          </form>
        )}
      </div>
    </div>
  )
}

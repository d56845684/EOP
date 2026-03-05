'use client'

import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '@/lib/hooks/useAuth'
import { accountsApi, AccountInfo, PageInfo, UserPageOverride } from '@/lib/api/accounts'
import { Search, Pencil, Shield, Lock, ChevronLeft, ChevronRight, X, CheckCircle, XCircle } from 'lucide-react'
import DashboardLayout from '@/components/DashboardLayout'

const ROLES = ['admin', 'employee', 'teacher', 'student'] as const
const EMPLOYEE_SUBTYPES = ['admin', 'full_time', 'part_time', 'intern'] as const

const roleLabels: Record<string, string> = {
  admin: '管理員',
  employee: '員工',
  teacher: '教師',
  student: '學生',
}

const subtypeLabels: Record<string, string> = {
  admin: '管理員',
  full_time: '正式員工',
  part_time: '兼職員工',
  intern: '工讀生',
}

const roleBadgeColors: Record<string, string> = {
  admin: 'bg-red-100 text-red-700',
  employee: 'bg-blue-100 text-blue-700',
  teacher: 'bg-green-100 text-green-700',
  student: 'bg-yellow-100 text-yellow-700',
}

export default function AccountsPage() {
  const { user, profile } = useAuth()

  const [accounts, setAccounts] = useState<AccountInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [filterRole, setFilterRole] = useState('')
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [total, setTotal] = useState(0)
  const perPage = 20

  // Edit modal
  const [showEditModal, setShowEditModal] = useState(false)
  const [editingAccount, setEditingAccount] = useState<AccountInfo | null>(null)
  const [editRole, setEditRole] = useState('')
  const [editSubtype, setEditSubtype] = useState('')
  const [editIsActive, setEditIsActive] = useState(true)
  const [editSaving, setEditSaving] = useState(false)
  const [editError, setEditError] = useState<string | null>(null)

  // Permission modal
  const [showPermModal, setShowPermModal] = useState(false)
  const [permAccount, setPermAccount] = useState<AccountInfo | null>(null)
  const [allPages, setAllPages] = useState<PageInfo[]>([])
  const [rolePageIds, setRolePageIds] = useState<Set<string>>(new Set())
  const [overrides, setOverrides] = useState<Map<string, 'grant' | 'revoke'>>(new Map())
  const [permSaving, setPermSaving] = useState(false)
  const [permError, setPermError] = useState<string | null>(null)

  const fetchAccounts = useCallback(async () => {
    setLoading(true)
    setError(null)
    const { data, error: err } = await accountsApi.list({
      page,
      per_page: perPage,
      role: filterRole || undefined,
      search: searchTerm || undefined,
    })
    if (err) {
      setError(err.message)
    } else if (data) {
      setAccounts(data.data)
      setTotal(data.total)
      setTotalPages(data.total_pages)
    }
    setLoading(false)
  }, [page, perPage, filterRole, searchTerm])

  useEffect(() => {
    fetchAccounts()
  }, [fetchAccounts])

  // Reset page when filters change
  useEffect(() => {
    setPage(1)
  }, [filterRole, searchTerm])

  // ===== Edit Modal =====
  const openEditModal = (account: AccountInfo) => {
    setEditingAccount(account)
    setEditRole(account.role)
    setEditSubtype(account.employee_subtype || '')
    setEditIsActive(account.is_active)
    setEditError(null)
    setShowEditModal(true)
  }

  const handleEditSave = async () => {
    if (!editingAccount) return
    setEditSaving(true)
    setEditError(null)

    const updateData: any = {}
    if (editRole !== editingAccount.role) updateData.role = editRole
    if (editSubtype !== (editingAccount.employee_subtype || '')) updateData.employee_subtype = editSubtype || null
    if (editIsActive !== editingAccount.is_active) updateData.is_active = editIsActive

    if (Object.keys(updateData).length === 0) {
      setShowEditModal(false)
      setEditSaving(false)
      return
    }

    const { error: err } = await accountsApi.update(editingAccount.id, updateData)
    if (err) {
      setEditError(err.message)
    } else {
      setShowEditModal(false)
      fetchAccounts()
    }
    setEditSaving(false)
  }

  // ===== Permission Modal =====
  const openPermModal = async (account: AccountInfo) => {
    setPermAccount(account)
    setPermError(null)
    setPermSaving(false)
    setShowPermModal(true)

    // Load all pages + role defaults + user overrides in parallel
    const [pagesRes, rolePagesRes, overridesRes] = await Promise.all([
      accountsApi.getAllPages(),
      accountsApi.getRolePages(account.role),
      accountsApi.getUserOverrides(account.id),
    ])

    if (pagesRes.data) {
      setAllPages(pagesRes.data.filter(p => p.is_active))
    }
    if (rolePagesRes.data) {
      setRolePageIds(new Set(rolePagesRes.data.map(p => p.id)))
    }
    if (overridesRes.data) {
      const m = new Map<string, 'grant' | 'revoke'>()
      overridesRes.data.forEach(o => m.set(o.page_id, o.access_type))
      setOverrides(m)
    }
  }

  const togglePageOverride = (pageId: string) => {
    const isRoleDefault = rolePageIds.has(pageId)
    const currentOverride = overrides.get(pageId)

    const newOverrides = new Map(overrides)

    if (isRoleDefault) {
      // Role default: ON -> cycle: no override (on) -> revoke (off) -> back to no override
      if (!currentOverride) {
        newOverrides.set(pageId, 'revoke')
      } else {
        newOverrides.delete(pageId)
      }
    } else {
      // Not role default: OFF -> cycle: no override (off) -> grant (on) -> back to no override
      if (!currentOverride) {
        newOverrides.set(pageId, 'grant')
      } else {
        newOverrides.delete(pageId)
      }
    }

    setOverrides(newOverrides)
  }

  const getPageStatus = (pageId: string): 'role-default' | 'granted' | 'revoked' | 'off' => {
    const isRoleDefault = rolePageIds.has(pageId)
    const override = overrides.get(pageId)

    if (override === 'grant') return 'granted'
    if (override === 'revoke') return 'revoked'
    if (isRoleDefault) return 'role-default'
    return 'off'
  }

  const handlePermSave = async () => {
    if (!permAccount) return
    setPermSaving(true)
    setPermError(null)

    const overrideEntries = Array.from(overrides.entries()).map(([page_id, access_type]) => ({
      page_id,
      access_type,
    }))

    const { error: err } = await accountsApi.setUserOverrides(permAccount.id, overrideEntries)
    if (err) {
      setPermError(err.message)
    } else {
      setShowPermModal(false)
    }
    setPermSaving(false)
  }

  // Group pages by parent_key
  const groupedPages = allPages.reduce((acc, page) => {
    const group = page.parent_key || '_root'
    if (!acc[group]) acc[group] = []
    acc[group].push(page)
    return acc
  }, {} as Record<string, PageInfo[]>)

  return (
    <DashboardLayout>
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-gray-900">帳號管理</h1>
          <span className="text-sm text-gray-500">共 {total} 個帳號</span>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-3 mb-4">
          <div className="relative flex-1 min-w-[200px] max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="搜尋 email 或名稱..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <select
            value={filterRole}
            onChange={(e) => setFilterRole(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="">全部角色</option>
            {ROLES.map(r => (
              <option key={r} value={r}>{roleLabels[r]}</option>
            ))}
          </select>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">{error}</div>
        )}

        {/* Table */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">名稱</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">角色</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">員工類型</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">狀態</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {loading ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                      <div className="flex items-center justify-center gap-2">
                        <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600" />
                        載入中...
                      </div>
                    </td>
                  </tr>
                ) : accounts.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-gray-500">沒有找到帳號</td>
                  </tr>
                ) : (
                  accounts.map(account => (
                    <tr key={account.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm text-gray-900">
                        <div className="flex items-center gap-1.5">
                          {account.is_protected && <Lock className="w-3.5 h-3.5 text-amber-500 flex-shrink-0" />}
                          <span className="truncate max-w-[200px]">{account.email}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-700">{account.name || '-'}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-block px-2 py-0.5 text-xs font-medium rounded ${roleBadgeColors[account.role] || 'bg-gray-100 text-gray-700'}`}>
                          {roleLabels[account.role] || account.role}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-700">
                        {account.employee_subtype ? subtypeLabels[account.employee_subtype] || account.employee_subtype : '-'}
                      </td>
                      <td className="px-4 py-3">
                        {account.is_active ? (
                          <span className="inline-flex items-center gap-1 text-xs text-green-700">
                            <CheckCircle className="w-3.5 h-3.5" /> 啟用
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-xs text-red-600">
                            <XCircle className="w-3.5 h-3.5" /> 停用
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {account.is_protected ? (
                          <span className="text-xs text-gray-400">受保護</span>
                        ) : (
                          <div className="flex items-center gap-1">
                            <button
                              onClick={() => openEditModal(account)}
                              className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                              title="編輯帳號"
                            >
                              <Pencil className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => openPermModal(account)}
                              className="p-1.5 text-gray-400 hover:text-purple-600 hover:bg-purple-50 rounded-lg transition-colors"
                              title="頁面權限"
                            >
                              <Shield className="w-4 h-4" />
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200">
              <span className="text-sm text-gray-500">第 {page} / {totalPages} 頁</span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="p-1.5 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  className="p-1.5 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Edit Modal */}
        {showEditModal && editingAccount && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 m-4">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">編輯帳號</h2>
                <button onClick={() => setShowEditModal(false)} className="p-1 hover:bg-gray-100 rounded-lg">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="text-sm text-gray-500 mb-4">{editingAccount.email}</div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">角色</label>
                  <select
                    value={editRole}
                    onChange={(e) => setEditRole(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    {ROLES.map(r => (
                      <option key={r} value={r}>{roleLabels[r]}</option>
                    ))}
                  </select>
                </div>

                {(editRole === 'admin' || editRole === 'employee') && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">員工子類型</label>
                    <select
                      value={editSubtype}
                      onChange={(e) => setEditSubtype(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="">未設定</option>
                      {EMPLOYEE_SUBTYPES.map(s => (
                        <option key={s} value={s}>{subtypeLabels[s]}</option>
                      ))}
                    </select>
                  </div>
                )}

                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="editIsActive"
                    checked={editIsActive}
                    onChange={(e) => setEditIsActive(e.target.checked)}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <label htmlFor="editIsActive" className="text-sm text-gray-700">帳號啟用</label>
                </div>
              </div>

              {editError && (
                <div className="mt-3 p-3 bg-red-50 text-red-700 rounded-lg text-sm">{editError}</div>
              )}

              <div className="flex justify-end gap-2 mt-6">
                <button
                  onClick={() => setShowEditModal(false)}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50"
                >
                  取消
                </button>
                <button
                  onClick={handleEditSave}
                  disabled={editSaving}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
                >
                  {editSaving ? '儲存中...' : '儲存'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Permission Modal */}
        {showPermModal && permAccount && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6 m-4 max-h-[80vh] flex flex-col">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-lg font-semibold">頁面權限</h2>
                  <p className="text-sm text-gray-500">{permAccount.email} ({roleLabels[permAccount.role]})</p>
                </div>
                <button onClick={() => setShowPermModal(false)} className="p-1 hover:bg-gray-100 rounded-lg">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="text-xs text-gray-500 mb-3 flex items-center gap-3 flex-wrap">
                <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-gray-200 inline-block" /> 角色預設</span>
                <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-green-200 inline-block" /> 個人授權</span>
                <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-red-200 inline-block" /> 個人撤銷</span>
              </div>

              <div className="flex-1 overflow-y-auto space-y-4 pr-1">
                {Object.entries(groupedPages).sort().map(([groupKey, pages]) => (
                  <div key={groupKey}>
                    {groupKey !== '_root' && (
                      <div className="text-xs font-medium text-gray-500 uppercase mb-1.5">{groupKey}</div>
                    )}
                    <div className="space-y-1">
                      {pages.map(pg => {
                        const status = getPageStatus(pg.id)
                        const isChecked = status === 'role-default' || status === 'granted'
                        let bgClass = ''
                        if (status === 'role-default') bgClass = 'bg-gray-50'
                        else if (status === 'granted') bgClass = 'bg-green-50'
                        else if (status === 'revoked') bgClass = 'bg-red-50'

                        return (
                          <label
                            key={pg.id}
                            className={`flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer hover:bg-gray-100 transition-colors ${bgClass}`}
                          >
                            <input
                              type="checkbox"
                              checked={isChecked}
                              onChange={() => togglePageOverride(pg.id)}
                              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                            />
                            <div className="flex-1 min-w-0">
                              <div className="text-sm font-medium text-gray-800">{pg.name}</div>
                              <div className="text-xs text-gray-400">{pg.key}</div>
                            </div>
                            {status === 'role-default' && (
                              <span className="text-[10px] text-gray-400 bg-gray-200 px-1.5 py-0.5 rounded">預設</span>
                            )}
                            {status === 'granted' && (
                              <span className="text-[10px] text-green-600 bg-green-200 px-1.5 py-0.5 rounded">授權</span>
                            )}
                            {status === 'revoked' && (
                              <span className="text-[10px] text-red-600 bg-red-200 px-1.5 py-0.5 rounded">撤銷</span>
                            )}
                          </label>
                        )
                      })}
                    </div>
                  </div>
                ))}
              </div>

              {permError && (
                <div className="mt-3 p-3 bg-red-50 text-red-700 rounded-lg text-sm">{permError}</div>
              )}

              <div className="flex justify-end gap-2 mt-4 pt-4 border-t border-gray-200">
                <button
                  onClick={() => setShowPermModal(false)}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50"
                >
                  取消
                </button>
                <button
                  onClick={handlePermSave}
                  disabled={permSaving}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
                >
                  {permSaving ? '儲存中...' : '儲存權限'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}

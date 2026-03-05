'use client'

import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '@/lib/hooks/useAuth'
import { accountsApi, PageInfo, RoleInfo } from '@/lib/api/accounts'
import { Pencil, X, Save, Shield, Plus, Trash2, Lock } from 'lucide-react'
import DashboardLayout from '@/components/DashboardLayout'

const roleBadgeColors: Record<string, string> = {
  admin: 'bg-red-100 text-red-700',
  employee: 'bg-blue-100 text-blue-700',
  teacher: 'bg-green-100 text-green-700',
  student: 'bg-yellow-100 text-yellow-700',
}

export default function RolePermissionsPage() {
  const { user, profile } = useAuth()

  const [roles, setRoles] = useState<RoleInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Create modal
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [createRole, setCreateRole] = useState('')
  const [createName, setCreateName] = useState('')
  const [createDesc, setCreateDesc] = useState('')
  const [createSaving, setCreateSaving] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)

  // Edit name modal
  const [editingRoleInfo, setEditingRoleInfo] = useState<RoleInfo | null>(null)
  const [editName, setEditName] = useState('')
  const [editDesc, setEditDesc] = useState('')
  const [editSaving, setEditSaving] = useState(false)
  const [editError, setEditError] = useState<string | null>(null)

  // Permission modal
  const [permRole, setPermRole] = useState<RoleInfo | null>(null)
  const [allPages, setAllPages] = useState<PageInfo[]>([])
  const [checkedIds, setCheckedIds] = useState<Set<string>>(new Set())
  const [savedIds, setSavedIds] = useState<Set<string>>(new Set())
  const [modalLoading, setModalLoading] = useState(false)
  const [permSaving, setPermSaving] = useState(false)
  const [permError, setPermError] = useState<string | null>(null)
  const [permSuccess, setPermSuccess] = useState<string | null>(null)

  // Delete confirm
  const [deleteTarget, setDeleteTarget] = useState<RoleInfo | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const hasPermChanges = (() => {
    if (checkedIds.size !== savedIds.size) return true
    for (const id of checkedIds) {
      if (!savedIds.has(id)) return true
    }
    return false
  })()

  const fetchRoles = useCallback(async () => {
    setLoading(true)
    setError(null)
    const { data, error: err } = await accountsApi.getRoles()
    if (err) setError(err.message)
    else if (data) setRoles(data)
    setLoading(false)
  }, [])

  useEffect(() => { fetchRoles() }, [fetchRoles])

  // ===== Create =====
  const handleCreate = async () => {
    setCreateSaving(true)
    setCreateError(null)
    const { error: err } = await accountsApi.createRole({
      role: createRole, name: createName, description: createDesc || undefined,
    })
    if (err) {
      setCreateError(err.message)
    } else {
      setShowCreateModal(false)
      setCreateRole('')
      setCreateName('')
      setCreateDesc('')
      fetchRoles()
    }
    setCreateSaving(false)
  }

  // ===== Edit name =====
  const openEditInfo = (role: RoleInfo) => {
    setEditingRoleInfo(role)
    setEditName(role.name)
    setEditDesc(role.description || '')
    setEditError(null)
  }

  const handleEditSave = async () => {
    if (!editingRoleInfo) return
    setEditSaving(true)
    setEditError(null)
    const { error: err } = await accountsApi.updateRole(editingRoleInfo.role, {
      name: editName, description: editDesc || undefined,
    })
    if (err) {
      setEditError(err.message)
    } else {
      setEditingRoleInfo(null)
      fetchRoles()
    }
    setEditSaving(false)
  }

  // ===== Delete =====
  const handleDelete = async () => {
    if (!deleteTarget) return
    setDeleting(true)
    setDeleteError(null)
    const { error: err } = await accountsApi.deleteRole(deleteTarget.role)
    if (err) {
      setDeleteError(err.message)
    } else {
      setDeleteTarget(null)
      fetchRoles()
    }
    setDeleting(false)
  }

  // ===== Permission Modal =====
  const openPermModal = async (role: RoleInfo) => {
    setPermRole(role)
    setPermError(null)
    setPermSuccess(null)
    setModalLoading(true)

    const [pagesRes, rolePagesRes] = await Promise.all([
      accountsApi.getAllPages(),
      accountsApi.getRolePages(role.role),
    ])

    if (pagesRes.data) setAllPages(pagesRes.data.filter(p => p.is_active))
    if (rolePagesRes.data) {
      const ids = new Set(rolePagesRes.data.map(p => p.id))
      setCheckedIds(ids)
      setSavedIds(new Set(ids))
    }
    setModalLoading(false)
  }

  const togglePage = (pageId: string) => {
    setCheckedIds(prev => {
      const next = new Set(prev)
      if (next.has(pageId)) next.delete(pageId)
      else next.add(pageId)
      return next
    })
  }

  const toggleGroup = (pageIds: string[]) => {
    setCheckedIds(prev => {
      const next = new Set(prev)
      const allChecked = pageIds.every(id => next.has(id))
      if (allChecked) pageIds.forEach(id => next.delete(id))
      else pageIds.forEach(id => next.add(id))
      return next
    })
  }

  const handlePermSave = async () => {
    if (!permRole) return
    setPermSaving(true)
    setPermError(null)
    setPermSuccess(null)

    const { error: err } = await accountsApi.setRolePages(permRole.role, Array.from(checkedIds))
    if (err) {
      setPermError(err.message)
    } else {
      setSavedIds(new Set(checkedIds))
      setPermSuccess('儲存成功')
      setRoles(prev => prev.map(r => r.role === permRole.role ? { ...r, page_count: checkedIds.size } : r))
      setTimeout(() => setPermSuccess(null), 3000)
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
          <h1 className="text-2xl font-bold text-gray-900">角色權限管理</h1>
          <button
            onClick={() => { setShowCreateModal(true); setCreateError(null) }}
            className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
          >
            <Plus className="w-4 h-4" />
            新增角色
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">{error}</div>
        )}

        {/* Roles Table */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">角色 Key</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">顯示名稱</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">說明</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">頁面數</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {loading ? (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-gray-500">
                    <div className="flex items-center justify-center gap-2">
                      <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600" />
                      載入中...
                    </div>
                  </td>
                </tr>
              ) : roles.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-gray-500">尚無角色</td>
                </tr>
              ) : (
                roles.map(role => (
                  <tr key={role.role} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-1.5">
                        <span className={`inline-block px-2.5 py-1 text-xs font-medium rounded ${roleBadgeColors[role.role] || 'bg-purple-100 text-purple-700'}`}>
                          {role.role}
                        </span>
                        {role.is_system && <Lock className="w-3.5 h-3.5 text-gray-400" title="系統內建" />}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">{role.name}</td>
                    <td className="px-6 py-4 text-sm text-gray-500 max-w-[200px] truncate">{role.description || '-'}</td>
                    <td className="px-6 py-4">
                      <span className="inline-flex items-center gap-1.5 text-sm text-gray-700">
                        <Shield className="w-4 h-4 text-gray-400" />
                        {role.page_count}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => openEditInfo(role)}
                          className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                          title="編輯名稱"
                        >
                          <Pencil className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => openPermModal(role)}
                          className="p-1.5 text-gray-400 hover:text-purple-600 hover:bg-purple-50 rounded-lg transition-colors"
                          title="編輯頁面權限"
                        >
                          <Shield className="w-4 h-4" />
                        </button>
                        {!role.is_system && (
                          <button
                            onClick={() => { setDeleteTarget(role); setDeleteError(null) }}
                            className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                            title="刪除角色"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* ===== Create Modal ===== */}
        {showCreateModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 m-4">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">新增角色</h2>
                <button onClick={() => setShowCreateModal(false)} className="p-1 hover:bg-gray-100 rounded-lg">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">角色 Key（英文小寫+底線）</label>
                  <input
                    type="text"
                    value={createRole}
                    onChange={(e) => setCreateRole(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ''))}
                    placeholder="例: assistant, intern"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">顯示名稱</label>
                  <input
                    type="text"
                    value={createName}
                    onChange={(e) => setCreateName(e.target.value)}
                    placeholder="例: 助教"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">說明（選填）</label>
                  <input
                    type="text"
                    value={createDesc}
                    onChange={(e) => setCreateDesc(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>

              {createError && (
                <div className="mt-3 p-3 bg-red-50 text-red-700 rounded-lg text-sm">{createError}</div>
              )}

              <div className="flex justify-end gap-2 mt-6">
                <button onClick={() => setShowCreateModal(false)} className="px-4 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50">取消</button>
                <button
                  onClick={handleCreate}
                  disabled={createSaving || !createRole || !createName}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
                >
                  {createSaving ? '建立中...' : '建立'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ===== Edit Name Modal ===== */}
        {editingRoleInfo && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 m-4">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">編輯角色</h2>
                <button onClick={() => setEditingRoleInfo(null)} className="p-1 hover:bg-gray-100 rounded-lg">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="text-sm text-gray-500 mb-4">
                Key: <span className="font-mono bg-gray-100 px-1.5 py-0.5 rounded">{editingRoleInfo.role}</span>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">顯示名稱</label>
                  <input
                    type="text"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">說明</label>
                  <input
                    type="text"
                    value={editDesc}
                    onChange={(e) => setEditDesc(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>

              {editError && (
                <div className="mt-3 p-3 bg-red-50 text-red-700 rounded-lg text-sm">{editError}</div>
              )}

              <div className="flex justify-end gap-2 mt-6">
                <button onClick={() => setEditingRoleInfo(null)} className="px-4 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50">取消</button>
                <button
                  onClick={handleEditSave}
                  disabled={editSaving || !editName}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
                >
                  {editSaving ? '儲存中...' : '儲存'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ===== Delete Confirm Modal ===== */}
        {deleteTarget && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6 m-4">
              <h2 className="text-lg font-semibold mb-2">確認刪除角色</h2>
              <p className="text-sm text-gray-600 mb-4">
                確定要刪除角色 <span className="font-semibold">{deleteTarget.name}</span>（{deleteTarget.role}）嗎？此操作無法復原。
              </p>

              {deleteError && (
                <div className="mb-3 p-3 bg-red-50 text-red-700 rounded-lg text-sm">{deleteError}</div>
              )}

              <div className="flex justify-end gap-2">
                <button onClick={() => setDeleteTarget(null)} className="px-4 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50">取消</button>
                <button
                  onClick={handleDelete}
                  disabled={deleting}
                  className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm hover:bg-red-700 disabled:opacity-50"
                >
                  {deleting ? '刪除中...' : '刪除'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ===== Permission Modal ===== */}
        {permRole && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl p-6 m-4 max-h-[85vh] flex flex-col">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <h2 className="text-lg font-semibold">編輯頁面權限</h2>
                  <span className={`inline-block px-2.5 py-1 text-xs font-medium rounded ${roleBadgeColors[permRole.role] || 'bg-purple-100 text-purple-700'}`}>
                    {permRole.name}
                  </span>
                </div>
                <button onClick={() => setPermRole(null)} className="p-1 hover:bg-gray-100 rounded-lg">
                  <X className="w-5 h-5" />
                </button>
              </div>

              {permError && <div className="mb-3 p-3 bg-red-50 text-red-700 rounded-lg text-sm">{permError}</div>}
              {permSuccess && <div className="mb-3 p-3 bg-green-50 text-green-700 rounded-lg text-sm">{permSuccess}</div>}

              <div className="flex-1 overflow-y-auto pr-1">
                {modalLoading ? (
                  <div className="flex items-center justify-center py-8 gap-2 text-gray-500">
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600" />
                    載入中...
                  </div>
                ) : (
                  <div className="space-y-5">
                    {Object.entries(groupedPages).sort().map(([groupKey, pages]) => {
                      const groupPageIds = pages.map(p => p.id)
                      const allGroupChecked = groupPageIds.every(id => checkedIds.has(id))
                      const someGroupChecked = groupPageIds.some(id => checkedIds.has(id))

                      return (
                        <div key={groupKey}>
                          <div className="flex items-center gap-2 mb-2 pb-2 border-b border-gray-100">
                            <input
                              type="checkbox"
                              checked={allGroupChecked}
                              ref={(el) => { if (el) el.indeterminate = someGroupChecked && !allGroupChecked }}
                              onChange={() => toggleGroup(groupPageIds)}
                              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                            />
                            <span className="text-sm font-semibold text-gray-700 uppercase">
                              {groupKey === '_root' ? '其他' : groupKey}
                            </span>
                            <span className="text-xs text-gray-400">
                              ({groupPageIds.filter(id => checkedIds.has(id)).length}/{groupPageIds.length})
                            </span>
                          </div>
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-1 pl-6">
                            {pages.map(pg => (
                              <label key={pg.id} className="flex items-center gap-2.5 px-3 py-2 rounded-lg cursor-pointer hover:bg-gray-50 transition-colors">
                                <input
                                  type="checkbox"
                                  checked={checkedIds.has(pg.id)}
                                  onChange={() => togglePage(pg.id)}
                                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                />
                                <div className="min-w-0">
                                  <div className="text-sm text-gray-800">{pg.name}</div>
                                  <div className="text-xs text-gray-400">{pg.key}</div>
                                </div>
                              </label>
                            ))}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>

              <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-200">
                <div className="text-sm text-gray-500">
                  已選 {checkedIds.size} 個頁面
                  {hasPermChanges && <span className="ml-2 text-amber-600">（有未儲存的變更）</span>}
                </div>
                <div className="flex items-center gap-2">
                  <button onClick={() => setPermRole(null)} className="px-4 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50">取消</button>
                  <button
                    onClick={handlePermSave}
                    disabled={permSaving || !hasPermChanges}
                    className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Save className="w-4 h-4" />
                    {permSaving ? '儲存中...' : '儲存'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}

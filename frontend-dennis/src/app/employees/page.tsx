'use client'

import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '@/lib/hooks/useAuth'
import { employeesApi, Employee, CreateEmployeeData, UpdateEmployeeData } from '@/lib/api/employees'
import { invitesApi } from '@/lib/api/invites'
import { Plus, Pencil, Trash2, Search, X, Users, CheckCircle, XCircle, Mail, Phone, UserPlus, Copy, Check } from 'lucide-react'
import DashboardLayout from '@/components/DashboardLayout'

const employeeTypeLabels: Record<string, string> = {
    admin: '管理員',
    full_time: '全職',
    part_time: '兼職',
    intern: '實習',
}

export default function EmployeesPage() {
    const { user, profile } = useAuth()

    const [employees, setEmployees] = useState<Employee[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [searchTerm, setSearchTerm] = useState('')
    const [filterActive, setFilterActive] = useState<boolean | undefined>(undefined)
    const [filterType, setFilterType] = useState('')

    const [page, setPage] = useState(1)
    const [totalPages, setTotalPages] = useState(1)
    const [total, setTotal] = useState(0)
    const perPage = 10

    const [showModal, setShowModal] = useState(false)
    const [modalMode, setModalMode] = useState<'create' | 'edit'>('create')
    const [editingEmployee, setEditingEmployee] = useState<Employee | null>(null)
    const [formData, setFormData] = useState<CreateEmployeeData>({
        employee_no: '', employee_type: 'full_time', name: '', email: '',
        phone: '', address: '', hire_date: '', is_active: true,
    })
    const [formError, setFormError] = useState<string | null>(null)
    const [submitting, setSubmitting] = useState(false)

    const [deleteConfirm, setDeleteConfirm] = useState<Employee | null>(null)
    const [deleting, setDeleting] = useState(false)

    // 邀請連結
    const [inviteUrl, setInviteUrl] = useState<string | null>(null)
    const [inviteEmployee, setInviteEmployee] = useState<Employee | null>(null)
    const [inviteLoading, setInviteLoading] = useState(false)
    const [inviteError, setInviteError] = useState<string | null>(null)
    const [copied, setCopied] = useState(false)

    const isAdmin = profile?.role === 'admin'

    const fetchEmployees = useCallback(async () => {
        setLoading(true)
        setError(null)
        const { data, error } = await employeesApi.list({
            page, per_page: perPage,
            search: searchTerm || undefined,
            is_active: filterActive,
            employee_type: filterType || undefined,
        })
        if (error) {
            setError(error.message)
        } else if (data) {
            setEmployees(data.data)
            setTotalPages(data.total_pages)
            setTotal(data.total)
        }
        setLoading(false)
    }, [page, searchTerm, filterActive, filterType])

    useEffect(() => {
        if (user) fetchEmployees()
    }, [user, fetchEmployees])

    useEffect(() => {
        const timer = setTimeout(() => setPage(1), 300)
        return () => clearTimeout(timer)
    }, [searchTerm])

    const openCreateModal = () => {
        setModalMode('create')
        setEditingEmployee(null)
        setFormData({
            employee_no: '', employee_type: 'full_time', name: '', email: '',
            phone: '', address: '', hire_date: '', is_active: true,
        })
        setFormError(null)
        setShowModal(true)
    }

    const openEditModal = (emp: Employee) => {
        setModalMode('edit')
        setEditingEmployee(emp)
        setFormData({
            employee_no: emp.employee_no,
            employee_type: emp.employee_type,
            name: emp.name,
            email: emp.email,
            phone: emp.phone || '',
            address: emp.address || '',
            hire_date: emp.hire_date || '',
            termination_date: emp.termination_date || undefined,
            is_active: emp.is_active,
        })
        setFormError(null)
        setShowModal(true)
    }

    const closeModal = () => { setShowModal(false); setEditingEmployee(null); setFormError(null) }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setFormError(null)
        setSubmitting(true)
        try {
            if (modalMode === 'create') {
                const submitData = { ...formData }
                if (!submitData.phone) delete (submitData as any).phone
                if (!submitData.address) delete (submitData as any).address
                if (!submitData.termination_date) delete (submitData as any).termination_date
                const { error } = await employeesApi.create(submitData)
                if (error) { setFormError(error.message) } else { closeModal(); fetchEmployees() }
            } else if (editingEmployee) {
                const updateData: UpdateEmployeeData = {}
                if (formData.name !== editingEmployee.name) updateData.name = formData.name
                if (formData.employee_type !== editingEmployee.employee_type) updateData.employee_type = formData.employee_type
                if (formData.email !== editingEmployee.email) updateData.email = formData.email
                if ((formData.phone || '') !== (editingEmployee.phone || '')) updateData.phone = formData.phone || undefined
                if ((formData.address || '') !== (editingEmployee.address || '')) updateData.address = formData.address || undefined
                if ((formData.hire_date || '') !== (editingEmployee.hire_date || '')) updateData.hire_date = formData.hire_date || undefined
                if ((formData.termination_date || '') !== (editingEmployee.termination_date || '')) updateData.termination_date = formData.termination_date || undefined
                if (formData.is_active !== editingEmployee.is_active) updateData.is_active = formData.is_active
                const { error } = await employeesApi.update(editingEmployee.id, updateData)
                if (error) { setFormError(error.message) } else { closeModal(); fetchEmployees() }
            }
        } finally { setSubmitting(false) }
    }

    const handleDelete = async () => {
        if (!deleteConfirm) return
        setDeleting(true)
        const { error } = await employeesApi.delete(deleteConfirm.id)
        if (error) { setError(error.message) } else { setDeleteConfirm(null); fetchEmployees() }
        setDeleting(false)
    }

    // === 邀請連結 ===
    const handleGenerateInvite = async (emp: Employee) => {
        setInviteEmployee(emp)
        setInviteUrl(null)
        setInviteError(null)
        setInviteLoading(true)
        setCopied(false)

        const { data, error } = await invitesApi.generate('employee', emp.id)
        if (error) {
            setInviteError(error.message)
        } else if (data) {
            setInviteUrl(data.invite_url)
        }
        setInviteLoading(false)
    }

    const closeInviteModal = () => {
        setInviteEmployee(null)
        setInviteUrl(null)
        setInviteError(null)
        setCopied(false)
    }

    const handleCopyUrl = async () => {
        if (!inviteUrl) return
        try {
            await navigator.clipboard.writeText(inviteUrl)
            setCopied(true)
            setTimeout(() => setCopied(false), 2000)
        } catch {
            const textArea = document.createElement('textarea')
            textArea.value = inviteUrl
            document.body.appendChild(textArea)
            textArea.select()
            document.execCommand('copy')
            document.body.removeChild(textArea)
            setCopied(true)
            setTimeout(() => setCopied(false), 2000)
        }
    }

    return (
        <DashboardLayout>
            <div className="py-8">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    {/* Header */}
                    <div className="mb-8">
                        <div className="flex items-center justify-between">
                            <div>
                                <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
                                    <Users className="w-8 h-8 text-blue-600" />
                                    員工管理
                                </h1>
                                <p className="mt-2 text-gray-600">共 {total} 位員工</p>
                            </div>
                            {isAdmin && (
                                <button onClick={openCreateModal} className="btn-primary flex items-center gap-2">
                                    <Plus className="w-5 h-5" /> 新增員工
                                </button>
                            )}
                        </div>
                    </div>

                    {/* Filters */}
                    <div className="card mb-6">
                        <div className="flex flex-col sm:flex-row gap-4">
                            <div className="flex-1 relative">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                                <input type="text" placeholder="搜尋員工編號、姓名或 Email..."
                                    value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)}
                                    className="input-field pl-10" />
                                {searchTerm && (
                                    <button onClick={() => setSearchTerm('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                                        <X className="w-5 h-5" />
                                    </button>
                                )}
                            </div>
                            <select value={filterActive === undefined ? 'all' : filterActive ? 'active' : 'inactive'}
                                onChange={(e) => { setFilterActive(e.target.value === 'all' ? undefined : e.target.value === 'active'); setPage(1) }}
                                className="input-field w-full sm:w-40">
                                <option value="all">全部狀態</option>
                                <option value="active">啟用中</option>
                                <option value="inactive">已停用</option>
                            </select>
                            <select value={filterType}
                                onChange={(e) => { setFilterType(e.target.value); setPage(1) }}
                                className="input-field w-full sm:w-40">
                                <option value="">全部類型</option>
                                <option value="admin">管理員</option>
                                <option value="full_time">全職</option>
                                <option value="part_time">兼職</option>
                                <option value="intern">實習</option>
                            </select>
                        </div>
                    </div>

                    {error && <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">{error}</div>}

                    {/* Table */}
                    {loading ? (
                        <div className="flex justify-center py-12"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div></div>
                    ) : employees.length === 0 ? (
                        <div className="card text-center py-12">
                            <Users className="w-16 h-16 mx-auto text-gray-300 mb-4" />
                            <h3 className="text-lg font-medium text-gray-900 mb-2">沒有找到員工</h3>
                            <p className="text-gray-500">{searchTerm ? '請嘗試其他搜尋條件' : '點擊「新增員工」建立第一位員工'}</p>
                        </div>
                    ) : (
                        <div className="card overflow-x-auto">
                            <table className="min-w-full divide-y divide-gray-200">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">編號</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">姓名</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">聯絡方式</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">類型</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">到職日</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">狀態</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">帳號</th>
                                        {isAdmin && <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">操作</th>}
                                    </tr>
                                </thead>
                                <tbody className="bg-white divide-y divide-gray-200">
                                    {employees.map((emp) => (
                                        <tr key={emp.id} className="hover:bg-gray-50">
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <span className="font-mono text-sm bg-gray-100 px-2 py-1 rounded">{emp.employee_no}</span>
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="font-medium text-gray-900">{emp.name}</div>
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="flex flex-col gap-0.5">
                                                    <span className="text-sm text-gray-600 flex items-center gap-1"><Mail className="w-3 h-3" />{emp.email}</span>
                                                    {emp.phone && <span className="text-sm text-gray-500 flex items-center gap-1"><Phone className="w-3 h-3" />{emp.phone}</span>}
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                                                    emp.employee_type === 'admin' ? 'bg-red-100 text-red-800' :
                                                    emp.employee_type === 'full_time' ? 'bg-blue-100 text-blue-800' :
                                                    emp.employee_type === 'part_time' ? 'bg-yellow-100 text-yellow-800' :
                                                    'bg-gray-100 text-gray-800'
                                                }`}>
                                                    {employeeTypeLabels[emp.employee_type] || emp.employee_type}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                                                {emp.hire_date || '-'}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                {emp.is_active ? (
                                                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800"><CheckCircle className="w-3 h-3 mr-1" />啟用中</span>
                                                ) : (
                                                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800"><XCircle className="w-3 h-3 mr-1" />已停用</span>
                                                )}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                {emp.email_verified_at ? (
                                                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800"><CheckCircle className="w-3 h-3 mr-1" />已驗證</span>
                                                ) : (
                                                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800"><XCircle className="w-3 h-3 mr-1" />未驗證</span>
                                                )}
                                            </td>
                                            {isAdmin && (
                                                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                                    {!emp.email_verified_at && (
                                                        <button onClick={() => handleGenerateInvite(emp)} className="text-green-600 hover:text-green-900 mr-4" title="產生邀請連結"><UserPlus className="w-5 h-5" /></button>
                                                    )}
                                                    <button onClick={() => openEditModal(emp)} className="text-blue-600 hover:text-blue-900 mr-4" title="編輯"><Pencil className="w-5 h-5" /></button>
                                                    <button onClick={() => setDeleteConfirm(emp)} className="text-red-600 hover:text-red-900" title="刪除"><Trash2 className="w-5 h-5" /></button>
                                                </td>
                                            )}
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}

                    {/* Pagination */}
                    {totalPages > 1 && (
                        <div className="mt-6 flex items-center justify-between">
                            <div className="text-sm text-gray-500">顯示 {(page - 1) * perPage + 1} - {Math.min(page * perPage, total)} 共 {total} 項</div>
                            <div className="flex gap-2">
                                <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed">上一頁</button>
                                <span className="px-4 py-2 text-gray-600">{page} / {totalPages}</span>
                                <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages} className="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed">下一頁</button>
                            </div>
                        </div>
                    )}
                </div>

                {/* Create/Edit Modal */}
                {showModal && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                        <div className="bg-white rounded-xl shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
                            <div className="p-6">
                                <div className="flex items-center justify-between mb-6">
                                    <h2 className="text-xl font-bold text-gray-900">{modalMode === 'create' ? '新增員工' : '編輯員工'}</h2>
                                    <button onClick={closeModal} className="text-gray-400 hover:text-gray-600"><X className="w-6 h-6" /></button>
                                </div>
                                {formError && <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{formError}</div>}
                                <form onSubmit={handleSubmit} className="space-y-4">
                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">員工編號 <span className="text-red-500">*</span></label>
                                            <input type="text" value={formData.employee_no} onChange={(e) => setFormData({ ...formData, employee_no: e.target.value })}
                                                className="input-field" placeholder="例如：E001" required disabled={modalMode === 'edit'} />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">姓名 <span className="text-red-500">*</span></label>
                                            <input type="text" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                                className="input-field" required />
                                        </div>
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">Email <span className="text-red-500">*</span></label>
                                        <input type="email" value={formData.email} onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                            className="input-field" required />
                                    </div>
                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">電話</label>
                                            <input type="text" value={formData.phone || ''} onChange={(e) => setFormData({ ...formData, phone: e.target.value })} className="input-field" />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">員工類型 <span className="text-red-500">*</span></label>
                                            <select value={formData.employee_type} onChange={(e) => setFormData({ ...formData, employee_type: e.target.value })} className="input-field">
                                                <option value="admin">管理員</option>
                                                <option value="full_time">全職</option>
                                                <option value="part_time">兼職</option>
                                                <option value="intern">實習</option>
                                            </select>
                                        </div>
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">地址</label>
                                        <input type="text" value={formData.address || ''} onChange={(e) => setFormData({ ...formData, address: e.target.value })} className="input-field" />
                                    </div>
                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">到職日 <span className="text-red-500">*</span></label>
                                            <input type="date" value={formData.hire_date} onChange={(e) => setFormData({ ...formData, hire_date: e.target.value })}
                                                className="input-field" required />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">離職日</label>
                                            <input type="date" value={formData.termination_date || ''} onChange={(e) => setFormData({ ...formData, termination_date: e.target.value || undefined })}
                                                className="input-field" />
                                        </div>
                                    </div>
                                    <div className="flex items-end pb-1">
                                        <label className="flex items-center gap-2">
                                            <input type="checkbox" checked={formData.is_active} onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                                                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded" />
                                            <span className="text-sm text-gray-700">啟用</span>
                                        </label>
                                    </div>
                                    <div className="flex gap-3 pt-4">
                                        <button type="button" onClick={closeModal} className="btn-secondary flex-1" disabled={submitting}>取消</button>
                                        <button type="submit" className="btn-primary flex-1" disabled={submitting}>
                                            {submitting ? <span className="flex items-center justify-center"><div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>處理中...</span> : modalMode === 'create' ? '建立' : '儲存'}
                                        </button>
                                    </div>
                                </form>
                            </div>
                        </div>
                    </div>
                )}

                {/* Delete Confirmation */}
                {deleteConfirm && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                        <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
                            <h3 className="text-lg font-bold text-gray-900 mb-2">確認刪除員工</h3>
                            <p className="text-gray-600 mb-6">確定要刪除員工「<span className="font-medium">{deleteConfirm.name}</span>」（{deleteConfirm.employee_no}）嗎？</p>
                            <div className="flex gap-3">
                                <button onClick={() => setDeleteConfirm(null)} className="btn-secondary flex-1" disabled={deleting}>取消</button>
                                <button onClick={handleDelete} className="btn-danger flex-1" disabled={deleting}>
                                    {deleting ? <span className="flex items-center justify-center"><div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>刪除中...</span> : '確認刪除'}
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {/* Invite Modal */}
                {inviteEmployee && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                        <div className="bg-white rounded-xl shadow-xl max-w-lg w-full p-6">
                            <div className="flex items-center justify-between mb-4">
                                <h3 className="text-lg font-bold text-gray-900">邀請連結</h3>
                                <button onClick={closeInviteModal} className="text-gray-400 hover:text-gray-600">
                                    <X className="w-6 h-6" />
                                </button>
                            </div>
                            <p className="text-sm text-gray-600 mb-4">
                                員工：<span className="font-medium">{inviteEmployee.name}</span>（{inviteEmployee.email}）
                            </p>

                            {inviteLoading && (
                                <div className="flex justify-center py-8">
                                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                                </div>
                            )}

                            {inviteError && (
                                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm mb-4">
                                    {inviteError}
                                </div>
                            )}

                            {inviteUrl && (
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">邀請 URL</label>
                                    <div className="flex gap-2">
                                        <input type="text" readOnly value={inviteUrl}
                                            className="input-field flex-1 text-sm bg-gray-50" />
                                        <button onClick={handleCopyUrl}
                                            className={`px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-1 ${copied ? 'bg-green-100 text-green-700' : 'bg-blue-600 text-white hover:bg-blue-700'}`}>
                                            {copied ? <><Check className="w-4 h-4" />已複製</> : <><Copy className="w-4 h-4" />複製</>}
                                        </button>
                                    </div>
                                    <p className="text-xs text-gray-400 mt-2">此連結有效期為 7 天，僅可使用一次</p>
                                </div>
                            )}

                            <div className="flex gap-3 mt-6">
                                <button onClick={closeInviteModal} className="btn-secondary flex-1">關閉</button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </DashboardLayout>
    )
}

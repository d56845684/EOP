'use client'

import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '@/lib/hooks/useAuth'
import {
    zoomApi,
    ZoomAccount,
    CreateZoomAccountData,
    UpdateZoomAccountData,
} from '@/lib/api/zoom'
import { Plus, Pencil, Trash2, X, Video, Zap, CheckCircle, XCircle } from 'lucide-react'
import DashboardLayout from '@/components/DashboardLayout'

export default function ZoomAccountsPage() {
    const { user, profile } = useAuth()

    const [accounts, setAccounts] = useState<ZoomAccount[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    // Pagination
    const [page, setPage] = useState(1)
    const [totalPages, setTotalPages] = useState(1)
    const [total, setTotal] = useState(0)
    const perPage = 20

    // Modal
    const [showModal, setShowModal] = useState(false)
    const [modalMode, setModalMode] = useState<'create' | 'edit'>('create')
    const [editingAccount, setEditingAccount] = useState<ZoomAccount | null>(null)
    const [formData, setFormData] = useState<CreateZoomAccountData>({
        account_name: '',
        zoom_account_id: '',
        zoom_client_id: '',
        zoom_client_secret: '',
        zoom_user_email: '',
        is_active: true,
        notes: '',
    })
    const [formError, setFormError] = useState<string | null>(null)
    const [submitting, setSubmitting] = useState(false)

    // Delete
    const [deleteConfirm, setDeleteConfirm] = useState<ZoomAccount | null>(null)
    const [deleting, setDeleting] = useState(false)

    // Test connection
    const [testingId, setTestingId] = useState<string | null>(null)
    const [testResult, setTestResult] = useState<{ id: string, success: boolean, message: string } | null>(null)

    const isStaff = profile?.role === 'admin' || profile?.role === 'employee'

    const fetchAccounts = useCallback(async () => {
        setLoading(true)
        setError(null)
        const { data, error } = await zoomApi.listAccounts({ page, per_page: perPage })
        if (error) {
            setError(error.message)
        } else if (data) {
            setAccounts(data.data)
            setTotalPages(data.total_pages)
            setTotal(data.total)
        }
        setLoading(false)
    }, [page])

    useEffect(() => {
        if (user) fetchAccounts()
    }, [user, fetchAccounts])

    // === Create / Edit ===
    const openCreateModal = () => {
        setModalMode('create')
        setEditingAccount(null)
        setFormData({
            account_name: '',
            zoom_account_id: '',
            zoom_client_id: '',
            zoom_client_secret: '',
            zoom_user_email: '',
            is_active: true,
            notes: '',
        })
        setFormError(null)
        setShowModal(true)
    }

    const openEditModal = (account: ZoomAccount) => {
        setModalMode('edit')
        setEditingAccount(account)
        setFormData({
            account_name: account.account_name,
            zoom_account_id: account.zoom_account_id,
            zoom_client_id: account.zoom_client_id,
            zoom_client_secret: '',
            zoom_user_email: account.zoom_user_email || '',
            is_active: account.is_active,
            notes: account.notes || '',
        })
        setFormError(null)
        setShowModal(true)
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setFormError(null)
        setSubmitting(true)

        if (modalMode === 'create') {
            const { error } = await zoomApi.createAccount(formData)
            if (error) { setFormError(error.message) }
            else { setShowModal(false); fetchAccounts() }
        } else if (editingAccount) {
            const updateData: UpdateZoomAccountData = {}
            if (formData.account_name) updateData.account_name = formData.account_name
            if (formData.zoom_account_id) updateData.zoom_account_id = formData.zoom_account_id
            if (formData.zoom_client_id) updateData.zoom_client_id = formData.zoom_client_id
            if (formData.zoom_client_secret) updateData.zoom_client_secret = formData.zoom_client_secret
            if (formData.zoom_user_email !== undefined) updateData.zoom_user_email = formData.zoom_user_email
            if (formData.is_active !== undefined) updateData.is_active = formData.is_active
            if (formData.notes !== undefined) updateData.notes = formData.notes

            const { error } = await zoomApi.updateAccount(editingAccount.id, updateData)
            if (error) { setFormError(error.message) }
            else { setShowModal(false); fetchAccounts() }
        }
        setSubmitting(false)
    }

    // === Delete ===
    const handleDelete = async () => {
        if (!deleteConfirm) return
        setDeleting(true)
        const { error } = await zoomApi.deleteAccount(deleteConfirm.id)
        if (!error) {
            setDeleteConfirm(null)
            fetchAccounts()
        }
        setDeleting(false)
    }

    // === Test Connection ===
    const handleTestConnection = async (accountId: string) => {
        setTestingId(accountId)
        setTestResult(null)
        const { success, error } = await zoomApi.testAccount(accountId)
        setTestResult({
            id: accountId,
            success,
            message: success ? '連線成功' : (error?.message || '連線失敗'),
        })
        setTestingId(null)
    }

    return (
        <DashboardLayout>
            <div className="p-6">
                {/* Header */}
                <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
                            <Video className="w-5 h-5 text-blue-600" />
                        </div>
                        <div>
                            <h1 className="text-2xl font-bold text-gray-900">Zoom 帳號管理</h1>
                            <p className="text-sm text-gray-500">共 {total} 個帳號</p>
                        </div>
                    </div>
                    {isStaff && (
                        <button onClick={openCreateModal} className="btn-primary flex items-center gap-2">
                            <Plus className="w-4 h-4" /> 新增帳號
                        </button>
                    )}
                </div>

                {/* Error */}
                {error && <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{error}</div>}

                {/* Table */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                    {loading ? (
                        <div className="flex items-center justify-center py-12">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                        </div>
                    ) : accounts.length === 0 ? (
                        <div className="text-center py-12 text-gray-500">
                            <Video className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                            <p>尚無 Zoom 帳號</p>
                            <p className="text-sm mt-1">點擊「新增帳號」開始設定帳號池</p>
                        </div>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full">
                                <thead className="bg-gray-50 border-b border-gray-200">
                                    <tr>
                                        <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">帳號名稱</th>
                                        <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Zoom Email</th>
                                        <th className="text-center px-4 py-3 text-xs font-medium text-gray-500 uppercase">狀態</th>
                                        <th className="text-center px-4 py-3 text-xs font-medium text-gray-500 uppercase">今日用量</th>
                                        <th className="text-center px-4 py-3 text-xs font-medium text-gray-500 uppercase">連線測試</th>
                                        {isStaff && <th className="text-right px-4 py-3 text-xs font-medium text-gray-500 uppercase">操作</th>}
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-200">
                                    {accounts.map((account) => (
                                        <tr key={account.id} className="hover:bg-gray-50">
                                            <td className="px-4 py-3">
                                                <div className="text-sm font-medium text-gray-900">{account.account_name}</div>
                                                <div className="text-xs text-gray-500">{account.zoom_account_id}</div>
                                            </td>
                                            <td className="px-4 py-3 text-sm text-gray-600">
                                                {account.zoom_user_email || '-'}
                                            </td>
                                            <td className="px-4 py-3 text-center">
                                                {account.is_active ? (
                                                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                                        <CheckCircle className="w-3 h-3 mr-1" /> 啟用
                                                    </span>
                                                ) : (
                                                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                                                        <XCircle className="w-3 h-3 mr-1" /> 停用
                                                    </span>
                                                )}
                                            </td>
                                            <td className="px-4 py-3 text-center text-sm text-gray-600">
                                                {account.daily_meeting_count}
                                            </td>
                                            <td className="px-4 py-3 text-center">
                                                <button
                                                    onClick={() => handleTestConnection(account.id)}
                                                    disabled={testingId === account.id}
                                                    className="inline-flex items-center gap-1 px-3 py-1 text-xs rounded-md border border-gray-300 hover:bg-gray-100 disabled:opacity-50"
                                                >
                                                    {testingId === account.id ? (
                                                        <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-blue-600"></div>
                                                    ) : (
                                                        <Zap className="w-3 h-3" />
                                                    )}
                                                    測試
                                                </button>
                                                {testResult && testResult.id === account.id && (
                                                    <div className={`mt-1 text-xs ${testResult.success ? 'text-green-600' : 'text-red-600'}`}>
                                                        {testResult.message}
                                                    </div>
                                                )}
                                            </td>
                                            {isStaff && (
                                                <td className="px-4 py-3 text-right">
                                                    <button onClick={() => openEditModal(account)} className="text-blue-600 hover:text-blue-900 mr-3" title="編輯">
                                                        <Pencil className="w-4 h-4" />
                                                    </button>
                                                    <button onClick={() => setDeleteConfirm(account)} className="text-red-600 hover:text-red-900" title="刪除">
                                                        <Trash2 className="w-4 h-4" />
                                                    </button>
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
                        <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 bg-gray-50">
                            <p className="text-sm text-gray-500">
                                第 {page} / {totalPages} 頁，共 {total} 個
                            </p>
                            <div className="flex gap-2">
                                <button
                                    onClick={() => setPage(p => Math.max(1, p - 1))}
                                    disabled={page <= 1}
                                    className="px-3 py-1 text-sm rounded border border-gray-300 disabled:opacity-50 hover:bg-gray-100"
                                >
                                    上一頁
                                </button>
                                <button
                                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                                    disabled={page >= totalPages}
                                    className="px-3 py-1 text-sm rounded border border-gray-300 disabled:opacity-50 hover:bg-gray-100"
                                >
                                    下一頁
                                </button>
                            </div>
                        </div>
                    )}
                </div>

                {/* Create / Edit Modal */}
                {showModal && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                        <div className="bg-white rounded-xl shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
                            <div className="p-6">
                                <div className="flex items-center justify-between mb-6">
                                    <h2 className="text-xl font-bold text-gray-900">
                                        {modalMode === 'create' ? '新增 Zoom 帳號' : '編輯 Zoom 帳號'}
                                    </h2>
                                    <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-gray-600">
                                        <X className="w-6 h-6" />
                                    </button>
                                </div>

                                {formError && <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{formError}</div>}

                                <form onSubmit={handleSubmit} className="space-y-4">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">帳號名稱 <span className="text-red-500">*</span></label>
                                        <input
                                            type="text"
                                            value={formData.account_name}
                                            onChange={(e) => setFormData({ ...formData, account_name: e.target.value })}
                                            className="input-field"
                                            placeholder="例如：Zoom 帳號 A"
                                            required
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">Zoom Account ID <span className="text-red-500">*</span></label>
                                        <input
                                            type="text"
                                            value={formData.zoom_account_id}
                                            onChange={(e) => setFormData({ ...formData, zoom_account_id: e.target.value })}
                                            className="input-field"
                                            placeholder="S2S OAuth App 的 Account ID"
                                            required
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">Zoom Client ID <span className="text-red-500">*</span></label>
                                        <input
                                            type="text"
                                            value={formData.zoom_client_id}
                                            onChange={(e) => setFormData({ ...formData, zoom_client_id: e.target.value })}
                                            className="input-field"
                                            placeholder="S2S OAuth App 的 Client ID"
                                            required
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            Zoom Client Secret <span className="text-red-500">{modalMode === 'create' ? '*' : ''}</span>
                                        </label>
                                        <input
                                            type="password"
                                            value={formData.zoom_client_secret}
                                            onChange={(e) => setFormData({ ...formData, zoom_client_secret: e.target.value })}
                                            className="input-field"
                                            placeholder={modalMode === 'edit' ? '留空不更新' : 'S2S OAuth App 的 Client Secret'}
                                            required={modalMode === 'create'}
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">Zoom User Email</label>
                                        <input
                                            type="email"
                                            value={formData.zoom_user_email || ''}
                                            onChange={(e) => setFormData({ ...formData, zoom_user_email: e.target.value })}
                                            className="input-field"
                                            placeholder="建立會議用的使用者 Email（選填）"
                                        />
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <input
                                            type="checkbox"
                                            id="is_active"
                                            checked={formData.is_active}
                                            onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                                            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                        />
                                        <label htmlFor="is_active" className="text-sm text-gray-700">啟用此帳號</label>
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">備註</label>
                                        <textarea
                                            value={formData.notes || ''}
                                            onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                                            className="input-field"
                                            rows={2}
                                        />
                                    </div>

                                    <div className="flex gap-3 pt-4">
                                        <button type="button" onClick={() => setShowModal(false)} className="btn-secondary flex-1" disabled={submitting}>
                                            取消
                                        </button>
                                        <button type="submit" className="btn-primary flex-1" disabled={submitting}>
                                            {submitting ? (
                                                <span className="flex items-center justify-center">
                                                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                                                    處理中...
                                                </span>
                                            ) : modalMode === 'create' ? '新增' : '儲存'}
                                        </button>
                                    </div>
                                </form>
                            </div>
                        </div>
                    </div>
                )}

                {/* Delete Confirm Modal */}
                {deleteConfirm && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                        <div className="bg-white rounded-xl shadow-xl max-w-sm w-full p-6">
                            <h3 className="text-lg font-bold text-gray-900 mb-2">確認刪除</h3>
                            <p className="text-sm text-gray-600 mb-6">
                                確定要刪除 Zoom 帳號「<span className="font-medium">{deleteConfirm.account_name}</span>」嗎？此操作無法復原。
                            </p>
                            <div className="flex gap-3">
                                <button onClick={() => setDeleteConfirm(null)} className="btn-secondary flex-1" disabled={deleting}>
                                    取消
                                </button>
                                <button onClick={handleDelete} className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 flex-1" disabled={deleting}>
                                    {deleting ? '刪除中...' : '確認刪除'}
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </DashboardLayout>
    )
}

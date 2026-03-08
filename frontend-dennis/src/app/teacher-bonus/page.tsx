'use client'

import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '@/lib/hooks/useAuth'
import {
    teacherBonusApi,
    TeacherBonus,
    CreateTeacherBonusData,
    UpdateTeacherBonusData,
    BonusType,
    BONUS_TYPE_LABELS,
    TeacherOption,
} from '@/lib/api/teacherBonus'
import { Plus, Pencil, Trash2, Search, X, DollarSign, Calendar } from 'lucide-react'
import DashboardLayout from '@/components/DashboardLayout'

const bonusTypeColors: Record<BonusType, { bg: string, text: string }> = {
    trial_to_formal: { bg: 'bg-green-100', text: 'text-green-800' },
    performance: { bg: 'bg-blue-100', text: 'text-blue-800' },
    substitute: { bg: 'bg-orange-100', text: 'text-orange-800' },
    referral: { bg: 'bg-purple-100', text: 'text-purple-800' },
    other: { bg: 'bg-gray-100', text: 'text-gray-800' },
}

export default function TeacherBonusPage() {
    const { user, profile } = useAuth()

    const [bonuses, setBonuses] = useState<TeacherBonus[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    // Filters
    const [filterTeacher, setFilterTeacher] = useState('')
    const [filterType, setFilterType] = useState<BonusType | ''>('')
    const [filterDateFrom, setFilterDateFrom] = useState('')
    const [filterDateTo, setFilterDateTo] = useState('')

    // Options
    const [teacherOptions, setTeacherOptions] = useState<TeacherOption[]>([])

    // Pagination
    const [page, setPage] = useState(1)
    const [totalPages, setTotalPages] = useState(1)
    const [total, setTotal] = useState(0)
    const perPage = 10

    // Modal
    const [showModal, setShowModal] = useState(false)
    const [modalMode, setModalMode] = useState<'create' | 'edit'>('create')
    const [editingBonus, setEditingBonus] = useState<TeacherBonus | null>(null)
    const [formData, setFormData] = useState<CreateTeacherBonusData>({
        teacher_id: '',
        bonus_type: 'trial_to_formal',
        amount: 0,
        bonus_date: '',
        description: '',
        notes: '',
    })
    const [formError, setFormError] = useState<string | null>(null)
    const [submitting, setSubmitting] = useState(false)

    // Delete
    const [deleteConfirm, setDeleteConfirm] = useState<TeacherBonus | null>(null)
    const [deleting, setDeleting] = useState(false)

    const isStaff = profile?.employee_id != null

    const fetchBonuses = useCallback(async () => {
        setLoading(true)
        setError(null)
        const { data, error } = await teacherBonusApi.list({
            page, per_page: perPage,
            teacher_id: filterTeacher || undefined,
            bonus_type: (filterType as BonusType) || undefined,
            date_from: filterDateFrom || undefined,
            date_to: filterDateTo || undefined,
        })
        if (error) {
            setError(error.message)
        } else if (data) {
            setBonuses(data.data)
            setTotalPages(data.total_pages)
            setTotal(data.total)
        }
        setLoading(false)
    }, [page, filterTeacher, filterType, filterDateFrom, filterDateTo])

    useEffect(() => {
        if (user) fetchBonuses()
    }, [user, fetchBonuses])

    useEffect(() => {
        if (user && isStaff) {
            teacherBonusApi.getTeacherOptions().then(({ data }) => {
                setTeacherOptions(data)
            })
        }
    }, [user, isStaff])

    useEffect(() => {
        setPage(1)
    }, [filterTeacher, filterType, filterDateFrom, filterDateTo])

    // === Create / Edit ===
    const openCreateModal = () => {
        setModalMode('create')
        setEditingBonus(null)
        setFormData({
            teacher_id: '',
            bonus_type: 'trial_to_formal',
            amount: 0,
            bonus_date: new Date().toISOString().slice(0, 10),
            description: '',
            notes: '',
        })
        setFormError(null)
        setShowModal(true)
    }

    const openEditModal = (bonus: TeacherBonus) => {
        setModalMode('edit')
        setEditingBonus(bonus)
        setFormData({
            teacher_id: bonus.teacher_id,
            bonus_type: bonus.bonus_type,
            amount: bonus.amount,
            bonus_date: bonus.bonus_date || '',
            description: bonus.description || '',
            notes: bonus.notes || '',
        })
        setFormError(null)
        setShowModal(true)
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setFormError(null)
        setSubmitting(true)

        if (modalMode === 'create') {
            const { error } = await teacherBonusApi.create(formData)
            if (error) { setFormError(error.message) }
            else { setShowModal(false); fetchBonuses() }
        } else if (editingBonus) {
            const updateData: UpdateTeacherBonusData = {
                bonus_type: formData.bonus_type,
                amount: formData.amount,
                bonus_date: formData.bonus_date || undefined,
                description: formData.description || undefined,
                notes: formData.notes || undefined,
            }
            const { error } = await teacherBonusApi.update(editingBonus.id, updateData)
            if (error) { setFormError(error.message) }
            else { setShowModal(false); fetchBonuses() }
        }
        setSubmitting(false)
    }

    // === Delete ===
    const handleDelete = async () => {
        if (!deleteConfirm) return
        setDeleting(true)
        const { error } = await teacherBonusApi.delete(deleteConfirm.id)
        if (!error) {
            setDeleteConfirm(null)
            fetchBonuses()
        }
        setDeleting(false)
    }

    return (
        <DashboardLayout>
            <div className="p-6">
                {/* Header */}
                <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center">
                            <DollarSign className="w-5 h-5 text-green-600" />
                        </div>
                        <div>
                            <h1 className="text-2xl font-bold text-gray-900">教師獎金</h1>
                            <p className="text-sm text-gray-500">共 {total} 筆紀錄</p>
                        </div>
                    </div>
                    {isStaff && (
                        <button onClick={openCreateModal} className="btn-primary flex items-center gap-2">
                            <Plus className="w-4 h-4" /> 新增獎金
                        </button>
                    )}
                </div>

                {/* Filters */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 mb-6">
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                        {isStaff && (
                            <div>
                                <label className="block text-xs font-medium text-gray-500 mb-1">教師</label>
                                <select value={filterTeacher} onChange={(e) => setFilterTeacher(e.target.value)} className="input-field">
                                    <option value="">全部教師</option>
                                    {teacherOptions.map(t => (
                                        <option key={t.id} value={t.id}>{t.name}（{t.teacher_no}）</option>
                                    ))}
                                </select>
                            </div>
                        )}
                        <div>
                            <label className="block text-xs font-medium text-gray-500 mb-1">獎金類型</label>
                            <select value={filterType} onChange={(e) => setFilterType(e.target.value as BonusType | '')} className="input-field">
                                <option value="">全部類型</option>
                                {(Object.keys(BONUS_TYPE_LABELS) as BonusType[]).map(k => (
                                    <option key={k} value={k}>{BONUS_TYPE_LABELS[k]}</option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label className="block text-xs font-medium text-gray-500 mb-1">起始日期</label>
                            <input type="date" value={filterDateFrom} onChange={(e) => setFilterDateFrom(e.target.value)} className="input-field" />
                        </div>
                        <div>
                            <label className="block text-xs font-medium text-gray-500 mb-1">結束日期</label>
                            <input type="date" value={filterDateTo} onChange={(e) => setFilterDateTo(e.target.value)} className="input-field" />
                        </div>
                    </div>
                </div>

                {/* Error */}
                {error && <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{error}</div>}

                {/* Table */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                    {loading ? (
                        <div className="flex items-center justify-center py-12">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                        </div>
                    ) : bonuses.length === 0 ? (
                        <div className="text-center py-12 text-gray-500">
                            <DollarSign className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                            <p>尚無獎金紀錄</p>
                        </div>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full">
                                <thead className="bg-gray-50 border-b border-gray-200">
                                    <tr>
                                        <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">教師</th>
                                        <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">獎金類型</th>
                                        <th className="text-right px-4 py-3 text-xs font-medium text-gray-500 uppercase">金額</th>
                                        <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">日期</th>
                                        <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">說明</th>
                                        <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">關聯學生</th>
                                        {isStaff && <th className="text-right px-4 py-3 text-xs font-medium text-gray-500 uppercase">操作</th>}
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-200">
                                    {bonuses.map((bonus) => {
                                        const typeColor = bonusTypeColors[bonus.bonus_type] || bonusTypeColors.other
                                        return (
                                            <tr key={bonus.id} className="hover:bg-gray-50">
                                                <td className="px-4 py-3 text-sm font-medium text-gray-900">
                                                    {bonus.teacher_name || bonus.teacher_id}
                                                </td>
                                                <td className="px-4 py-3">
                                                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${typeColor.bg} ${typeColor.text}`}>
                                                        {BONUS_TYPE_LABELS[bonus.bonus_type] || bonus.bonus_type}
                                                    </span>
                                                </td>
                                                <td className="px-4 py-3 text-sm text-right font-medium text-gray-900">
                                                    ${bonus.amount.toLocaleString()}
                                                </td>
                                                <td className="px-4 py-3 text-sm text-gray-600">
                                                    {bonus.bonus_date || '-'}
                                                </td>
                                                <td className="px-4 py-3 text-sm text-gray-600 max-w-[200px] truncate">
                                                    {bonus.description || '-'}
                                                </td>
                                                <td className="px-4 py-3 text-sm text-gray-600">
                                                    {bonus.student_name || '-'}
                                                </td>
                                                {isStaff && (
                                                    <td className="px-4 py-3 text-right">
                                                        <button onClick={() => openEditModal(bonus)} className="text-blue-600 hover:text-blue-900 mr-3" title="編輯">
                                                            <Pencil className="w-4 h-4" />
                                                        </button>
                                                        <button onClick={() => setDeleteConfirm(bonus)} className="text-red-600 hover:text-red-900" title="刪除">
                                                            <Trash2 className="w-4 h-4" />
                                                        </button>
                                                    </td>
                                                )}
                                            </tr>
                                        )
                                    })}
                                </tbody>
                            </table>
                        </div>
                    )}

                    {/* Pagination */}
                    {totalPages > 1 && (
                        <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 bg-gray-50">
                            <p className="text-sm text-gray-500">
                                第 {page} / {totalPages} 頁，共 {total} 筆
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
                                        {modalMode === 'create' ? '新增教師獎金' : '編輯教師獎金'}
                                    </h2>
                                    <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-gray-600">
                                        <X className="w-6 h-6" />
                                    </button>
                                </div>

                                {formError && <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{formError}</div>}

                                <form onSubmit={handleSubmit} className="space-y-4">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">教師 <span className="text-red-500">*</span></label>
                                        <select
                                            value={formData.teacher_id}
                                            onChange={(e) => setFormData({ ...formData, teacher_id: e.target.value })}
                                            className="input-field"
                                            required
                                            disabled={modalMode === 'edit'}
                                        >
                                            <option value="">請選擇教師</option>
                                            {teacherOptions.map(t => (
                                                <option key={t.id} value={t.id}>{t.name}（{t.teacher_no}）</option>
                                            ))}
                                        </select>
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">獎金類型 <span className="text-red-500">*</span></label>
                                        <select
                                            value={formData.bonus_type}
                                            onChange={(e) => setFormData({ ...formData, bonus_type: e.target.value as BonusType })}
                                            className="input-field"
                                            required
                                        >
                                            {(Object.keys(BONUS_TYPE_LABELS) as BonusType[]).map(k => (
                                                <option key={k} value={k}>{BONUS_TYPE_LABELS[k]}</option>
                                            ))}
                                        </select>
                                    </div>
                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">金額 <span className="text-red-500">*</span></label>
                                            <input
                                                type="number"
                                                min={0}
                                                step={1}
                                                value={formData.amount}
                                                onChange={(e) => setFormData({ ...formData, amount: parseFloat(e.target.value) || 0 })}
                                                className="input-field"
                                                required
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">日期</label>
                                            <input
                                                type="date"
                                                value={formData.bonus_date || ''}
                                                onChange={(e) => setFormData({ ...formData, bonus_date: e.target.value })}
                                                className="input-field"
                                            />
                                        </div>
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">說明</label>
                                        <input
                                            type="text"
                                            value={formData.description || ''}
                                            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                            className="input-field"
                                            maxLength={255}
                                        />
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
                                確定要刪除 <span className="font-medium">{deleteConfirm.teacher_name}</span> 的
                                <span className="font-medium"> {BONUS_TYPE_LABELS[deleteConfirm.bonus_type] || deleteConfirm.bonus_type}</span> 紀錄
                                （${deleteConfirm.amount.toLocaleString()}）嗎？此操作無法復原。
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

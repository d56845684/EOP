'use client'

import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '@/lib/hooks/useAuth'
import { teachersApi, Teacher, CreateTeacherData, UpdateTeacherData } from '@/lib/api/teachers'
import { invitesApi } from '@/lib/api/invites'
import { teacherDetailsApi, TeacherDetail, TeacherDetailType, CreateTeacherDetailData, UpdateTeacherDetailData, DETAIL_TYPE_LABELS } from '@/lib/api/teacherDetails'
import { Plus, Pencil, Trash2, Search, X, Users, CheckCircle, XCircle, Mail, Phone, Star, Copy, Check, UserPlus, FileText, Upload, Download } from 'lucide-react'
import DashboardLayout from '@/components/DashboardLayout'

export default function TeachersPage() {
    const { user, profile } = useAuth()

    const [teachers, setTeachers] = useState<Teacher[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [searchTerm, setSearchTerm] = useState('')
    const [filterActive, setFilterActive] = useState<boolean | undefined>(undefined)

    const [page, setPage] = useState(1)
    const [totalPages, setTotalPages] = useState(1)
    const [total, setTotal] = useState(0)
    const perPage = 10

    const [showModal, setShowModal] = useState(false)
    const [modalMode, setModalMode] = useState<'create' | 'edit'>('create')
    const [editingTeacher, setEditingTeacher] = useState<Teacher | null>(null)
    const [formData, setFormData] = useState<CreateTeacherData>({
        teacher_no: '', name: '', email: '', phone: '', address: '',
        bio: '', teacher_level: 1, is_active: true,
    })
    const [formError, setFormError] = useState<string | null>(null)
    const [submitting, setSubmitting] = useState(false)

    const [deleteConfirm, setDeleteConfirm] = useState<Teacher | null>(null)
    const [deleting, setDeleting] = useState(false)

    // 邀請連結
    const [inviteUrl, setInviteUrl] = useState<string | null>(null)
    const [inviteTeacher, setInviteTeacher] = useState<Teacher | null>(null)
    const [inviteLoading, setInviteLoading] = useState(false)
    const [inviteError, setInviteError] = useState<string | null>(null)
    const [copied, setCopied] = useState(false)

    // 教師明細
    const [detailTeacher, setDetailTeacher] = useState<Teacher | null>(null)
    const [details, setDetails] = useState<TeacherDetail[]>([])
    const [detailsLoading, setDetailsLoading] = useState(false)
    const [detailsError, setDetailsError] = useState<string | null>(null)
    const [showDetailForm, setShowDetailForm] = useState(false)
    const [editingDetail, setEditingDetail] = useState<TeacherDetail | null>(null)
    const [detailFormData, setDetailFormData] = useState<CreateTeacherDetailData>({
        teacher_id: '', detail_type: 'qualification', content: '', issue_date: '', expiry_date: '',
    })
    const [detailFormError, setDetailFormError] = useState<string | null>(null)
    const [detailSubmitting, setDetailSubmitting] = useState(false)
    const [uploadingDetailId, setUploadingDetailId] = useState<string | null>(null)

    const isStaff = profile?.employee_id != null

    const fetchTeachers = useCallback(async () => {
        setLoading(true)
        setError(null)
        const { data, error } = await teachersApi.list({
            page, per_page: perPage,
            search: searchTerm || undefined,
            is_active: filterActive,
        })
        if (error) {
            setError(error.message)
        } else if (data) {
            setTeachers(data.data)
            setTotalPages(data.total_pages)
            setTotal(data.total)
        }
        setLoading(false)
    }, [page, searchTerm, filterActive])

    useEffect(() => {
        if (user) fetchTeachers()
    }, [user, fetchTeachers])

    useEffect(() => {
        const timer = setTimeout(() => setPage(1), 300)
        return () => clearTimeout(timer)
    }, [searchTerm])

    const openCreateModal = () => {
        setModalMode('create')
        setEditingTeacher(null)
        setFormData({ teacher_no: '', name: '', email: '', phone: '', address: '', bio: '', teacher_level: 1, is_active: true })
        setFormError(null)
        setShowModal(true)
    }

    const openEditModal = (teacher: Teacher) => {
        setModalMode('edit')
        setEditingTeacher(teacher)
        setFormData({
            teacher_no: teacher.teacher_no, name: teacher.name, email: teacher.email,
            phone: teacher.phone || '', address: teacher.address || '',
            bio: teacher.bio || '', teacher_level: teacher.teacher_level,
            is_active: teacher.is_active,
        })
        setFormError(null)
        setShowModal(true)
    }

    const closeModal = () => { setShowModal(false); setEditingTeacher(null); setFormError(null) }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setFormError(null)
        setSubmitting(true)
        try {
            if (modalMode === 'create') {
                const submitData = { ...formData }
                if (!submitData.phone) delete (submitData as any).phone
                if (!submitData.address) delete (submitData as any).address
                if (!submitData.bio) delete (submitData as any).bio
                const { error } = await teachersApi.create(submitData)
                if (error) { setFormError(error.message) } else { closeModal(); fetchTeachers() }
            } else if (editingTeacher) {
                const updateData: UpdateTeacherData = {}
                if (formData.name !== editingTeacher.name) updateData.name = formData.name
                if (formData.email !== editingTeacher.email) updateData.email = formData.email
                if ((formData.phone || '') !== (editingTeacher.phone || '')) updateData.phone = formData.phone || undefined
                if ((formData.address || '') !== (editingTeacher.address || '')) updateData.address = formData.address || undefined
                if ((formData.bio || '') !== (editingTeacher.bio || '')) updateData.bio = formData.bio || undefined
                if (formData.teacher_level !== editingTeacher.teacher_level) updateData.teacher_level = formData.teacher_level
                if (formData.is_active !== editingTeacher.is_active) updateData.is_active = formData.is_active
                const { error } = await teachersApi.update(editingTeacher.id, updateData)
                if (error) { setFormError(error.message) } else { closeModal(); fetchTeachers() }
            }
        } finally { setSubmitting(false) }
    }

    const handleDelete = async () => {
        if (!deleteConfirm) return
        setDeleting(true)
        const { error } = await teachersApi.delete(deleteConfirm.id)
        if (error) { setError(error.message) } else { setDeleteConfirm(null); fetchTeachers() }
        setDeleting(false)
    }

    // === 邀請連結 ===
    const handleGenerateInvite = async (teacher: Teacher) => {
        setInviteTeacher(teacher)
        setInviteUrl(null)
        setInviteError(null)
        setInviteLoading(true)
        setCopied(false)

        const { data, error } = await invitesApi.generate('teacher', teacher.id)
        if (error) {
            setInviteError(error.message)
        } else if (data) {
            setInviteUrl(data.invite_url)
        }
        setInviteLoading(false)
    }

    const closeInviteModal = () => {
        setInviteTeacher(null)
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

    // === 教師明細 ===
    const openDetailsModal = async (teacher: Teacher) => {
        setDetailTeacher(teacher)
        setDetailsError(null)
        setShowDetailForm(false)
        setEditingDetail(null)
        setDetailsLoading(true)
        const { data, error } = await teacherDetailsApi.list(teacher.id)
        if (error) {
            setDetailsError(error.message)
        } else if (data) {
            setDetails(data.data)
        }
        setDetailsLoading(false)
    }

    const closeDetailsModal = () => {
        setDetailTeacher(null)
        setDetails([])
        setDetailsError(null)
        setShowDetailForm(false)
        setEditingDetail(null)
    }

    const openDetailCreateForm = () => {
        if (!detailTeacher) return
        setEditingDetail(null)
        setDetailFormData({
            teacher_id: detailTeacher.id,
            detail_type: 'qualification',
            content: '',
            issue_date: '',
            expiry_date: '',
        })
        setDetailFormError(null)
        setShowDetailForm(true)
    }

    const openDetailEditForm = (detail: TeacherDetail) => {
        if (!detailTeacher) return
        setEditingDetail(detail)
        setDetailFormData({
            teacher_id: detailTeacher.id,
            detail_type: detail.detail_type as TeacherDetailType,
            content: detail.content || '',
            issue_date: detail.issue_date || '',
            expiry_date: detail.expiry_date || '',
        })
        setDetailFormError(null)
        setShowDetailForm(true)
    }

    const handleDetailSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setDetailFormError(null)
        setDetailSubmitting(true)
        try {
            if (editingDetail) {
                const updateData: UpdateTeacherDetailData = {}
                if (detailFormData.content) updateData.content = detailFormData.content
                if (detailFormData.issue_date) updateData.issue_date = detailFormData.issue_date
                if (detailFormData.expiry_date) updateData.expiry_date = detailFormData.expiry_date
                const { error } = await teacherDetailsApi.update(editingDetail.id, updateData)
                if (error) { setDetailFormError(error.message) } else {
                    setShowDetailForm(false)
                    if (detailTeacher) await openDetailsModal(detailTeacher)
                }
            } else {
                const createData: CreateTeacherDetailData = {
                    teacher_id: detailFormData.teacher_id,
                    detail_type: detailFormData.detail_type,
                }
                if (detailFormData.content) createData.content = detailFormData.content
                if (detailFormData.issue_date) createData.issue_date = detailFormData.issue_date
                if (detailFormData.expiry_date) createData.expiry_date = detailFormData.expiry_date
                const { error } = await teacherDetailsApi.create(createData)
                if (error) { setDetailFormError(error.message) } else {
                    setShowDetailForm(false)
                    if (detailTeacher) await openDetailsModal(detailTeacher)
                }
            }
        } finally { setDetailSubmitting(false) }
    }

    const handleDetailDelete = async (detailId: string) => {
        if (!confirm('確定要刪除此明細嗎？')) return
        const { error } = await teacherDetailsApi.delete(detailId)
        if (error) {
            setDetailsError(error.message)
        } else if (detailTeacher) {
            await openDetailsModal(detailTeacher)
        }
    }

    const handleFileUpload = async (detail: TeacherDetail, file: File) => {
        setUploadingDetailId(detail.id)
        try {
            const { data: urlData, error: urlError } = await teacherDetailsApi.getUploadUrl(detail.id)
            if (urlError || !urlData) {
                setDetailsError(urlError?.message || '取得上傳連結失敗')
                return
            }

            const uploadRes = await fetch(urlData.upload_url, {
                method: 'PUT',
                body: file,
                headers: { 'Content-Type': file.type || 'application/octet-stream' },
            })
            if (!uploadRes.ok) {
                setDetailsError('檔案上傳失敗')
                return
            }

            const { error: confirmError } = await teacherDetailsApi.confirmUpload(detail.id, urlData.storage_path, file.name)
            if (confirmError) {
                setDetailsError(confirmError.message)
                return
            }

            if (detailTeacher) await openDetailsModal(detailTeacher)
        } catch {
            setDetailsError('檔案上傳過程發生錯誤')
        } finally {
            setUploadingDetailId(null)
        }
    }

    const handleFileDownload = async (detail: TeacherDetail) => {
        const { data, error } = await teacherDetailsApi.getDownloadUrl(detail.id)
        if (error || !data) {
            setDetailsError(error?.message || '取得下載連結失敗')
            return
        }
        window.open(data.download_url, '_blank')
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
                                    教師管理
                                </h1>
                                <p className="mt-2 text-gray-600">共 {total} 位教師</p>
                            </div>
                            {isStaff && (
                                <button onClick={openCreateModal} className="btn-primary flex items-center gap-2">
                                    <Plus className="w-5 h-5" /> 新增教師
                                </button>
                            )}
                        </div>
                    </div>

                    {/* Filters */}
                    <div className="card mb-6">
                        <div className="flex flex-col sm:flex-row gap-4">
                            <div className="flex-1 relative">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                                <input type="text" placeholder="搜尋教師編號、姓名或 Email..."
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
                        </div>
                    </div>

                    {error && <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">{error}</div>}

                    {/* Table */}
                    {loading ? (
                        <div className="flex justify-center py-12"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div></div>
                    ) : teachers.length === 0 ? (
                        <div className="card text-center py-12">
                            <Users className="w-16 h-16 mx-auto text-gray-300 mb-4" />
                            <h3 className="text-lg font-medium text-gray-900 mb-2">沒有找到教師</h3>
                            <p className="text-gray-500">{searchTerm ? '請嘗試其他搜尋條件' : '點擊「新增教師」建立第一位教師'}</p>
                        </div>
                    ) : (
                        <div className="card overflow-hidden">
                            <table className="min-w-full divide-y divide-gray-200">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">編號</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">姓名</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">聯絡方式</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">等級</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">狀態</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">帳號</th>
                                        {isStaff && <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">操作</th>}
                                    </tr>
                                </thead>
                                <tbody className="bg-white divide-y divide-gray-200">
                                    {teachers.map((teacher) => (
                                        <tr key={teacher.id} className="hover:bg-gray-50">
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <span className="font-mono text-sm bg-gray-100 px-2 py-1 rounded">{teacher.teacher_no}</span>
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="font-medium text-gray-900">{teacher.name}</div>
                                                {teacher.bio && <div className="text-sm text-gray-500 truncate max-w-xs">{teacher.bio}</div>}
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="flex flex-col gap-0.5">
                                                    <span className="text-sm text-gray-600 flex items-center gap-1"><Mail className="w-3 h-3" />{teacher.email}</span>
                                                    {teacher.phone && <span className="text-sm text-gray-500 flex items-center gap-1"><Phone className="w-3 h-3" />{teacher.phone}</span>}
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                                                    <Star className="w-3 h-3 mr-1" /> Lv.{teacher.teacher_level}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                {teacher.is_active ? (
                                                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800"><CheckCircle className="w-3 h-3 mr-1" />啟用中</span>
                                                ) : (
                                                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800"><XCircle className="w-3 h-3 mr-1" />已停用</span>
                                                )}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                {teacher.email_verified_at ? (
                                                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800"><CheckCircle className="w-3 h-3 mr-1" />已驗證</span>
                                                ) : (
                                                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800"><XCircle className="w-3 h-3 mr-1" />未驗證</span>
                                                )}
                                            </td>
                                            {isStaff && (
                                                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                                    <button onClick={() => openDetailsModal(teacher)} className="text-purple-600 hover:text-purple-900 mr-4" title="明細管理"><FileText className="w-5 h-5" /></button>
                                                    {!teacher.email_verified_at && (
                                                        <button onClick={() => handleGenerateInvite(teacher)} className="text-green-600 hover:text-green-900 mr-4" title="產生邀請連結"><UserPlus className="w-5 h-5" /></button>
                                                    )}
                                                    <button onClick={() => openEditModal(teacher)} className="text-blue-600 hover:text-blue-900 mr-4" title="編輯"><Pencil className="w-5 h-5" /></button>
                                                    <button onClick={() => setDeleteConfirm(teacher)} className="text-red-600 hover:text-red-900" title="刪除"><Trash2 className="w-5 h-5" /></button>
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
                                    <h2 className="text-xl font-bold text-gray-900">{modalMode === 'create' ? '新增教師' : '編輯教師'}</h2>
                                    <button onClick={closeModal} className="text-gray-400 hover:text-gray-600"><X className="w-6 h-6" /></button>
                                </div>
                                {formError && <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{formError}</div>}
                                <form onSubmit={handleSubmit} className="space-y-4">
                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">教師編號 <span className="text-red-500">*</span></label>
                                            <input type="text" value={formData.teacher_no} onChange={(e) => setFormData({ ...formData, teacher_no: e.target.value })}
                                                className="input-field" placeholder="例如：T001" required disabled={modalMode === 'edit'} />
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
                                            <input type="text" value={formData.phone} onChange={(e) => setFormData({ ...formData, phone: e.target.value })} className="input-field" />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">教師等級</label>
                                            <input type="number" min={1} value={formData.teacher_level} onChange={(e) => setFormData({ ...formData, teacher_level: parseInt(e.target.value) || 1 })} className="input-field" />
                                        </div>
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">地址</label>
                                        <input type="text" value={formData.address} onChange={(e) => setFormData({ ...formData, address: e.target.value })} className="input-field" />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">簡介</label>
                                        <textarea value={formData.bio} onChange={(e) => setFormData({ ...formData, bio: e.target.value })} className="input-field" rows={3} placeholder="教師簡介..." />
                                    </div>
                                    <div className="flex items-center">
                                        <input type="checkbox" id="is_active" checked={formData.is_active} onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                                            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded" />
                                        <label htmlFor="is_active" className="ml-2 block text-sm text-gray-700">啟用教師</label>
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
                            <h3 className="text-lg font-bold text-gray-900 mb-2">確認刪除教師</h3>
                            <p className="text-gray-600 mb-6">確定要刪除教師「<span className="font-medium">{deleteConfirm.name}</span>」（{deleteConfirm.teacher_no}）嗎？</p>
                            <div className="flex gap-3">
                                <button onClick={() => setDeleteConfirm(null)} className="btn-secondary flex-1" disabled={deleting}>取消</button>
                                <button onClick={handleDelete} className="btn-danger flex-1" disabled={deleting}>
                                    {deleting ? <span className="flex items-center justify-center"><div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>刪除中...</span> : '確認刪除'}
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {/* 教師明細 Modal */}
                {detailTeacher && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                        <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                            <div className="p-6">
                                <div className="flex items-center justify-between mb-4">
                                    <div>
                                        <h2 className="text-xl font-bold text-gray-900">教師明細</h2>
                                        <p className="text-sm text-gray-500">{detailTeacher.name}（{detailTeacher.teacher_no}）</p>
                                    </div>
                                    <button onClick={closeDetailsModal} className="text-gray-400 hover:text-gray-600"><X className="w-6 h-6" /></button>
                                </div>

                                {detailsError && <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{detailsError}</div>}

                                {detailsLoading ? (
                                    <div className="flex justify-center py-8"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div></div>
                                ) : (
                                    <>
                                        {isStaff && !showDetailForm && (
                                            <button onClick={openDetailCreateForm} className="btn-primary flex items-center gap-2 mb-4 text-sm">
                                                <Plus className="w-4 h-4" /> 新增明細
                                            </button>
                                        )}

                                        {showDetailForm && (
                                            <div className="mb-4 p-4 bg-gray-50 rounded-lg border">
                                                <h3 className="text-sm font-medium mb-3">{editingDetail ? '編輯明細' : '新增明細'}</h3>
                                                {detailFormError && <div className="mb-3 p-2 bg-red-50 border border-red-200 rounded text-red-700 text-xs">{detailFormError}</div>}
                                                <form onSubmit={handleDetailSubmit} className="space-y-3">
                                                    {!editingDetail && (
                                                        <div>
                                                            <label className="block text-xs font-medium text-gray-700 mb-1">類型 <span className="text-red-500">*</span></label>
                                                            <select value={detailFormData.detail_type}
                                                                onChange={(e) => setDetailFormData({ ...detailFormData, detail_type: e.target.value as TeacherDetailType })}
                                                                className="input-field text-sm">
                                                                {(Object.keys(DETAIL_TYPE_LABELS) as TeacherDetailType[]).map((type) => (
                                                                    <option key={type} value={type}>{DETAIL_TYPE_LABELS[type]}</option>
                                                                ))}
                                                            </select>
                                                        </div>
                                                    )}
                                                    <div>
                                                        <label className="block text-xs font-medium text-gray-700 mb-1">內容</label>
                                                        <textarea value={detailFormData.content}
                                                            onChange={(e) => setDetailFormData({ ...detailFormData, content: e.target.value })}
                                                            className="input-field text-sm" rows={2} placeholder="描述..." />
                                                    </div>
                                                    <div className="grid grid-cols-2 gap-3">
                                                        <div>
                                                            <label className="block text-xs font-medium text-gray-700 mb-1">發證日期</label>
                                                            <input type="date" value={detailFormData.issue_date}
                                                                onChange={(e) => setDetailFormData({ ...detailFormData, issue_date: e.target.value })}
                                                                className="input-field text-sm" />
                                                        </div>
                                                        <div>
                                                            <label className="block text-xs font-medium text-gray-700 mb-1">到期日期</label>
                                                            <input type="date" value={detailFormData.expiry_date}
                                                                onChange={(e) => setDetailFormData({ ...detailFormData, expiry_date: e.target.value })}
                                                                className="input-field text-sm" />
                                                        </div>
                                                    </div>
                                                    <div className="flex gap-2 pt-2">
                                                        <button type="button" onClick={() => setShowDetailForm(false)} className="btn-secondary text-sm flex-1" disabled={detailSubmitting}>取消</button>
                                                        <button type="submit" className="btn-primary text-sm flex-1" disabled={detailSubmitting}>
                                                            {detailSubmitting ? '處理中...' : editingDetail ? '儲存' : '新增'}
                                                        </button>
                                                    </div>
                                                </form>
                                            </div>
                                        )}

                                        {details.length === 0 ? (
                                            <div className="text-center py-8">
                                                <FileText className="w-12 h-12 mx-auto text-gray-300 mb-3" />
                                                <p className="text-gray-500 text-sm">尚無明細資料</p>
                                            </div>
                                        ) : (
                                            <div className="space-y-3">
                                                {details.map((detail) => (
                                                    <div key={detail.id} className="p-4 border rounded-lg hover:bg-gray-50">
                                                        <div className="flex items-start justify-between">
                                                            <div className="flex-1">
                                                                <div className="flex items-center gap-2 mb-1">
                                                                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800">
                                                                        {DETAIL_TYPE_LABELS[detail.detail_type as TeacherDetailType] || detail.detail_type}
                                                                    </span>
                                                                    {detail.file_name && (
                                                                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                                                                            <FileText className="w-3 h-3 mr-1" />有附件
                                                                        </span>
                                                                    )}
                                                                </div>
                                                                {detail.content && <p className="text-sm text-gray-700 mb-1">{detail.content}</p>}
                                                                <div className="flex gap-4 text-xs text-gray-400">
                                                                    {detail.issue_date && <span>發證：{detail.issue_date}</span>}
                                                                    {detail.expiry_date && <span>到期：{detail.expiry_date}</span>}
                                                                </div>
                                                            </div>
                                                            <div className="flex items-center gap-1 ml-4">
                                                                {detail.file_name && (
                                                                    <button onClick={() => handleFileDownload(detail)} className="text-blue-600 hover:text-blue-800 p-1" title="下載檔案">
                                                                        <Download className="w-4 h-4" />
                                                                    </button>
                                                                )}
                                                                {isStaff && (
                                                                    <>
                                                                        <label className="text-green-600 hover:text-green-800 p-1 cursor-pointer" title="上傳檔案">
                                                                            {uploadingDetailId === detail.id ? (
                                                                                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-green-600"></div>
                                                                            ) : (
                                                                                <Upload className="w-4 h-4" />
                                                                            )}
                                                                            <input type="file" className="hidden"
                                                                                onChange={(e) => {
                                                                                    const file = e.target.files?.[0]
                                                                                    if (file) handleFileUpload(detail, file)
                                                                                    e.target.value = ''
                                                                                }}
                                                                                disabled={uploadingDetailId === detail.id} />
                                                                        </label>
                                                                        <button onClick={() => openDetailEditForm(detail)} className="text-blue-600 hover:text-blue-800 p-1" title="編輯">
                                                                            <Pencil className="w-4 h-4" />
                                                                        </button>
                                                                        <button onClick={() => handleDetailDelete(detail.id)} className="text-red-600 hover:text-red-800 p-1" title="刪除">
                                                                            <Trash2 className="w-4 h-4" />
                                                                        </button>
                                                                    </>
                                                                )}
                                                            </div>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </>
                                )}

                                <div className="flex gap-3 mt-6">
                                    <button onClick={closeDetailsModal} className="btn-secondary flex-1">關閉</button>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* 邀請連結 Modal */}
                {inviteTeacher && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                        <div className="bg-white rounded-xl shadow-xl max-w-lg w-full p-6">
                            <div className="flex items-center justify-between mb-4">
                                <h3 className="text-lg font-bold text-gray-900">邀請連結</h3>
                                <button onClick={closeInviteModal} className="text-gray-400 hover:text-gray-600"><X className="w-6 h-6" /></button>
                            </div>
                            <p className="text-sm text-gray-600 mb-4">
                                教師：<span className="font-medium">{inviteTeacher.name}</span>（{inviteTeacher.email}）
                            </p>

                            {inviteLoading && (
                                <div className="flex justify-center py-8">
                                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                                </div>
                            )}

                            {inviteError && (
                                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm mb-4">{inviteError}</div>
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

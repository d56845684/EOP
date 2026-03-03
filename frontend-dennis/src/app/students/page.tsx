'use client'

import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '@/lib/hooks/useAuth'
import { studentsApi, Student, CreateStudentData, UpdateStudentData, ConvertToFormalData } from '@/lib/api/students'
import { Booking } from '@/lib/api/bookings'
import { studentTeacherPreferencesApi, StudentTeacherPreference, CreatePreferenceData } from '@/lib/api/studentTeacherPreferences'
import { bookingsApi, TeacherOption, CourseOption } from '@/lib/api/bookings'
import { invitesApi } from '@/lib/api/invites'
import { Plus, Pencil, Trash2, Search, X, GraduationCap, CheckCircle, XCircle, Mail, Phone, Star, Settings, ArrowLeft, Link, Copy, Check, UserPlus, ArrowUpCircle } from 'lucide-react'
import DashboardLayout from '@/components/DashboardLayout'

export default function StudentsPage() {
    const { user, profile } = useAuth()

    const [students, setStudents] = useState<Student[]>([])
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
    const [editingStudent, setEditingStudent] = useState<Student | null>(null)
    const [formData, setFormData] = useState<CreateStudentData>({
        student_no: '', name: '', email: '', phone: '', address: '',
        birth_date: '', student_type: 'formal', is_active: true,
    })
    const [formError, setFormError] = useState<string | null>(null)
    const [submitting, setSubmitting] = useState(false)

    const [deleteConfirm, setDeleteConfirm] = useState<Student | null>(null)
    const [deleting, setDeleting] = useState(false)

    // 教師偏好設定
    const [prefStudent, setPrefStudent] = useState<Student | null>(null)
    const [preferences, setPreferences] = useState<StudentTeacherPreference[]>([])
    const [prefLoading, setPrefLoading] = useState(false)
    const [prefError, setPrefError] = useState<string | null>(null)
    const [teacherOptions, setTeacherOptions] = useState<TeacherOption[]>([])
    const [courseOptions, setCourseOptions] = useState<CourseOption[]>([])
    const [showPrefForm, setShowPrefForm] = useState(false)
    const [prefFormMode, setPrefFormMode] = useState<'create' | 'edit'>('create')
    const [editingPref, setEditingPref] = useState<StudentTeacherPreference | null>(null)
    const [prefFormData, setPrefFormData] = useState({ course_id: '', min_teacher_level: 1, primary_teacher_id: '' })
    const [prefFormError, setPrefFormError] = useState<string | null>(null)
    const [prefSubmitting, setPrefSubmitting] = useState(false)
    const [prefDeleteConfirm, setPrefDeleteConfirm] = useState<StudentTeacherPreference | null>(null)
    const [prefDeleting, setPrefDeleting] = useState(false)

    // 邀請連結
    const [inviteUrl, setInviteUrl] = useState<string | null>(null)
    const [inviteStudent, setInviteStudent] = useState<Student | null>(null)
    const [inviteLoading, setInviteLoading] = useState(false)
    const [inviteError, setInviteError] = useState<string | null>(null)
    const [copied, setCopied] = useState(false)

    // 試上轉正
    const [convertStudent, setConvertStudent] = useState<Student | null>(null)
    const [convertFormData, setConvertFormData] = useState<ConvertToFormalData>({
        contract_no: '', total_lessons: 1, total_amount: 0,
        start_date: '', end_date: '',
    })
    const [convertError, setConvertError] = useState<string | null>(null)
    const [convertSubmitting, setConvertSubmitting] = useState(false)
    const [convertBookings, setConvertBookings] = useState<Booking[]>([])
    const [convertBookingsLoading, setConvertBookingsLoading] = useState(false)

    const isStaff = profile?.role === 'admin' || profile?.role === 'employee'

    const fetchStudents = useCallback(async () => {
        setLoading(true)
        setError(null)
        const { data, error } = await studentsApi.list({
            page, per_page: perPage,
            search: searchTerm || undefined,
            is_active: filterActive,
            student_type: filterType || undefined,
        })
        if (error) {
            setError(error.message)
        } else if (data) {
            setStudents(data.data)
            setTotalPages(data.total_pages)
            setTotal(data.total)
        }
        setLoading(false)
    }, [page, searchTerm, filterActive, filterType])

    useEffect(() => {
        if (user) fetchStudents()
    }, [user, fetchStudents])

    useEffect(() => {
        const timer = setTimeout(() => setPage(1), 300)
        return () => clearTimeout(timer)
    }, [searchTerm])

    const openCreateModal = () => {
        setModalMode('create')
        setEditingStudent(null)
        setFormData({ student_no: '', name: '', email: '', phone: '', address: '', birth_date: '', student_type: 'formal', is_active: true })
        setFormError(null)
        setShowModal(true)
    }

    const openEditModal = (student: Student) => {
        setModalMode('edit')
        setEditingStudent(student)
        setFormData({
            student_no: student.student_no, name: student.name, email: student.email,
            phone: student.phone || '', address: student.address || '',
            birth_date: student.birth_date || '', student_type: student.student_type || 'formal',
            is_active: student.is_active,
        })
        setFormError(null)
        setShowModal(true)
    }

    const closeModal = () => { setShowModal(false); setEditingStudent(null); setFormError(null) }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setFormError(null)
        setSubmitting(true)
        try {
            if (modalMode === 'create') {
                const submitData = { ...formData }
                if (!submitData.birth_date) delete (submitData as any).birth_date
                if (!submitData.phone) delete (submitData as any).phone
                if (!submitData.address) delete (submitData as any).address
                const { error } = await studentsApi.create(submitData)
                if (error) { setFormError(error.message) } else { closeModal(); fetchStudents() }
            } else if (editingStudent) {
                const updateData: UpdateStudentData = {}
                if (formData.name !== editingStudent.name) updateData.name = formData.name
                if (formData.email !== editingStudent.email) updateData.email = formData.email
                if ((formData.phone || '') !== (editingStudent.phone || '')) updateData.phone = formData.phone || undefined
                if ((formData.address || '') !== (editingStudent.address || '')) updateData.address = formData.address || undefined
                if ((formData.birth_date || '') !== (editingStudent.birth_date || '')) updateData.birth_date = formData.birth_date || undefined
                if (formData.student_type !== editingStudent.student_type) updateData.student_type = formData.student_type
                if (formData.is_active !== editingStudent.is_active) updateData.is_active = formData.is_active
                const { error } = await studentsApi.update(editingStudent.id, updateData)
                if (error) { setFormError(error.message) } else { closeModal(); fetchStudents() }
            }
        } finally { setSubmitting(false) }
    }

    const handleDelete = async () => {
        if (!deleteConfirm) return
        setDeleting(true)
        const { error } = await studentsApi.delete(deleteConfirm.id)
        if (error) { setError(error.message) } else { setDeleteConfirm(null); fetchStudents() }
        setDeleting(false)
    }

    // === 教師偏好設定 ===
    const openPreferences = async (student: Student) => {
        setPrefStudent(student)
        setPrefLoading(true)
        setPrefError(null)
        setShowPrefForm(false)

        const [prefsRes, teachersRes, coursesRes] = await Promise.all([
            studentTeacherPreferencesApi.list(student.id),
            bookingsApi.getTeacherOptions(),
            bookingsApi.getCourseOptions(),
        ])

        if (prefsRes.error) { setPrefError(prefsRes.error.message) }
        else { setPreferences(prefsRes.data || []) }

        setTeacherOptions(teachersRes.data || [])
        setCourseOptions(coursesRes.data || [])
        setPrefLoading(false)
    }

    const closePreferences = () => {
        setPrefStudent(null)
        setPreferences([])
        setShowPrefForm(false)
        setEditingPref(null)
        setPrefError(null)
    }

    const openPrefCreate = () => {
        setPrefFormMode('create')
        setEditingPref(null)
        setPrefFormData({ course_id: '', min_teacher_level: 1, primary_teacher_id: '' })
        setPrefFormError(null)
        setShowPrefForm(true)
    }

    const openPrefEdit = (pref: StudentTeacherPreference) => {
        setPrefFormMode('edit')
        setEditingPref(pref)
        setPrefFormData({
            course_id: pref.course_id || '',
            min_teacher_level: pref.min_teacher_level,
            primary_teacher_id: pref.primary_teacher_id || '',
        })
        setPrefFormError(null)
        setShowPrefForm(true)
    }

    const handlePrefSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!prefStudent) return
        setPrefFormError(null)
        setPrefSubmitting(true)

        try {
            if (prefFormMode === 'create') {
                const createData: CreatePreferenceData = {
                    student_id: prefStudent.id,
                    min_teacher_level: prefFormData.min_teacher_level,
                    course_id: prefFormData.course_id || null,
                    primary_teacher_id: prefFormData.primary_teacher_id || null,
                }
                const { error } = await studentTeacherPreferencesApi.create(createData)
                if (error) { setPrefFormError(error.message) }
                else {
                    setShowPrefForm(false)
                    const { data } = await studentTeacherPreferencesApi.list(prefStudent.id)
                    setPreferences(data || [])
                }
            } else if (editingPref) {
                const { error } = await studentTeacherPreferencesApi.update(editingPref.id, {
                    min_teacher_level: prefFormData.min_teacher_level,
                    primary_teacher_id: prefFormData.primary_teacher_id || null,
                })
                if (error) { setPrefFormError(error.message) }
                else {
                    setShowPrefForm(false)
                    const { data } = await studentTeacherPreferencesApi.list(prefStudent.id)
                    setPreferences(data || [])
                }
            }
        } finally { setPrefSubmitting(false) }
    }

    const handlePrefDelete = async () => {
        if (!prefDeleteConfirm || !prefStudent) return
        setPrefDeleting(true)
        const { error } = await studentTeacherPreferencesApi.delete(prefDeleteConfirm.id)
        if (error) { setPrefError(error.message) }
        else {
            setPrefDeleteConfirm(null)
            const { data } = await studentTeacherPreferencesApi.list(prefStudent.id)
            setPreferences(data || [])
        }
        setPrefDeleting(false)
    }

    // === 試上轉正 ===
    const openConvertModal = async (student: Student) => {
        setConvertStudent(student)
        setConvertFormData({
            contract_no: '', total_lessons: 1, total_amount: 0,
            start_date: '', end_date: '',
        })
        setConvertError(null)
        setConvertBookings([])
        setConvertBookingsLoading(true)
        try {
            const { data } = await bookingsApi.list({ student_id: student.id, per_page: 100 })
            if (data) setConvertBookings(data.data)
        } catch {}
        setConvertBookingsLoading(false)
    }

    const handleConvert = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!convertStudent) return
        setConvertError(null)
        setConvertSubmitting(true)

        const { data, error } = await studentsApi.convertToFormal(convertStudent.id, convertFormData)
        if (error) {
            setConvertError(error.message)
        } else {
            setConvertStudent(null)
            fetchStudents()
        }
        setConvertSubmitting(false)
    }

    // === 邀請連結 ===
    const handleGenerateInvite = async (student: Student) => {
        setInviteStudent(student)
        setInviteUrl(null)
        setInviteError(null)
        setInviteLoading(true)
        setCopied(false)

        const { data, error } = await invitesApi.generate('student', student.id)
        if (error) {
            setInviteError(error.message)
        } else if (data) {
            setInviteUrl(data.invite_url)
        }
        setInviteLoading(false)
    }

    const closeInviteModal = () => {
        setInviteStudent(null)
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
            // fallback
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
                                    <GraduationCap className="w-8 h-8 text-blue-600" />
                                    學生管理
                                </h1>
                                <p className="mt-2 text-gray-600">共 {total} 位學生</p>
                            </div>
                            {isStaff && (
                                <button onClick={openCreateModal} className="btn-primary flex items-center gap-2">
                                    <Plus className="w-5 h-5" /> 新增學生
                                </button>
                            )}
                        </div>
                    </div>

                    {/* Filters */}
                    <div className="card mb-6">
                        <div className="flex flex-col sm:flex-row gap-4">
                            <div className="flex-1 relative">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                                <input type="text" placeholder="搜尋學生編號、姓名或 Email..."
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
                                <option value="formal">正式</option>
                                <option value="trial">試上</option>
                            </select>
                        </div>
                    </div>

                    {error && <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">{error}</div>}

                    {/* Table */}
                    {loading ? (
                        <div className="flex justify-center py-12"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div></div>
                    ) : students.length === 0 ? (
                        <div className="card text-center py-12">
                            <GraduationCap className="w-16 h-16 mx-auto text-gray-300 mb-4" />
                            <h3 className="text-lg font-medium text-gray-900 mb-2">沒有找到學生</h3>
                            <p className="text-gray-500">{searchTerm ? '請嘗試其他搜尋條件' : '點擊「新增學生」建立第一位學生'}</p>
                        </div>
                    ) : (
                        <div className="card overflow-hidden">
                            <table className="min-w-full divide-y divide-gray-200">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">編號</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">姓名</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">聯絡方式</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">類型</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">狀態</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">帳號</th>
                                        {isStaff && <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">操作</th>}
                                    </tr>
                                </thead>
                                <tbody className="bg-white divide-y divide-gray-200">
                                    {students.map((student) => (
                                        <tr key={student.id} className="hover:bg-gray-50">
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <span className="font-mono text-sm bg-gray-100 px-2 py-1 rounded">{student.student_no}</span>
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="font-medium text-gray-900">{student.name}</div>
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="flex flex-col gap-0.5">
                                                    <span className="text-sm text-gray-600 flex items-center gap-1"><Mail className="w-3 h-3" />{student.email}</span>
                                                    {student.phone && <span className="text-sm text-gray-500 flex items-center gap-1"><Phone className="w-3 h-3" />{student.phone}</span>}
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${student.student_type === 'trial' ? 'bg-yellow-100 text-yellow-800' : 'bg-blue-100 text-blue-800'}`}>
                                                    {student.student_type === 'trial' ? '試上' : '正式'}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                {student.is_active ? (
                                                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800"><CheckCircle className="w-3 h-3 mr-1" />啟用中</span>
                                                ) : (
                                                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800"><XCircle className="w-3 h-3 mr-1" />已停用</span>
                                                )}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                {student.email_verified_at ? (
                                                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800"><CheckCircle className="w-3 h-3 mr-1" />已驗證</span>
                                                ) : (
                                                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800"><XCircle className="w-3 h-3 mr-1" />未驗證</span>
                                                )}
                                            </td>
                                            {isStaff && (
                                                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                                    {!student.email_verified_at && (
                                                        <button onClick={() => handleGenerateInvite(student)} className="text-green-600 hover:text-green-900 mr-4" title="產生邀請連結"><UserPlus className="w-5 h-5" /></button>
                                                    )}
                                                    {student.student_type === 'trial' && (
                                                        <button onClick={() => openConvertModal(student)} className="text-amber-600 hover:text-amber-900 mr-4" title="試上轉正"><ArrowUpCircle className="w-5 h-5" /></button>
                                                    )}
                                                    <button onClick={() => openPreferences(student)} className="text-purple-600 hover:text-purple-900 mr-4" title="教師偏好設定"><Settings className="w-5 h-5" /></button>
                                                    <button onClick={() => openEditModal(student)} className="text-blue-600 hover:text-blue-900 mr-4" title="編輯"><Pencil className="w-5 h-5" /></button>
                                                    <button onClick={() => setDeleteConfirm(student)} className="text-red-600 hover:text-red-900" title="刪除"><Trash2 className="w-5 h-5" /></button>
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
                                    <h2 className="text-xl font-bold text-gray-900">{modalMode === 'create' ? '新增學生' : '編輯學生'}</h2>
                                    <button onClick={closeModal} className="text-gray-400 hover:text-gray-600"><X className="w-6 h-6" /></button>
                                </div>
                                {formError && <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{formError}</div>}
                                <form onSubmit={handleSubmit} className="space-y-4">
                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">學生編號 <span className="text-red-500">*</span></label>
                                            <input type="text" value={formData.student_no} onChange={(e) => setFormData({ ...formData, student_no: e.target.value })}
                                                className="input-field" placeholder="例如：S001" required disabled={modalMode === 'edit'} />
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
                                            <label className="block text-sm font-medium text-gray-700 mb-1">生日</label>
                                            <input type="date" value={formData.birth_date} onChange={(e) => setFormData({ ...formData, birth_date: e.target.value })} className="input-field" />
                                        </div>
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">地址</label>
                                        <input type="text" value={formData.address} onChange={(e) => setFormData({ ...formData, address: e.target.value })} className="input-field" />
                                    </div>
                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">學生類型</label>
                                            <select value={formData.student_type} onChange={(e) => setFormData({ ...formData, student_type: e.target.value })} className="input-field">
                                                <option value="formal">正式</option>
                                                <option value="trial">試上</option>
                                            </select>
                                        </div>
                                        <div className="flex items-end pb-1">
                                            <label className="flex items-center gap-2">
                                                <input type="checkbox" checked={formData.is_active} onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                                                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded" />
                                                <span className="text-sm text-gray-700">啟用</span>
                                            </label>
                                        </div>
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
                            <h3 className="text-lg font-bold text-gray-900 mb-2">確認刪除學生</h3>
                            <p className="text-gray-600 mb-6">確定要刪除學生「<span className="font-medium">{deleteConfirm.name}</span>」（{deleteConfirm.student_no}）嗎？</p>
                            <div className="flex gap-3">
                                <button onClick={() => setDeleteConfirm(null)} className="btn-secondary flex-1" disabled={deleting}>取消</button>
                                <button onClick={handleDelete} className="btn-danger flex-1" disabled={deleting}>
                                    {deleting ? <span className="flex items-center justify-center"><div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>刪除中...</span> : '確認刪除'}
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {/* 教師偏好設定 Modal */}
                {prefStudent && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                        <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                            <div className="p-6">
                                {/* Header */}
                                <div className="flex items-center justify-between mb-6">
                                    <div className="flex items-center gap-3">
                                        <button onClick={closePreferences} className="text-gray-400 hover:text-gray-600">
                                            <ArrowLeft className="w-5 h-5" />
                                        </button>
                                        <div>
                                            <h2 className="text-xl font-bold text-gray-900">教師偏好設定</h2>
                                            <p className="text-sm text-gray-500">{prefStudent.name}（{prefStudent.student_no}）</p>
                                        </div>
                                    </div>
                                    <button onClick={closePreferences} className="text-gray-400 hover:text-gray-600">
                                        <X className="w-6 h-6" />
                                    </button>
                                </div>

                                {prefError && <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{prefError}</div>}

                                {prefLoading ? (
                                    <div className="flex justify-center py-12"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div></div>
                                ) : (
                                    <>
                                        {/* 偏好列表 */}
                                        {!showPrefForm && (
                                            <>
                                                <div className="flex items-center justify-between mb-4">
                                                    <h3 className="text-sm font-medium text-gray-700">偏好列表</h3>
                                                    <button onClick={openPrefCreate} className="btn-primary text-sm flex items-center gap-1 px-3 py-1.5">
                                                        <Plus className="w-4 h-4" /> 新增偏好
                                                    </button>
                                                </div>

                                                {preferences.length === 0 ? (
                                                    <div className="text-center py-8 bg-gray-50 rounded-lg">
                                                        <Star className="w-10 h-10 mx-auto text-gray-300 mb-2" />
                                                        <p className="text-gray-500 text-sm">尚無教師偏好設定</p>
                                                        <p className="text-gray-400 text-xs mt-1">新增偏好可限制學生可預約的教師等級</p>
                                                    </div>
                                                ) : (
                                                    <div className="space-y-3">
                                                        {preferences.map((pref) => (
                                                            <div key={pref.id} className="border border-gray-200 rounded-lg p-4 hover:border-blue-200 transition-colors">
                                                                <div className="flex items-start justify-between">
                                                                    <div className="flex-1">
                                                                        <div className="flex items-center gap-2 mb-2">
                                                                            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${pref.course_id ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-800'}`}>
                                                                                {pref.course_id ? pref.course_name || '指定課程' : '全域預設'}
                                                                            </span>
                                                                        </div>
                                                                        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
                                                                            <div>
                                                                                <span className="text-gray-500">最低教師等級：</span>
                                                                                <span className="font-medium text-gray-900">Lv.{pref.min_teacher_level}</span>
                                                                            </div>
                                                                            <div>
                                                                                <span className="text-gray-500">主要教師：</span>
                                                                                <span className="font-medium text-gray-900">
                                                                                    {pref.primary_teacher_id ? (
                                                                                        <span className="inline-flex items-center gap-1">
                                                                                            <Star className="w-3 h-3 text-yellow-500 fill-yellow-500" />
                                                                                            {pref.primary_teacher_name || '未知'}
                                                                                        </span>
                                                                                    ) : '未指定'}
                                                                                </span>
                                                                            </div>
                                                                        </div>
                                                                    </div>
                                                                    <div className="flex items-center gap-2 ml-4">
                                                                        <button onClick={() => openPrefEdit(pref)} className="text-blue-600 hover:text-blue-900" title="編輯">
                                                                            <Pencil className="w-4 h-4" />
                                                                        </button>
                                                                        <button onClick={() => setPrefDeleteConfirm(pref)} className="text-red-600 hover:text-red-900" title="刪除">
                                                                            <Trash2 className="w-4 h-4" />
                                                                        </button>
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}
                                            </>
                                        )}

                                        {/* 新增/編輯偏好表單 */}
                                        {showPrefForm && (
                                            <div>
                                                <div className="flex items-center gap-2 mb-4">
                                                    <button onClick={() => setShowPrefForm(false)} className="text-gray-400 hover:text-gray-600">
                                                        <ArrowLeft className="w-4 h-4" />
                                                    </button>
                                                    <h3 className="text-sm font-medium text-gray-700">
                                                        {prefFormMode === 'create' ? '新增偏好' : '編輯偏好'}
                                                    </h3>
                                                </div>

                                                {prefFormError && <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{prefFormError}</div>}

                                                <form onSubmit={handlePrefSubmit} className="space-y-4">
                                                    {prefFormMode === 'create' && (
                                                        <div>
                                                            <label className="block text-sm font-medium text-gray-700 mb-1">適用課程</label>
                                                            <select value={prefFormData.course_id}
                                                                onChange={(e) => setPrefFormData({ ...prefFormData, course_id: e.target.value })}
                                                                className="input-field">
                                                                <option value="">全域預設（所有課程）</option>
                                                                {courseOptions.map((c) => (
                                                                    <option key={c.id} value={c.id}>{c.course_name}（{c.course_code}）</option>
                                                                ))}
                                                            </select>
                                                            <p className="text-xs text-gray-400 mt-1">選擇「全域預設」表示適用所有課程；選擇特定課程則僅適用於該課程</p>
                                                        </div>
                                                    )}

                                                    <div>
                                                        <label className="block text-sm font-medium text-gray-700 mb-1">最低教師等級</label>
                                                        <input type="number" min={1} max={10} value={prefFormData.min_teacher_level}
                                                            onChange={(e) => setPrefFormData({ ...prefFormData, min_teacher_level: parseInt(e.target.value) || 1 })}
                                                            className="input-field" />
                                                        <p className="text-xs text-gray-400 mt-1">學生只能預約等級 &ge; 此值的教師</p>
                                                    </div>

                                                    <div>
                                                        <label className="block text-sm font-medium text-gray-700 mb-1">主要教師</label>
                                                        <select value={prefFormData.primary_teacher_id}
                                                            onChange={(e) => setPrefFormData({ ...prefFormData, primary_teacher_id: e.target.value })}
                                                            className="input-field">
                                                            <option value="">不指定</option>
                                                            {teacherOptions.map((t) => (
                                                                <option key={t.id} value={t.id}>
                                                                    {t.name}（{t.teacher_no}）Lv.{t.teacher_level || 1}
                                                                </option>
                                                            ))}
                                                        </select>
                                                        <p className="text-xs text-gray-400 mt-1">主要教師會在預約時優先顯示</p>
                                                    </div>

                                                    <div className="flex gap-3 pt-4">
                                                        <button type="button" onClick={() => setShowPrefForm(false)} className="btn-secondary flex-1" disabled={prefSubmitting}>取消</button>
                                                        <button type="submit" className="btn-primary flex-1" disabled={prefSubmitting}>
                                                            {prefSubmitting ? <span className="flex items-center justify-center"><div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>處理中...</span> : prefFormMode === 'create' ? '建立' : '儲存'}
                                                        </button>
                                                    </div>
                                                </form>
                                            </div>
                                        )}
                                    </>
                                )}
                            </div>
                        </div>
                    </div>
                )}

                {/* 偏好刪除確認 */}
                {prefDeleteConfirm && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[60] p-4">
                        <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
                            <h3 className="text-lg font-bold text-gray-900 mb-2">確認刪除偏好</h3>
                            <p className="text-gray-600 mb-6">
                                確定要刪除「{prefDeleteConfirm.course_id ? prefDeleteConfirm.course_name || '指定課程' : '全域預設'}」的偏好設定嗎？
                            </p>
                            <div className="flex gap-3">
                                <button onClick={() => setPrefDeleteConfirm(null)} className="btn-secondary flex-1" disabled={prefDeleting}>取消</button>
                                <button onClick={handlePrefDelete} className="btn-danger flex-1" disabled={prefDeleting}>
                                    {prefDeleting ? <span className="flex items-center justify-center"><div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>刪除中...</span> : '確認刪除'}
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {/* 試上轉正 Modal */}
                {convertStudent && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                        <div className="bg-white rounded-xl shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
                            <div className="p-6">
                                <div className="flex items-center justify-between mb-6">
                                    <div>
                                        <h2 className="text-xl font-bold text-gray-900">試上轉正</h2>
                                        <p className="text-sm text-gray-500">{convertStudent.name}（{convertStudent.student_no}）</p>
                                    </div>
                                    <button onClick={() => setConvertStudent(null)} className="text-gray-400 hover:text-gray-600"><X className="w-6 h-6" /></button>
                                </div>

                                {convertError && <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{convertError}</div>}

                                <form onSubmit={handleConvert} className="space-y-4">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">合約編號 <span className="text-red-500">*</span></label>
                                        <input type="text" value={convertFormData.contract_no}
                                            onChange={(e) => setConvertFormData({ ...convertFormData, contract_no: e.target.value })}
                                            className="input-field" placeholder="例如：SC20260303001" required />
                                    </div>
                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">總堂數 <span className="text-red-500">*</span></label>
                                            <input type="number" min={1} value={convertFormData.total_lessons}
                                                onChange={(e) => setConvertFormData({ ...convertFormData, total_lessons: parseInt(e.target.value) || 1 })}
                                                className="input-field" required />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">合約總金額 <span className="text-red-500">*</span></label>
                                            <input type="number" min={0} step={1} value={convertFormData.total_amount}
                                                onChange={(e) => setConvertFormData({ ...convertFormData, total_amount: parseFloat(e.target.value) || 0 })}
                                                className="input-field" required />
                                        </div>
                                    </div>
                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">開始日期 <span className="text-red-500">*</span></label>
                                            <input type="date" value={convertFormData.start_date}
                                                onChange={(e) => setConvertFormData({ ...convertFormData, start_date: e.target.value })}
                                                className="input-field" required />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">結束日期 <span className="text-red-500">*</span></label>
                                            <input type="date" value={convertFormData.end_date}
                                                onChange={(e) => setConvertFormData({ ...convertFormData, end_date: e.target.value })}
                                                className="input-field" required />
                                        </div>
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">關聯試上預約（選填）</label>
                                        {convertBookingsLoading ? (
                                            <div className="text-sm text-gray-400">載入預約中...</div>
                                        ) : convertBookings.length > 0 ? (
                                            <select
                                                value={convertFormData.booking_id || ''}
                                                onChange={(e) => {
                                                    const bookingId = e.target.value || undefined
                                                    const selectedBooking = convertBookings.find(b => b.id === bookingId)
                                                    setConvertFormData({
                                                        ...convertFormData,
                                                        booking_id: bookingId,
                                                        teacher_id: selectedBooking?.teacher_id || convertFormData.teacher_id,
                                                    })
                                                }}
                                                className="input-field"
                                            >
                                                <option value="">不選擇</option>
                                                {convertBookings.map(b => (
                                                    <option key={b.id} value={b.id}>
                                                        {b.booking_date} {b.start_time}-{b.end_time} [{b.teacher_name || b.teacher_id}]
                                                    </option>
                                                ))}
                                            </select>
                                        ) : (
                                            <div className="text-sm text-gray-400">無預約紀錄</div>
                                        )}
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">指定教師（選填，計算轉正獎金）</label>
                                        <select
                                            value={convertFormData.teacher_id || ''}
                                            onChange={(e) => setConvertFormData({ ...convertFormData, teacher_id: e.target.value || undefined })}
                                            className="input-field"
                                        >
                                            <option value="">不選擇</option>
                                            {teacherOptions.map(t => (
                                                <option key={t.id} value={t.id}>{t.name}（{t.teacher_no}）</option>
                                            ))}
                                        </select>
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">備註</label>
                                        <textarea value={convertFormData.notes || ''}
                                            onChange={(e) => setConvertFormData({ ...convertFormData, notes: e.target.value || undefined })}
                                            className="input-field" rows={2} />
                                    </div>
                                    <div className="flex gap-3 pt-4">
                                        <button type="button" onClick={() => setConvertStudent(null)} className="btn-secondary flex-1" disabled={convertSubmitting}>取消</button>
                                        <button type="submit" className="btn-primary flex-1" disabled={convertSubmitting}>
                                            {convertSubmitting ? <span className="flex items-center justify-center"><div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>處理中...</span> : '確認轉正'}
                                        </button>
                                    </div>
                                </form>
                            </div>
                        </div>
                    </div>
                )}

                {/* 邀請連結 Modal */}
                {inviteStudent && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                        <div className="bg-white rounded-xl shadow-xl max-w-lg w-full p-6">
                            <div className="flex items-center justify-between mb-4">
                                <h3 className="text-lg font-bold text-gray-900">邀請連結</h3>
                                <button onClick={closeInviteModal} className="text-gray-400 hover:text-gray-600"><X className="w-6 h-6" /></button>
                            </div>
                            <p className="text-sm text-gray-600 mb-4">
                                學生：<span className="font-medium">{inviteStudent.name}</span>（{inviteStudent.email}）
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

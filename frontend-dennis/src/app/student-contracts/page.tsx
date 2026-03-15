'use client'

import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '@/lib/hooks/useAuth'
import {
    studentContractsApi,
    StudentContract,
    StudentContractDetail,
    StudentContractLeaveRecord,
    CreateStudentContractData,
    UpdateStudentContractData,
    CreateDetailData,
    UpdateDetailData,
    CreateLeaveRecordData,
    ContractStatus,
    DetailType,
    StudentOption,
    CourseOption,
} from '@/lib/api/studentContracts'
import { Plus, Pencil, Trash2, Search, X, FileText, Calendar, CheckCircle, Clock, XCircle, AlertCircle, Upload, Download } from 'lucide-react'
import DashboardLayout from '@/components/DashboardLayout'

const statusLabels: Record<ContractStatus, string> = {
    pending: '待生效',
    active: '生效中',
    expired: '已過期',
    terminated: '已終止',
}

const statusColors: Record<ContractStatus, { bg: string, text: string }> = {
    pending: { bg: 'bg-yellow-100', text: 'text-yellow-800' },
    active: { bg: 'bg-green-100', text: 'text-green-800' },
    expired: { bg: 'bg-gray-100', text: 'text-gray-800' },
    terminated: { bg: 'bg-red-100', text: 'text-red-800' },
}

const statusIcons: Record<ContractStatus, React.ReactNode> = {
    pending: <Clock className="w-3 h-3 mr-1" />,
    active: <CheckCircle className="w-3 h-3 mr-1" />,
    expired: <XCircle className="w-3 h-3 mr-1" />,
    terminated: <AlertCircle className="w-3 h-3 mr-1" />,
}

const detailTypeLabels: Record<DetailType, string> = {
    lesson_price: '課程單價',
    discount: '優惠折扣',
    compensation: '補償堂數',
}

const detailTypeColors: Record<DetailType, { bg: string, text: string }> = {
    lesson_price: { bg: 'bg-blue-100', text: 'text-blue-800' },
    discount: { bg: 'bg-orange-100', text: 'text-orange-800' },
    compensation: { bg: 'bg-green-100', text: 'text-green-800' },
}

export default function StudentContractsPage() {
    const { user, profile } = useAuth()

    // State
    const [contracts, setContracts] = useState<StudentContract[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [searchTerm, setSearchTerm] = useState('')
    const [filterStatus, setFilterStatus] = useState<ContractStatus | ''>('')
    const [filterStudent, setFilterStudent] = useState('')

    // Options for dropdowns
    const [studentOptions, setStudentOptions] = useState<StudentOption[]>([])
    const [courseOptions, setCourseOptions] = useState<CourseOption[]>([])

    // Pagination
    const [page, setPage] = useState(1)
    const [totalPages, setTotalPages] = useState(1)
    const [total, setTotal] = useState(0)
    const perPage = 10

    // Modal state
    const [showModal, setShowModal] = useState(false)
    const [modalMode, setModalMode] = useState<'create' | 'edit'>('create')
    const [editingContract, setEditingContract] = useState<StudentContract | null>(null)
    const [formData, setFormData] = useState<CreateStudentContractData>({
        student_id: '',
        contract_status: 'pending',
        start_date: '',
        end_date: '',
        total_lessons: 10,
        remaining_lessons: 10,
        total_amount: 0,
        total_leave_allowed: 20,
        is_recurring: false,
        notes: '',
    })
    const [formError, setFormError] = useState<string | null>(null)
    const [submitting, setSubmitting] = useState(false)

    // Details state (for edit modal)
    const [details, setDetails] = useState<StudentContractDetail[]>([])
    const [detailsLoading, setDetailsLoading] = useState(false)
    const [showDetailForm, setShowDetailForm] = useState(false)
    const [editingDetail, setEditingDetail] = useState<StudentContractDetail | null>(null)
    const [detailFormData, setDetailFormData] = useState<CreateDetailData>({
        detail_type: 'lesson_price',
        course_id: undefined,
        description: '',
        amount: 0,
        notes: '',
    })
    const [detailFormError, setDetailFormError] = useState<string | null>(null)
    const [detailSubmitting, setDetailSubmitting] = useState(false)
    // Filtered course options for lesson_price detail (only student's enrolled courses)
    const [filteredCourseOptions, setFilteredCourseOptions] = useState<CourseOption[]>([])

    // Leave records state (for edit modal)
    const [leaveRecords, setLeaveRecords] = useState<StudentContractLeaveRecord[]>([])
    const [leaveRecordsLoading, setLeaveRecordsLoading] = useState(false)
    const [leaveFormData, setLeaveFormData] = useState<CreateLeaveRecordData>({
        leave_date: '',
        reason: '',
    })
    const [leaveFormError, setLeaveFormError] = useState<string | null>(null)
    const [leaveSubmitting, setLeaveSubmitting] = useState(false)

    // Delete confirmation
    const [deleteConfirm, setDeleteConfirm] = useState<StudentContract | null>(null)
    const [deleting, setDeleting] = useState(false)

    // Upload state
    const [uploading, setUploading] = useState<string | null>(null)

    // Fetch options
    const fetchOptions = useCallback(async () => {
        const [studentsResult, coursesResult] = await Promise.all([
            studentContractsApi.getStudentOptions(),
            studentContractsApi.getCourseOptions(),
        ])

        if (studentsResult.data) setStudentOptions(studentsResult.data)
        if (coursesResult.data) setCourseOptions(coursesResult.data)
    }, [])

    // Fetch contracts
    const fetchContracts = useCallback(async () => {
        setLoading(true)
        setError(null)

        const { data, error } = await studentContractsApi.list({
            page,
            per_page: perPage,
            search: searchTerm || undefined,
            contract_status: filterStatus || undefined,
            student_id: filterStudent || undefined,
        })

        if (error) {
            setError(error.message)
        } else if (data) {
            setContracts(data.data)
            setTotalPages(data.total_pages)
            setTotal(data.total)
        }

        setLoading(false)
    }, [page, searchTerm, filterStatus, filterStudent])

    useEffect(() => {
        if (user) {
            fetchOptions()
            fetchContracts()
        }
    }, [user, fetchOptions, fetchContracts])

    // Search with debounce
    useEffect(() => {
        const timer = setTimeout(() => {
            setPage(1)
        }, 300)
        return () => clearTimeout(timer)
    }, [searchTerm])

    // Fetch details for edit modal
    const fetchDetails = useCallback(async (contractId: string) => {
        setDetailsLoading(true)
        const { data, error } = await studentContractsApi.listDetails(contractId)
        if (data) setDetails(data)
        if (error) setError(error.message)
        setDetailsLoading(false)
    }, [])

    // Fetch leave records for edit modal
    const fetchLeaveRecords = useCallback(async (contractId: string) => {
        setLeaveRecordsLoading(true)
        const { data, error } = await studentContractsApi.listLeaveRecords(contractId)
        if (data) setLeaveRecords(data)
        if (error) setError(error.message)
        setLeaveRecordsLoading(false)
    }, [])

    // Fetch filtered course options for a student
    const fetchFilteredCourses = useCallback(async (studentId: string) => {
        const { data } = await studentContractsApi.getCourseOptions(studentId)
        setFilteredCourseOptions(data || [])
    }, [])

    // Modal handlers
    const openCreateModal = () => {
        setModalMode('create')
        setEditingContract(null)
        setDetails([])
        setLeaveRecords([])
        const today = new Date().toISOString().split('T')[0]
        const nextYear = new Date()
        nextYear.setFullYear(nextYear.getFullYear() + 1)
        const endDate = nextYear.toISOString().split('T')[0]

        setFormData({
            student_id: '',
            contract_status: 'pending',
            start_date: today,
            end_date: endDate,
            total_lessons: 10,
            remaining_lessons: 10,
            total_amount: 0,
            total_leave_allowed: 20,
            is_recurring: false,
            notes: '',
        })
        setFormError(null)
        setShowDetailForm(false)
        setEditingDetail(null)
        setShowModal(true)
    }

    const openEditModal = (contract: StudentContract) => {
        setModalMode('edit')
        setEditingContract(contract)
        setFormData({
            student_id: contract.student_id,
            contract_status: contract.contract_status,
            start_date: contract.start_date,
            end_date: contract.end_date,
            total_lessons: contract.total_lessons,
            remaining_lessons: contract.remaining_lessons,
            total_amount: contract.total_amount ?? 0,
            total_leave_allowed: contract.total_leave_allowed,
            is_recurring: contract.is_recurring,
            notes: contract.notes || '',
        })
        setDetails(contract.details || [])
        setLeaveRecords(contract.leave_records || [])
        setFormError(null)
        setShowDetailForm(false)
        setEditingDetail(null)
        setLeaveFormData({ leave_date: '', reason: '' })
        setLeaveFormError(null)
        setShowModal(true)
        // Refresh from server
        fetchDetails(contract.id)
        fetchLeaveRecords(contract.id)
        // Fetch filtered courses for this student
        if (contract.student_id) {
            fetchFilteredCourses(contract.student_id)
        }
    }

    const closeModal = () => {
        setShowModal(false)
        setEditingContract(null)
        setFormError(null)
        setShowDetailForm(false)
        setEditingDetail(null)
    }

    // Auto-calculate total_leave_allowed when total_lessons changes (create mode)
    useEffect(() => {
        if (showModal && modalMode === 'create') {
            setFormData(prev => ({ ...prev, total_leave_allowed: prev.total_lessons * 2 }))
        }
    }, [formData.total_lessons, showModal, modalMode])

    // Form submit
    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setFormError(null)
        setSubmitting(true)

        try {
            if (modalMode === 'create') {
                const { data, error } = await studentContractsApi.create(formData)
                if (error) {
                    setFormError(error.message)
                } else {
                    closeModal()
                    fetchContracts()
                }
            } else if (editingContract) {
                const updateData: UpdateStudentContractData = {}
                if (formData.student_id !== editingContract.student_id) updateData.student_id = formData.student_id
                if (formData.contract_status !== editingContract.contract_status) updateData.contract_status = formData.contract_status
                if (formData.start_date !== editingContract.start_date) updateData.start_date = formData.start_date
                if (formData.end_date !== editingContract.end_date) updateData.end_date = formData.end_date
                if (formData.total_lessons !== editingContract.total_lessons) updateData.total_lessons = formData.total_lessons
                if (formData.remaining_lessons !== editingContract.remaining_lessons) updateData.remaining_lessons = formData.remaining_lessons
                if (formData.total_amount !== (editingContract.total_amount ?? 0)) updateData.total_amount = formData.total_amount
                if ((formData.total_leave_allowed ?? 0) !== editingContract.total_leave_allowed) updateData.total_leave_allowed = formData.total_leave_allowed
                if ((formData.is_recurring ?? false) !== editingContract.is_recurring) updateData.is_recurring = formData.is_recurring
                if (formData.notes !== (editingContract.notes || '')) updateData.notes = formData.notes

                const { data, error } = await studentContractsApi.update(editingContract.id, updateData)
                if (error) {
                    setFormError(error.message)
                } else {
                    closeModal()
                    fetchContracts()
                }
            }
        } finally {
            setSubmitting(false)
        }
    }

    // Detail form handlers
    const openAddDetail = () => {
        setEditingDetail(null)
        setDetailFormData({
            detail_type: 'lesson_price',
            course_id: undefined,
            description: '',
            amount: 0,
            notes: '',
        })
        setDetailFormError(null)
        setShowDetailForm(true)
    }

    const openEditDetail = (detail: StudentContractDetail) => {
        setEditingDetail(detail)
        setDetailFormData({
            detail_type: detail.detail_type,
            course_id: detail.course_id,
            description: detail.description || '',
            amount: detail.amount,
            notes: detail.notes || '',
        })
        setDetailFormError(null)
        setShowDetailForm(true)
    }

    const handleDetailSubmit = async () => {
        if (!editingContract) return
        setDetailFormError(null)
        setDetailSubmitting(true)

        try {
            if (editingDetail) {
                const updateData: UpdateDetailData = {
                    description: detailFormData.description || undefined,
                    amount: detailFormData.amount,
                    notes: detailFormData.notes || undefined,
                }
                const { error } = await studentContractsApi.updateDetail(
                    editingContract.id, editingDetail.id, updateData
                )
                if (error) {
                    setDetailFormError(error.message)
                    return
                }
            } else {
                const { error } = await studentContractsApi.createDetail(
                    editingContract.id, detailFormData
                )
                if (error) {
                    setDetailFormError(error.message)
                    return
                }
            }

            setShowDetailForm(false)
            setEditingDetail(null)
            await fetchDetails(editingContract.id)
            await fetchContracts()

            // 補償堂數連動：重新取得合約以更新 remaining_lessons
            const { data: refreshed } = await studentContractsApi.get(editingContract.id)
            if (refreshed) {
                setEditingContract(refreshed)
                setFormData(prev => ({ ...prev, remaining_lessons: refreshed.remaining_lessons }))
            }
        } finally {
            setDetailSubmitting(false)
        }
    }

    const handleDeleteDetail = async (detailId: string) => {
        if (!editingContract) return
        const { error } = await studentContractsApi.deleteDetail(editingContract.id, detailId)
        if (error) {
            setError(error.message)
        } else {
            await fetchDetails(editingContract.id)
            await fetchContracts()

            // 補償堂數連動：重新取得合約以更新 remaining_lessons
            const { data: refreshed } = await studentContractsApi.get(editingContract.id)
            if (refreshed) {
                setEditingContract(refreshed)
                setFormData(prev => ({ ...prev, remaining_lessons: refreshed.remaining_lessons }))
            }
        }
    }

    // Leave record handlers
    const handleAddLeaveRecord = async () => {
        if (!editingContract || !leaveFormData.leave_date) return
        setLeaveFormError(null)
        setLeaveSubmitting(true)

        try {
            const { error } = await studentContractsApi.createLeaveRecord(
                editingContract.id, leaveFormData
            )
            if (error) {
                setLeaveFormError(error.message)
                return
            }
            setLeaveFormData({ leave_date: '', reason: '' })
            await fetchLeaveRecords(editingContract.id)
            fetchContracts()
        } finally {
            setLeaveSubmitting(false)
        }
    }

    const handleDeleteLeaveRecord = async (recordId: string) => {
        if (!editingContract) return
        const { error } = await studentContractsApi.deleteLeaveRecord(editingContract.id, recordId)
        if (error) {
            setError(error.message)
        } else {
            await fetchLeaveRecords(editingContract.id)
            fetchContracts()
        }
    }

    // Delete handler
    const handleDelete = async () => {
        if (!deleteConfirm) return
        setDeleting(true)

        const { success, error } = await studentContractsApi.delete(deleteConfirm.id)

        if (error) {
            setError(error.message)
        } else {
            setDeleteConfirm(null)
            fetchContracts()
        }

        setDeleting(false)
    }

    // Download handler
    const handleDownload = async (contractId: string) => {
        const { url, error } = await studentContractsApi.downloadFile(contractId)
        if (error) {
            setError(error.message)
        } else if (url) {
            window.open(url, '_blank')
        }
    }

    // Upload handler
    const handleUpload = async (contractId: string, file: File) => {
        setUploading(contractId)
        const { data, error } = await studentContractsApi.uploadFile(contractId, file)
        if (error) {
            setError(error.message)
        } else {
            fetchContracts()
        }
        setUploading(null)
    }

    const isStaff = profile?.employee_id != null

    const formatDate = (dateStr: string) => {
        return new Date(dateStr).toLocaleDateString('zh-TW')
    }

    const formatCurrency = (amount: number) => {
        return new Intl.NumberFormat('zh-TW', { style: 'currency', currency: 'TWD', minimumFractionDigits: 0 }).format(amount)
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
                                    <FileText className="w-8 h-8 text-blue-600" />
                                    學生合約管理
                                </h1>
                                <p className="mt-2 text-gray-600">
                                    共 {total} 份合約
                                </p>
                            </div>
                            {isStaff && (
                                <button
                                    onClick={openCreateModal}
                                    className="btn-primary flex items-center gap-2"
                                >
                                    <Plus className="w-5 h-5" />
                                    新增合約
                                </button>
                            )}
                        </div>
                    </div>

                    {/* Filters */}
                    <div className="card mb-6">
                        <div className="flex flex-col sm:flex-row gap-4">
                            {/* Search */}
                            <div className="flex-1 relative">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                                <input
                                    type="text"
                                    placeholder="搜尋合約編號..."
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                    className="input-field pl-10"
                                />
                                {searchTerm && (
                                    <button
                                        onClick={() => setSearchTerm('')}
                                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                                    >
                                        <X className="w-5 h-5" />
                                    </button>
                                )}
                            </div>

                            {/* Filter by status */}
                            <select
                                value={filterStatus}
                                onChange={(e) => {
                                    setFilterStatus(e.target.value as ContractStatus | '')
                                    setPage(1)
                                }}
                                className="input-field w-full sm:w-40"
                            >
                                <option value="">全部狀態</option>
                                <option value="pending">待生效</option>
                                <option value="active">生效中</option>
                                <option value="expired">已過期</option>
                                <option value="terminated">已終止</option>
                            </select>

                            {/* Filter by student */}
                            <select
                                value={filterStudent}
                                onChange={(e) => {
                                    setFilterStudent(e.target.value)
                                    setPage(1)
                                }}
                                className="input-field w-full sm:w-48"
                            >
                                <option value="">全部學生</option>
                                {studentOptions.map((s) => (
                                    <option key={s.id} value={s.id}>{s.name}</option>
                                ))}
                            </select>
                        </div>
                    </div>

                    {/* Error */}
                    {error && (
                        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
                            {error}
                        </div>
                    )}

                    {/* Contract List */}
                    {loading ? (
                        <div className="flex justify-center py-12">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                        </div>
                    ) : contracts.length === 0 ? (
                        <div className="card text-center py-12">
                            <FileText className="w-16 h-16 mx-auto text-gray-300 mb-4" />
                            <h3 className="text-lg font-medium text-gray-900 mb-2">沒有找到合約</h3>
                            <p className="text-gray-500">
                                {searchTerm ? '請嘗試其他搜尋條件' : '點擊「新增合約」建立第一份學生合約'}
                            </p>
                        </div>
                    ) : (
                        <div className="card overflow-hidden">
                            <div className="overflow-x-auto">
                                <table className="min-w-full divide-y divide-gray-200">
                                    <thead className="bg-gray-50">
                                        <tr>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                合約編號
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                學生
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                狀態
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                帶狀
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                合約期間
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                堂數
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                總金額
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                請假
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                合約檔案
                                            </th>
                                            {isStaff && (
                                                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    操作
                                                </th>
                                            )}
                                        </tr>
                                    </thead>
                                    <tbody className="bg-white divide-y divide-gray-200">
                                        {contracts.map((contract) => (
                                            <tr key={contract.id} className="hover:bg-gray-50">
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <span className="font-mono text-sm bg-gray-100 px-2 py-1 rounded">
                                                        {contract.contract_no}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <span className="font-medium text-gray-900">
                                                        {contract.student_name || '-'}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColors[contract.contract_status].bg} ${statusColors[contract.contract_status].text}`}>
                                                        {statusIcons[contract.contract_status]}
                                                        {statusLabels[contract.contract_status]}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${contract.is_recurring ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-800'}`}>
                                                        {contract.is_recurring ? '是' : '否'}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <div className="flex items-center text-sm text-gray-600">
                                                        <Calendar className="w-4 h-4 mr-1" />
                                                        {formatDate(contract.start_date)} ~ {formatDate(contract.end_date)}
                                                    </div>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <span className="text-gray-900">
                                                        {contract.remaining_lessons} / {contract.total_lessons}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <span className="text-gray-900">
                                                        {contract.total_amount != null ? formatCurrency(contract.total_amount) : '-'}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <span className="text-gray-900">
                                                        {contract.used_leave_count} / {contract.total_leave_allowed}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    {contract.contract_file_path ? (
                                                        <div className="flex items-center gap-2">
                                                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                                                <CheckCircle className="w-3 h-3 mr-1" />
                                                                已上傳
                                                            </span>
                                                            {isStaff && (
                                                                <button
                                                                    onClick={() => handleDownload(contract.id)}
                                                                    className="text-blue-600 hover:text-blue-900"
                                                                    title="下載"
                                                                >
                                                                    <Download className="w-4 h-4" />
                                                                </button>
                                                            )}
                                                        </div>
                                                    ) : (
                                                        <span className="text-gray-400 text-sm">-</span>
                                                    )}
                                                    {isStaff && (
                                                        <>
                                                            <input
                                                                type="file"
                                                                accept=".pdf"
                                                                id={`upload-${contract.id}`}
                                                                className="hidden"
                                                                onChange={(e) => {
                                                                    const file = e.target.files?.[0]
                                                                    if (file) {
                                                                        handleUpload(contract.id, file)
                                                                        e.target.value = ''
                                                                    }
                                                                }}
                                                            />
                                                            <button
                                                                onClick={() => document.getElementById(`upload-${contract.id}`)?.click()}
                                                                disabled={uploading === contract.id}
                                                                className="mt-1 inline-flex items-center text-xs text-blue-600 hover:text-blue-900 disabled:opacity-50"
                                                                title="上傳合約 PDF"
                                                            >
                                                                {uploading === contract.id ? (
                                                                    <span className="flex items-center">
                                                                        <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-blue-600 mr-1"></div>
                                                                        上傳中...
                                                                    </span>
                                                                ) : (
                                                                    <>
                                                                        <Upload className="w-3 h-3 mr-1" />
                                                                        {contract.contract_file_path ? '重新上傳' : '上傳'}
                                                                    </>
                                                                )}
                                                            </button>
                                                        </>
                                                    )}
                                                </td>
                                                {isStaff && (
                                                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                                        <button
                                                            onClick={() => openEditModal(contract)}
                                                            className="text-blue-600 hover:text-blue-900 mr-4"
                                                            title="編輯"
                                                        >
                                                            <Pencil className="w-5 h-5" />
                                                        </button>
                                                        <button
                                                            onClick={() => setDeleteConfirm(contract)}
                                                            className="text-red-600 hover:text-red-900"
                                                            title="刪除"
                                                        >
                                                            <Trash2 className="w-5 h-5" />
                                                        </button>
                                                    </td>
                                                )}
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {/* Pagination */}
                    {totalPages > 1 && (
                        <div className="mt-6 flex items-center justify-between">
                            <div className="text-sm text-gray-500">
                                顯示 {(page - 1) * perPage + 1} - {Math.min(page * perPage, total)} 共 {total} 項
                            </div>
                            <div className="flex gap-2">
                                <button
                                    onClick={() => setPage(p => Math.max(1, p - 1))}
                                    disabled={page === 1}
                                    className="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    上一頁
                                </button>
                                <span className="px-4 py-2 text-gray-600">
                                    {page} / {totalPages}
                                </span>
                                <button
                                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                                    disabled={page === totalPages}
                                    className="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    下一頁
                                </button>
                            </div>
                        </div>
                    )}
                </div>

                {/* Create/Edit Modal */}
                {showModal && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                        <div className="bg-white rounded-xl shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
                            <div className="p-6">
                                <div className="flex items-center justify-between mb-6">
                                    <h2 className="text-xl font-bold text-gray-900">
                                        {modalMode === 'create' ? '新增學生合約' : '編輯學生合約'}
                                    </h2>
                                    <button
                                        onClick={closeModal}
                                        className="text-gray-400 hover:text-gray-600"
                                    >
                                        <X className="w-6 h-6" />
                                    </button>
                                </div>

                                {formError && (
                                    <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                                        {formError}
                                    </div>
                                )}

                                <form onSubmit={handleSubmit} className="space-y-4">
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                學生 <span className="text-red-500">*</span>
                                            </label>
                                            <select
                                                value={formData.student_id}
                                                onChange={(e) => setFormData({ ...formData, student_id: e.target.value })}
                                                className="input-field"
                                                required
                                            >
                                                <option value="">請選擇學生</option>
                                                {studentOptions.map((s) => (
                                                    <option key={s.id} value={s.id}>{s.student_no} - {s.name}</option>
                                                ))}
                                            </select>
                                        </div>

                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                合約狀態 <span className="text-red-500">*</span>
                                            </label>
                                            <select
                                                value={formData.contract_status}
                                                onChange={(e) => setFormData({ ...formData, contract_status: e.target.value as ContractStatus })}
                                                className="input-field"
                                                required
                                            >
                                                <option value="pending">待生效</option>
                                                <option value="active">生效中</option>
                                                <option value="expired">已過期</option>
                                                <option value="terminated">已終止</option>
                                            </select>
                                        </div>

                                        <div className="flex items-center">
                                            <label className="relative inline-flex items-center cursor-pointer">
                                                <input
                                                    type="checkbox"
                                                    checked={formData.is_recurring ?? false}
                                                    onChange={(e) => setFormData({ ...formData, is_recurring: e.target.checked })}
                                                    className="sr-only peer"
                                                />
                                                <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-blue-600"></div>
                                                <span className="ml-2 text-sm font-medium text-gray-700">帶狀學生</span>
                                            </label>
                                        </div>

                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                開始日期 <span className="text-red-500">*</span>
                                            </label>
                                            <input
                                                type="date"
                                                value={formData.start_date}
                                                onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                                                className="input-field"
                                                required
                                            />
                                        </div>

                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                結束日期 <span className="text-red-500">*</span>
                                            </label>
                                            <input
                                                type="date"
                                                value={formData.end_date}
                                                onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                                                className="input-field"
                                                required
                                            />
                                        </div>

                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                總堂數 <span className="text-red-500">*</span>
                                            </label>
                                            <input
                                                type="number"
                                                value={formData.total_lessons}
                                                onChange={(e) => setFormData({ ...formData, total_lessons: parseInt(e.target.value) || 0 })}
                                                className="input-field"
                                                min={1}
                                                required
                                            />
                                        </div>

                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                剩餘堂數 <span className="text-red-500">*</span>
                                            </label>
                                            <input
                                                type="number"
                                                value={formData.remaining_lessons}
                                                onChange={(e) => setFormData({ ...formData, remaining_lessons: parseInt(e.target.value) || 0 })}
                                                className="input-field"
                                                min={0}
                                                required
                                            />
                                        </div>

                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                合約總金額 <span className="text-red-500">*</span>
                                            </label>
                                            <input
                                                type="number"
                                                value={formData.total_amount}
                                                onChange={(e) => setFormData({ ...formData, total_amount: parseFloat(e.target.value) || 0 })}
                                                className="input-field"
                                                min={0}
                                                step={1}
                                                required
                                            />
                                        </div>

                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                可請假次數
                                            </label>
                                            <input
                                                type="number"
                                                value={formData.total_leave_allowed ?? 0}
                                                onChange={(e) => setFormData({ ...formData, total_leave_allowed: parseInt(e.target.value) || 0 })}
                                                className="input-field"
                                                min={0}
                                            />
                                            <p className="text-xs text-gray-500 mt-1">
                                                預設 = 總堂數 x 2 = {formData.total_lessons * 2}
                                            </p>
                                        </div>

                                        {modalMode === 'edit' && editingContract && (
                                            <div>
                                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                                    已請假次數
                                                </label>
                                                <input
                                                    type="number"
                                                    value={editingContract.used_leave_count}
                                                    className="input-field bg-gray-50"
                                                    disabled
                                                />
                                            </div>
                                        )}
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            備註
                                        </label>
                                        <textarea
                                            value={formData.notes}
                                            onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                                            className="input-field"
                                            placeholder="合約備註..."
                                            rows={3}
                                        />
                                    </div>

                                    {/* Contract Details Section (edit mode only) */}
                                    {modalMode === 'edit' && editingContract && (
                                        <div className="border-t pt-4 mt-4">
                                            <div className="flex items-center justify-between mb-3">
                                                <h3 className="text-lg font-semibold text-gray-900">合約明細</h3>
                                                <button
                                                    type="button"
                                                    onClick={openAddDetail}
                                                    className="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1"
                                                >
                                                    <Plus className="w-4 h-4" />
                                                    新增明細
                                                </button>
                                            </div>

                                            {/* Detail Form */}
                                            {showDetailForm && (
                                                <div className="mb-4 p-4 bg-gray-50 rounded-lg border">
                                                    <h4 className="text-sm font-medium text-gray-700 mb-3">
                                                        {editingDetail ? '編輯明細' : '新增明細'}
                                                    </h4>
                                                    {detailFormError && (
                                                        <div className="mb-3 p-2 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
                                                            {detailFormError}
                                                        </div>
                                                    )}
                                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                                        {!editingDetail && (
                                                            <div>
                                                                <label className="block text-xs font-medium text-gray-600 mb-1">類型</label>
                                                                <select
                                                                    value={detailFormData.detail_type}
                                                                    onChange={(e) => {
                                                                        const dt = e.target.value as DetailType
                                                                        setDetailFormData({
                                                                            ...detailFormData,
                                                                            detail_type: dt,
                                                                            course_id: dt !== 'lesson_price' ? undefined : detailFormData.course_id,
                                                                        })
                                                                    }}
                                                                    className="input-field text-sm"
                                                                >
                                                                    <option value="lesson_price">課程單價</option>
                                                                    <option value="discount">優惠折扣</option>
                                                                    <option value="compensation">補償堂數</option>
                                                                </select>
                                                            </div>
                                                        )}
                                                        {!editingDetail && detailFormData.detail_type === 'lesson_price' && (
                                                            <div>
                                                                <label className="block text-xs font-medium text-gray-600 mb-1">課程</label>
                                                                <select
                                                                    value={detailFormData.course_id || ''}
                                                                    onChange={(e) => setDetailFormData({ ...detailFormData, course_id: e.target.value || undefined })}
                                                                    className="input-field text-sm"
                                                                    required
                                                                >
                                                                    <option value="">請選擇課程</option>
                                                                    {filteredCourseOptions.map((c) => (
                                                                        <option key={c.id} value={c.id}>{c.course_code} - {c.course_name}</option>
                                                                    ))}
                                                                </select>
                                                                {filteredCourseOptions.length === 0 && (
                                                                    <p className="text-xs text-orange-600 mt-1">
                                                                        此學生尚未選修任何課程，請先至「學生選課」新增
                                                                    </p>
                                                                )}
                                                            </div>
                                                        )}
                                                        <div>
                                                            <label className="block text-xs font-medium text-gray-600 mb-1">說明</label>
                                                            <input
                                                                type="text"
                                                                value={detailFormData.description || ''}
                                                                onChange={(e) => setDetailFormData({ ...detailFormData, description: e.target.value })}
                                                                className="input-field text-sm"
                                                                placeholder="說明文字"
                                                                maxLength={100}
                                                            />
                                                        </div>
                                                        <div>
                                                            <label className="block text-xs font-medium text-gray-600 mb-1">金額</label>
                                                            <input
                                                                type="number"
                                                                value={detailFormData.amount}
                                                                onChange={(e) => setDetailFormData({ ...detailFormData, amount: parseFloat(e.target.value) || 0 })}
                                                                className="input-field text-sm"
                                                                step="0.01"
                                                                required
                                                            />
                                                        </div>
                                                    </div>
                                                    <div className="mt-3">
                                                        <label className="block text-xs font-medium text-gray-600 mb-1">備註</label>
                                                        <input
                                                            type="text"
                                                            value={detailFormData.notes || ''}
                                                            onChange={(e) => setDetailFormData({ ...detailFormData, notes: e.target.value })}
                                                            className="input-field text-sm"
                                                            placeholder="備註"
                                                        />
                                                    </div>
                                                    <div className="flex gap-2 mt-3">
                                                        <button
                                                            type="button"
                                                            onClick={() => { setShowDetailForm(false); setEditingDetail(null) }}
                                                            className="btn-secondary text-sm px-3 py-1"
                                                        >
                                                            取消
                                                        </button>
                                                        <button
                                                            type="button"
                                                            onClick={handleDetailSubmit}
                                                            disabled={detailSubmitting}
                                                            className="btn-primary text-sm px-3 py-1"
                                                        >
                                                            {detailSubmitting ? '處理中...' : editingDetail ? '更新' : '新增'}
                                                        </button>
                                                    </div>
                                                </div>
                                            )}

                                            {/* Details List */}
                                            {detailsLoading ? (
                                                <div className="text-center py-4">
                                                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600 mx-auto"></div>
                                                </div>
                                            ) : details.length === 0 ? (
                                                <p className="text-sm text-gray-500 py-2">尚無明細</p>
                                            ) : (
                                                <div className="space-y-2">
                                                    {details.map((detail) => (
                                                        <div key={detail.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                                                            <div className="flex items-center gap-3 flex-1 min-w-0">
                                                                <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${detailTypeColors[detail.detail_type].bg} ${detailTypeColors[detail.detail_type].text}`}>
                                                                    {detailTypeLabels[detail.detail_type]}
                                                                </span>
                                                                <span className="text-sm text-gray-700 truncate">
                                                                    {detail.course_name || detail.description || '-'}
                                                                </span>
                                                                <span className="text-sm font-medium text-gray-900 whitespace-nowrap">
                                                                    {formatCurrency(detail.amount)}
                                                                </span>
                                                            </div>
                                                            <div className="flex items-center gap-1 ml-2">
                                                                <button
                                                                    type="button"
                                                                    onClick={() => openEditDetail(detail)}
                                                                    className="text-blue-600 hover:text-blue-800 p-1"
                                                                    title="編輯"
                                                                >
                                                                    <Pencil className="w-4 h-4" />
                                                                </button>
                                                                <button
                                                                    type="button"
                                                                    onClick={() => handleDeleteDetail(detail.id)}
                                                                    className="text-red-600 hover:text-red-800 p-1"
                                                                    title="刪除"
                                                                >
                                                                    <Trash2 className="w-4 h-4" />
                                                                </button>
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    {/* Leave Records Section (edit mode only) */}
                                    {modalMode === 'edit' && editingContract && (
                                        <div className="border-t pt-4 mt-4">
                                            <div className="flex items-center justify-between mb-3">
                                                <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                                                    <Calendar className="w-5 h-5" />
                                                    請假紀錄
                                                    <span className="text-sm font-normal text-gray-500">
                                                        ({editingContract.used_leave_count} / {editingContract.total_leave_allowed})
                                                    </span>
                                                </h3>
                                            </div>

                                            {/* Add Leave Record Form */}
                                            <div className="mb-4 flex items-end gap-3">
                                                <div className="flex-1">
                                                    <label className="block text-xs font-medium text-gray-600 mb-1">請假日期</label>
                                                    <input
                                                        type="date"
                                                        value={leaveFormData.leave_date}
                                                        onChange={(e) => setLeaveFormData({ ...leaveFormData, leave_date: e.target.value })}
                                                        className="input-field text-sm"
                                                    />
                                                </div>
                                                <div className="flex-1">
                                                    <label className="block text-xs font-medium text-gray-600 mb-1">原因</label>
                                                    <input
                                                        type="text"
                                                        value={leaveFormData.reason || ''}
                                                        onChange={(e) => setLeaveFormData({ ...leaveFormData, reason: e.target.value })}
                                                        className="input-field text-sm"
                                                        placeholder="請假原因"
                                                    />
                                                </div>
                                                <button
                                                    type="button"
                                                    onClick={handleAddLeaveRecord}
                                                    disabled={!leaveFormData.leave_date || leaveSubmitting}
                                                    className="btn-primary text-sm px-3 py-2 disabled:opacity-50"
                                                >
                                                    {leaveSubmitting ? '...' : '新增'}
                                                </button>
                                            </div>
                                            {leaveFormError && (
                                                <div className="mb-3 p-2 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
                                                    {leaveFormError}
                                                </div>
                                            )}

                                            {/* Leave Records List */}
                                            {leaveRecordsLoading ? (
                                                <div className="text-center py-4">
                                                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600 mx-auto"></div>
                                                </div>
                                            ) : leaveRecords.length === 0 ? (
                                                <p className="text-sm text-gray-500 py-2">尚無請假紀錄</p>
                                            ) : (
                                                <div className="space-y-2">
                                                    {leaveRecords.map((record) => (
                                                        <div key={record.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                                                            <div className="flex items-center gap-3 flex-1 min-w-0">
                                                                <span className="text-sm font-medium text-gray-900 whitespace-nowrap">
                                                                    {formatDate(record.leave_date)}
                                                                </span>
                                                                <span className="text-sm text-gray-600 truncate">
                                                                    {record.reason || '-'}
                                                                </span>
                                                            </div>
                                                            <button
                                                                type="button"
                                                                onClick={() => handleDeleteLeaveRecord(record.id)}
                                                                className="text-red-600 hover:text-red-800 p-1 ml-2"
                                                                title="刪除"
                                                            >
                                                                <Trash2 className="w-4 h-4" />
                                                            </button>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    <div className="flex gap-3 pt-4">
                                        <button
                                            type="button"
                                            onClick={closeModal}
                                            className="btn-secondary flex-1"
                                            disabled={submitting}
                                        >
                                            取消
                                        </button>
                                        <button
                                            type="submit"
                                            className="btn-primary flex-1"
                                            disabled={submitting}
                                        >
                                            {submitting ? (
                                                <span className="flex items-center justify-center">
                                                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                                                    處理中...
                                                </span>
                                            ) : modalMode === 'create' ? '建立' : '儲存'}
                                        </button>
                                    </div>
                                </form>
                            </div>
                        </div>
                    </div>
                )}

                {/* Delete Confirmation Modal */}
                {deleteConfirm && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                        <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
                            <h3 className="text-lg font-bold text-gray-900 mb-2">
                                確認刪除合約
                            </h3>
                            <p className="text-gray-600 mb-6">
                                確定要刪除合約「<span className="font-medium">{deleteConfirm.contract_no}</span>」嗎？
                                此操作將同時刪除合約明細、教師綁定和請假紀錄，且無法復原。
                            </p>
                            <div className="flex gap-3">
                                <button
                                    onClick={() => setDeleteConfirm(null)}
                                    className="btn-secondary flex-1"
                                    disabled={deleting}
                                >
                                    取消
                                </button>
                                <button
                                    onClick={handleDelete}
                                    className="btn-danger flex-1"
                                    disabled={deleting}
                                >
                                    {deleting ? (
                                        <span className="flex items-center justify-center">
                                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                                            刪除中...
                                        </span>
                                    ) : '確認刪除'}
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </DashboardLayout>
    )
}

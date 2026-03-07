'use client'

import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '@/lib/hooks/useAuth'
import {
    teacherContractsApi,
    TeacherContract,
    TeacherContractDetail,
    CreateTeacherContractData,
    UpdateTeacherContractData,
    CreateDetailData,
    UpdateDetailData,
    ContractStatus,
    EmploymentType,
    DetailType,
    TeacherOption,
    CourseOption
} from '@/lib/api/teacherContracts'
import { Plus, Pencil, Trash2, Search, X, Users, Calendar, CheckCircle, Clock, XCircle, AlertCircle, Upload, Download } from 'lucide-react'
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

const employmentTypeLabels: Record<EmploymentType, string> = {
    hourly: '時薪',
    full_time: '正職',
}

const employmentTypeColors: Record<EmploymentType, { bg: string, text: string }> = {
    hourly: { bg: 'bg-blue-100', text: 'text-blue-800' },
    full_time: { bg: 'bg-purple-100', text: 'text-purple-800' },
}

const detailTypeLabels: Record<DetailType, string> = {
    course_rate: '課程時薪',
    base_salary: '底薪',
    allowance: '津貼',
}

const detailTypeColors: Record<DetailType, { bg: string, text: string }> = {
    course_rate: { bg: 'bg-blue-100', text: 'text-blue-800' },
    base_salary: { bg: 'bg-green-100', text: 'text-green-800' },
    allowance: { bg: 'bg-orange-100', text: 'text-orange-800' },
}

export default function TeacherContractsPage() {
    const { user, profile } = useAuth()

    // State
    const [contracts, setContracts] = useState<TeacherContract[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [searchTerm, setSearchTerm] = useState('')
    const [filterStatus, setFilterStatus] = useState<ContractStatus | ''>('')
    const [filterEmploymentType, setFilterEmploymentType] = useState<EmploymentType | ''>('')
    const [filterTeacher, setFilterTeacher] = useState('')

    // Options for dropdowns
    const [teacherOptions, setTeacherOptions] = useState<TeacherOption[]>([])
    const [courseOptions, setCourseOptions] = useState<CourseOption[]>([])

    // Pagination
    const [page, setPage] = useState(1)
    const [totalPages, setTotalPages] = useState(1)
    const [total, setTotal] = useState(0)
    const perPage = 10

    // Modal state
    const [showModal, setShowModal] = useState(false)
    const [modalMode, setModalMode] = useState<'create' | 'edit'>('create')
    const [editingContract, setEditingContract] = useState<TeacherContract | null>(null)
    const [formData, setFormData] = useState<CreateTeacherContractData>({
        teacher_id: '',
        contract_status: 'pending',
        start_date: '',
        end_date: '',
        employment_type: 'hourly',
        trial_to_formal_bonus: 0,
        notes: '',
    })
    const [formError, setFormError] = useState<string | null>(null)
    const [submitting, setSubmitting] = useState(false)

    // Details state (for edit modal)
    const [details, setDetails] = useState<TeacherContractDetail[]>([])
    const [detailsLoading, setDetailsLoading] = useState(false)
    const [showDetailForm, setShowDetailForm] = useState(false)
    const [editingDetail, setEditingDetail] = useState<TeacherContractDetail | null>(null)
    const [detailFormData, setDetailFormData] = useState<CreateDetailData>({
        detail_type: 'course_rate',
        course_id: undefined,
        description: '',
        amount: 0,
        notes: '',
    })
    const [detailFormError, setDetailFormError] = useState<string | null>(null)
    const [detailSubmitting, setDetailSubmitting] = useState(false)

    // Delete confirmation
    const [deleteConfirm, setDeleteConfirm] = useState<TeacherContract | null>(null)
    const [deleting, setDeleting] = useState(false)

    // Upload state
    const [uploading, setUploading] = useState<string | null>(null)

    // Fetch options
    const fetchOptions = useCallback(async () => {
        const [teachersResult, coursesResult] = await Promise.all([
            teacherContractsApi.getTeacherOptions(),
            teacherContractsApi.getCourseOptions(),
        ])
        if (teachersResult.data) setTeacherOptions(teachersResult.data)
        if (coursesResult.data) setCourseOptions(coursesResult.data)
    }, [])

    // Fetch contracts
    const fetchContracts = useCallback(async () => {
        setLoading(true)
        setError(null)

        const { data, error } = await teacherContractsApi.list({
            page,
            per_page: perPage,
            search: searchTerm || undefined,
            contract_status: filterStatus || undefined,
            employment_type: filterEmploymentType || undefined,
            teacher_id: filterTeacher || undefined,
        })

        if (error) {
            setError(error.message)
        } else if (data) {
            setContracts(data.data)
            setTotalPages(data.total_pages)
            setTotal(data.total)
        }

        setLoading(false)
    }, [page, searchTerm, filterStatus, filterEmploymentType, filterTeacher])

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
        const { data, error } = await teacherContractsApi.listDetails(contractId)
        if (data) setDetails(data)
        if (error) setError(error.message)
        setDetailsLoading(false)
    }, [])

    // Modal handlers
    const openCreateModal = () => {
        setModalMode('create')
        setEditingContract(null)
        setDetails([])
        const today = new Date().toISOString().split('T')[0]
        const nextYear = new Date()
        nextYear.setFullYear(nextYear.getFullYear() + 1)
        const endDate = nextYear.toISOString().split('T')[0]

        setFormData({
            teacher_id: '',
            contract_status: 'pending',
            start_date: today,
            end_date: endDate,
            employment_type: 'hourly',
            trial_to_formal_bonus: 0,
            notes: '',
        })
        setFormError(null)
        setShowDetailForm(false)
        setEditingDetail(null)
        setShowModal(true)
    }

    const openEditModal = (contract: TeacherContract) => {
        setModalMode('edit')
        setEditingContract(contract)
        setFormData({
            teacher_id: contract.teacher_id,
            contract_status: contract.contract_status,
            start_date: contract.start_date,
            end_date: contract.end_date,
            employment_type: contract.employment_type,
            trial_to_formal_bonus: contract.trial_to_formal_bonus ?? 0,
            notes: contract.notes || '',
        })
        setDetails(contract.details || [])
        setFormError(null)
        setShowDetailForm(false)
        setEditingDetail(null)
        setShowModal(true)
        // Also refresh details from server
        fetchDetails(contract.id)
    }

    const closeModal = () => {
        setShowModal(false)
        setEditingContract(null)
        setFormError(null)
        setShowDetailForm(false)
        setEditingDetail(null)
    }

    // Form submit
    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setFormError(null)
        setSubmitting(true)

        try {
            if (modalMode === 'create') {
                const { data, error } = await teacherContractsApi.create(formData)
                if (error) {
                    setFormError(error.message)
                } else {
                    closeModal()
                    fetchContracts()
                }
            } else if (editingContract) {
                const updateData: UpdateTeacherContractData = {}
                if (formData.teacher_id !== editingContract.teacher_id) updateData.teacher_id = formData.teacher_id
                if (formData.contract_status !== editingContract.contract_status) updateData.contract_status = formData.contract_status
                if (formData.start_date !== editingContract.start_date) updateData.start_date = formData.start_date
                if (formData.end_date !== editingContract.end_date) updateData.end_date = formData.end_date
                if (formData.employment_type !== editingContract.employment_type) updateData.employment_type = formData.employment_type
                if (formData.trial_to_formal_bonus !== (editingContract.trial_to_formal_bonus ?? 0)) updateData.trial_to_formal_bonus = formData.trial_to_formal_bonus
                if (formData.notes !== (editingContract.notes || '')) updateData.notes = formData.notes

                const { data, error } = await teacherContractsApi.update(editingContract.id, updateData)
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
        const isHourly = formData.employment_type === 'hourly'
        setDetailFormData({
            detail_type: isHourly ? 'course_rate' : 'base_salary',
            course_id: undefined,
            description: '',
            amount: 0,
            notes: '',
        })
        setDetailFormError(null)
        setShowDetailForm(true)
    }

    const openEditDetail = (detail: TeacherContractDetail) => {
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
                // Update
                const updateData: UpdateDetailData = {
                    description: detailFormData.description || undefined,
                    amount: detailFormData.amount,
                    notes: detailFormData.notes || undefined,
                }
                const { error } = await teacherContractsApi.updateDetail(
                    editingContract.id, editingDetail.id, updateData
                )
                if (error) {
                    setDetailFormError(error.message)
                    return
                }
            } else {
                // Create
                const { error } = await teacherContractsApi.createDetail(
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
            fetchContracts()
        } finally {
            setDetailSubmitting(false)
        }
    }

    const handleDeleteDetail = async (detailId: string) => {
        if (!editingContract) return
        const { error } = await teacherContractsApi.deleteDetail(editingContract.id, detailId)
        if (error) {
            setError(error.message)
        } else {
            await fetchDetails(editingContract.id)
            fetchContracts()
        }
    }

    // Delete handler
    const handleDelete = async () => {
        if (!deleteConfirm) return
        setDeleting(true)

        const { success, error } = await teacherContractsApi.delete(deleteConfirm.id)

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
        const { url, error } = await teacherContractsApi.downloadFile(contractId)
        if (error) {
            setError(error.message)
        } else if (url) {
            window.open(url, '_blank')
        }
    }

    // Upload handler
    const handleUpload = async (contractId: string, file: File) => {
        setUploading(contractId)
        const { data, error } = await teacherContractsApi.uploadFile(contractId, file)
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

    const formatCurrency = (amount: number | undefined | null) => {
        if (amount === undefined || amount === null) return '-'
        return new Intl.NumberFormat('zh-TW', { style: 'currency', currency: 'TWD', minimumFractionDigits: 0 }).format(amount)
    }

    // Compute details total in modal
    const detailsTotal = details.reduce((sum, d) => sum + d.amount, 0)

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
                                    教師合約管理
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

                            {/* Filter by employment type */}
                            <select
                                value={filterEmploymentType}
                                onChange={(e) => {
                                    setFilterEmploymentType(e.target.value as EmploymentType | '')
                                    setPage(1)
                                }}
                                className="input-field w-full sm:w-40"
                            >
                                <option value="">全部類型</option>
                                <option value="hourly">時薪</option>
                                <option value="full_time">正職</option>
                            </select>

                            {/* Filter by teacher */}
                            <select
                                value={filterTeacher}
                                onChange={(e) => {
                                    setFilterTeacher(e.target.value)
                                    setPage(1)
                                }}
                                className="input-field w-full sm:w-48"
                            >
                                <option value="">全部教師</option>
                                {teacherOptions.map((t) => (
                                    <option key={t.id} value={t.id}>{t.name}</option>
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
                            <Users className="w-16 h-16 mx-auto text-gray-300 mb-4" />
                            <h3 className="text-lg font-medium text-gray-900 mb-2">沒有找到合約</h3>
                            <p className="text-gray-500">
                                {searchTerm ? '請嘗試其他搜尋條件' : '點擊「新增合約」建立第一份教師合約'}
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
                                                教師
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                僱用類型
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                狀態
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                合約期間
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                合約金額
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                轉正獎金
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
                                                        {contract.teacher_name || '-'}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${employmentTypeColors[contract.employment_type].bg} ${employmentTypeColors[contract.employment_type].text}`}>
                                                        {employmentTypeLabels[contract.employment_type]}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColors[contract.contract_status].bg} ${statusColors[contract.contract_status].text}`}>
                                                        {statusIcons[contract.contract_status]}
                                                        {statusLabels[contract.contract_status]}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <div className="flex items-center text-sm text-gray-600">
                                                        <Calendar className="w-4 h-4 mr-1" />
                                                        {formatDate(contract.start_date)} ~ {formatDate(contract.end_date)}
                                                    </div>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <span className="text-gray-900 font-medium">
                                                        {formatCurrency(contract.total_amount)}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <span className="text-gray-900">
                                                        {formatCurrency(contract.trial_to_formal_bonus)}
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
                        <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                            <div className="p-6">
                                <div className="flex items-center justify-between mb-6">
                                    <h2 className="text-xl font-bold text-gray-900">
                                        {modalMode === 'create' ? '新增教師合約' : '編輯教師合約'}
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
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            教師 <span className="text-red-500">*</span>
                                        </label>
                                        <select
                                            value={formData.teacher_id}
                                            onChange={(e) => setFormData({ ...formData, teacher_id: e.target.value })}
                                            className="input-field"
                                            required
                                        >
                                            <option value="">請選擇教師</option>
                                            {teacherOptions.map((t) => (
                                                <option key={t.id} value={t.id}>{t.teacher_no} - {t.name}</option>
                                            ))}
                                        </select>
                                    </div>

                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                僱用類型 <span className="text-red-500">*</span>
                                            </label>
                                            <select
                                                value={formData.employment_type}
                                                onChange={(e) => setFormData({ ...formData, employment_type: e.target.value as EmploymentType })}
                                                className="input-field"
                                                required
                                            >
                                                <option value="hourly">時薪</option>
                                                <option value="full_time">正職</option>
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
                                    </div>

                                    <div className="grid grid-cols-2 gap-4">
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
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            試上課轉正式獎金
                                        </label>
                                        <input
                                            type="number"
                                            value={formData.trial_to_formal_bonus ?? 0}
                                            onChange={(e) => setFormData({ ...formData, trial_to_formal_bonus: e.target.value ? parseFloat(e.target.value) : 0 })}
                                            className="input-field"
                                            min={0}
                                            step="1"
                                            placeholder="0"
                                        />
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

                                {/* Contract Details Section (only in edit mode) */}
                                {modalMode === 'edit' && editingContract && isStaff && (
                                    <div className="mt-8 pt-6 border-t border-gray-200">
                                        <div className="flex items-center justify-between mb-4">
                                            <h3 className="text-lg font-bold text-gray-900">合約明細</h3>
                                            <button
                                                type="button"
                                                onClick={openAddDetail}
                                                className="btn-primary text-sm flex items-center gap-1"
                                            >
                                                <Plus className="w-4 h-4" />
                                                {formData.employment_type === 'hourly' ? '新增課程時薪' : '新增項目'}
                                            </button>
                                        </div>

                                        {/* Detail Form */}
                                        {showDetailForm && (
                                            <div className="mb-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
                                                <h4 className="text-sm font-medium text-gray-700 mb-3">
                                                    {editingDetail ? '編輯明細' : '新增明細'}
                                                </h4>

                                                {detailFormError && (
                                                    <div className="mb-3 p-2 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
                                                        {detailFormError}
                                                    </div>
                                                )}

                                                <div className="space-y-3">
                                                    {!editingDetail && (
                                                        <>
                                                            {formData.employment_type === 'hourly' ? (
                                                                /* 時薪: 只有 course_rate */
                                                                <div>
                                                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                                                        課程 <span className="text-red-500">*</span>
                                                                    </label>
                                                                    <select
                                                                        value={detailFormData.course_id || ''}
                                                                        onChange={(e) => setDetailFormData({
                                                                            ...detailFormData,
                                                                            detail_type: 'course_rate',
                                                                            course_id: e.target.value || undefined
                                                                        })}
                                                                        className="input-field"
                                                                        required
                                                                    >
                                                                        <option value="">請選擇課程</option>
                                                                        {courseOptions.map((c) => (
                                                                            <option key={c.id} value={c.id}>{c.course_code} - {c.course_name}</option>
                                                                        ))}
                                                                    </select>
                                                                </div>
                                                            ) : (
                                                                /* 正職: base_salary or allowance */
                                                                <div>
                                                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                                                        明細類型 <span className="text-red-500">*</span>
                                                                    </label>
                                                                    <select
                                                                        value={detailFormData.detail_type}
                                                                        onChange={(e) => setDetailFormData({
                                                                            ...detailFormData,
                                                                            detail_type: e.target.value as DetailType,
                                                                            course_id: undefined
                                                                        })}
                                                                        className="input-field"
                                                                    >
                                                                        <option value="base_salary">底薪</option>
                                                                        <option value="allowance">津貼</option>
                                                                    </select>
                                                                </div>
                                                            )}
                                                        </>
                                                    )}

                                                    <div className="grid grid-cols-2 gap-3">
                                                        <div>
                                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                                說明
                                                            </label>
                                                            <input
                                                                type="text"
                                                                value={detailFormData.description || ''}
                                                                onChange={(e) => setDetailFormData({ ...detailFormData, description: e.target.value })}
                                                                className="input-field"
                                                                placeholder={detailFormData.detail_type === 'course_rate' ? '如：一對一教學' : '如：交通津貼'}
                                                                maxLength={100}
                                                            />
                                                        </div>
                                                        <div>
                                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                                金額 <span className="text-red-500">*</span>
                                                            </label>
                                                            <input
                                                                type="number"
                                                                value={detailFormData.amount || ''}
                                                                onChange={(e) => setDetailFormData({ ...detailFormData, amount: e.target.value ? parseFloat(e.target.value) : 0 })}
                                                                className="input-field"
                                                                min={0}
                                                                step="1"
                                                                required
                                                            />
                                                        </div>
                                                    </div>

                                                    <div>
                                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                                            備註
                                                        </label>
                                                        <input
                                                            type="text"
                                                            value={detailFormData.notes || ''}
                                                            onChange={(e) => setDetailFormData({ ...detailFormData, notes: e.target.value })}
                                                            className="input-field"
                                                            placeholder="選填"
                                                        />
                                                    </div>

                                                    <div className="flex gap-2 pt-1">
                                                        <button
                                                            type="button"
                                                            onClick={() => { setShowDetailForm(false); setEditingDetail(null) }}
                                                            className="btn-secondary text-sm"
                                                            disabled={detailSubmitting}
                                                        >
                                                            取消
                                                        </button>
                                                        <button
                                                            type="button"
                                                            onClick={handleDetailSubmit}
                                                            className="btn-primary text-sm"
                                                            disabled={detailSubmitting}
                                                        >
                                                            {detailSubmitting ? '處理中...' : editingDetail ? '更新' : '新增'}
                                                        </button>
                                                    </div>
                                                </div>
                                            </div>
                                        )}

                                        {/* Details List */}
                                        {detailsLoading ? (
                                            <div className="flex justify-center py-4">
                                                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
                                            </div>
                                        ) : details.length === 0 ? (
                                            <div className="text-center py-6 text-gray-400 text-sm">
                                                尚無合約明細
                                            </div>
                                        ) : (
                                            <div className="space-y-2">
                                                {details.map((detail) => (
                                                    <div key={detail.id} className="flex items-center justify-between p-3 bg-white border border-gray-200 rounded-lg">
                                                        <div className="flex items-center gap-3 flex-1 min-w-0">
                                                            <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${detailTypeColors[detail.detail_type].bg} ${detailTypeColors[detail.detail_type].text}`}>
                                                                {detailTypeLabels[detail.detail_type]}
                                                            </span>
                                                            <span className="text-sm text-gray-700 truncate">
                                                                {detail.detail_type === 'course_rate'
                                                                    ? (detail.course_name || '未知課程')
                                                                    : (detail.description || '-')
                                                                }
                                                                {detail.detail_type === 'course_rate' && detail.description && (
                                                                    <span className="text-gray-400 ml-1">({detail.description})</span>
                                                                )}
                                                            </span>
                                                        </div>
                                                        <div className="flex items-center gap-3 ml-4">
                                                            <span className="font-medium text-gray-900 whitespace-nowrap">
                                                                {formatCurrency(detail.amount)}
                                                            </span>
                                                            <button
                                                                type="button"
                                                                onClick={() => openEditDetail(detail)}
                                                                className="text-blue-600 hover:text-blue-900"
                                                                title="編輯"
                                                            >
                                                                <Pencil className="w-4 h-4" />
                                                            </button>
                                                            <button
                                                                type="button"
                                                                onClick={() => handleDeleteDetail(detail.id)}
                                                                className="text-red-600 hover:text-red-900"
                                                                title="刪除"
                                                            >
                                                                <Trash2 className="w-4 h-4" />
                                                            </button>
                                                        </div>
                                                    </div>
                                                ))}

                                                {/* Total — 僅正職合約顯示 */}
                                                {formData.employment_type === 'full_time' && (
                                                    <div className="flex items-center justify-between p-3 bg-gray-50 border border-gray-300 rounded-lg font-medium">
                                                        <span className="text-gray-700">合計金額</span>
                                                        <span className="text-gray-900">{formatCurrency(detailsTotal)}</span>
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                )}
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
                                此操作無法復原。
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

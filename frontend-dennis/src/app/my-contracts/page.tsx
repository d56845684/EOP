'use client'

import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '@/lib/hooks/useAuth'
import { studentContractsApi, StudentContract, ContractStatus } from '@/lib/api/studentContracts'
import { teacherContractsApi, TeacherContract } from '@/lib/api/teacherContracts'
import { Search, X, FileText, Calendar, CheckCircle, Clock, XCircle, AlertCircle, Download } from 'lucide-react'
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

export default function MyContractsPage() {
    const { user, profile } = useAuth()
    const role = profile?.student_id ? 'student' : profile?.teacher_id ? 'teacher' : profile?.role

    // Student contract state
    const [studentContracts, setStudentContracts] = useState<StudentContract[]>([])
    // Teacher contract state
    const [teacherContracts, setTeacherContracts] = useState<TeacherContract[]>([])

    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [searchTerm, setSearchTerm] = useState('')
    const [filterStatus, setFilterStatus] = useState<ContractStatus | ''>('')

    // Pagination
    const [page, setPage] = useState(1)
    const [totalPages, setTotalPages] = useState(1)
    const [total, setTotal] = useState(0)
    const perPage = 10

    const fetchContracts = useCallback(async () => {
        if (!role) return
        setLoading(true)
        setError(null)

        if (role === 'student') {
            const { data, error } = await studentContractsApi.list({
                page,
                per_page: perPage,
                search: searchTerm || undefined,
                contract_status: filterStatus || undefined,
            })
            if (error) {
                setError(error.message)
            } else if (data) {
                setStudentContracts(data.data)
                setTotalPages(data.total_pages)
                setTotal(data.total)
            }
        } else if (role === 'teacher') {
            const { data, error } = await teacherContractsApi.list({
                page,
                per_page: perPage,
                search: searchTerm || undefined,
                contract_status: filterStatus || undefined,
            })
            if (error) {
                setError(error.message)
            } else if (data) {
                setTeacherContracts(data.data)
                setTotalPages(data.total_pages)
                setTotal(data.total)
            }
        }

        setLoading(false)
    }, [role, page, searchTerm, filterStatus])

    useEffect(() => {
        if (user && role) {
            fetchContracts()
        }
    }, [user, role, fetchContracts])

    // Search with debounce
    useEffect(() => {
        const timer = setTimeout(() => {
            setPage(1)
        }, 300)
        return () => clearTimeout(timer)
    }, [searchTerm])

    // Download handlers
    const handleStudentDownload = async (contractId: string) => {
        const { url, error } = await studentContractsApi.downloadFile(contractId)
        if (error) {
            setError(error.message)
        } else if (url) {
            window.open(url, '_blank')
        }
    }

    const handleTeacherDownload = async (contractId: string) => {
        const { url, error } = await teacherContractsApi.downloadFile(contractId)
        if (error) {
            setError(error.message)
        } else if (url) {
            window.open(url, '_blank')
        }
    }

    const formatDate = (dateStr: string) => {
        return new Date(dateStr).toLocaleDateString('zh-TW')
    }

    const formatCurrency = (amount: number | undefined) => {
        if (amount === undefined || amount === null) return '-'
        return new Intl.NumberFormat('zh-TW', { style: 'currency', currency: 'TWD', minimumFractionDigits: 0 }).format(amount)
    }

    const renderStatusBadge = (status: ContractStatus) => (
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColors[status].bg} ${statusColors[status].text}`}>
            {statusIcons[status]}
            {statusLabels[status]}
        </span>
    )

    return (
        <DashboardLayout>
            <div className="py-8">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    {/* Header */}
                    <div className="mb-8">
                        <div>
                            <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
                                <FileText className="w-8 h-8 text-blue-600" />
                                我的合約
                            </h1>
                            <p className="mt-2 text-gray-600">
                                共 {total} 份合約
                            </p>
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
                    ) : role === 'student' ? (
                        /* Student Contracts Table */
                        studentContracts.length === 0 ? (
                            <div className="card text-center py-12">
                                <FileText className="w-16 h-16 mx-auto text-gray-300 mb-4" />
                                <h3 className="text-lg font-medium text-gray-900 mb-2">沒有找到合約</h3>
                                <p className="text-gray-500">
                                    {searchTerm ? '請嘗試其他搜尋條件' : '目前沒有合約資料'}
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
                                                    課程
                                                </th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    狀態
                                                </th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    合約期間
                                                </th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    堂數
                                                </th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    單堂價格
                                                </th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    總金額
                                                </th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    合約檔案
                                                </th>
                                            </tr>
                                        </thead>
                                        <tbody className="bg-white divide-y divide-gray-200">
                                            {studentContracts.map((contract) => (
                                                <tr key={contract.id} className="hover:bg-gray-50">
                                                    <td className="px-6 py-4 whitespace-nowrap">
                                                        <span className="font-mono text-sm bg-gray-100 px-2 py-1 rounded">
                                                            {contract.contract_no}
                                                        </span>
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap">
                                                        <span className="text-gray-600">
                                                            {contract.course_name || '-'}
                                                        </span>
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap">
                                                        {renderStatusBadge(contract.contract_status)}
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
                                                            {formatCurrency(contract.price_per_lesson)}
                                                        </span>
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap">
                                                        <span className="text-gray-900 font-medium">
                                                            {formatCurrency(contract.total_amount)}
                                                        </span>
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap">
                                                        {contract.contract_file_path ? (
                                                            <button
                                                                onClick={() => handleStudentDownload(contract.id)}
                                                                className="inline-flex items-center px-3 py-1 rounded-md text-sm font-medium text-blue-600 bg-blue-50 hover:bg-blue-100"
                                                            >
                                                                <Download className="w-4 h-4 mr-1" />
                                                                下載
                                                            </button>
                                                        ) : (
                                                            <span className="text-gray-400 text-sm">-</span>
                                                        )}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )
                    ) : role === 'teacher' ? (
                        /* Teacher Contracts Table */
                        teacherContracts.length === 0 ? (
                            <div className="card text-center py-12">
                                <FileText className="w-16 h-16 mx-auto text-gray-300 mb-4" />
                                <h3 className="text-lg font-medium text-gray-900 mb-2">沒有找到合約</h3>
                                <p className="text-gray-500">
                                    {searchTerm ? '請嘗試其他搜尋條件' : '目前沒有合約資料'}
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
                                                    狀態
                                                </th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    合約期間
                                                </th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    底薪
                                                </th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    備註
                                                </th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    合約檔案
                                                </th>
                                            </tr>
                                        </thead>
                                        <tbody className="bg-white divide-y divide-gray-200">
                                            {teacherContracts.map((contract) => (
                                                <tr key={contract.id} className="hover:bg-gray-50">
                                                    <td className="px-6 py-4 whitespace-nowrap">
                                                        <span className="font-mono text-sm bg-gray-100 px-2 py-1 rounded">
                                                            {contract.contract_no}
                                                        </span>
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap">
                                                        {renderStatusBadge(contract.contract_status)}
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap">
                                                        <div className="flex items-center text-sm text-gray-600">
                                                            <Calendar className="w-4 h-4 mr-1" />
                                                            {formatDate(contract.start_date)} ~ {formatDate(contract.end_date)}
                                                        </div>
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap">
                                                        <span className="text-gray-900 font-medium">
                                                            {formatCurrency(contract.base_salary)}
                                                        </span>
                                                    </td>
                                                    <td className="px-6 py-4">
                                                        <span className="text-gray-600 text-sm">
                                                            {contract.notes || '-'}
                                                        </span>
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap">
                                                        {contract.contract_file_path ? (
                                                            <button
                                                                onClick={() => handleTeacherDownload(contract.id)}
                                                                className="inline-flex items-center px-3 py-1 rounded-md text-sm font-medium text-blue-600 bg-blue-50 hover:bg-blue-100"
                                                            >
                                                                <Download className="w-4 h-4 mr-1" />
                                                                下載
                                                            </button>
                                                        ) : (
                                                            <span className="text-gray-400 text-sm">-</span>
                                                        )}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )
                    ) : (
                        <div className="card text-center py-12">
                            <FileText className="w-16 h-16 mx-auto text-gray-300 mb-4" />
                            <h3 className="text-lg font-medium text-gray-900 mb-2">無法存取</h3>
                            <p className="text-gray-500">此頁面僅供學生與教師使用</p>
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
            </div>
        </DashboardLayout>
    )
}

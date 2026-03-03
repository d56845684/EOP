'use client'

import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '@/lib/hooks/useAuth'
import {
    studentCoursesApi,
    StudentCourse,
    CreateStudentCourseData,
    StudentOption,
    CourseOption,
} from '@/lib/api/studentCourses'
import { Plus, Trash2, Search, X, BookOpen } from 'lucide-react'
import DashboardLayout from '@/components/DashboardLayout'

export default function StudentCoursesPage() {
    const { user, profile } = useAuth()

    // State
    const [enrollments, setEnrollments] = useState<StudentCourse[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [searchTerm, setSearchTerm] = useState('')
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
    const [formData, setFormData] = useState<CreateStudentCourseData>({
        student_id: '',
        course_id: '',
    })
    const [formError, setFormError] = useState<string | null>(null)
    const [submitting, setSubmitting] = useState(false)

    // Delete confirmation
    const [deleteConfirm, setDeleteConfirm] = useState<StudentCourse | null>(null)
    const [deleting, setDeleting] = useState(false)

    // Fetch options
    const fetchOptions = useCallback(async () => {
        const [studentsResult, coursesResult] = await Promise.all([
            studentCoursesApi.getStudentOptions(),
            studentCoursesApi.getCourseOptions(),
        ])

        if (studentsResult.data) setStudentOptions(studentsResult.data)
        if (coursesResult.data) setCourseOptions(coursesResult.data)
    }, [])

    // Fetch enrollments
    const fetchEnrollments = useCallback(async () => {
        setLoading(true)
        setError(null)

        const { data, error } = await studentCoursesApi.list({
            page,
            per_page: perPage,
            search: searchTerm || undefined,
            student_id: filterStudent || undefined,
        })

        if (error) {
            setError(error.message)
        } else if (data) {
            setEnrollments(data.data)
            setTotalPages(data.total_pages)
            setTotal(data.total)
        }

        setLoading(false)
    }, [page, searchTerm, filterStudent])

    useEffect(() => {
        if (user) {
            fetchOptions()
            fetchEnrollments()
        }
    }, [user, fetchOptions, fetchEnrollments])

    // Search with debounce
    useEffect(() => {
        const timer = setTimeout(() => {
            setPage(1)
        }, 300)
        return () => clearTimeout(timer)
    }, [searchTerm])

    // Modal handlers
    const openCreateModal = () => {
        setFormData({
            student_id: '',
            course_id: '',
        })
        setFormError(null)
        setShowModal(true)
    }

    const closeModal = () => {
        setShowModal(false)
        setFormError(null)
    }

    // Form submit
    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setFormError(null)
        setSubmitting(true)

        try {
            const { data, error } = await studentCoursesApi.create(formData)
            if (error) {
                setFormError(error.message)
            } else {
                closeModal()
                fetchEnrollments()
            }
        } finally {
            setSubmitting(false)
        }
    }

    // Delete handler
    const handleDelete = async () => {
        if (!deleteConfirm) return
        setDeleting(true)

        const { success, error } = await studentCoursesApi.delete(deleteConfirm.id)

        if (error) {
            setError(error.message)
        } else {
            setDeleteConfirm(null)
            fetchEnrollments()
        }

        setDeleting(false)
    }

    const isStaff = profile?.role === 'admin' || profile?.role === 'employee'

    const formatDate = (dateStr: string) => {
        return new Date(dateStr).toLocaleDateString('zh-TW')
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
                                    <BookOpen className="w-8 h-8 text-blue-600" />
                                    學生選課管理
                                </h1>
                                <p className="mt-2 text-gray-600">
                                    共 {total} 筆選課紀錄
                                </p>
                            </div>
                            {isStaff && (
                                <button
                                    onClick={openCreateModal}
                                    className="btn-primary flex items-center gap-2"
                                >
                                    <Plus className="w-5 h-5" />
                                    新增選課
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
                                    placeholder="搜尋課程代碼或名稱..."
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

                    {/* Enrollment List */}
                    {loading ? (
                        <div className="flex justify-center py-12">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                        </div>
                    ) : enrollments.length === 0 ? (
                        <div className="card text-center py-12">
                            <BookOpen className="w-16 h-16 mx-auto text-gray-300 mb-4" />
                            <h3 className="text-lg font-medium text-gray-900 mb-2">沒有找到選課紀錄</h3>
                            <p className="text-gray-500">
                                {searchTerm ? '請嘗試其他搜尋條件' : '點擊「新增選課」建立第一筆學生選課'}
                            </p>
                        </div>
                    ) : (
                        <div className="card overflow-hidden">
                            <div className="overflow-x-auto">
                                <table className="min-w-full divide-y divide-gray-200">
                                    <thead className="bg-gray-50">
                                        <tr>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                學生
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                課程代碼
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                課程名稱
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                選課日期
                                            </th>
                                            {isStaff && (
                                                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    操作
                                                </th>
                                            )}
                                        </tr>
                                    </thead>
                                    <tbody className="bg-white divide-y divide-gray-200">
                                        {enrollments.map((enrollment) => (
                                            <tr key={enrollment.id} className="hover:bg-gray-50">
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <span className="font-medium text-gray-900">
                                                        {enrollment.student_name || '-'}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <span className="font-mono text-sm bg-gray-100 px-2 py-1 rounded">
                                                        {enrollment.course_code || '-'}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <span className="text-gray-900">
                                                        {enrollment.course_name || '-'}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <span className="text-sm text-gray-600">
                                                        {enrollment.enrolled_at ? formatDate(enrollment.enrolled_at) : '-'}
                                                    </span>
                                                </td>
                                                {isStaff && (
                                                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                                        <button
                                                            onClick={() => setDeleteConfirm(enrollment)}
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

                {/* Create Modal */}
                {showModal && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                        <div className="bg-white rounded-xl shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto">
                            <div className="p-6">
                                <div className="flex items-center justify-between mb-6">
                                    <h2 className="text-xl font-bold text-gray-900">
                                        新增學生選課
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
                                            課程 <span className="text-red-500">*</span>
                                        </label>
                                        <select
                                            value={formData.course_id}
                                            onChange={(e) => setFormData({ ...formData, course_id: e.target.value })}
                                            className="input-field"
                                            required
                                        >
                                            <option value="">請選擇課程</option>
                                            {courseOptions.map((c) => (
                                                <option key={c.id} value={c.id}>{c.course_code} - {c.course_name}</option>
                                            ))}
                                        </select>
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
                                            ) : '建立'}
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
                                確認刪除選課
                            </h3>
                            <p className="text-gray-600 mb-6">
                                確定要刪除學生「<span className="font-medium">{deleteConfirm.student_name}</span>」的課程「<span className="font-medium">{deleteConfirm.course_name}</span>」選課紀錄嗎？
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

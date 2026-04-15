'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import { useAuth } from '@/lib/hooks/useAuth'
import { studentsApi, StudentOverviewItem } from '@/lib/api/students'
import DashboardLayout from '@/components/DashboardLayout'
import {
    Search, X, GraduationCap, CheckCircle, XCircle, Eye,
    BookOpen, Calendar, FileText, MessageSquare,
} from 'lucide-react'

const roleLabels: Record<string, string> = { admin: '管理員', employee: '員工', teacher: '老師', student: '學生' }
const typeLabels: Record<string, string> = { formal: '正式', trial: '試上' }
const statusLabels: Record<string, { label: string; color: string }> = {
    trial: { label: '試上', color: 'yellow' },
    pending: { label: '待開課', color: 'blue' },
    active: { label: '上課中', color: 'green' },
    suspended: { label: '暫停', color: 'yellow' },
    terminated: { label: '解約', color: 'red' },
    extended: { label: '展延', color: 'purple' },
    completed: { label: '已結業', color: 'gray' },
}

function Tag({ label, color }: { label: string; color: string }) {
    const map: Record<string, string> = {
        green: 'bg-green-100 text-green-800',
        red: 'bg-red-100 text-red-800',
        blue: 'bg-blue-100 text-blue-800',
        yellow: 'bg-yellow-100 text-yellow-800',
        purple: 'bg-purple-100 text-purple-800',
        gray: 'bg-gray-100 text-gray-600',
    }
    return <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${map[color] || map.gray}`}>{label}</span>
}

export default function StudentOverviewPage() {
    const { user } = useAuth()

    const [items, setItems] = useState<StudentOverviewItem[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    const [page, setPage] = useState(1)
    const [totalPages, setTotalPages] = useState(1)
    const [total, setTotal] = useState(0)
    const perPage = 20

    // Filters
    const [search, setSearch] = useState('')
    const [filterType, setFilterType] = useState('')
    const [filterActive, setFilterActive] = useState<string>('all')
    const [filterAccount, setFilterAccount] = useState<string>('all')
    const [filterContract, setFilterContract] = useState<string>('all')
    const [filterRole, setFilterRole] = useState<string>('')

    const fetchData = useCallback(async () => {
        setLoading(true)
        setError(null)
        const params: any = { page, per_page: perPage }
        if (search) params.search = search
        if (filterType) params.student_type = filterType
        if (filterActive !== 'all') params.is_active = filterActive === 'yes'
        if (filterAccount !== 'all') params.has_account = filterAccount === 'yes'
        if (filterContract !== 'all') params.has_active_contract = filterContract === 'yes'
        if (filterRole) params.role = filterRole

        const { data, error: err } = await studentsApi.listOverview(params)
        if (err) {
            setError(err.message)
        } else if (data) {
            setItems(data.data)
            setTotal(data.total)
            setTotalPages(data.total_pages)
        }
        setLoading(false)
    }, [page, search, filterType, filterActive, filterAccount, filterContract, filterRole])

    useEffect(() => { if (user) fetchData() }, [user, fetchData])
    useEffect(() => { const t = setTimeout(() => setPage(1), 300); return () => clearTimeout(t) }, [search])

    return (
        <DashboardLayout>
            <div className="space-y-4">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-xl font-bold flex items-center gap-2" style={{ color: 'var(--ep-text-color-primary)' }}>
                            <GraduationCap className="w-5 h-5" style={{ color: 'var(--ep-color-primary)' }} />
                            學生總覽
                        </h1>
                        <p className="text-xs mt-0.5" style={{ color: 'var(--ep-text-color-secondary)' }}>共 {total} 位學生</p>
                    </div>
                </div>

                {/* Filters */}
                <div className="card">
                    <div className="flex flex-wrap gap-3 items-center">
                        <div className="flex-1 min-w-[200px] relative">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                            <input type="text" placeholder="搜尋編號、姓名或 Email..."
                                value={search} onChange={e => setSearch(e.target.value)}
                                className="input-field pl-9" />
                            {search && (
                                <button onClick={() => setSearch('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                                    <X className="w-4 h-4" />
                                </button>
                            )}
                        </div>
                        <select value={filterType} onChange={e => { setFilterType(e.target.value); setPage(1) }} className="input-field w-28">
                            <option value="">全部類型</option>
                            <option value="formal">正式</option>
                            <option value="trial">試上</option>
                        </select>
                        <select value={filterActive} onChange={e => { setFilterActive(e.target.value); setPage(1) }} className="input-field w-28">
                            <option value="all">全部狀態</option>
                            <option value="yes">啟用中</option>
                            <option value="no">已停用</option>
                        </select>
                        <select value={filterAccount} onChange={e => { setFilterAccount(e.target.value); setPage(1) }} className="input-field w-32">
                            <option value="all">帳號不限</option>
                            <option value="yes">已有帳號</option>
                            <option value="no">尚無帳號</option>
                        </select>
                        <select value={filterContract} onChange={e => { setFilterContract(e.target.value); setPage(1) }} className="input-field w-32">
                            <option value="all">合約不限</option>
                            <option value="yes">有生效合約</option>
                            <option value="no">無生效合約</option>
                        </select>
                        <select value={filterRole} onChange={e => { setFilterRole(e.target.value); setPage(1) }} className="input-field w-28">
                            <option value="">全部角色</option>
                            <option value="student">學生</option>
                            <option value="teacher">老師</option>
                            <option value="employee">員工</option>
                            <option value="admin">管理員</option>
                        </select>
                    </div>
                </div>

                {error && <div className="p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">{error}</div>}

                {/* Table */}
                {loading ? (
                    <div className="flex justify-center py-16">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2" style={{ borderColor: 'var(--ep-color-primary)' }}></div>
                    </div>
                ) : items.length === 0 ? (
                    <div className="card text-center py-12">
                        <GraduationCap className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                        <p style={{ color: 'var(--ep-text-color-secondary)' }}>沒有符合條件的學生</p>
                    </div>
                ) : (
                    <div className="card p-0 overflow-hidden">
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="bg-gray-50 border-b" style={{ borderColor: 'var(--ep-border-color)' }}>
                                        <th className="text-left px-4 py-2.5 font-medium text-xs uppercase" style={{ color: 'var(--ep-text-color-secondary)' }}>學生</th>
                                        <th className="text-center px-3 py-2.5 font-medium text-xs uppercase" style={{ color: 'var(--ep-text-color-secondary)' }}>類型</th>
                                        <th className="text-center px-3 py-2.5 font-medium text-xs uppercase" style={{ color: 'var(--ep-text-color-secondary)' }}>學習狀態</th>
                                        <th className="text-center px-3 py-2.5 font-medium text-xs uppercase" style={{ color: 'var(--ep-text-color-secondary)' }}>帳號</th>
                                        <th className="text-center px-3 py-2.5 font-medium text-xs uppercase" style={{ color: 'var(--ep-text-color-secondary)' }}>LINE</th>
                                        <th className="text-center px-3 py-2.5 font-medium text-xs uppercase" style={{ color: 'var(--ep-text-color-secondary)' }}>合約</th>
                                        <th className="text-center px-3 py-2.5 font-medium text-xs uppercase" style={{ color: 'var(--ep-text-color-secondary)' }}>剩餘堂數</th>
                                        <th className="text-center px-3 py-2.5 font-medium text-xs uppercase" style={{ color: 'var(--ep-text-color-secondary)' }}>預約</th>
                                        <th className="text-center px-3 py-2.5 font-medium text-xs uppercase" style={{ color: 'var(--ep-text-color-secondary)' }}>待上課</th>
                                        <th className="text-center px-3 py-2.5 font-medium text-xs uppercase" style={{ color: 'var(--ep-text-color-secondary)' }}>操作</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {items.map((s, i) => (
                                        <tr key={s.id}
                                            className={`border-b hover:bg-gray-50 ${i % 2 === 1 ? 'bg-gray-50/50' : ''}`}
                                            style={{ borderColor: 'var(--ep-border-color-light, #e4e7ed)' }}>
                                            {/* 學生 */}
                                            <td className="px-4 py-2.5">
                                                <div className="flex items-center gap-2">
                                                    <div>
                                                        <div className="font-medium" style={{ color: 'var(--ep-text-color-primary)' }}>
                                                            {s.name}
                                                            {s.eng_name && <span className="ml-1 font-normal text-xs" style={{ color: 'var(--ep-text-color-secondary)' }}>({s.eng_name})</span>}
                                                        </div>
                                                        <div className="text-xs" style={{ color: 'var(--ep-text-color-secondary)' }}>
                                                            {s.student_no} &middot; {s.email}
                                                        </div>
                                                    </div>
                                                    {!s.is_active && <Tag label="停用" color="red" />}
                                                </div>
                                            </td>
                                            {/* 類型 */}
                                            <td className="px-3 py-2.5 text-center">
                                                <Tag label={typeLabels[s.student_type || ''] || s.student_type || '-'}
                                                    color={s.student_type === 'trial' ? 'yellow' : 'blue'} />
                                            </td>
                                            {/* 學習狀態 */}
                                            <td className="px-3 py-2.5 text-center">
                                                {(() => {
                                                    const info = statusLabels[s.student_status || 'trial'] || { label: s.student_status || '-', color: 'gray' }
                                                    return <Tag label={info.label} color={info.color} />
                                                })()}
                                            </td>
                                            {/* 帳號 */}
                                            <td className="px-3 py-2.5 text-center">
                                                {s.has_account ? (
                                                    <div className="flex flex-col items-center gap-0.5">
                                                        <CheckCircle className="w-4 h-4 text-green-500" />
                                                        {s.role && <span className="text-xs" style={{ color: 'var(--ep-text-color-secondary)' }}>{roleLabels[s.role] || s.role}</span>}
                                                    </div>
                                                ) : (
                                                    <XCircle className="w-4 h-4 text-gray-300 mx-auto" />
                                                )}
                                            </td>
                                            {/* LINE */}
                                            <td className="px-3 py-2.5 text-center">
                                                {s.line_bound ? (
                                                    <div className="flex flex-col items-center gap-0.5">
                                                        <MessageSquare className="w-4 h-4 text-[#06C755]" />
                                                        {s.line_display_name && <span className="text-xs truncate max-w-[60px]" style={{ color: 'var(--ep-text-color-secondary)' }}>{s.line_display_name}</span>}
                                                    </div>
                                                ) : (
                                                    <XCircle className="w-4 h-4 text-gray-300 mx-auto" />
                                                )}
                                            </td>
                                            {/* 合約 */}
                                            <td className="px-3 py-2.5 text-center">
                                                {s.active_contracts > 0 ? (
                                                    <Tag label={`${s.active_contracts} 生效`} color="green" />
                                                ) : s.total_contracts > 0 ? (
                                                    <Tag label={`${s.total_contracts} 份`} color="gray" />
                                                ) : (
                                                    <span className="text-xs" style={{ color: 'var(--ep-text-color-disabled, #a8abb2)' }}>-</span>
                                                )}
                                            </td>
                                            {/* 剩餘堂數 */}
                                            <td className="px-3 py-2.5 text-center">
                                                <span className={`font-semibold ${s.remaining_lessons > 0 ? '' : ''}`}
                                                    style={{ color: s.remaining_lessons > 0 ? 'var(--ep-color-primary)' : 'var(--ep-text-color-disabled)' }}>
                                                    {s.remaining_lessons}
                                                </span>
                                            </td>
                                            {/* 預約總數 */}
                                            <td className="px-3 py-2.5 text-center text-xs">
                                                <span style={{ color: 'var(--ep-text-color-primary)' }}>{s.completed_bookings}</span>
                                                <span style={{ color: 'var(--ep-text-color-secondary)' }}> / {s.total_bookings}</span>
                                            </td>
                                            {/* 待上課 */}
                                            <td className="px-3 py-2.5 text-center">
                                                {s.upcoming_bookings > 0 ? (
                                                    <Tag label={String(s.upcoming_bookings)} color="yellow" />
                                                ) : (
                                                    <span style={{ color: 'var(--ep-text-color-disabled)' }}>0</span>
                                                )}
                                            </td>
                                            {/* 操作 */}
                                            <td className="px-3 py-2.5 text-center">
                                                <Link href={`/students/view?id=${s.id}`}
                                                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium transition-colors"
                                                    style={{ color: 'var(--ep-color-primary)', border: '1px solid var(--ep-color-primary)' }}
                                                    onMouseEnter={e => { e.currentTarget.style.backgroundColor = 'var(--ep-color-primary)'; e.currentTarget.style.color = '#fff' }}
                                                    onMouseLeave={e => { e.currentTarget.style.backgroundColor = 'transparent'; e.currentTarget.style.color = 'var(--ep-color-primary)' }}
                                                >
                                                    <Eye className="w-3 h-3" /> 詳情
                                                </Link>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>

                        {/* Pagination */}
                        {totalPages > 1 && (
                            <div className="flex items-center justify-between px-4 py-3 border-t" style={{ borderColor: 'var(--ep-border-color)' }}>
                                <p className="text-xs" style={{ color: 'var(--ep-text-color-secondary)' }}>
                                    第 {page} / {totalPages} 頁，共 {total} 位
                                </p>
                                <div className="flex gap-2">
                                    <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1}
                                        className="btn-secondary px-3 py-1 text-xs disabled:opacity-50">上一頁</button>
                                    <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages}
                                        className="btn-secondary px-3 py-1 text-xs disabled:opacity-50">下一頁</button>
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </DashboardLayout>
    )
}

'use client'

import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '@/lib/hooks/useAuth'
import { teachersApi, TeacherOverviewItem } from '@/lib/api/teachers'
import DashboardLayout from '@/components/DashboardLayout'
import {
    Search, X, Users, CheckCircle, XCircle, Eye,
    Calendar, FileText, MessageSquare, DollarSign,
} from 'lucide-react'

const roleLabels: Record<string, string> = { admin: '管理員', employee: '員工', teacher: '老師', student: '學生' }

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

export default function TeacherOverviewPage() {
    const { user } = useAuth()

    const [items, setItems] = useState<TeacherOverviewItem[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    const [page, setPage] = useState(1)
    const [totalPages, setTotalPages] = useState(1)
    const [total, setTotal] = useState(0)
    const perPage = 20

    // Filters
    const [search, setSearch] = useState('')
    const [filterActive, setFilterActive] = useState<string>('all')
    const [filterAccount, setFilterAccount] = useState<string>('all')
    const [filterContract, setFilterContract] = useState<string>('all')
    const [filterRole, setFilterRole] = useState<string>('')

    const fetchData = useCallback(async () => {
        setLoading(true)
        setError(null)
        const params: any = { page, per_page: perPage }
        if (search) params.search = search
        if (filterActive !== 'all') params.is_active = filterActive === 'yes'
        if (filterAccount !== 'all') params.has_account = filterAccount === 'yes'
        if (filterContract !== 'all') params.has_active_contract = filterContract === 'yes'
        if (filterRole) params.role = filterRole

        const { data, error: err } = await teachersApi.listOverview(params)
        if (err) {
            setError(err.message)
        } else if (data) {
            setItems(data.data)
            setTotal(data.total)
            setTotalPages(data.total_pages)
        }
        setLoading(false)
    }, [page, search, filterActive, filterAccount, filterContract, filterRole])

    useEffect(() => { if (user) fetchData() }, [user, fetchData])
    useEffect(() => { const t = setTimeout(() => setPage(1), 300); return () => clearTimeout(t) }, [search])

    return (
        <DashboardLayout>
            <div className="space-y-4">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-xl font-bold flex items-center gap-2" style={{ color: 'var(--ep-text-color-primary)' }}>
                            <Users className="w-5 h-5" style={{ color: 'var(--ep-color-primary)' }} />
                            教師總覽
                        </h1>
                        <p className="text-xs mt-0.5" style={{ color: 'var(--ep-text-color-secondary)' }}>共 {total} 位教師</p>
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
                        <Users className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                        <p style={{ color: 'var(--ep-text-color-secondary)' }}>沒有符合條件的教師</p>
                    </div>
                ) : (
                    <div className="card p-0 overflow-hidden">
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="bg-gray-50 border-b" style={{ borderColor: 'var(--ep-border-color)' }}>
                                        <th className="text-left px-4 py-2.5 font-medium text-xs uppercase" style={{ color: 'var(--ep-text-color-secondary)' }}>教師</th>
                                        <th className="text-center px-3 py-2.5 font-medium text-xs uppercase" style={{ color: 'var(--ep-text-color-secondary)' }}>等級</th>
                                        <th className="text-center px-3 py-2.5 font-medium text-xs uppercase" style={{ color: 'var(--ep-text-color-secondary)' }}>帳號</th>
                                        <th className="text-center px-3 py-2.5 font-medium text-xs uppercase" style={{ color: 'var(--ep-text-color-secondary)' }}>LINE</th>
                                        <th className="text-center px-3 py-2.5 font-medium text-xs uppercase" style={{ color: 'var(--ep-text-color-secondary)' }}>合約</th>
                                        <th className="text-center px-3 py-2.5 font-medium text-xs uppercase" style={{ color: 'var(--ep-text-color-secondary)' }}>預約</th>
                                        <th className="text-center px-3 py-2.5 font-medium text-xs uppercase" style={{ color: 'var(--ep-text-color-secondary)' }}>待上課</th>
                                        <th className="text-center px-3 py-2.5 font-medium text-xs uppercase" style={{ color: 'var(--ep-text-color-secondary)' }}>獎金</th>
                                        <th className="text-center px-3 py-2.5 font-medium text-xs uppercase" style={{ color: 'var(--ep-text-color-secondary)' }}>操作</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {items.map((t, i) => (
                                        <tr key={t.id}
                                            className={`border-b hover:bg-gray-50 ${i % 2 === 1 ? 'bg-gray-50/50' : ''}`}
                                            style={{ borderColor: 'var(--ep-border-color-light, #e4e7ed)' }}>
                                            {/* 教師 */}
                                            <td className="px-4 py-2.5">
                                                <div className="flex items-center gap-2">
                                                    <div>
                                                        <div className="font-medium" style={{ color: 'var(--ep-text-color-primary)' }}>
                                                            {t.name}
                                                        </div>
                                                        <div className="text-xs" style={{ color: 'var(--ep-text-color-secondary)' }}>
                                                            {t.teacher_no} &middot; {t.email}
                                                        </div>
                                                    </div>
                                                    {!t.is_active && <Tag label="停用" color="red" />}
                                                </div>
                                            </td>
                                            {/* 等級 */}
                                            <td className="px-3 py-2.5 text-center">
                                                <Tag label={`Lv.${t.teacher_level}`} color="blue" />
                                            </td>
                                            {/* 帳號 */}
                                            <td className="px-3 py-2.5 text-center">
                                                {t.has_account ? (
                                                    <div className="flex flex-col items-center gap-0.5">
                                                        <CheckCircle className="w-4 h-4 text-green-500" />
                                                        {t.role && <span className="text-xs" style={{ color: 'var(--ep-text-color-secondary)' }}>{roleLabels[t.role] || t.role}</span>}
                                                    </div>
                                                ) : (
                                                    <XCircle className="w-4 h-4 text-gray-300 mx-auto" />
                                                )}
                                            </td>
                                            {/* LINE */}
                                            <td className="px-3 py-2.5 text-center">
                                                {t.line_bound ? (
                                                    <div className="flex flex-col items-center gap-0.5">
                                                        <MessageSquare className="w-4 h-4 text-[#06C755]" />
                                                        {t.line_display_name && <span className="text-xs truncate max-w-[60px]" style={{ color: 'var(--ep-text-color-secondary)' }}>{t.line_display_name}</span>}
                                                    </div>
                                                ) : (
                                                    <XCircle className="w-4 h-4 text-gray-300 mx-auto" />
                                                )}
                                            </td>
                                            {/* 合約 */}
                                            <td className="px-3 py-2.5 text-center">
                                                {t.active_contracts > 0 ? (
                                                    <Tag label={`${t.active_contracts} 生效`} color="green" />
                                                ) : t.total_contracts > 0 ? (
                                                    <Tag label={`${t.total_contracts} 份`} color="gray" />
                                                ) : (
                                                    <span className="text-xs" style={{ color: 'var(--ep-text-color-disabled, #a8abb2)' }}>-</span>
                                                )}
                                            </td>
                                            {/* 預約總數 */}
                                            <td className="px-3 py-2.5 text-center text-xs">
                                                <span style={{ color: 'var(--ep-text-color-primary)' }}>{t.completed_bookings}</span>
                                                <span style={{ color: 'var(--ep-text-color-secondary)' }}> / {t.total_bookings}</span>
                                            </td>
                                            {/* 待上課 */}
                                            <td className="px-3 py-2.5 text-center">
                                                {t.upcoming_bookings > 0 ? (
                                                    <Tag label={String(t.upcoming_bookings)} color="yellow" />
                                                ) : (
                                                    <span style={{ color: 'var(--ep-text-color-disabled)' }}>0</span>
                                                )}
                                            </td>
                                            {/* 獎金 */}
                                            <td className="px-3 py-2.5 text-center">
                                                {t.total_bonus > 0 ? (
                                                    <span className="font-semibold text-xs" style={{ color: 'var(--ep-color-primary)' }}>
                                                        ${t.total_bonus.toLocaleString()}
                                                    </span>
                                                ) : (
                                                    <span style={{ color: 'var(--ep-text-color-disabled)' }}>-</span>
                                                )}
                                            </td>
                                            {/* 操作 */}
                                            <td className="px-3 py-2.5 text-center">
                                                <a href={`/teachers/view?id=${t.id}`}
                                                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium transition-colors
                                                        text-primary-500 border border-primary-500 hover:bg-primary-500 hover:text-white"
                                                >
                                                    <Eye className="w-3 h-3" /> 詳情
                                                </a>
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

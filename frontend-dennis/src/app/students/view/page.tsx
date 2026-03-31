'use client'

import { useState, useEffect } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { Suspense } from 'react'
import { useAuth } from '@/lib/hooks/useAuth'
import { studentsApi, StudentViewData } from '@/lib/api/students'
import DashboardLayout from '@/components/DashboardLayout'
import {
    ArrowLeft, User, Mail, Phone, MapPin, Calendar, BookOpen,
    FileText, CheckCircle, XCircle, Clock, Users, MessageSquare,
    GraduationCap, TrendingUp, AlertTriangle,
} from 'lucide-react'

const statusColors: Record<string, string> = {
    active: 'bg-green-100 text-green-800',
    pending: 'bg-yellow-100 text-yellow-800',
    expired: 'bg-gray-100 text-gray-800',
    terminated: 'bg-red-100 text-red-800',
    confirmed: 'bg-blue-100 text-blue-800',
    completed: 'bg-green-100 text-green-800',
    cancelled: 'bg-gray-100 text-gray-600',
    approved: 'bg-green-100 text-green-800',
    rejected: 'bg-red-100 text-red-800',
    pending: 'bg-blue-100 text-blue-800',
    suspended: 'bg-orange-100 text-orange-800',
    extended: 'bg-purple-100 text-purple-800',
}
const statusLabels: Record<string, string> = {
    active: '生效中', pending: '待確認', expired: '已到期', terminated: '已終止',
    suspended: '暫停', extended: '展延',
    confirmed: '已確認', completed: '已結業', cancelled: '已取消',
    formal: '正式', trial: '試上', approved: '已核准', rejected: '已拒絕',
    normal: '一般', emergency: '緊急',
}
const studentStatusLabels: Record<string, string> = {
    trial: '試上', pending: '待開課', active: '上課中', suspended: '暫停',
    terminated: '解約', extended: '展延', completed: '已結業',
}

function Tag({ status }: { status: string }) {
    return (
        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${statusColors[status] || 'bg-gray-100 text-gray-800'}`}>
            {statusLabels[status] || status}
        </span>
    )
}

function StatCard({ label, value, icon, color = 'blue' }: { label: string; value: number | string; icon: React.ReactNode; color?: string }) {
    const bg = color === 'green' ? 'bg-green-50' : color === 'yellow' ? 'bg-yellow-50' : color === 'red' ? 'bg-red-50' : 'bg-blue-50'
    const text = color === 'green' ? 'text-green-600' : color === 'yellow' ? 'text-yellow-600' : color === 'red' ? 'text-red-600' : 'text-blue-600'
    return (
        <div className="card flex items-center gap-4">
            <div className={`w-10 h-10 rounded flex items-center justify-center ${bg}`}>
                <span className={text}>{icon}</span>
            </div>
            <div>
                <p className="text-2xl font-bold" style={{ color: 'var(--ep-text-color-primary)' }}>{value}</p>
                <p className="text-xs" style={{ color: 'var(--ep-text-color-secondary)' }}>{label}</p>
            </div>
        </div>
    )
}

function Section({ title, icon, children, empty }: { title: string; icon: React.ReactNode; children: React.ReactNode; empty?: string }) {
    return (
        <div className="card">
            <h3 className="text-sm font-semibold mb-3 flex items-center gap-2" style={{ color: 'var(--ep-text-color-primary)' }}>
                {icon} {title}
            </h3>
            {children}
        </div>
    )
}

function StudentViewContent() {
    const searchParams = useSearchParams()
    const router = useRouter()
    const { user } = useAuth()
    const studentId = searchParams.get('id')

    const [data, setData] = useState<StudentViewData | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        if (!user || !studentId) return
        const fetch = async () => {
            setLoading(true)
            const { data: result, error: err } = await studentsApi.getView(studentId)
            if (err) setError(err.message)
            else setData(result)
            setLoading(false)
        }
        fetch()
    }, [user, studentId])

    if (!studentId) {
        return (
            <DashboardLayout>
                <div className="card text-center py-12">
                    <p style={{ color: 'var(--ep-text-color-secondary)' }}>缺少學生 ID 參數</p>
                    <button onClick={() => router.push('/students')} className="btn-primary mt-4">返回學生列表</button>
                </div>
            </DashboardLayout>
        )
    }

    if (loading) {
        return (
            <DashboardLayout>
                <div className="flex justify-center py-20">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2" style={{ borderColor: 'var(--ep-color-primary)' }}></div>
                </div>
            </DashboardLayout>
        )
    }

    if (error || !data) {
        return (
            <DashboardLayout>
                <div className="card text-center py-12">
                    <AlertTriangle className="w-12 h-12 mx-auto mb-3 text-red-400" />
                    <p className="text-red-600 mb-4">{error || '載入失敗'}</p>
                    <button onClick={() => router.push('/students')} className="btn-secondary">返回學生列表</button>
                </div>
            </DashboardLayout>
        )
    }

    const { student: s, account, line_binding, contracts, bookings_recent, courses, teacher_preferences, leave_records_recent, stats } = data

    return (
        <DashboardLayout>
            <div className="space-y-5">
                {/* Header */}
                <div className="flex items-center gap-3">
                    <button onClick={() => router.push('/students')} className="btn-secondary px-2 py-1.5">
                        <ArrowLeft className="w-4 h-4" />
                    </button>
                    <div className="flex-1">
                        <h1 className="text-xl font-bold flex items-center gap-2" style={{ color: 'var(--ep-text-color-primary)' }}>
                            <GraduationCap className="w-5 h-5" style={{ color: 'var(--ep-color-primary)' }} />
                            {s.name} {s.eng_name ? `(${s.eng_name})` : ''}
                        </h1>
                        <p className="text-xs mt-0.5" style={{ color: 'var(--ep-text-color-secondary)' }}>
                            {s.student_no} &middot; <Tag status={s.student_type || 'formal'} /> <Tag status={s.student_status || 'trial'} />
                            {!s.is_active && <span className="ml-2 text-red-500 font-medium">已停用</span>}
                        </p>
                    </div>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                    <StatCard label="剩餘堂數" value={stats.total_remaining_lessons} icon={<BookOpen className="w-5 h-5" />} color="blue" />
                    <StatCard label="已完成" value={stats.completed_bookings} icon={<CheckCircle className="w-5 h-5" />} color="green" />
                    <StatCard label="待上課" value={stats.upcoming_bookings} icon={<Clock className="w-5 h-5" />} color="yellow" />
                    <StatCard label="生效合約" value={stats.active_contracts} icon={<FileText className="w-5 h-5" />} color="blue" />
                    <StatCard label="已請假" value={stats.total_leaves_used} icon={<Calendar className="w-5 h-5" />} color="red" />
                </div>

                {/* Row 1: Basic Info + Account + LINE */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                    {/* Basic Info */}
                    <Section title="基本資料" icon={<User className="w-4 h-4" />}>
                        <div className="space-y-2 text-sm">
                            <div className="flex items-center gap-2"><Mail className="w-3.5 h-3.5 text-gray-400" /> {s.email}</div>
                            {s.phone && <div className="flex items-center gap-2"><Phone className="w-3.5 h-3.5 text-gray-400" /> {s.phone}</div>}
                            {s.id_number && <div className="flex items-center gap-2"><span className="text-gray-400">🪪</span> {s.id_number.slice(0, 3)}{'*'.repeat(Math.max(0, s.id_number.length - 6))}{s.id_number.slice(-3)}</div>}
                            {s.address && <div className="flex items-center gap-2"><MapPin className="w-3.5 h-3.5 text-gray-400" /> {s.address}</div>}
                            {s.birth_date && <div className="flex items-center gap-2"><Calendar className="w-3.5 h-3.5 text-gray-400" /> {s.birth_date}</div>}
                            <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--ep-text-color-secondary)' }}>
                                建立於 {s.created_at ? new Date(s.created_at).toLocaleDateString() : '-'}
                            </div>
                        </div>
                    </Section>

                    {/* Account */}
                    <Section title="帳號狀態" icon={<CheckCircle className="w-4 h-4" />}>
                        <div className="space-y-2 text-sm">
                            <div className="flex items-center justify-between">
                                <span style={{ color: 'var(--ep-text-color-secondary)' }}>登入帳號</span>
                                {account.has_account ? (
                                    <span className="inline-flex items-center gap-1 text-green-600 text-xs font-medium"><CheckCircle className="w-3 h-3" /> 已建立</span>
                                ) : (
                                    <span className="inline-flex items-center gap-1 text-yellow-600 text-xs font-medium"><XCircle className="w-3 h-3" /> 未建立</span>
                                )}
                            </div>
                            <div className="flex items-center justify-between">
                                <span style={{ color: 'var(--ep-text-color-secondary)' }}>Email 驗證</span>
                                {s.email_verified_at ? (
                                    <span className="text-green-600 text-xs font-medium">已驗證</span>
                                ) : (
                                    <span className="text-yellow-600 text-xs font-medium">未驗證</span>
                                )}
                            </div>
                            {account.has_account && account.role && (
                                <div className="flex items-center justify-between">
                                    <span style={{ color: 'var(--ep-text-color-secondary)' }}>角色</span>
                                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium" style={{ backgroundColor: 'var(--ep-color-primary)', color: '#fff' }}>
                                        {{ admin: '管理員', employee: '員工', teacher: '老師', student: '學生' }[account.role] || account.role}
                                    </span>
                                </div>
                            )}
                            {account.has_account && (
                                <div className="flex items-center justify-between">
                                    <span style={{ color: 'var(--ep-text-color-secondary)' }}>帳號狀態</span>
                                    <span className={`text-xs font-medium ${account.is_active ? 'text-green-600' : 'text-red-500'}`}>
                                        {account.is_active ? '啟用中' : '已停用'}
                                    </span>
                                </div>
                            )}
                        </div>
                    </Section>

                    {/* LINE */}
                    <Section title="LINE 綁定" icon={<MessageSquare className="w-4 h-4" />}>
                        {line_binding.bound ? (
                            <div className="flex items-center gap-3">
                                {line_binding.line_picture_url ? (
                                    <img src={line_binding.line_picture_url} alt="" className="w-10 h-10 rounded-full" />
                                ) : (
                                    <div className="w-10 h-10 rounded-full bg-[#06C755] flex items-center justify-center text-white text-sm font-bold">L</div>
                                )}
                                <div>
                                    <p className="text-sm font-medium">{line_binding.line_display_name}</p>
                                    <Tag status={line_binding.binding_status || 'active'} />
                                </div>
                            </div>
                        ) : (
                            <p className="text-sm" style={{ color: 'var(--ep-text-color-secondary)' }}>尚未綁定 LINE 帳號</p>
                        )}
                    </Section>
                </div>

                {/* Contracts */}
                <Section title={`合約 (${contracts.length})`} icon={<FileText className="w-4 h-4" />}>
                    {contracts.length === 0 ? (
                        <p className="text-sm py-4 text-center" style={{ color: 'var(--ep-text-color-secondary)' }}>尚無合約</p>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="border-b" style={{ borderColor: 'var(--ep-border-color)' }}>
                                        <th className="text-left py-2 pr-4 font-medium">合約編號</th>
                                        <th className="text-left py-2 pr-4 font-medium">狀態</th>
                                        <th className="text-left py-2 pr-4 font-medium">期間</th>
                                        <th className="text-center py-2 pr-4 font-medium">堂數</th>
                                        <th className="text-center py-2 pr-4 font-medium">請假</th>
                                        <th className="text-left py-2 pr-4 font-medium">教師</th>
                                        <th className="text-center py-2 font-medium">附約</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {contracts.map(c => (
                                        <tr key={c.id} className="border-b hover:bg-gray-50" style={{ borderColor: 'var(--ep-border-color-light, #e4e7ed)' }}>
                                            <td className="py-2 pr-4 font-mono text-xs">{c.contract_no}</td>
                                            <td className="py-2 pr-4"><Tag status={c.contract_status} /></td>
                                            <td className="py-2 pr-4 text-xs" style={{ color: 'var(--ep-text-color-secondary)' }}>
                                                {c.start_date} ~ {c.end_date}
                                            </td>
                                            <td className="py-2 pr-4 text-center">
                                                <span className="font-semibold" style={{ color: 'var(--ep-color-primary)' }}>{c.remaining_lessons}</span>
                                                <span style={{ color: 'var(--ep-text-color-secondary)' }}> / {c.total_lessons}</span>
                                            </td>
                                            <td className="py-2 pr-4 text-center text-xs">
                                                {c.used_leave_count} / {c.total_leave_allowed}
                                            </td>
                                            <td className="py-2 pr-4 text-xs">{c.teachers.join('、') || '-'}</td>
                                            <td className="py-2 text-center text-xs">{c.addendum_count > 0 ? c.addendum_count : '-'}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </Section>

                {/* Row 2: Bookings + Courses + Preferences */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    {/* Recent Bookings */}
                    <Section title={`近期預約 (${stats.total_bookings})`} icon={<Calendar className="w-4 h-4" />}>
                        {bookings_recent.length === 0 ? (
                            <p className="text-sm py-4 text-center" style={{ color: 'var(--ep-text-color-secondary)' }}>尚無預約記錄</p>
                        ) : (
                            <div className="space-y-2 max-h-72 overflow-y-auto">
                                {bookings_recent.map(b => (
                                    <div key={b.id} className="flex items-center justify-between py-1.5 px-2 rounded hover:bg-gray-50 text-sm">
                                        <div>
                                            <span className="font-medium">{b.booking_date}</span>
                                            <span className="ml-2 text-xs" style={{ color: 'var(--ep-text-color-secondary)' }}>{b.start_time}-{b.end_time}</span>
                                            <div className="text-xs" style={{ color: 'var(--ep-text-color-secondary)' }}>
                                                {b.course_name} &middot; {b.teacher_name}
                                            </div>
                                        </div>
                                        <Tag status={b.booking_status} />
                                    </div>
                                ))}
                            </div>
                        )}
                    </Section>

                    {/* Courses + Preferences */}
                    <div className="space-y-4">
                        <Section title={`選課 (${courses.length})`} icon={<BookOpen className="w-4 h-4" />}>
                            {courses.length === 0 ? (
                                <p className="text-sm py-2 text-center" style={{ color: 'var(--ep-text-color-secondary)' }}>尚無選課</p>
                            ) : (
                                <div className="flex flex-wrap gap-2">
                                    {courses.map(c => (
                                        <span key={c.id} className="inline-flex items-center px-2.5 py-1 rounded text-xs font-medium bg-blue-50" style={{ color: 'var(--ep-color-primary)' }}>
                                            {c.course_name} {c.course_code ? `(${c.course_code})` : ''}
                                        </span>
                                    ))}
                                </div>
                            )}
                        </Section>

                        <Section title={`教師偏好 (${teacher_preferences.length})`} icon={<Users className="w-4 h-4" />}>
                            {teacher_preferences.length === 0 ? (
                                <p className="text-sm py-2 text-center" style={{ color: 'var(--ep-text-color-secondary)' }}>尚無偏好設定</p>
                            ) : (
                                <div className="space-y-1.5 text-sm">
                                    {teacher_preferences.map(p => (
                                        <div key={p.id} className="flex items-center justify-between">
                                            <span>{p.course_name || '全域'}</span>
                                            <span className="text-xs" style={{ color: 'var(--ep-text-color-secondary)' }}>
                                                {p.primary_teacher_name ? `指定：${p.primary_teacher_name}` : `等級 >= ${p.min_teacher_level}`}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </Section>

                        <Section title={`請假記錄 (${stats.total_leaves_used})`} icon={<AlertTriangle className="w-4 h-4" />}>
                            {leave_records_recent.length === 0 ? (
                                <p className="text-sm py-2 text-center" style={{ color: 'var(--ep-text-color-secondary)' }}>尚無請假記錄</p>
                            ) : (
                                <div className="space-y-1.5 text-sm">
                                    {leave_records_recent.map(l => (
                                        <div key={l.id} className="flex items-center justify-between">
                                            <div>
                                                <span className="font-medium">{l.leave_date}</span>
                                                {l.leave_type && <span className="ml-1.5"><Tag status={l.leave_type} /></span>}
                                            </div>
                                            <Tag status={l.leave_status} />
                                        </div>
                                    ))}
                                </div>
                            )}
                        </Section>
                    </div>
                </div>
            </div>
        </DashboardLayout>
    )
}

export default function StudentViewPage() {
    return (
        <Suspense fallback={
            <DashboardLayout>
                <div className="flex justify-center py-20">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2" style={{ borderColor: 'var(--ep-color-primary)' }}></div>
                </div>
            </DashboardLayout>
        }>
            <StudentViewContent />
        </Suspense>
    )
}

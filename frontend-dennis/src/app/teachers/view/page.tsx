'use client'

import { useState, useEffect } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { Suspense } from 'react'
import { useAuth } from '@/lib/hooks/useAuth'
import { teachersApi, TeacherViewData } from '@/lib/api/teachers'
import DashboardLayout from '@/components/DashboardLayout'
import {
    ArrowLeft, User, Mail, Phone, MapPin, Calendar, BookOpen,
    FileText, CheckCircle, XCircle, Clock, Users, MessageSquare,
    DollarSign, AlertTriangle, Camera,
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
    suspended: 'bg-orange-100 text-orange-800',
    extended: 'bg-purple-100 text-purple-800',
}
const statusLabels: Record<string, string> = {
    active: '生效中', pending: '待確認', expired: '已到期', terminated: '已終止',
    suspended: '暫停', extended: '展延',
    confirmed: '已確認', completed: '已完成', cancelled: '已取消',
    approved: '已核准', rejected: '已拒絕',
}
const bonusTypeLabels: Record<string, string> = {
    trial_completed: '試上完成', trial_to_formal: '試上轉正', performance: '績效',
    substitute: '代課', referral: '轉介', other: '其他',
}

function Tag({ status }: { status: string }) {
    return (
        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${statusColors[status] || 'bg-gray-100 text-gray-800'}`}>
            {statusLabels[status] || status}
        </span>
    )
}

function StatCard({ label, value, icon, color = 'blue' }: { label: string; value: number | string; icon: React.ReactNode; color?: string }) {
    const bg = color === 'green' ? 'bg-green-50' : color === 'yellow' ? 'bg-yellow-50' : color === 'red' ? 'bg-red-50' : color === 'purple' ? 'bg-purple-50' : 'bg-blue-50'
    const text = color === 'green' ? 'text-green-600' : color === 'yellow' ? 'text-yellow-600' : color === 'red' ? 'text-red-600' : color === 'purple' ? 'text-purple-600' : 'text-blue-600'
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

function Section({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
    return (
        <div className="card">
            <h3 className="text-sm font-semibold mb-3 flex items-center gap-2" style={{ color: 'var(--ep-text-color-primary)' }}>
                {icon} {title}
            </h3>
            {children}
        </div>
    )
}

function TeacherViewContent() {
    const searchParams = useSearchParams()
    const router = useRouter()
    const { user, profile } = useAuth()
    const teacherId = searchParams.get('id')

    const [data, setData] = useState<TeacherViewData | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        if (!user || !teacherId) return
        const fetchData = async () => {
            setLoading(true)
            const { data: result, error: err } = await teachersApi.getView(teacherId)
            if (err) setError(err.message)
            else setData(result)
            setLoading(false)
        }
        fetchData()
    }, [user, teacherId])

    if (!teacherId) {
        return (
            <DashboardLayout>
                <div className="card text-center py-12">
                    <p style={{ color: 'var(--ep-text-color-secondary)' }}>缺少教師 ID 參數</p>
                    <button onClick={() => router.push('/teacher-overview')} className="btn-primary mt-4">返回教師總覽</button>
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
                    <button onClick={() => router.push('/teacher-overview')} className="btn-secondary">返回教師總覽</button>
                </div>
            </DashboardLayout>
        )
    }

    const { teacher: t, account, line_binding, contracts, bookings_recent, bonus_records_recent, stats } = data

    return (
        <DashboardLayout>
            <div className="space-y-5">
                {/* Header */}
                <div className="flex items-center gap-3">
                    <button onClick={() => router.push('/teacher-overview')} className="btn-secondary px-2 py-1.5">
                        <ArrowLeft className="w-4 h-4" />
                    </button>
                    {/* Avatar */}
                    <div className="relative group">
                        {t.avatar_url ? (
                            <img src={t.avatar_url} alt={t.name}
                                className="w-14 h-14 rounded-full object-cover border-2 border-white shadow" />
                        ) : (
                            <div className="w-14 h-14 rounded-full flex items-center justify-center text-white text-lg font-bold shadow"
                                style={{ background: 'linear-gradient(135deg, #4f6ef7, #7b93fa)' }}>
                                {t.name.charAt(0)}
                            </div>
                        )}
                        {profile?.employee_id && (
                            <label className="absolute inset-0 flex items-center justify-center rounded-full bg-black/40 opacity-0 group-hover:opacity-100 cursor-pointer transition-opacity">
                                <Camera className="w-5 h-5 text-white" />
                                <input type="file" className="hidden" accept=".jpg,.jpeg,.png,.webp"
                                    onChange={async (e) => {
                                        const file = e.target.files?.[0]
                                        if (!file) return
                                        if (file.size > 2 * 1024 * 1024) {
                                            alert('圖片大小不可超過 2MB')
                                            return
                                        }
                                        const { data: updated, error: err } = await teachersApi.uploadAvatar(t.id, file)
                                        if (err) {
                                            alert(err.message)
                                        } else {
                                            alert('頭像上傳成功')
                                            window.location.reload()
                                        }
                                    }}
                                />
                            </label>
                        )}
                    </div>
                    <div className="flex-1">
                        <h1 className="text-xl font-bold flex items-center gap-2" style={{ color: 'var(--ep-text-color-primary)' }}>
                            {t.name}
                        </h1>
                        <p className="text-xs mt-0.5" style={{ color: 'var(--ep-text-color-secondary)' }}>
                            {t.teacher_no} &middot; Lv.{t.teacher_level}
                            {!t.is_active && <span className="ml-2 text-red-500 font-medium">已停用</span>}
                        </p>
                    </div>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                    <StatCard label="已授學生" value={stats.total_students_taught} icon={<Users className="w-5 h-5" />} color="blue" />
                    <StatCard label="已完成" value={stats.completed_bookings} icon={<CheckCircle className="w-5 h-5" />} color="green" />
                    <StatCard label="待上課" value={stats.upcoming_bookings} icon={<Clock className="w-5 h-5" />} color="yellow" />
                    <StatCard label="生效合約" value={stats.active_contracts} icon={<FileText className="w-5 h-5" />} color="blue" />
                    <StatCard label="獎金總額" value={`$${stats.total_bonus_amount.toLocaleString()}`} icon={<DollarSign className="w-5 h-5" />} color="purple" />
                </div>

                {/* Row 1: Basic Info + Account + LINE */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                    {/* Basic Info */}
                    <Section title="基本資料" icon={<User className="w-4 h-4" />}>
                        <div className="space-y-2 text-sm">
                            <div className="flex items-center gap-2"><Mail className="w-3.5 h-3.5 text-gray-400" /> {t.email}</div>
                            {t.phone && <div className="flex items-center gap-2"><Phone className="w-3.5 h-3.5 text-gray-400" /> {t.phone}</div>}
                            {t.address && <div className="flex items-center gap-2"><MapPin className="w-3.5 h-3.5 text-gray-400" /> {t.address}</div>}
                            {t.bio && <div className="text-xs mt-2 p-2 rounded bg-gray-50" style={{ color: 'var(--ep-text-color-secondary)' }}>{t.bio}</div>}
                            <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--ep-text-color-secondary)' }}>
                                建立於 {t.created_at ? new Date(t.created_at).toLocaleDateString() : '-'}
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
                                {t.email_verified_at ? (
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
                                        <th className="text-center py-2 pr-4 font-medium">聘用類型</th>
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
                                            <td className="py-2 pr-4 text-center text-xs">
                                                {c.employment_type === 'hourly' ? '時薪制' : c.employment_type === 'monthly' ? '月薪制' : c.employment_type || '-'}
                                            </td>
                                            <td className="py-2 text-center text-xs">{c.addendum_count > 0 ? c.addendum_count : '-'}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </Section>

                {/* Row 2: Bookings + Bonus */}
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
                                                {b.course_name} &middot; {b.student_name}
                                            </div>
                                        </div>
                                        <Tag status={b.booking_status} />
                                    </div>
                                ))}
                            </div>
                        )}
                    </Section>

                    {/* Bonus Records */}
                    <Section title={`獎金記錄 (${stats.total_bonus_count})`} icon={<DollarSign className="w-4 h-4" />}>
                        {bonus_records_recent.length === 0 ? (
                            <p className="text-sm py-4 text-center" style={{ color: 'var(--ep-text-color-secondary)' }}>尚無獎金記錄</p>
                        ) : (
                            <div className="space-y-2 max-h-72 overflow-y-auto">
                                {bonus_records_recent.map(b => (
                                    <div key={b.id} className="flex items-center justify-between py-1.5 px-2 rounded hover:bg-gray-50 text-sm">
                                        <div>
                                            <span className="font-medium">{b.bonus_date}</span>
                                            <span className="ml-2 inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800">
                                                {bonusTypeLabels[b.bonus_type] || b.bonus_type}
                                            </span>
                                            {b.student_name && (
                                                <div className="text-xs" style={{ color: 'var(--ep-text-color-secondary)' }}>
                                                    學生：{b.student_name}
                                                </div>
                                            )}
                                            {b.description && (
                                                <div className="text-xs" style={{ color: 'var(--ep-text-color-secondary)' }}>{b.description}</div>
                                            )}
                                        </div>
                                        <span className="font-semibold text-sm" style={{ color: 'var(--ep-color-primary)' }}>
                                            ${b.amount.toLocaleString()}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        )}
                    </Section>
                </div>
            </div>
        </DashboardLayout>
    )
}

export default function TeacherViewPage() {
    return (
        <Suspense fallback={
            <DashboardLayout>
                <div className="flex justify-center py-20">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2" style={{ borderColor: 'var(--ep-color-primary)' }}></div>
                </div>
            </DashboardLayout>
        }>
            <TeacherViewContent />
        </Suspense>
    )
}

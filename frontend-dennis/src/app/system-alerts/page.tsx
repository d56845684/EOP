'use client'

import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '@/lib/hooks/useAuth'
import { alertsApi, SystemAlert, AlertSeverity } from '@/lib/api/alerts'
import DashboardLayout from '@/components/DashboardLayout'
import {
    Bell, AlertTriangle, AlertCircle, Info,
    CheckCircle, ChevronLeft, ChevronRight,
    Filter, Eye, CheckCheck
} from 'lucide-react'

// ============================================================
// 告警類別設定 — 未來擴充只需在這裡加一筆
// ============================================================

interface AlertTypeConfig {
    label: string
    color: string
    bgColor: string
}

const ALERT_TYPE_MAP: Record<string, AlertTypeConfig> = {
    calendar_sync_failed: { label: 'Calendar 同步失敗', color: 'text-orange-700', bgColor: 'bg-orange-50' },
    zoom_create_failed: { label: 'Zoom 建立失敗', color: 'text-red-700', bgColor: 'bg-red-50' },
    line_send_failed: { label: 'LINE 發送失敗', color: 'text-green-700', bgColor: 'bg-green-50' },
    email_send_failed: { label: 'Email 發送失敗', color: 'text-blue-700', bgColor: 'bg-blue-50' },
}

const SEVERITY_CONFIG: Record<AlertSeverity, { label: string; icon: typeof AlertCircle; color: string; bgColor: string; borderColor: string }> = {
    error: { label: '錯誤', icon: AlertCircle, color: 'text-red-600', bgColor: 'bg-red-50', borderColor: 'border-red-200' },
    warning: { label: '警告', icon: AlertTriangle, color: 'text-amber-600', bgColor: 'bg-amber-50', borderColor: 'border-amber-200' },
    info: { label: '資訊', icon: Info, color: 'text-blue-600', bgColor: 'bg-blue-50', borderColor: 'border-blue-200' },
}

function getAlertTypeConfig(type: string): AlertTypeConfig {
    return ALERT_TYPE_MAP[type] || { label: type, color: 'text-slate-700', bgColor: 'bg-slate-50' }
}

function formatTime(isoString: string): string {
    const d = new Date(isoString)
    const now = new Date()
    const diffMs = now.getTime() - d.getTime()
    const diffMin = Math.floor(diffMs / 60000)
    const diffHour = Math.floor(diffMs / 3600000)
    const diffDay = Math.floor(diffMs / 86400000)

    if (diffMin < 1) return '剛剛'
    if (diffMin < 60) return `${diffMin} 分鐘前`
    if (diffHour < 24) return `${diffHour} 小時前`
    if (diffDay < 7) return `${diffDay} 天前`
    return d.toLocaleDateString('zh-TW', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

// ============================================================
// Page
// ============================================================

export default function SystemAlertsPage() {
    const { hasPage } = useAuth()

    const [alerts, setAlerts] = useState<SystemAlert[]>([])
    const [loading, setLoading] = useState(true)
    const [page, setPage] = useState(1)
    const [totalPages, setTotalPages] = useState(1)
    const [total, setTotal] = useState(0)
    const [unreadCount, setUnreadCount] = useState(0)

    // 篩選
    const [filterSeverity, setFilterSeverity] = useState<string>('')
    const [filterRead, setFilterRead] = useState<string>('')  // '' | 'true' | 'false'
    const [filterType, setFilterType] = useState<string>('')

    const fetchAlerts = useCallback(async () => {
        setLoading(true)
        const params: Record<string, unknown> = { page, per_page: 20 }
        if (filterSeverity) params.severity = filterSeverity
        if (filterRead !== '') params.is_read = filterRead === 'true'

        const { data, error } = await alertsApi.list(params as any)
        if (!error && data) {
            let items = data.data || []
            // 前端篩選 alert_type（後端目前沒有此篩選）
            if (filterType) {
                items = items.filter(a => a.alert_type === filterType)
            }
            setAlerts(items)
            setTotal(data.total)
            setTotalPages(data.total_pages)
            setUnreadCount(data.unread_count)
        }
        setLoading(false)
    }, [page, filterSeverity, filterRead, filterType])

    useEffect(() => { fetchAlerts() }, [fetchAlerts])

    const handleMarkRead = async (alertId: string) => {
        await alertsApi.markRead(alertId)
        fetchAlerts()
    }

    const handleMarkAllRead = async () => {
        await alertsApi.markAllRead()
        fetchAlerts()
    }

    // 收集已有的 alert_type（動態）
    const alertTypes = [...new Set(alerts.map(a => a.alert_type))]

    return (
        <DashboardLayout>
            <div className="max-w-5xl mx-auto">
                {/* Header */}
                <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-red-50 flex items-center justify-center">
                            <Bell className="w-5 h-5 text-red-500" />
                        </div>
                        <div>
                            <h1 className="text-xl font-semibold text-slate-900">系統告警</h1>
                            <p className="text-sm text-slate-500">
                                共 {total} 筆{unreadCount > 0 && <span className="text-red-500 font-medium">，{unreadCount} 筆未讀</span>}
                            </p>
                        </div>
                    </div>
                    {unreadCount > 0 && (
                        <button onClick={handleMarkAllRead} className="btn-secondary flex items-center gap-1.5 text-sm">
                            <CheckCheck className="w-4 h-4" />
                            全部已讀
                        </button>
                    )}
                </div>

                {/* Filters */}
                <div className="flex flex-wrap items-center gap-3 mb-4">
                    <Filter className="w-4 h-4 text-slate-400" />

                    <select
                        value={filterSeverity}
                        onChange={e => { setFilterSeverity(e.target.value); setPage(1) }}
                        className="input-field text-sm py-1.5 px-3 w-auto"
                    >
                        <option value="">所有嚴重度</option>
                        <option value="error">錯誤</option>
                        <option value="warning">警告</option>
                        <option value="info">資訊</option>
                    </select>

                    <select
                        value={filterRead}
                        onChange={e => { setFilterRead(e.target.value); setPage(1) }}
                        className="input-field text-sm py-1.5 px-3 w-auto"
                    >
                        <option value="">全部</option>
                        <option value="false">未讀</option>
                        <option value="true">已讀</option>
                    </select>

                    <select
                        value={filterType}
                        onChange={e => { setFilterType(e.target.value); setPage(1) }}
                        className="input-field text-sm py-1.5 px-3 w-auto"
                    >
                        <option value="">所有類別</option>
                        {Object.entries(ALERT_TYPE_MAP).map(([key, cfg]) => (
                            <option key={key} value={key}>{cfg.label}</option>
                        ))}
                    </select>
                </div>

                {/* Alert List */}
                {loading ? (
                    <div className="flex justify-center py-20">
                        <div className="w-7 h-7 rounded-full border-2 border-slate-200 border-t-primary-500 animate-spin" />
                    </div>
                ) : alerts.length === 0 ? (
                    <div className="text-center py-20">
                        <CheckCircle className="w-12 h-12 text-green-300 mx-auto mb-3" />
                        <p className="text-slate-500">目前沒有告警</p>
                    </div>
                ) : (
                    <div className="space-y-3">
                        {alerts.map(alert => {
                            const sevCfg = SEVERITY_CONFIG[alert.severity]
                            const typeCfg = getAlertTypeConfig(alert.alert_type)
                            const SevIcon = sevCfg.icon

                            return (
                                <div
                                    key={alert.id}
                                    className={`border rounded-xl p-4 transition-colors ${
                                        alert.is_read
                                            ? 'bg-white border-slate-200 opacity-60'
                                            : `bg-white ${sevCfg.borderColor} border-l-4`
                                    }`}
                                >
                                    <div className="flex items-start gap-3">
                                        {/* Severity icon */}
                                        <div className={`mt-0.5 p-1.5 rounded-lg ${sevCfg.bgColor}`}>
                                            <SevIcon className={`w-4 h-4 ${sevCfg.color}`} />
                                        </div>

                                        {/* Content */}
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2 mb-1">
                                                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${typeCfg.bgColor} ${typeCfg.color}`}>
                                                    {typeCfg.label}
                                                </span>
                                                <span className={`text-xs px-1.5 py-0.5 rounded ${sevCfg.bgColor} ${sevCfg.color}`}>
                                                    {sevCfg.label}
                                                </span>
                                                <span className="text-xs text-slate-400 ml-auto shrink-0">
                                                    {formatTime(alert.created_at)}
                                                </span>
                                            </div>
                                            <h3 className="text-sm font-medium text-slate-900">{alert.title}</h3>
                                            {alert.message && (
                                                <p className="text-xs text-slate-500 mt-1 line-clamp-2">{alert.message}</p>
                                            )}
                                            {alert.metadata && Object.keys(alert.metadata).length > 0 && (
                                                <div className="flex flex-wrap gap-2 mt-2">
                                                    {Object.entries(alert.metadata).map(([k, v]) => (
                                                        <span key={k} className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded">
                                                            {k}: {String(v)}
                                                        </span>
                                                    ))}
                                                </div>
                                            )}
                                        </div>

                                        {/* Actions */}
                                        {!alert.is_read && (
                                            <button
                                                onClick={() => handleMarkRead(alert.id)}
                                                className="shrink-0 p-1.5 rounded-lg text-slate-400 hover:text-primary-500 hover:bg-primary-50 transition-colors"
                                                title="標記已讀"
                                            >
                                                <Eye className="w-4 h-4" />
                                            </button>
                                        )}
                                    </div>
                                </div>
                            )
                        })}
                    </div>
                )}

                {/* Pagination */}
                {totalPages > 1 && (
                    <div className="flex items-center justify-center gap-2 mt-6">
                        <button
                            onClick={() => setPage(p => Math.max(1, p - 1))}
                            disabled={page === 1}
                            className="btn-secondary p-2 disabled:opacity-40"
                        >
                            <ChevronLeft className="w-4 h-4" />
                        </button>
                        <span className="text-sm text-slate-600 px-3">
                            {page} / {totalPages}
                        </span>
                        <button
                            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                            disabled={page === totalPages}
                            className="btn-secondary p-2 disabled:opacity-40"
                        >
                            <ChevronRight className="w-4 h-4" />
                        </button>
                    </div>
                )}
            </div>
        </DashboardLayout>
    )
}

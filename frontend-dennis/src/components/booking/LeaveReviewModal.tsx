'use client'

import { useState, useEffect } from 'react'
import { X, CheckCircle, XCircle, UserPlus } from 'lucide-react'
import { leaveRecordsApi, LeaveRecord } from '@/lib/api/leaveRecords'
import { substituteDetailsApi } from '@/lib/api/substituteDetails'
import { bookingsApi, TeacherOption, TeacherContractOption } from '@/lib/api/bookings'

interface LeaveReviewModalProps {
    leaveRecord: LeaveRecord
    onClose: () => void
    onSuccess: () => void
}

export default function LeaveReviewModal({ leaveRecord, onClose, onSuccess }: LeaveReviewModalProps) {
    const isTeacherLeave = leaveRecord.initiator_type === 'teacher'
    const [mode, setMode] = useState<'view' | 'reject' | 'substitute'>('view')
    const [rejectionReason, setRejectionReason] = useState('')
    const [submitting, setSubmitting] = useState(false)
    const [error, setError] = useState<string | null>(null)

    // 代課表單
    const [subTeacherId, setSubTeacherId] = useState('')
    const [subContractId, setSubContractId] = useState('')
    const [subReason, setSubReason] = useState('')
    const [teacherOptions, setTeacherOptions] = useState<TeacherOption[]>([])
    const [contractOptions, setContractOptions] = useState<TeacherContractOption[]>([])
    const [loadingTeachers, setLoadingTeachers] = useState(false)
    const [loadingContracts, setLoadingContracts] = useState(false)

    // booking 資料（代課用）
    const [bookingData, setBookingData] = useState<{ student_id: string; teacher_id: string } | null>(null)

    // 載入 booking 資料（用於教師請假的代課流程）
    useEffect(() => {
        if (!isTeacherLeave || !leaveRecord.booking_id) return
        const load = async () => {
            const { data } = await bookingsApi.get(leaveRecord.booking_id!)
            if (data) {
                setBookingData({ student_id: data.student_id, teacher_id: data.teacher_id })
            }
        }
        load()
    }, [isTeacherLeave, leaveRecord.booking_id])

    // 進入代課模式時，載入教師選項（依學生偏好過濾 + 排除原教師）
    useEffect(() => {
        if (mode !== 'substitute' || !bookingData) return
        const load = async () => {
            setLoadingTeachers(true)
            const { data } = await bookingsApi.getTeacherOptions({ student_id: bookingData.student_id })
            if (data) {
                setTeacherOptions(data.filter(t => t.id !== bookingData.teacher_id))
            }
            setLoadingTeachers(false)
        }
        load()
    }, [mode, bookingData])

    // 選擇代課教師後載入合約
    useEffect(() => {
        if (!subTeacherId) {
            setContractOptions([])
            setSubContractId('')
            return
        }
        const load = async () => {
            setLoadingContracts(true)
            const { data } = await bookingsApi.getTeacherContractOptions(subTeacherId)
            const contracts = data || []
            setContractOptions(contracts)
            setSubContractId(contracts.length > 0 ? contracts[0].id : '')
            setLoadingContracts(false)
        }
        load()
    }, [subTeacherId])

    const handleApprove = async () => {
        setSubmitting(true)
        setError(null)
        const { error: apiError } = await leaveRecordsApi.approve(leaveRecord.id)
        if (apiError) {
            setError(apiError.message)
            setSubmitting(false)
        } else {
            onSuccess()
        }
    }

    const handleReject = async () => {
        if (!rejectionReason.trim()) {
            setError('請填寫駁回原因')
            return
        }
        setSubmitting(true)
        setError(null)
        const { error: apiError } = await leaveRecordsApi.reject(leaveRecord.id, rejectionReason.trim())
        if (apiError) {
            setError(apiError.message)
            setSubmitting(false)
        } else {
            onSuccess()
        }
    }

    const handleSubstitute = async () => {
        if (!subTeacherId) { setError('請選擇代課教師'); return }
        if (!subContractId) { setError('請選擇代課教師合約'); return }
        setSubmitting(true)
        setError(null)

        // 1. 建立代課
        const { error: subError } = await substituteDetailsApi.create({
            booking_id: leaveRecord.booking_id!,
            substitute_teacher_id: subTeacherId,
            substitute_contract_id: subContractId,
            reason: subReason.trim() || leaveRecord.reason,
        })
        if (subError) {
            setError(subError.message)
            setSubmitting(false)
            return
        }

        // 2. 核准請假（預約保持 confirmed，不會取消）
        const { error: approveError } = await leaveRecordsApi.approve(leaveRecord.id)
        if (approveError) {
            // 代課已建立但核准失敗，提示但仍算部分成功
            setError(`代課已指派，但請假核准失敗: ${approveError.message}`)
            setSubmitting(false)
            return
        }

        onSuccess()
    }

    return (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 max-h-[90vh] overflow-y-auto">
                <div className="flex items-center justify-between p-4 border-b">
                    <h3 className="text-lg font-semibold text-gray-900">
                        審核請假申請
                        {isTeacherLeave && (
                            <span className="ml-2 text-sm font-normal text-purple-600">（教師請假）</span>
                        )}
                    </h3>
                    <button onClick={onClose} className="text-gray-400 hover:text-gray-500">
                        <X className="w-5 h-5" />
                    </button>
                </div>
                <div className="p-4 space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                        <div>
                            <label className="block text-xs font-medium text-gray-500">請假編號</label>
                            <p className="text-sm font-mono bg-gray-100 px-2 py-1 rounded mt-0.5">{leaveRecord.leave_no}</p>
                        </div>
                        <div>
                            <label className="block text-xs font-medium text-gray-500">預約編號</label>
                            <p className="text-sm font-mono bg-gray-100 px-2 py-1 rounded mt-0.5">{leaveRecord.booking_no || '-'}</p>
                        </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                        <div>
                            <label className="block text-xs font-medium text-gray-500">發起者</label>
                            <p className="text-sm text-gray-900 mt-0.5">
                                {leaveRecord.initiator_name || '-'}
                                <span className="ml-1 text-xs text-gray-500">
                                    ({isTeacherLeave ? '教師' : '學生'})
                                </span>
                            </p>
                        </div>
                        <div>
                            <label className="block text-xs font-medium text-gray-500">請假日期</label>
                            <p className="text-sm text-gray-900 mt-0.5">{leaveRecord.leave_date}</p>
                        </div>
                    </div>
                    <div>
                        <label className="block text-xs font-medium text-gray-500">請假原因</label>
                        <p className="text-sm text-gray-900 mt-0.5 bg-gray-50 px-3 py-2 rounded border">{leaveRecord.reason}</p>
                    </div>

                    {/* === view 模式提示 === */}
                    {mode === 'view' && !isTeacherLeave && (
                        <div className="bg-amber-50 border border-amber-200 rounded-md p-3">
                            <p className="text-sm text-amber-800">
                                核准後將自動取消預約（歸還堂數、釋放時段、取消 Zoom 會議），並寫入合約請假紀錄。
                            </p>
                        </div>
                    )}
                    {mode === 'view' && isTeacherLeave && (
                        <div className="bg-purple-50 border border-purple-200 rounded-md p-3">
                            <p className="text-sm text-purple-800">
                                教師請假需要指派代課教師。指派代課後預約維持確認狀態，由代課教師授課。
                            </p>
                            <p className="text-sm text-purple-600 mt-1">
                                若不指派代課，也可直接「核准取消」來取消此預約。
                            </p>
                        </div>
                    )}

                    {/* === reject 模式 === */}
                    {mode === 'reject' && (
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                駁回原因 <span className="text-red-500">*</span>
                            </label>
                            <textarea
                                value={rejectionReason}
                                onChange={(e) => setRejectionReason(e.target.value)}
                                rows={3}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                                placeholder="請輸入駁回原因..."
                            />
                        </div>
                    )}

                    {/* === substitute 模式（教師請假專用） === */}
                    {mode === 'substitute' && (
                        <div className="space-y-3 border-t pt-3">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    代課教師 <span className="text-red-500">*</span>
                                </label>
                                {loadingTeachers ? (
                                    <p className="text-sm text-gray-500">載入中...</p>
                                ) : (
                                    <select
                                        value={subTeacherId}
                                        onChange={(e) => setSubTeacherId(e.target.value)}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                                    >
                                        <option value="">請選擇代課教師</option>
                                        {teacherOptions.map(t => (
                                            <option key={t.id} value={t.id}>
                                                {t.teacher_no} - {t.name} (Lv.{t.teacher_level || '-'})
                                            </option>
                                        ))}
                                    </select>
                                )}
                            </div>
                            {subTeacherId && (
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        代課教師合約 <span className="text-red-500">*</span>
                                    </label>
                                    {loadingContracts ? (
                                        <p className="text-sm text-gray-500">載入中...</p>
                                    ) : contractOptions.length === 0 ? (
                                        <p className="text-sm text-red-500">此教師無有效合約</p>
                                    ) : (
                                        <select
                                            value={subContractId}
                                            onChange={(e) => setSubContractId(e.target.value)}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                                        >
                                            {contractOptions.map(c => (
                                                <option key={c.id} value={c.id}>{c.contract_no}</option>
                                            ))}
                                        </select>
                                    )}
                                </div>
                            )}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">代課備註</label>
                                <textarea
                                    value={subReason}
                                    onChange={(e) => setSubReason(e.target.value)}
                                    rows={2}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                                    placeholder="選填"
                                />
                            </div>
                        </div>
                    )}

                    {error && (
                        <div className="bg-red-50 border border-red-200 rounded-md p-3">
                            <p className="text-sm text-red-600">{error}</p>
                        </div>
                    )}
                </div>

                {/* === 按鈕區 === */}
                <div className="flex justify-end gap-2 p-4 border-t">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md"
                    >
                        關閉
                    </button>

                    {mode === 'view' && (
                        <>
                            <button
                                onClick={() => { setMode('reject'); setError(null) }}
                                disabled={submitting}
                                className="inline-flex items-center px-4 py-2 text-sm font-medium text-red-700 bg-red-50 hover:bg-red-100 rounded-md disabled:opacity-50"
                            >
                                <XCircle className="w-4 h-4 mr-1" />
                                駁回
                            </button>
                            {isTeacherLeave && (
                                <button
                                    onClick={() => { setMode('substitute'); setError(null) }}
                                    disabled={submitting || !bookingData}
                                    className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 rounded-md disabled:opacity-50"
                                >
                                    <UserPlus className="w-4 h-4 mr-1" />
                                    指派代課
                                </button>
                            )}
                            <button
                                onClick={handleApprove}
                                disabled={submitting}
                                className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 rounded-md disabled:opacity-50"
                            >
                                <CheckCircle className="w-4 h-4 mr-1" />
                                {submitting ? '處理中...' : isTeacherLeave ? '核准取消' : '核准'}
                            </button>
                        </>
                    )}

                    {mode === 'reject' && (
                        <>
                            <button
                                onClick={() => { setMode('view'); setRejectionReason(''); setError(null) }}
                                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md"
                            >
                                返回
                            </button>
                            <button
                                onClick={handleReject}
                                disabled={submitting}
                                className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-md disabled:opacity-50"
                            >
                                <XCircle className="w-4 h-4 mr-1" />
                                {submitting ? '處理中...' : '確認駁回'}
                            </button>
                        </>
                    )}

                    {mode === 'substitute' && (
                        <>
                            <button
                                onClick={() => { setMode('view'); setSubTeacherId(''); setSubContractId(''); setSubReason(''); setError(null) }}
                                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md"
                            >
                                返回
                            </button>
                            <button
                                onClick={handleSubstitute}
                                disabled={submitting || !subTeacherId || !subContractId}
                                className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 rounded-md disabled:opacity-50"
                            >
                                <UserPlus className="w-4 h-4 mr-1" />
                                {submitting ? '處理中...' : '確認指派代課'}
                            </button>
                        </>
                    )}
                </div>
            </div>
        </div>
    )
}

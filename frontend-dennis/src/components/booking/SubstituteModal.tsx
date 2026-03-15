'use client'

import { useState, useEffect } from 'react'
import { X } from 'lucide-react'
import { substituteDetailsApi } from '@/lib/api/substituteDetails'
import { bookingsApi, TeacherOption, TeacherContractOption } from '@/lib/api/bookings'

interface SubstituteModalProps {
    bookingId: string
    bookingNo: string
    studentId: string
    originalTeacherId: string
    onClose: () => void
    onSuccess: () => void
}

export default function SubstituteModal({ bookingId, bookingNo, studentId, originalTeacherId, onClose, onSuccess }: SubstituteModalProps) {
    const [teacherId, setTeacherId] = useState('')
    const [contractId, setContractId] = useState('')
    const [reason, setReason] = useState('')
    const [submitting, setSubmitting] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const [teacherOptions, setTeacherOptions] = useState<TeacherOption[]>([])
    const [contractOptions, setContractOptions] = useState<TeacherContractOption[]>([])
    const [loadingTeachers, setLoadingTeachers] = useState(true)
    const [loadingContracts, setLoadingContracts] = useState(false)

    // 載入教師選項（依學生偏好過濾 + 排除原教師）
    useEffect(() => {
        const load = async () => {
            setLoadingTeachers(true)
            const { data } = await bookingsApi.getTeacherOptions({ student_id: studentId })
            if (data) {
                setTeacherOptions(data.filter(t => t.id !== originalTeacherId))
            }
            setLoadingTeachers(false)
        }
        load()
    }, [studentId, originalTeacherId])

    // 選擇教師後載入合約
    useEffect(() => {
        if (!teacherId) {
            setContractOptions([])
            setContractId('')
            return
        }
        const load = async () => {
            setLoadingContracts(true)
            const { data } = await bookingsApi.getTeacherContractOptions(teacherId)
            const contracts = data || []
            setContractOptions(contracts)
            if (contracts.length > 0) {
                setContractId(contracts[0].id)
            } else {
                setContractId('')
            }
            setLoadingContracts(false)
        }
        load()
    }, [teacherId])

    const handleSubmit = async () => {
        if (!teacherId) {
            setError('請選擇代課教師')
            return
        }
        if (!contractId) {
            setError('請選擇代課教師合約')
            return
        }
        setSubmitting(true)
        setError(null)

        const { error: apiError } = await substituteDetailsApi.create({
            booking_id: bookingId,
            substitute_teacher_id: teacherId,
            substitute_contract_id: contractId,
            reason: reason.trim() || undefined,
        })

        if (apiError) {
            setError(apiError.message)
            setSubmitting(false)
        } else {
            onSuccess()
        }
    }

    return (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
                <div className="flex items-center justify-between p-4 border-b">
                    <h3 className="text-lg font-semibold text-gray-900">指派代課</h3>
                    <button onClick={onClose} className="text-gray-400 hover:text-gray-500">
                        <X className="w-5 h-5" />
                    </button>
                </div>
                <div className="p-4 space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">預約編號</label>
                        <p className="text-sm text-gray-900 font-mono bg-gray-100 px-3 py-2 rounded">{bookingNo}</p>
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            代課教師 <span className="text-red-500">*</span>
                        </label>
                        {loadingTeachers ? (
                            <p className="text-sm text-gray-500">載入中...</p>
                        ) : (
                            <select
                                value={teacherId}
                                onChange={(e) => setTeacherId(e.target.value)}
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
                    {teacherId && (
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
                                    value={contractId}
                                    onChange={(e) => setContractId(e.target.value)}
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
                        <label className="block text-sm font-medium text-gray-700 mb-1">代課原因</label>
                        <textarea
                            value={reason}
                            onChange={(e) => setReason(e.target.value)}
                            rows={2}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                            placeholder="選填"
                        />
                    </div>
                    {error && (
                        <div className="bg-red-50 border border-red-200 rounded-md p-3">
                            <p className="text-sm text-red-600">{error}</p>
                        </div>
                    )}
                </div>
                <div className="flex justify-end gap-3 p-4 border-t">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md"
                    >
                        取消
                    </button>
                    <button
                        onClick={handleSubmit}
                        disabled={submitting || !teacherId || !contractId}
                        className="px-4 py-2 text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 rounded-md disabled:opacity-50"
                    >
                        {submitting ? '指派中...' : '確認指派'}
                    </button>
                </div>
            </div>
        </div>
    )
}

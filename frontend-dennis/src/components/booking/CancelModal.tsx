'use client'

import { useState } from 'react'
import { X } from 'lucide-react'
import { bookingsApi } from '@/lib/api/bookings'

interface CancelModalProps {
    bookingId: string
    bookingNo: string
    onClose: () => void
    onSuccess: () => void
}

export default function CancelModal({ bookingId, bookingNo, onClose, onSuccess }: CancelModalProps) {
    const [reason, setReason] = useState('')
    const [submitting, setSubmitting] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const handleSubmit = async () => {
        if (!reason.trim()) {
            setError('請填寫取消原因')
            return
        }
        setSubmitting(true)
        setError(null)

        const { error: apiError } = await bookingsApi.update(bookingId, {
            booking_status: 'cancelled',
            notes: reason.trim(),
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
                    <h3 className="text-lg font-semibold text-gray-900">取消預約</h3>
                    <button onClick={onClose} className="text-gray-400 hover:text-gray-500">
                        <X className="w-5 h-5" />
                    </button>
                </div>
                <div className="p-4 space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">預約編號</label>
                        <p className="text-sm text-gray-900 font-mono bg-gray-100 px-3 py-2 rounded">{bookingNo}</p>
                    </div>
                    <div className="bg-red-50 border border-red-200 rounded-md p-3">
                        <p className="text-sm text-red-700">取消預約將歸還堂數並釋放時段，此操作無法復原。</p>
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            取消原因 <span className="text-red-500">*</span>
                        </label>
                        <textarea
                            value={reason}
                            onChange={(e) => setReason(e.target.value)}
                            rows={3}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                            placeholder="請輸入取消原因..."
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
                        返回
                    </button>
                    <button
                        onClick={handleSubmit}
                        disabled={submitting}
                        className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-md disabled:opacity-50"
                    >
                        {submitting ? '取消中...' : '確認取消'}
                    </button>
                </div>
            </div>
        </div>
    )
}

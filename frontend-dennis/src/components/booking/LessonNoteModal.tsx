'use client'

import { useEffect, useState } from 'react'
import { X, ExternalLink, CheckCircle, Clock, FileText, Pencil } from 'lucide-react'
import { lessonNotesApi, type LessonNote } from '@/lib/api/lessonNotes'

type ViewerRole = 'teacher' | 'student' | 'staff'

interface LessonNoteModalProps {
  bookingId: string
  bookingNo: string
  viewerRole: ViewerRole
  onClose: () => void
  onSuccess?: () => void
}

const GOOGLE_DOC_PREFIX = 'https://docs.google.com/'

export default function LessonNoteModal({
  bookingId,
  bookingNo,
  viewerRole,
  onClose,
  onSuccess,
}: LessonNoteModalProps) {
  const [loading, setLoading] = useState(true)
  const [note, setNote] = useState<LessonNote | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [urlInput, setUrlInput] = useState('')
  const [editing, setEditing] = useState(false)

  useEffect(() => {
    void fetchNote()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bookingId])

  async function fetchNote() {
    setLoading(true)
    setError(null)
    const { data, error: apiError } = await lessonNotesApi.get(bookingId)
    if (apiError) {
      setError(apiError.message)
    } else {
      setNote(data ?? null)
    }
    setLoading(false)
  }

  async function handleUpload() {
    const url = urlInput.trim()
    if (!url.startsWith(GOOGLE_DOC_PREFIX)) {
      setError(`筆記連結必須以 ${GOOGLE_DOC_PREFIX} 開頭`)
      return
    }
    setSubmitting(true)
    setError(null)
    const { data, error: apiError } = await lessonNotesApi.upload(bookingId, url)
    if (apiError) {
      setError(apiError.message)
      setSubmitting(false)
      return
    }
    setNote(data ?? null)
    setSubmitting(false)
    onSuccess?.()
  }

  async function handleUpdate() {
    const url = urlInput.trim()
    if (!url.startsWith(GOOGLE_DOC_PREFIX)) {
      setError(`筆記連結必須以 ${GOOGLE_DOC_PREFIX} 開頭`)
      return
    }
    setSubmitting(true)
    setError(null)
    const { data, error: apiError } = await lessonNotesApi.update(bookingId, url)
    if (apiError) {
      setError(apiError.message)
      setSubmitting(false)
      return
    }
    setNote(data ?? null)
    setEditing(false)
    setSubmitting(false)
    onSuccess?.()
  }

  function startEdit() {
    if (!note) return
    setUrlInput(note.google_doc_url)
    setEditing(true)
    setError(null)
  }

  function cancelEdit() {
    setEditing(false)
    setUrlInput('')
    setError(null)
  }

  async function handleConfirm() {
    setSubmitting(true)
    setError(null)
    const { data, error: apiError } = await lessonNotesApi.confirm(bookingId)
    if (apiError) {
      setError(apiError.message)
      setSubmitting(false)
      return
    }
    setNote(data ?? null)
    setSubmitting(false)
    onSuccess?.()
  }

  const isTeacher = viewerRole === 'teacher'
  const canConfirm = viewerRole === 'student' || viewerRole === 'staff'

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4">
        <div className="flex items-center justify-between p-4 border-b">
          <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <FileText className="w-5 h-5 text-blue-600" />
            課後筆記
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-500">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">預約編號</label>
            <p className="text-sm text-gray-900 font-mono bg-gray-100 px-3 py-2 rounded">{bookingNo}</p>
          </div>

          {loading && <p className="text-sm text-gray-500">載入中...</p>}

          {/* 已確認 */}
          {!loading && note && note.status === 'confirmed' && (
            <div className="bg-green-50 border border-green-200 rounded-md p-3 space-y-2">
              <div className="flex items-center gap-2 text-green-700">
                <CheckCircle className="w-4 h-4" />
                <span className="text-sm font-medium">筆記已確認</span>
              </div>
              <a
                href={note.google_doc_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline break-all"
              >
                <ExternalLink className="w-4 h-4 shrink-0" />
                {note.google_doc_url}
              </a>
              <p className="text-xs text-gray-500">
                確認者類型：{note.confirmed_by_role === 'student' ? '學生' : '員工/管理員'}
                {note.confirmed_at && ` ・ ${new Date(note.confirmed_at).toLocaleString()}`}
              </p>
            </div>
          )}

          {/* 待確認 — 非編輯模式 */}
          {!loading && note && note.status === 'pending_confirmation' && !editing && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-md p-3 space-y-2">
              <div className="flex items-center gap-2 text-yellow-700">
                <Clock className="w-4 h-4" />
                <span className="text-sm font-medium">等待確認</span>
              </div>
              <a
                href={note.google_doc_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline break-all"
              >
                <ExternalLink className="w-4 h-4 shrink-0" />
                {note.google_doc_url}
              </a>
              <p className="text-xs text-gray-500">
                上傳時間：{new Date(note.uploaded_at).toLocaleString()}
              </p>
            </div>
          )}

          {/* 待確認 + 老師 + 編輯模式 */}
          {!loading && note && note.status === 'pending_confirmation' && editing && isTeacher && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Google Doc 連結 <span className="text-red-500">*</span>
              </label>
              <input
                type="url"
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                placeholder="https://docs.google.com/document/d/..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm"
              />
              <p className="mt-1 text-xs text-gray-500">
                修改後立即生效。確認後將無法再修改。
              </p>
            </div>
          )}

          {/* 老師 + 尚未上傳 → 上傳表單 */}
          {!loading && !note && isTeacher && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Google Doc 連結 <span className="text-red-500">*</span>
              </label>
              <input
                type="url"
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                placeholder="https://docs.google.com/document/d/..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm"
              />
              <p className="mt-1 text-xs text-gray-500">
                上傳後將通知學生確認；學生或管理員任一確認，預約即轉為「完成」。
              </p>
            </div>
          )}

          {/* 學生/管理員 + 尚未上傳 → 提示 */}
          {!loading && !note && !isTeacher && (
            <div className="bg-gray-50 border border-gray-200 rounded-md p-3">
              <p className="text-sm text-gray-600">老師尚未上傳本堂課後筆記</p>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-md p-3">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}
        </div>

        <div className="flex justify-end gap-3 p-4 border-t">
          {/* 編輯模式：取消編輯回到檢視 */}
          {editing ? (
            <button
              onClick={cancelEdit}
              disabled={submitting}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md disabled:opacity-50"
            >
              取消編輯
            </button>
          ) : (
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md"
            >
              關閉
            </button>
          )}

          {/* 老師：上傳 */}
          {!loading && !note && isTeacher && (
            <button
              onClick={handleUpload}
              disabled={submitting || !urlInput.trim()}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md disabled:opacity-50"
            >
              {submitting ? '上傳中...' : '上傳筆記'}
            </button>
          )}

          {/* 老師：編輯（pending 且未進入編輯模式） */}
          {!loading && note && note.status === 'pending_confirmation' && isTeacher && !editing && (
            <button
              onClick={startEdit}
              className="inline-flex items-center px-4 py-2 text-sm font-medium text-blue-700 bg-blue-50 hover:bg-blue-100 rounded-md"
            >
              <Pencil className="w-4 h-4 mr-1" />
              修改連結
            </button>
          )}

          {/* 老師：儲存修改 */}
          {!loading && note && note.status === 'pending_confirmation' && isTeacher && editing && (
            <button
              onClick={handleUpdate}
              disabled={submitting || !urlInput.trim()}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md disabled:opacity-50"
            >
              {submitting ? '儲存中...' : '儲存修改'}
            </button>
          )}

          {/* 學生/管理員：確認（status 為 pending、且老師沒在編輯中） */}
          {!loading && note && note.status === 'pending_confirmation' && canConfirm && !editing && (
            <button
              onClick={handleConfirm}
              disabled={submitting}
              className="px-4 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 rounded-md disabled:opacity-50"
            >
              {submitting ? '確認中...' : '確認筆記'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

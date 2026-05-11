import { apiGet, apiPost, apiPut } from './client'

export type LessonNoteStatus = 'pending_confirmation' | 'confirmed'

export interface LessonNote {
  id: string
  booking_id: string
  google_doc_url: string
  status: LessonNoteStatus
  uploaded_by: string
  uploaded_at: string
  confirmed_by?: string | null
  confirmed_by_role?: 'student' | 'employee' | null
  confirmed_at?: string | null
  created_at: string
  updated_at: string
}

export const lessonNotesApi = {
  get: (bookingId: string) =>
    apiGet<LessonNote | null>(
      `/api/v1/bookings/${bookingId}/lesson-note`,
      '取得課後筆記失敗'
    ),

  upload: (bookingId: string, googleDocUrl: string) =>
    apiPost<LessonNote>(
      `/api/v1/bookings/${bookingId}/lesson-note`,
      { google_doc_url: googleDocUrl },
      '上傳課後筆記失敗'
    ),

  update: (bookingId: string, googleDocUrl: string) =>
    apiPut<LessonNote>(
      `/api/v1/bookings/${bookingId}/lesson-note`,
      { google_doc_url: googleDocUrl },
      '修改課後筆記失敗'
    ),

  confirm: (bookingId: string) =>
    apiPost<LessonNote>(
      `/api/v1/bookings/${bookingId}/lesson-note/confirm`,
      undefined,
      '確認課後筆記失敗'
    ),
}

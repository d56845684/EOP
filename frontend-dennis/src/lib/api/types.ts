/** 後端統一錯誤回傳格式 */
export interface ApiErrorBody {
  success: false
  message: string
  detail: string
  error_code: number  // 6 位數：<3-status><3-seq>，例 401005=IDLE_TIMEOUT
}

/** 前端 API 函式統一錯誤物件 */
export interface ApiError {
  message: string   // 給使用者看的中文訊息
  code: number      // 後端 error_code（6 位數）
  status: number    // HTTP status code
}

/** 回傳資料的 API 結果 */
export type ApiResult<T> =
  | { data: T; error: null }
  | { data: null; error: ApiError }

/** 不回傳資料的 API 結果（DELETE 等） */
export type ApiActionResult =
  | { success: true; message: string; error: null }
  | { success: false; message: string; error: ApiError }

/** Blob 下載結果 */
export type ApiBlobResult =
  | { blob: Blob; error: null }
  | { blob: null; error: ApiError }

import i18n from '@/i18n';
import {
  getApiErrorTranslationKey,
  getApiErrorTranslationKeyByRequest,
} from '@/constants/apiErrorMessages';

export interface ApiResponseMeta {
  success: boolean;
  message?: string;
  error_code?: string | null;
}

export interface BaseResponse extends ApiResponseMeta {}

export interface DataResponse<T> extends BaseResponse {
  data: T;
}

export interface DownloadResponse extends BaseResponse {
  file_name: string;
  download_url: string;
}

export interface ListResponse<T> extends BaseResponse {
  data: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface PaginatedData<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface PaginatedResponse<T> extends BaseResponse {
  data: PaginatedData<T>;
}

type ApiErrorLike = Partial<ApiResponseMeta> & {
  detail?: unknown;
  request_url?: string | null;
  response?: {
    data?: Partial<ApiResponseMeta> & { detail?: unknown };
  };
};

const getDetailMessage = (detail: unknown) => {
  if (typeof detail === 'string') return detail;

  if (Array.isArray(detail) && detail.length > 0) {
    const message = detail.find((item) => typeof item?.msg === 'string')?.msg;
    return message?.replace(/^Value error,\s*/, '');
  }

  return '';
};

const getTranslatedApiErrorMessage = (errorCode?: string | null) => {
  if (!errorCode) return '';

  const key = getApiErrorTranslationKey(errorCode);
  if (!key || !i18n.global.te(key)) return '';

  return i18n.global.t(key) as string;
};

const getTranslatedApiErrorMessageByRequest = (
  requestUrl?: string | null,
  errorCode?: string | null,
) => {
  const key = getApiErrorTranslationKeyByRequest(requestUrl, errorCode);
  if (key && i18n.global.te(key)) {
    return i18n.global.t(key) as string;
  }

  return '';
};

export const assertApiSuccess = <T extends Partial<ApiResponseMeta>>(response: T, fallback = '操作失敗'): T => {
  if (response.success === false) {
    const error = new Error(response.message || fallback) as Error & ApiResponseMeta;
    error.success = false;
    error.message = response.message || fallback;
    error.error_code = response.error_code ?? null;
    throw error;
  }

  return response;
};

export const getApiErrorMessage = (error: unknown, fallback = '操作失敗') => {
  const apiError = error as ApiErrorLike | undefined;
  const errorCode = apiError?.response?.data?.error_code || apiError?.error_code;
  const requestUrl = apiError?.request_url;

  const requestScopedMessage = getTranslatedApiErrorMessageByRequest(requestUrl, errorCode);
  if (requestScopedMessage) return requestScopedMessage;

  const translatedMessage = getTranslatedApiErrorMessage(errorCode);
  if (translatedMessage) return translatedMessage;

  return apiError?.response?.data?.message
    || getDetailMessage(apiError?.response?.data?.detail)
    || apiError?.message
    || getDetailMessage(apiError?.detail)
    || fallback;
};

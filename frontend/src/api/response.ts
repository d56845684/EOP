export interface ApiResponseMeta {
  success: boolean;
  message?: string;
  error_code?: string | null;
}

export interface BaseResponse extends ApiResponseMeta {}

export interface DataResponse<T> extends BaseResponse {
  data: T;
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
  return apiError?.response?.data?.message
    || getDetailMessage(apiError?.response?.data?.detail)
    || apiError?.message
    || getDetailMessage(apiError?.detail)
    || fallback;
};

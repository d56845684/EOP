import axios from 'axios';
import { useAuthStore } from '@/stores/auth';
import { refreshToken } from '@/api/auth';
import { getAccessToken, setAuthTokens } from '@/utils/auth-token';

const AUTH_SESSION_EXPIRED = 'AUTH_SESSION_EXPIRED';

const getApiBaseURL = () => {
  const baseURL = import.meta.env.VITE_API_BASE_URL || '/api';

  if (typeof window !== 'undefined' && window.location.protocol === 'https:' && baseURL.startsWith('http://')) {
    const apiURL = new URL(baseURL);
    if (apiURL.hostname === window.location.hostname) {
      apiURL.protocol = 'https:';
      return apiURL.toString();
    }
  }

  return baseURL;
};

let isHandlingSessionExpired = false;

interface ApiErrorPayload {
  success: false;
  status: number;
  message: string;
  detail?: unknown;
  error_code?: string | null;
  response?: {
    status: number;
    data: unknown;
  };
}

const normalizeApiError = (
  status: number,
  data?: Record<string, any>,
  fallbackMessage = '系統異常',
): ApiErrorPayload => {
  const message = data?.message || (typeof data?.detail === 'string' ? data.detail : '') || fallbackMessage;

  return {
    success: false,
    status,
    message,
    detail: data?.detail,
    error_code: data?.error_code ?? null,
    response: {
      status,
      data,
    },
  };
};

const redirectToLoginForExpiredSession = () => {
  if (isHandlingSessionExpired) return;

  isHandlingSessionExpired = true;

  const authStore = useAuthStore();
  authStore.clearLocalState();

  window.setTimeout(() => {
    isHandlingSessionExpired = false;
  }, 1000);
};

// 1. Axios Instance Setup
const service = axios.create({
  baseURL: getApiBaseURL(),
  timeout: 10000, // 10s
  withCredentials: true, // Mandatory for cross-origin cookie transmission
});

// Flags for token refresh
let isRefreshing = false;
let failedQueue: any[] = [];

const processQueue = (error: any) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve();
    }
  });
  failedQueue = [];
};

// 2. Request Interceptor
service.interceptors.request.use(
  (config) => {
    const accessToken = getAccessToken();
    if (accessToken) {
      config.headers.Authorization = `Bearer ${accessToken}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 3. Response Interceptor
service.interceptors.response.use(
  (response) => {
    // 檢查 responseType 是否為 blob，或者是 Content-Type 是否為檔案類型
    // 如果是檔案下載，直接回傳完整的 response 物件
    if (response.config.responseType === 'blob' || response.data instanceof Blob) {
      return response;
    }
    // Success: Return the actual data payload directly
    return response.data;
  },
  async (error) => {
    const { response } = error;
    const originalRequest = error.config;

    // --- 新增：處理 Blob 類型的錯誤訊息 ---
    if (response?.data instanceof Blob && response.data.type === 'application/json') {
      try {
        // 將 Blob 轉回 JSON 文字，這樣才能顯示正確的錯誤訊息
        const text = await response.data.text();
        const errorData = JSON.parse(text);
        const normalizedBlobError = normalizeApiError(response.status || 500, errorData, '操作失敗');
        if (errorData.error_code === AUTH_SESSION_EXPIRED) {
          redirectToLoginForExpiredSession();
        }
        return Promise.reject(normalizedBlobError);
      } catch {
        return Promise.reject(normalizeApiError(response.status || 500, undefined, '操作失敗'));
      }
    }

    if (response?.data?.error_code === AUTH_SESSION_EXPIRED) {
      redirectToLoginForExpiredSession();
      return Promise.reject(normalizeApiError(response.status || 401, response.data, '登入狀態已過期，請重新登入'));
    }

    if (response?.status === 401 && !originalRequest._retry) {
      // Prevent infinite loops if the refresh API itself returns 401
      if (originalRequest.url?.includes('/v1/auth/refresh')) {
        const authStore = useAuthStore();
        authStore.clearLocalState();
        return Promise.reject(normalizeApiError(response.status || 401, response.data, '登入狀態已過期，請重新登入'));
      }

      if (isRefreshing) {
        // If already refreshing, queue this request
        return new Promise(function (resolve, reject) {
          failedQueue.push({ resolve, reject });
        })
          .then(() => {
            return service(originalRequest);
          })
          .catch((err) => {
            return Promise.reject(err);
          });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const refreshResponse = await refreshToken();
        setAuthTokens(refreshResponse.tokens || refreshResponse.data);
        processQueue(null); // Resolve queued requests
        return service(originalRequest); // Retry the original request
      } catch (refreshError) {
        processQueue(refreshError);
        const authStore = useAuthStore();
        authStore.clearLocalState(); // Force logout
        if (axios.isAxiosError(refreshError)) {
          return Promise.reject(
            normalizeApiError(
              refreshError.response?.status || 401,
              refreshError.response?.data,
              '登入狀態已過期，請重新登入',
            ),
          );
        }
        return Promise.reject(normalizeApiError(401, undefined, '登入狀態已過期，請重新登入'));
      } finally {
        isRefreshing = false;
      }
    }

    if (!error.response) {
      return Promise.reject(normalizeApiError(0, undefined, '網路連線異常，請稍後再試'));
    }

    // 處理 400 / 403 / 404 / 409 / 422 / 500 等一般錯誤
    if (response) {
      return Promise.reject(normalizeApiError(response.status, response.data, '系統異常'));
    }

    return Promise.reject(normalizeApiError(0, undefined, '網路連線異常，請稍後再試'));
  }
);

export default service;

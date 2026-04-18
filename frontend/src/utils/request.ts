import axios from 'axios';
import { ElMessage } from 'element-plus';
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

const redirectToLoginForExpiredSession = (message = '登入狀態已過期，請重新登入') => {
  if (isHandlingSessionExpired) return;

  isHandlingSessionExpired = true;
  ElMessage.closeAll();
  ElMessage.error(message);

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
      // 將 Blob 轉回 JSON 文字，這樣才能顯示正確的錯誤訊息
      const text = await response.data.text();
      const errorData = JSON.parse(text);
      if (errorData.error_code === AUTH_SESSION_EXPIRED) {
        redirectToLoginForExpiredSession(errorData.message);
        return Promise.reject(errorData);
      }
      ElMessage.error(errorData.message || '操作失敗');
      return Promise.reject(errorData);
    }

    if (response?.data?.error_code === AUTH_SESSION_EXPIRED) {
      redirectToLoginForExpiredSession(response.data.message);
      return Promise.reject(response.data);
    }

    if (response?.status === 401 && !originalRequest._retry) {
      // Prevent infinite loops if the refresh API itself returns 401
      if (originalRequest.url?.includes('/v1/auth/refresh')) {
        const authStore = useAuthStore();
        authStore.clearLocalState();
        return Promise.reject(error);
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
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    if (!error.response) {
      ElMessage.error('網路連線異常，請稍後再試');
    }

    // 處理 400 或其他一般錯誤
    if (response) {
      // 這裡提取後端回傳的錯誤內容
      // 假設後端格式為 { message: "手機號碼格式錯誤", code: 40001 }
      const errorMessage = response.data?.message || '系統異常';
      
      // 根據需求決定是否要過濾 401（因為 401 可能由上面的重刷邏輯處理）
      if (response.status !== 401) {
        if (originalRequest?.showError !== false) {
          ElMessage.closeAll();
          ElMessage.error(errorMessage);
        }
      }
      
      // 即將後端的錯誤資料傳回，讓組件知道發生什麼事，但不一定要再彈窗
      return Promise.reject(response.data); 
    } else {
      // 網路中斷或 Timeout
      ElMessage.error('網路連線異常，請稍後再試');
      return Promise.reject(error);
    }
  }
);

export default service;

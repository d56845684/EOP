import axios from 'axios';
import { ElMessage } from 'element-plus';
import { useAuthStore } from '@/stores/auth';
import { refreshToken } from '@/api/auth';

// 1. Axios Instance Setup
const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
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
    // Bearer Token logic removed. 
    // We rely entirely on the browser's cookie management with withCredentials: true.
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 3. Response Interceptor
service.interceptors.response.use(
  (response) => {
    // Success: Return the actual data payload directly
    return response.data;
  },
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
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
        await refreshToken();
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
    return Promise.reject(error);
  }
);

export default service;

import axios from 'axios';
import { ElMessage } from 'element-plus';
import router from '@/router';

// 1. Axios Instance Setup
const service = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
    timeout: 10000, // 10s
    withCredentials: true, // Mandatory for cross-origin cookie transmission
});

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
    (error) => {
        if (error.response) {
            const status = error.response.status;
            const message = error.response.data.message || error.response.data.detail;
            switch (status) {
                case 400:
                    ElMessage.error(message || '請求錯誤 (Bad Request)');
                    break;
                case 401:
                    ElMessage.error(message || '請重新登入 (Unauthorized)');
                    // The cookie is typically invalid or expired here.
                    router.push('/login');
                    break;
                case 403:
                    ElMessage.error(message || '權限不足 (Forbidden)');
                    break;
                case 404:
                    ElMessage.error(message || '找不到資源 (Not Found)');
                    break;
                case 500:
                    ElMessage.error(message || '伺服器錯誤 (Internal Server Error)');
                    break;
                default:
                    ElMessage.error(message || `連線錯誤 (${status})`);
            }
        } else {
            ElMessage.error('網路連線異常，請稍後再試');
        }
        return Promise.reject(error);
    }
);

export default service;

import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { loginApi, logout as logoutApi, getMeApi, type LoginRequest, type UserInfo } from '@/api/auth';
import { usePermissionStore } from '@/stores/permission';
import router from '@/router';

export const useAuthStore = defineStore('auth', () => {
    // State: Only keep userInfo
    const userInfo = ref<UserInfo | null>(null);

    // Getters: Authenticated if userInfo exists
    const isAuthenticated = computed(() => !!userInfo.value);

    // Actions
    const login = async (credentials: LoginRequest) => {
        const res = await loginApi(credentials);
        if (res.success) {
            if (res.user) {
                userInfo.value = res.user;
            } else {
                await checkAuth();
            }
        }
        return res;
    };

    const checkAuth = async () => {
        try {
            const res = await getMeApi();
            if (res.success && res.data) {
                userInfo.value = res.data;
            } else {
                userInfo.value = null;
            }
        } catch (e) {
            console.error('Check Auth failed:', e);
            userInfo.value = null;
        }
    };

    const clearLocalState = () => {
        console.log('clearLocalState');
        // 1. Clear user info
        userInfo.value = null;

        // 2. Clear permissions and route generation flags
        const permissionStore = usePermissionStore();
        permissionStore.resetState();

        // 3. Clear LocalStorage/SessionStorage if you have any persisted data
        localStorage.removeItem('auth'); // Adjust based on your persistence setup

        // 4. Redirect to login
        if (router) {
            router.push('/login');
        }
    };

    const logout = async (logoutAll: boolean = false) => {
        try {
            await logoutApi({ logout_all_devices: logoutAll });
        } catch (error) {
            console.warn('Logout API failed, but continuing local cleanup', error);
        } finally {
            clearLocalState();
        }
    };

    return { userInfo, isAuthenticated, login, checkAuth, logout, clearLocalState };
});

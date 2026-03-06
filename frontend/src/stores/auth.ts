import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { loginApi, logoutApi, getMeApi, type LoginRequest, type UserInfo } from '@/api/auth';
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

    const logout = async () => {
        try {
            await logoutApi();
        } catch (e) {
            console.error('Logout API failed', e);
        } finally {
            userInfo.value = null;
            if (router) {
                router.push('/login');
            }
        }
    };

    return { userInfo, isAuthenticated, login, checkAuth, logout };
});

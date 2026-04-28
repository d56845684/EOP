import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { loginApi, logout as logoutApi, getMeApi, type LoginRequest, type UserInfo } from '@/api/auth';
import { usePermissionStore } from '@/stores/permission';
import router from '@/router';
import { getUserProfileApi, type UserProfile } from '@/api/user';
import { assertApiSuccess } from '@/api/response';
import adminAvatar from '@/assets/avatars/admin.svg?url';
import teacherAvatar from '@/assets/avatars/teacher.svg?url';
import studentAvatar from '@/assets/avatars/student.svg?url';
import defaultAvatar from '@/assets/avatars/default.svg?url';
import { clearAuthTokens, setAuthTokens } from '@/utils/auth-token';
import { useApiError } from '@/composables/useApiError';


export const useAuthStore = defineStore('auth', () => {
  const { showApiError } = useApiError();
  // State: Keep userInfo and add profile
  const userInfo = ref<UserInfo | null>(null);
  const profile = ref<UserProfile | null>(null);

  // Getters: Authenticated if userInfo exists
  const isAuthenticated = computed(() => !!userInfo.value);

  const userAvatar = computed(() => {
    let avatar = '';
    switch (profile.value?.role) {
      case 'admin':
        avatar = adminAvatar;
        break;
      case 'teacher':
        avatar = teacherAvatar;
        break;
      case 'student':
        avatar = studentAvatar;
        break;
      default:
        avatar = defaultAvatar;
    }
    return profile.value?.avatar_url || avatar;
  });

  // Actions
  const fetchProfile = async () => {
    try {
      const res = assertApiSuccess(await getUserProfileApi(), '取得使用者資料失敗');
      if (res.data) {
        profile.value = res.data;
      } else {
        clearLocalState();
        throw new Error('Profile data is empty');
      }
    } catch (error) {
      console.error('Fetch profile failed:', error);
      showApiError(error, 'Failed to fetch user profile');
      clearLocalState();
      throw error;
    }
  };
  const login = async (credentials: LoginRequest) => {
    const res = await loginApi(credentials);
    if (res.success) {
      setAuthTokens(res.tokens);
      if (res.user) {
        userInfo.value = res.user;
      } else {
        await checkAuth();
      }
      await fetchProfile();
    }
    return res;
  };

  const checkAuth = async () => {
    try {
      const res = assertApiSuccess(await getMeApi(), '取得登入資訊失敗');
      if (res.success && res.data) {
        userInfo.value = res.data;
      } else {
        userInfo.value = null;
        clearLocalState();
      }
    } catch (e) {
      console.error('Check Auth failed:', e);
      userInfo.value = null;
      clearLocalState();
      throw e;
    }
  };

  const clearLocalState = (options: { redirect?: boolean } = {}) => {
    const { redirect = true } = options;
    console.log('clearLocalState');
    // 1. Clear user info & profile
    userInfo.value = null;
    profile.value = null;

    // 2. Clear permissions and route generation flags
    const permissionStore = usePermissionStore();
    permissionStore.resetState();

    // 3. Clear LocalStorage/SessionStorage if you have any persisted data
    localStorage.removeItem('auth'); // Adjust based on your persistence setup
    clearAuthTokens();

    // 4. Redirect to login
    if (redirect && router) {
      router.replace({ name: 'Login' }).catch(() => {});
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

  return { userInfo, profile, isAuthenticated, userAvatar, login, checkAuth, fetchProfile, logout, clearLocalState };
});

import router from '@/router';
import { useAuthStore } from '@/stores/auth';
import { usePermissionStore } from '@/stores/permission';
import { ElMessage } from 'element-plus';

console.log('🛡️ 路由守衛檔案已成功載入！');
// Optional: import NProgress from 'nprogress'; // If you use a loading bar

const whiteList = ['/login', '/register', '/404'];

router.beforeEach(async (to, _from, next) => {
    console.log(`🚀 準備前往路由：${to.path}`);
    const authStore = useAuthStore();
    const permissionStore = usePermissionStore();

    // 1. If the route is in the whitelist, let it pass directly
    if (whiteList.includes(to.path)) {
        return next();
    }

    // 🌟 改變判斷方式：不要看陣列長度，看我們專屬的旗標
    const hasPermissions = permissionStore.isRoutesGenerated;

    if (hasPermissions) {
        console.log("hasPermissions", hasPermissions)
        // If loaded, just proceed
        if (to.path === '/login') {
            next({ path: '/' });
        } else {
            next();
        }
    } else {
        // 3. If not loaded (e.g., fresh login or page refresh), fetch them
        try {
            // If user info is missing, fetch it first
            if (!authStore.userInfo) {
                await authStore.checkAuth(); // using checkAuth which exists in the store
            }

            // Fetch permissions and generate dynamic routes
            const role = authStore.userInfo?.role || '';
            const accessRoutes = await permissionStore.generateRoutes(role);
            console.log("accessRoutes", accessRoutes)

            // Dynamically add routes to the router
            accessRoutes.forEach((route) => {
                router.addRoute('Layout', route); // Add as children of Layout
            });

            // Hack: replace: true ensures the dynamically added routes are completely resolved before navigating
            next({ ...to, replace: true });

        } catch (error) {
            // If any API fails (e.g., 401 Unauthorized because cookie expired or missing)
            console.error('Permission Error:', error);
            await authStore.logout(); // Clear any residual state
            ElMessage.error('登入驗證失敗或已過期，請重新登入');
            next(`/login?redirect=${to.path}`);
        }
    }
});

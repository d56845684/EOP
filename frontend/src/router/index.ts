import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';
import { useAuthStore } from '../stores/auth';
import { usePermissionStore } from '../stores/permission';

const router = createRouter({
    history: createWebHistory(),
    routes: [
        {
            path: '/login',
            name: 'Login',
            component: () => import('../views/auth/LoginView.vue'),
        },
        {
            path: '/',
            name: 'Layout',
            component: () => import('../layouts/MainLayout.vue'),
            redirect: '/dashboard', // Safe landing
            children: [], // Populated dynamically
        },
    ],
});

router.beforeEach(async (to, _from, next) => {
    const authStore = useAuthStore();
    const permissionStore = usePermissionStore();

    // Simple auth check
    if (to.name !== 'Login' && !authStore.isAuthenticated) {
        next({ name: 'Login' });
    } else {
        if (to.name === 'Login') {
            next();
        } else {
            // Check if routes are already generated
            if (permissionStore.addRoutes.length === 0) {
                // TEMPORARY BYPASS FOR DEVELOPMENT
                const accessRoutes = permissionStore.generateRoutesUnfiltered();

                accessRoutes.forEach(route => {
                    router.addRoute('Layout', route as RouteRecordRaw);
                });

                // TODO: Revert this bypass when backend RBAC is ready
                next({ ...to, replace: true });
            } else {
                next();
            }
        }
    }
});

export default router;

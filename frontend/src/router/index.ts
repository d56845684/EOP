import { createRouter, createWebHistory } from 'vue-router';
import { constantRoutes } from './routes';

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
            redirect: '/dashboard',
            children: constantRoutes,
        },
    ],
});



export default router;

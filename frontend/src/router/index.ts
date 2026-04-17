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
            path: '/auth/success',
            name: 'AuthSuccess',
            component: () => import('../views/auth/AuthSuccess.vue'),
        },
        {
            path: '/auth/error',
            name: 'AuthError',
            component: () => import('../views/auth/AuthError.vue'),
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

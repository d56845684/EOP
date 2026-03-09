import { createRouter, createWebHistory } from 'vue-router';

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



export default router;

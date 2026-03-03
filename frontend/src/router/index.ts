import { createRouter, createWebHistory } from 'vue-router';
import { useMockStore } from '../stores/mockStore';

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
            component: () => import('../layouts/MainLayout.vue'),
            redirect: '/dashboard', // Safe landing
            children: [
                {
                    path: 'dashboard',
                    name: 'Dashboard',
                    component: () => import('../views/Dashboard.vue'),
                },
                {
                    path: 'reports',
                    name: 'Reports',
                    component: () => import('../views/reports/ReportStats.vue'),
                },
                {
                    path: 'teacher',
                    name: 'Teachers',
                    component: () => import('../views/teacher/TeacherList.vue'),
                },
                {
                    path: 'student',
                    name: 'Students',
                    component: () => import('../views/student/StudentList.vue'),
                },
                {
                    path: 'booking',
                    name: 'Bookings',
                    component: () => import('../views/booking/BookingList.vue'),
                },
                {
                    path: 'course',
                    name: 'Courses',
                    component: () => import('../views/course/CourseList.vue'),
                },
                {
                    path: 'salary',
                    name: 'Salary',
                    component: () => import('../views/salary/SalaryReport.vue'),
                },
                {
                    path: 'settings/account',
                    name: 'AccountSettings',
                    component: () => import('../views/settings/AccountList.vue'),
                },
                {
                    path: 'settings/role',
                    name: 'RoleSettings',
                    component: () => import('../views/settings/RoleList.vue'),
                },
                // --- Teacher Portal ---
                {
                    path: 'teacher-portal/schedule',
                    name: 'ScheduleSettings',
                    component: () => import('../views/teacher-portal/ScheduleSettings.vue'),
                },
                {
                    path: 'teacher-portal/history',
                    name: 'BookingHistory',
                    component: () => import('../views/teacher-portal/BookingHistory.vue'),
                },
                {
                    path: 'teacher-portal/profile',
                    name: 'TeacherProfile',
                    component: () => import('../views/teacher-portal/TeacherProfile.vue'),
                },
                // --- Student Portal ---
                {
                    path: 'student-portal/booking',
                    name: 'ClassBooking',
                    component: () => import('../views/student-portal/ClassBooking.vue'),
                },
                {
                    path: 'student-portal/profile',
                    name: 'StudentProfile',
                    component: () => import('../views/student-portal/StudentProfile.vue'),
                },
            ],
        },
    ],
});

router.beforeEach(async (to, _from, next) => {
    const store = useMockStore();
    // Simple auth check
    if (to.name !== 'Login' && !store.currentUser) {
        next({ name: 'Login' });
    } else {
        next();
    }
});

export default router;

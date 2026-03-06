import { defineStore } from 'pinia';
import { ref } from 'vue';
import type { RouteRecordRaw } from 'vue-router';
import { SYSTEM_MODULES } from './mockStore';

export const usePermissionStore = defineStore('permission', () => {
    const routes = ref<RouteRecordRaw[]>([]);
    const addRoutes = ref<RouteRecordRaw[]>([]);

    // The async routes (everything under Dashboard, Teacher, Student, etc)
    const asyncRoutes: RouteRecordRaw[] = [
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
    ];

    const constantRoutes: RouteRecordRaw[] = [
        // Login and other static routes
    ];

    const generateRoutesUnfiltered = () => {
        // TEMPORARY BYPASS FOR DEVELOPMENT
        // Combine constantRoutes and ALL asyncRoutes
        addRoutes.value = asyncRoutes;
        routes.value = constantRoutes.concat(asyncRoutes);

        // Provide the menu structure too, overriding what might have been filtered
        // We export SYSTEM_MODULES directly for the Sidebar to consume
        return asyncRoutes;
    };

    return { routes, addRoutes, generateRoutesUnfiltered, menuModules: SYSTEM_MODULES };
});

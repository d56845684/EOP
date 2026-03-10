import type { RouteRecordRaw } from 'vue-router';

// Constant routes that don't need permissions
export const constantRoutes: RouteRecordRaw[] = [
    {
        path: '/dashboard',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue'),
        meta: { title: '儀表板', icon: 'i-hugeicons:home-12' }
    },
    {
        path: '/profile',
        name: 'Profile',
        component: () => import('../views/Profile.vue'),
        meta: { title: '個人設定', icon: 'i-hugeicons:user-settings-01' }
    }
];

// Admin routes that need permission filtering if employee
export const adminRoutes: RouteRecordRaw[] = [
    {
        path: '/reports',
        name: 'Reports',
        component: () => import('../views/reports/ReportStats.vue'),
        meta: { title: '報表分析', icon: 'i-hugeicons:analytics-01', pageKey: 'reports.view' }
    },
    {
        path: '/teacher',
        name: 'Teachers',
        component: () => import('../views/teacher/TeacherList.vue'),
        meta: { title: '講師管理', icon: 'i-hugeicons:manager', pageKey: 'teachers.list' }
    },
    {
        path: '/student',
        name: 'Students',
        component: () => import('../views/student/StudentList.vue'),
        meta: { title: '學員管理', icon: 'i-hugeicons:student', pageKey: 'students.list' }
    },
    {
        path: '/booking',
        name: 'Bookings',
        component: () => import('../views/booking/BookingList.vue'),
        meta: { title: '預約管理', icon: 'i-hugeicons:calendar-02', pageKey: 'bookings.list' }
    },
    {
        path: '/course',
        name: 'Courses',
        component: () => import('../views/course/CourseList.vue'),
        meta: { title: '課程管理', icon: 'i-hugeicons:books-01', pageKey: 'courses.list' }
    },
    {
        path: '/salary',
        name: 'Salary',
        component: () => import('../views/salary/SalaryReport.vue'),
        meta: { title: '薪資計算', icon: 'i-hugeicons:money-bag-02', pageKey: 'salary.view' }
    },
    {
        path: '/settings',
        name: 'Settings',
        meta: { title: '系統設定', icon: 'i-hugeicons:settings-01' }, // A parent wrapper
        children: [
            {
                path: '/account',
                name: 'AccountSettings',
                component: () => import('../views/settings/AccountList.vue'),
                meta: { title: '帳號管理', icon: 'i-hugeicons:account-setting-02', pageKey: 'settings.account' }
            },
            {
                path: '/role',
                name: 'RoleSettings',
                component: () => import('../views/settings/RoleList.vue'),
                meta: { title: '角色權限', icon: 'i-hugeicons:shield-user', pageKey: 'settings.role' }
            }
        ]
    }
];

// Teacher routes bypass filtering
export const teacherRoutes: RouteRecordRaw[] = [
    {
        path: '/teacher-portal/dashboard',
        name: 'TeacherDashboard',
        component: () => import('../views/Dashboard.vue'),
        meta: { title: '儀表板', icon: 'i-hugeicons:home-12' }
    },
    {
        path: '/teacher-portal/profile',
        name: 'TeacherProfile',
        component: () => import('../views/teacher-portal/TeacherProfile.vue'),
        meta: { title: '個人設定', icon: 'i-hugeicons:user-settings-01', pageKey: 'teachers.details' }
    },
    {
        path: '/teacher-portal/schedule',
        name: 'TeacherSchedule',
        component: () => import('../views/teacher-portal/ScheduleSettings.vue'),
        meta: { title: '班表設定', icon: 'i-hugeicons:calendar-setting-01', pageKey: 'teachers.slots' }
    },
    {
        path: '/teacher-portal/history',
        name: 'TeacherHistory',
        component: () => import('../views/teacher-portal/BookingHistory.vue'),
        meta: { title: '預約紀錄', icon: 'i-hugeicons:calendar-02', pageKey: 'bookings.list' }
    }
];

// Student routes bypass filtering
export const studentRoutes: RouteRecordRaw[] = [
    {
        path: '/student-portal/dashboard',
        name: 'StudentDashboard',
        component: () => import('../views/Dashboard.vue'),
        meta: { title: '儀表板', icon: 'i-hugeicons:home-12' }
    },
    {
        path: '/student-portal/profile',
        name: 'StudentProfile',
        component: () => import('../views/student-portal/StudentProfile.vue'),
        meta: { title: '個人設定', icon: 'i-hugeicons:user-settings-01', pageKey: 'student_portal' }
    },
    {
        path: '/student-portal/booking',
        name: 'StudentBooking',
        component: () => import('../views/student-portal/ClassBooking.vue'),
        meta: { title: '我的預約', icon: 'i-hugeicons:calendar-02', pageKey: 'student_portal' }
    }
];

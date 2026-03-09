import type { RouteRecordRaw } from 'vue-router';

// Constant routes that don't need permissions
export const constantRoutes: RouteRecordRaw[] = [
    {
        path: '/dashboard',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue'),
        meta: { title: '儀表板', icon: 'House' }
    },
    {
        path: '/profile',
        name: 'Profile',
        component: () => import('../views/Profile.vue'),
        meta: { title: '個人設定', icon: 'User' }
    }
];

// Admin routes that need permission filtering if employee
export const adminRoutes: RouteRecordRaw[] = [
    {
        path: '/reports',
        name: 'Reports',
        component: () => import('../views/reports/ReportStats.vue'),
        meta: { title: '報表分析', pageKey: 'reports.view' }
    },
    {
        path: '/teacher',
        name: 'Teachers',
        component: () => import('../views/teacher/TeacherList.vue'),
        meta: { title: '講師管理', pageKey: 'teachers.list' }
    },
    {
        path: '/student',
        name: 'Students',
        component: () => import('../views/student/StudentList.vue'),
        meta: { title: '學員管理', pageKey: 'students.list' }
    },
    {
        path: '/booking',
        name: 'Bookings',
        component: () => import('../views/booking/BookingList.vue'),
        meta: { title: '預約記錄', pageKey: 'bookings.list' }
    },
    {
        path: '/course',
        name: 'Courses',
        component: () => import('../views/course/CourseList.vue'),
        meta: { title: '課程管理', pageKey: 'courses.list' }
    },
    {
        path: '/salary',
        name: 'Salary',
        component: () => import('../views/salary/SalaryReport.vue'),
        meta: { title: '薪資計算', pageKey: 'salary.view' }
    },
    {
        path: '/settings',
        name: 'Settings',
        meta: { title: '系統設定' }, // A parent wrapper
        children: [
            {
                path: '/account',
                name: 'AccountSettings',
                component: () => import('../views/settings/AccountList.vue'),
                meta: { title: '帳號管理', pageKey: 'settings.account' }
            },
            {
                path: '/role',
                name: 'RoleSettings',
                component: () => import('../views/settings/RoleList.vue'),
                meta: { title: '角色權限', pageKey: 'settings.role' }
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
        meta: { title: '儀表板', icon: 'House' }
    },
    {
        path: '/teacher-portal/profile',
        name: 'TeacherProfile',
        component: () => import('../views/teacher-portal/TeacherProfile.vue'),
        meta: { title: '個人設定', icon: 'User', pageKey: 'teachers.details' }
    },
    {
        path: '/teacher-portal/schedule',
        name: 'TeacherSchedule',
        component: () => import('../views/teacher-portal/ScheduleSettings.vue'),
        meta: { title: '班表設定', icon: 'Calendar', pageKey: 'teachers.slots' }
    },
    {
        path: '/teacher-portal/history',
        name: 'TeacherHistory',
        component: () => import('../views/teacher-portal/BookingHistory.vue'),
        meta: { title: '預約紀錄', icon: 'List', pageKey: 'bookings.list' }
    }
];

// Student routes bypass filtering
export const studentRoutes: RouteRecordRaw[] = [
    {
        path: '/student-portal/dashboard',
        name: 'StudentDashboard',
        component: () => import('../views/Dashboard.vue'),
        meta: { title: '儀表板', icon: 'House' }
    },
    {
        path: '/student-portal/profile',
        name: 'StudentProfile',
        component: () => import('../views/student-portal/StudentProfile.vue'),
        meta: { title: '個人設定', icon: 'User', pageKey: 'student_portal' }
    },
    {
        path: '/student-portal/booking',
        name: 'StudentBooking',
        component: () => import('../views/student-portal/ClassBooking.vue'),
        meta: { title: '我的預約', icon: 'Calendar', pageKey: 'student_portal' }
    }
];

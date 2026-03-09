import { defineStore } from 'pinia';
import { ref } from 'vue';
import type { RouteRecordRaw } from 'vue-router';
import { SYSTEM_MODULES } from './mockStore';
import { getMyPermissions } from '../api/permission';
import { adminRoutes, teacherRoutes, studentRoutes, constantRoutes } from '../router/routes';

export const usePermissionStore = defineStore('permission', () => {
    const routes = ref<RouteRecordRaw[]>([]);
    const addRoutes = ref<RouteRecordRaw[]>([]);
    const isRoutesGenerated = ref<boolean>(false);

    // Define pageKeys
    const pageKeys = ref<string[]>([]);

    const hasPermission = (permissionKey: string, userRole?: string) => {
        if (userRole === 'admin' || userRole === 'super_admin') return true;
        return pageKeys.value.includes(permissionKey);
    };

    const filterAsyncRoutes = (routes: RouteRecordRaw[], keys: string[]) => {
        const filtered: RouteRecordRaw[] = [];
        routes.forEach(route => {
            const tmp = { ...route } as any;
            // A route is kept if it has NO pageKey requirement OR the user has the required pageKey
            if (!tmp.meta || !tmp.meta.pageKey || keys.includes(tmp.meta.pageKey)) {
                if (tmp.children) {
                    tmp.children = filterAsyncRoutes(tmp.children, keys);
                }
                filtered.push(tmp);
            }
        });
        return filtered;
    };

    const generateRoutes = async (role: string) => {
        // 1. ALWAYS fetch permissions first
        try {
            const res = await getMyPermissions();
            pageKeys.value = res.page_keys || [];
        } catch (error) {
            console.warn('Failed to fetch permissions, defaulting to empty array', error);
            pageKeys.value = [];
        }

        let accessedRoutes: RouteRecordRaw[] = [];

        // 2. Assign routes based on role
        if (role === 'admin' || role === 'super_admin' || role === 'super admin') {
            accessedRoutes = adminRoutes;
        } else if (role === 'teacher') {
            accessedRoutes = teacherRoutes;
        } else if (role === 'student') {
            accessedRoutes = studentRoutes;
        } else {
            // Employee logic: Needs fine-grained filtering
            accessedRoutes = filterAsyncRoutes(adminRoutes, pageKeys.value);
        }

        addRoutes.value = accessedRoutes;
        routes.value = constantRoutes.concat(accessedRoutes);
        isRoutesGenerated.value = true;
        return accessedRoutes;
    };

    const resetState = () => {
        routes.value = [];
        addRoutes.value = [];
        pageKeys.value = [];
        isRoutesGenerated.value = false;
    }

    const generateRoutesUnfiltered = () => {
        // TEMPORARY BYPASS FOR DEVELOPMENT
        addRoutes.value = adminRoutes;
        routes.value = constantRoutes.concat(adminRoutes);
        return adminRoutes;
    };

    return { routes, addRoutes, isRoutesGenerated, generateRoutes, generateRoutesUnfiltered, resetState, menuModules: SYSTEM_MODULES, pageKeys, hasPermission };
});

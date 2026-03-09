import type { Directive, DirectiveBinding } from 'vue';
import { usePermissionStore } from '@/stores/permission';
import { useAuthStore } from '@/stores/auth';

export const permission: Directive = {
    mounted(el: HTMLElement, binding: DirectiveBinding) {
        const { value } = binding;
        const permissionStore = usePermissionStore();
        const authStore = useAuthStore();

        if (value && typeof value === 'string') {
            const role = authStore.userInfo?.role;
            const hasPermission = permissionStore.hasPermission(value, role);
            if (!hasPermission) {
                // Remove the element from the DOM if no permission
                el.parentNode && el.parentNode.removeChild(el);
            }
        } else {
            throw new Error(`Need permission key! Like v-permission="'teachers.edit'"`);
        }
    }
};

import request from '@/utils/request';

export interface PageResponse {
    id: string;
    key: string;
    name: string;
    description?: string | null;
    parent_key?: string | null;
    sort_order: number;
    is_active: boolean;
    created_at?: string | null;
    updated_at?: string | null;
}

export interface MyPermissionsResponse {
    success: boolean;
    role: string;
    page_keys: string[];
    pages: PageResponse[];
}

export function getMyPermissions() {
    return request.get<any, MyPermissionsResponse>('/v1/permissions/me');
}

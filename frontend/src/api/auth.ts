import request from '@/utils/request';

// Interfaces based on Swagger
export interface LoginRequest {
    email: string;
    password: string;
}

export interface TokenPair {
    access_token: string;
    refresh_token: string;
    expires_in: number;
}

export interface UserInfo {
    id: string;
    email: string;
    role: string; // 'student' | 'teacher' | 'employee'
    name?: string | null;
    // ... other fields can be added as needed
}

export interface LoginResponse {
    success: boolean;
    message: string;
    user: UserInfo;
    tokens: TokenPair;
}

export function loginApi(data: LoginRequest) {
    return request.post<any, LoginResponse>('/v1/auth/login', data);
}

export function logoutApi(logout_all_devices: boolean = false) {
    return request.post('/v1/auth/logout', { logout_all_devices });
}

export function getMeApi() {
    return request.get<any, { success: boolean; data: UserInfo }>('/v1/auth/me');
}

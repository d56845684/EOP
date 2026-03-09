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

export interface LogoutRequest {
    logout_all_devices?: boolean;
}

export function logout(data: LogoutRequest = { logout_all_devices: false }) {
    return request.post('/v1/auth/logout', data);
}

export function refreshToken() {
    // The Swagger doesn't specify a body, assuming token is sent via HTTP-only cookie or Authorization header
    return request.post('/v1/auth/refresh');
}

export function getMeApi() {
    return request.get<any, { success: boolean; data: UserInfo }>('/v1/auth/me');
}

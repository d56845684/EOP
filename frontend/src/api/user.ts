import request from '@/utils/request';

export interface UserProfile {
  id: string;
  email: string;
  role: string;
  name: string | null;
  avatar_url: string | null;
  is_active: boolean;
  created_at: string | null;
}

export interface DataResponse_UserProfile_ {
  data: UserProfile;
  message?: string;
  success?: boolean;
}

export function getUserProfileApi() {
  return request.get<any, DataResponse_UserProfile_>('/v1/users/profile');
}

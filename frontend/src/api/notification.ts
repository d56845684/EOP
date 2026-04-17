import request from '@/utils/request';
import type { DataResponse } from './response';

export interface NotificationPreferences {
  email_enabled: boolean;
  booking_confirmed: boolean;
  booking_cancelled: boolean;
  contract_activated: boolean;
  contract_converted: boolean;
  contract_terminated: boolean;
}

export type NotificationPreferenceKey = keyof NotificationPreferences;

export const getNotificationPreferencesApi = () => {
  return request.get<any, DataResponse<NotificationPreferences>>('/v1/notifications/preferences');
};

export const updateNotificationPreferencesApi = (data: NotificationPreferences) => {
  return request.put<any, DataResponse<NotificationPreferences>>('/v1/notifications/preferences', data);
};

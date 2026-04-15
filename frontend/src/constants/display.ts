import type { EmployeeType } from '@/api/employee';
import { CONTRACT_STATUS } from './contract';
import { STUDENT_STATUS } from './student';

export type DisplayTagType = '' | 'success' | 'warning' | 'danger' | 'info' | 'primary';

export const EMPLOYEE_TYPE_TAG_MAP: Partial<Record<EmployeeType, DisplayTagType>> = {
  admin: 'primary',
  full_time: 'success',
  part_time: 'warning',
  intern: 'info',
};

export const STUDENT_STATUS_TAG_MAP: Record<string, DisplayTagType> = {
  [STUDENT_STATUS.ACTIVE]: 'success',
  [STUDENT_STATUS.TERMINATED]: 'info',
  [STUDENT_STATUS.TRIAL]: 'warning',
};

export const STUDENT_CONTRACT_STATUS_TAG_MAP: Record<string, DisplayTagType> = {
  [CONTRACT_STATUS.PENDING]: 'warning',
  [CONTRACT_STATUS.ACTIVE]: 'success',
  [CONTRACT_STATUS.EXPIRED]: 'info',
  [CONTRACT_STATUS.TERMINATED]: 'danger',
  [CONTRACT_STATUS.SUSPENDED]: 'warning',
};

export const TEACHER_CONTRACT_STATUS_TAG_MAP: Record<string, DisplayTagType> = {
  [CONTRACT_STATUS.PENDING]: 'warning',
  [CONTRACT_STATUS.ACTIVE]: 'success',
  [CONTRACT_STATUS.EXPIRED]: 'info',
  [CONTRACT_STATUS.TERMINATED]: 'danger',
};

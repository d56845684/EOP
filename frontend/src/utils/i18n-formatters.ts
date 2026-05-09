import i18n from '@/i18n';
import type { EmployeeType } from '@/api/employee';
import { CONTRACT_STATUS, STUDENT_CONTRACT_STATUS_VALUES, TEACHER_CONTRACT_STATUS_VALUES } from '@/constants/contract';
import { STUDENT_STATUS } from '@/constants/student';

export type AppRole = 'admin' | 'employee' | 'teacher' | 'student';
type TranslateFn = (key: string, named?: Record<string, unknown>) => string;

const ROLE_LABEL_KEY_MAP: Record<AppRole, string> = {
  admin: 'roleLabel.admin',
  employee: 'roleLabel.employee',
  teacher: 'roleLabel.teacher',
  student: 'roleLabel.student',
};

const defaultT: TranslateFn = (key, named) => (
  named ? i18n.global.t(key, named) : i18n.global.t(key)
) as string;

const translateByMap = (
  value: string | null | undefined,
  keyMap: Record<string, string>,
  fallback = '-',
  t: TranslateFn = defaultT,
) => {
  if (!value) return fallback;

  const normalizedValue = value.toLowerCase();
  const key = keyMap[value] || keyMap[normalizedValue];
  if (!key) return value;

  return t(key);
};

const EMPLOYEE_TYPE_LABEL_KEY_MAP: Record<EmployeeType, string> = {
  admin: 'employee.type.admin',
  full_time: 'employee.type.full_time',
  part_time: 'employee.type.part_time',
  intern: 'employee.type.intern',
};

const STUDENT_STATUS_LABEL_KEY_MAP: Record<string, string> = {
  [STUDENT_STATUS.PENDING]: 'display.studentStatus.pending',
  [STUDENT_STATUS.ACTIVE]: 'display.studentStatus.active',
  [STUDENT_STATUS.TERMINATED]: 'display.studentStatus.terminated',
  [STUDENT_STATUS.TRIAL]: 'display.studentStatus.trial',
};

const CONTRACT_STATUS_LABEL_KEY_MAP: Record<string, string> = {
  [CONTRACT_STATUS.PENDING]: 'display.contractStatus.pending',
  [CONTRACT_STATUS.ACTIVE]: 'display.contractStatus.active',
  [CONTRACT_STATUS.EXPIRED]: 'display.contractStatus.expired',
  [CONTRACT_STATUS.TERMINATED]: 'display.contractStatus.terminated',
  [CONTRACT_STATUS.SUSPENDED]: 'display.contractStatus.suspended',
};

export const formatRoleLabel = (role?: string | null, fallback = '-', t: TranslateFn = defaultT) => {
  return translateByMap(role, ROLE_LABEL_KEY_MAP, fallback, t);
};

export const formatEmployeeTypeLabel = (
  employeeType?: EmployeeType | null,
  fallback = '-',
  t: TranslateFn = defaultT,
) => {
  return translateByMap(employeeType, EMPLOYEE_TYPE_LABEL_KEY_MAP, fallback, t);
};

export const formatStudentStatusLabel = (status?: string | null, fallback = '-', t: TranslateFn = defaultT) => {
  return translateByMap(status, STUDENT_STATUS_LABEL_KEY_MAP, fallback, t);
};

export const formatStudentContractStatusLabel = (
  status?: string | null,
  fallback = '-',
  t: TranslateFn = defaultT,
) => {
  return translateByMap(status, CONTRACT_STATUS_LABEL_KEY_MAP, fallback, t);
};

export const formatTeacherContractStatusLabel = (
  status?: string | null,
  fallback = '-',
  t: TranslateFn = defaultT,
) => {
  return translateByMap(status, CONTRACT_STATUS_LABEL_KEY_MAP, fallback, t);
};

export const getStudentContractStatusOptions = (t: TranslateFn = defaultT) => {
  return STUDENT_CONTRACT_STATUS_VALUES.map((value) => ({
    value,
    label: formatStudentContractStatusLabel(value, value, t),
  }));
};

export const getTeacherContractStatusOptions = (t: TranslateFn = defaultT) => {
  return TEACHER_CONTRACT_STATUS_VALUES.map((value) => ({
    value,
    label: formatTeacherContractStatusLabel(value, value, t),
  }));
};

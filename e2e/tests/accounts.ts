export type Role = 'admin' | 'employee' | 'teacher' | 'student';

export interface Account {
  role: Role;
  email: string;
  password: string;
  storageStateFile: string;
}

const adminPassword =
  process.env.E2E_ADMIN_PASSWORD || process.env.SUPER_ADMIN_PASSWORD || 'eopsuper888';
const defaultPassword = process.env.E2E_DEFAULT_PASSWORD || 'TestPassword123!';

export const ACCOUNTS: Record<Role, Account> = {
  admin: {
    role: 'admin',
    email: process.env.E2E_ADMIN_EMAIL || 'eopAdmin@example.com',
    password: adminPassword,
    storageStateFile: '.auth/admin.json',
  },
  employee: {
    role: 'employee',
    email: process.env.E2E_EMPLOYEE_EMAIL || 'employee@eop-test.com',
    password: defaultPassword,
    storageStateFile: '.auth/employee.json',
  },
  teacher: {
    role: 'teacher',
    email: process.env.E2E_TEACHER_EMAIL || 'teacher@eop-test.com',
    password: defaultPassword,
    storageStateFile: '.auth/teacher.json',
  },
  student: {
    role: 'student',
    email: process.env.E2E_STUDENT_EMAIL || 'student@eop-test.com',
    password: defaultPassword,
    storageStateFile: '.auth/student.json',
  },
};

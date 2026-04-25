import { test as base, APIRequestContext } from '@playwright/test';
import { getApiContext } from '../helpers/api';

/**
 * World fixture — worker-scoped
 *
 * 提供整個測試 run 共用的「測試世界」：
 *   - admin/employee API context（已登入、可以打 backend）
 *   - 從 /auth/me 動態解析的固定測試帳號 entity id（不要 hardcode UUID，DB 會被重建）
 *   - 後續組別會擴充 course/contract/slot 等 seed 欄位
 */

export interface World {
  adminApi: APIRequestContext;
  employeeApi: APIRequestContext;

  fixedEmployeeId: string;
  fixedTeacherId: string;
  fixedStudentId: string;
  fixedEmployeeUserId: string;
  fixedTeacherUserId: string;
  fixedStudentUserId: string;
}

async function fetchEntityIds(api: APIRequestContext, role: 'admin' | 'employee' | 'teacher' | 'student') {
  const res = await api.get('/api/v1/auth/me');
  if (!res.ok()) {
    throw new Error(`[world] /auth/me failed for ${role}: ${res.status()} ${await res.text()}`);
  }
  const body = await res.json();
  return body.data;
}

export const test = base.extend<{}, { world: World }>({
  world: [
    async ({}, use) => {
      const adminApi = await getApiContext('admin');
      const employeeApi = await getApiContext('employee');
      const teacherApi = await getApiContext('teacher');
      const studentApi = await getApiContext('student');

      const employeeMe = await fetchEntityIds(employeeApi, 'employee');
      const teacherMe = await fetchEntityIds(teacherApi, 'teacher');
      const studentMe = await fetchEntityIds(studentApi, 'student');

      const world: World = {
        adminApi,
        employeeApi,
        fixedEmployeeId: employeeMe.employee_id,
        fixedTeacherId: teacherMe.teacher_id,
        fixedStudentId: studentMe.student_id,
        fixedEmployeeUserId: employeeMe.id,
        fixedTeacherUserId: teacherMe.id,
        fixedStudentUserId: studentMe.id,
      };

      await teacherApi.dispose();
      await studentApi.dispose();

      await use(world);

      await adminApi.dispose();
      await employeeApi.dispose();
    },
    { scope: 'worker' },
  ],
});

export { expect } from '@playwright/test';

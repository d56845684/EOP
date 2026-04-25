import { test, expect } from '../_fixtures/world';
import {
  createStudent,
  createTeacher,
  deleteStudent,
  deleteTeacher,
  safeCleanup,
  SeededStudent,
  SeededTeacher,
} from '../helpers/seed';

test.describe('學生教師偏好 /student-teacher-preferences', () => {
  let student: SeededStudent;
  let teacher: SeededTeacher;
  let preferenceIds: string[] = [];

  test.beforeAll(async ({ world }) => {
    student = await createStudent(world.adminApi);
    teacher = await createTeacher(world.adminApi);
  });

  test.afterAll(async ({ world }) => {
    for (const id of preferenceIds) {
      await safeCleanup(async () => {
        await world.adminApi.delete(`/api/v1/student-teacher-preferences/${id}`);
      });
    }
    if (student) await safeCleanup(() => deleteStudent(world.adminApi, student.id));
    if (teacher) await safeCleanup(() => deleteTeacher(world.adminApi, teacher.id));
  });

  test('POST 建立教師偏好（指定教師）', async ({ world }) => {
    const res = await world.adminApi.post('/api/v1/student-teacher-preferences', {
      data: {
        student_id: student.id,
        primary_teacher_ids: [teacher.id],
      },
    });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    // 回應可能是單筆或批次，兩種都接受
    if (Array.isArray(body.data)) {
      for (const p of body.data) preferenceIds.push(p.id);
    } else if (body.data?.id) {
      preferenceIds.push(body.data.id);
    }
  });

  test('POST 建立教師偏好（等級限制）', async ({ world }) => {
    const res = await world.adminApi.post('/api/v1/student-teacher-preferences', {
      data: {
        student_id: student.id,
        min_teacher_level: 2,
      },
    });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    if (Array.isArray(body.data)) for (const p of body.data) preferenceIds.push(p.id);
    else if (body.data?.id) preferenceIds.push(body.data.id);
  });

  test('GET /student-teacher-preferences 可以列表', async ({ world }) => {
    const res = await world.adminApi.get(
      `/api/v1/student-teacher-preferences?student_id=${student.id}`
    );
    expect(res.ok()).toBeTruthy();
  });

  test('GET /allowed-teachers 取得學生白名單', async ({ world }) => {
    const res = await world.adminApi.get(
      `/api/v1/student-teacher-preferences/allowed-teachers?student_id=${student.id}`
    );
    expect(res.ok()).toBeTruthy();
    expect(Array.isArray((await res.json()).data)).toBeTruthy();
  });
});

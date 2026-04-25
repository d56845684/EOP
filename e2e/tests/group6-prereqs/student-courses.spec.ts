import { test, expect } from '../_fixtures/world';
import {
  createCourse,
  createStudent,
  deleteCourse,
  deleteStudent,
  enrollStudentInCourse,
  unenrollStudentCourse,
  safeCleanup,
  SeededCourse,
  SeededStudent,
} from '../helpers/seed';

test.describe('學生選課 /student-courses', () => {
  let student: SeededStudent;
  let course: SeededCourse;
  let enrollmentIds: string[] = [];

  test.beforeAll(async ({ world }) => {
    student = await createStudent(world.adminApi);
    course = await createCourse(world.adminApi);
  });

  test.afterAll(async ({ world }) => {
    for (const id of enrollmentIds) await safeCleanup(() => unenrollStudentCourse(world.adminApi, id));
    if (course) await safeCleanup(() => deleteCourse(world.adminApi, course.id));
    if (student) await safeCleanup(() => deleteStudent(world.adminApi, student.id));
  });

  test('POST /student-courses 學生選課', async ({ world }) => {
    const e = await enrollStudentInCourse(world.adminApi, {
      student_id: student.id,
      course_id: course.id,
    });
    enrollmentIds.push(e.id);

    const res = await world.adminApi.get(`/api/v1/student-courses/by-student/${student.id}`);
    expect(res.ok()).toBeTruthy();
    const courses = (await res.json()).data;
    const found = courses.find((c: any) => c.course_id === course.id);
    expect(found).toBeDefined();
  });

  test('重複選同一課應失敗', async ({ world }) => {
    // 第一次先確保已選
    if (enrollmentIds.length === 0) {
      const e = await enrollStudentInCourse(world.adminApi, {
        student_id: student.id,
        course_id: course.id,
      });
      enrollmentIds.push(e.id);
    }
    const res = await world.adminApi.post('/api/v1/student-courses', {
      data: { student_id: student.id, course_id: course.id },
    });
    expect(res.status()).toBeGreaterThanOrEqual(400);
  });

  test('DELETE /student-courses/{id} 取消選課', async ({ world }) => {
    const e = await enrollStudentInCourse(world.adminApi, {
      student_id: student.id,
      course_id: course.id,
    }).catch(async () => {
      // 已選了，直接拿現有的
      const list = await world.adminApi.get(`/api/v1/student-courses/by-student/${student.id}`);
      return { id: (await list.json()).data[0].id };
    });

    const res = await world.adminApi.delete(`/api/v1/student-courses/${e.id}`);
    expect(res.ok()).toBeTruthy();
    enrollmentIds = enrollmentIds.filter((id) => id !== e.id);
  });
});

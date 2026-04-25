import { test, expect } from '../_fixtures/world';
import { gotoReady } from '../helpers/nav';
import {
  createCourse,
  createStudent,
  createStudentContract,
  createTeacher,
  createTeacherContract,
  createTeacherSlot,
  enrollStudentInCourse,
  safeCleanup,
  deleteCourse,
  deleteStudent,
  deleteStudentContract,
  deleteTeacher,
  deleteTeacherContract,
  deleteTeacherSlot,
  unenrollStudentCourse,
} from '../helpers/seed';

test.describe('請假管理 /leave-management', () => {
  let setup: any;

  test.beforeAll(async ({ world }) => {
    const student = await createStudent(world.adminApi, { student_type: 'formal' });
    const teacher = await createTeacher(world.adminApi);
    const course = await createCourse(world.adminApi);
    const teacherContract = await createTeacherContract(world.adminApi, { teacher_id: teacher.id });
    await world.adminApi.post(`/api/v1/teacher-contracts/${teacherContract.id}/details`, {
      data: { detail_type: 'course_rate', course_id: course.id, amount: 500 },
    });
    const studentContract = await createStudentContract(world.adminApi, { student_id: student.id });
    const enrollment = await enrollStudentInCourse(world.adminApi, {
      student_id: student.id,
      course_id: course.id,
    });
    await world.adminApi.post('/api/v1/student-teacher-preferences', {
      data: { student_id: student.id, primary_teacher_ids: [teacher.id] },
    });

    const tomorrow = new Date(Date.now() + 2 * 24 * 3600 * 1000).toISOString().slice(0, 10);
    const slot = await createTeacherSlot(world.adminApi, {
      teacher_id: teacher.id,
      teacher_contract_id: teacherContract.id,
      slot_date: tomorrow,
      start_time: '10:00:00',
      end_time: '12:00:00',
    });

    // 建立並確認 booking
    const bookingRes = await world.adminApi.post('/api/v1/bookings', {
      data: {
        student_id: student.id,
        teacher_id: teacher.id,
        course_id: course.id,
        student_contract_id: studentContract.id,
        teacher_contract_id: teacherContract.id,
        booking_date: tomorrow,
        start_time: '10:00:00',
        end_time: '11:00:00',
      },
    });
    if (!bookingRes.ok()) throw new Error(`seed booking failed: ${await bookingRes.text()}`);
    const booking = (await bookingRes.json()).data;
    await world.adminApi.put(`/api/v1/bookings/${booking.id}`, {
      data: { booking_status: 'confirmed' },
    });

    setup = { student, teacher, course, teacherContract, studentContract, enrollment, slot, booking, leaves: [] };
  });

  test.afterAll(async ({ world }) => {
    if (!setup) return;
    // 不清 leave 紀錄、booking、slot 也讓 safeCleanup 包住即可
    await safeCleanup(async () => {
      await world.adminApi.delete(`/api/v1/bookings/${setup.booking.id}`);
    });
    await safeCleanup(() => deleteTeacherSlot(world.adminApi, setup.slot.id));
    await safeCleanup(() => unenrollStudentCourse(world.adminApi, setup.enrollment.id));
    await safeCleanup(() => deleteStudentContract(world.adminApi, setup.studentContract.id));
    await safeCleanup(() => deleteTeacherContract(world.adminApi, setup.teacherContract.id));
    await safeCleanup(() => deleteCourse(world.adminApi, setup.course.id));
    await safeCleanup(() => deleteTeacher(world.adminApi, setup.teacher.id));
    await safeCleanup(() => deleteStudent(world.adminApi, setup.student.id));
  });

  test('頁面載入', async ({ page }) => {
    await gotoReady(page, '/leave-management');
    await expect(page.getByText('請假管理').first()).toBeVisible({ timeout: 10_000 });
  });

  test('GET /leave-records 列表', async ({ world }) => {
    const res = await world.adminApi.get('/api/v1/leave-records?page=1&per_page=10');
    expect(res.ok()).toBeTruthy();
  });

  test('POST 建立請假 (admin 代申請)', async ({ world }) => {
    const res = await world.adminApi.post('/api/v1/leave-records', {
      data: { booking_id: setup.booking.id, reason: 'e2e 測試請假' },
    });
    if (!res.ok()) {
      console.log('leave POST failed:', res.status(), await res.text());
    }
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.data.leave_status).toBe('pending');
    expect(body.data.leave_no).toMatch(/^LV/);
    setup.leaves.push(body.data);
  });

  test('POST /leave-records/{id}/approve 核准請假', async ({ world }) => {
    if (setup.leaves.length === 0) test.skip();
    const leaveId = setup.leaves[0].id;
    const res = await world.adminApi.post(`/api/v1/leave-records/${leaveId}/approve`, {
      data: {},
    });
    if (!res.ok()) {
      console.log('approve failed:', res.status(), await res.text());
    }
    expect(res.ok()).toBeTruthy();
    expect((await res.json()).data.leave_status).toBe('approved');
  });
});

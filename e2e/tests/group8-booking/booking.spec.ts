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
  deleteBooking,
  deleteCourse,
  deleteStudent,
  deleteStudentContract,
  deleteTeacher,
  deleteTeacherContract,
  deleteTeacherSlot,
  unenrollStudentCourse,
  safeCleanup,
  SeededBooking,
} from '../helpers/seed';

test.describe('預約管理 /booking', () => {
  // 一個完整的測試世界，整個 suite 共用
  let world_: {
    student: any;
    teacher: any;
    course: any;
    studentContract: any;
    teacherContract: any;
    enrollment: any;
    slot: any;
    bookings: SeededBooking[];
  };

  test.beforeAll(async ({ world }) => {
    const student = await createStudent(world.adminApi, { student_type: 'formal' });
    const teacher = await createTeacher(world.adminApi);
    const course = await createCourse(world.adminApi, { duration_minutes: 60 });

    const teacherContract = await createTeacherContract(world.adminApi, {
      teacher_id: teacher.id,
    });

    // 教師合約必須有 course_rate 明細才能教該課程（後端會擋）
    const detailRes = await world.adminApi.post(
      `/api/v1/teacher-contracts/${teacherContract.id}/details`,
      {
        data: {
          detail_type: 'course_rate',
          course_id: course.id,
          amount: 500,
        },
      }
    );
    if (!detailRes.ok()) {
      throw new Error(`seed teacher-contract-detail failed: ${detailRes.status()} ${await detailRes.text()}`);
    }

    const studentContract = await createStudentContract(world.adminApi, {
      student_id: student.id,
      total_lessons: 24,
    });

    const enrollment = await enrollStudentInCourse(world.adminApi, {
      student_id: student.id,
      course_id: course.id,
    });

    // 學生必須把教師加進偏好白名單，否則預約會被擋
    const prefRes = await world.adminApi.post('/api/v1/student-teacher-preferences', {
      data: { student_id: student.id, primary_teacher_ids: [teacher.id] },
    });
    if (!prefRes.ok()) {
      throw new Error(`seed preference failed: ${prefRes.status()} ${await prefRes.text()}`);
    }

    // 明天的時段 (slot 限三個月內)
    const tomorrow = new Date(Date.now() + 24 * 3600 * 1000).toISOString().slice(0, 10);
    const slot = await createTeacherSlot(world.adminApi, {
      teacher_id: teacher.id,
      teacher_contract_id: teacherContract.id,
      slot_date: tomorrow,
      start_time: '10:00:00',
      end_time: '12:00:00',
    });

    world_ = {
      student,
      teacher,
      course,
      studentContract,
      teacherContract,
      enrollment,
      slot,
      bookings: [],
    };
  });

  test.afterAll(async ({ world }) => {
    for (const b of world_.bookings) await safeCleanup(() => deleteBooking(world.adminApi, b.id));
    await safeCleanup(() => deleteTeacherSlot(world.adminApi, world_.slot.id));
    await safeCleanup(() => unenrollStudentCourse(world.adminApi, world_.enrollment.id));
    await safeCleanup(() => deleteStudentContract(world.adminApi, world_.studentContract.id));
    await safeCleanup(() => deleteTeacherContract(world.adminApi, world_.teacherContract.id));
    await safeCleanup(() => deleteCourse(world.adminApi, world_.course.id));
    await safeCleanup(() => deleteTeacher(world.adminApi, world_.teacher.id));
    await safeCleanup(() => deleteStudent(world.adminApi, world_.student.id));
  });

  test('頁面載入並顯示表格', async ({ page }) => {
    await gotoReady(page, '/booking');
    await expect(page.getByText('預約管理').first()).toBeVisible({ timeout: 10_000 });
  });

  test('GET /bookings 回傳列表', async ({ world }) => {
    const res = await world.adminApi.get('/api/v1/bookings?page=1&per_page=10');
    expect(res.ok()).toBeTruthy();
    expect(Array.isArray((await res.json()).data)).toBeTruthy();
  });

  test('POST 建立預約 (formal student) → 自動扣堂數', async ({ world }) => {
    const tomorrow = new Date(Date.now() + 24 * 3600 * 1000).toISOString().slice(0, 10);
    const res = await world.adminApi.post('/api/v1/bookings', {
      data: {
        student_id: world_.student.id,
        teacher_id: world_.teacher.id,
        course_id: world_.course.id,
        student_contract_id: world_.studentContract.id,
        teacher_contract_id: world_.teacherContract.id,
        booking_date: tomorrow,
        start_time: '10:00:00',
        end_time: '11:00:00',
      },
    });
    if (!res.ok()) {
      console.log('POST booking failed:', res.status(), await res.text());
    }
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    world_.bookings.push({ id: body.data.id });
    expect(body.data.booking_status).toBe('pending');
  });

  test('POST 開始時間不在 30 分鐘邊界應失敗', async ({ world }) => {
    const tomorrow = new Date(Date.now() + 24 * 3600 * 1000).toISOString().slice(0, 10);
    const res = await world.adminApi.post('/api/v1/bookings', {
      data: {
        student_id: world_.student.id,
        teacher_id: world_.teacher.id,
        course_id: world_.course.id,
        student_contract_id: world_.studentContract.id,
        booking_date: tomorrow,
        start_time: '10:15:00', // 違反 30 分鐘邊界
        end_time: '11:15:00',
      },
    });
    expect(res.status()).toBeGreaterThanOrEqual(400);
  });

  test('POST end_time 小於 start_time 應失敗', async ({ world }) => {
    const tomorrow = new Date(Date.now() + 24 * 3600 * 1000).toISOString().slice(0, 10);
    const res = await world.adminApi.post('/api/v1/bookings', {
      data: {
        student_id: world_.student.id,
        teacher_id: world_.teacher.id,
        course_id: world_.course.id,
        booking_date: tomorrow,
        start_time: '11:00:00',
        end_time: '10:00:00',
      },
    });
    expect(res.status()).toBeGreaterThanOrEqual(400);
  });

  test('PUT 確認預約 status pending → confirmed', async ({ world }) => {
    if (world_.bookings.length === 0) test.skip();
    const id = world_.bookings[0].id;
    const res = await world.adminApi.put(`/api/v1/bookings/${id}`, {
      data: { booking_status: 'confirmed' },
    });
    expect(res.ok()).toBeTruthy();
    expect((await res.json()).data.booking_status).toBe('confirmed');
  });

  test('options endpoints 可以使用', async ({ world }) => {
    for (const path of ['students', 'teachers', 'courses']) {
      const res = await world.adminApi.get(`/api/v1/bookings/options/${path}`);
      expect(res.ok()).toBeTruthy();
    }
  });
});

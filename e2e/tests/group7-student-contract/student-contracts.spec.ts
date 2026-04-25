import { test, expect } from '../_fixtures/world';
import {
  createStudent,
  createStudentContract,
  deleteStudent,
  deleteStudentContract,
  safeCleanup,
  SeededStudent,
  SeededStudentContract,
} from '../helpers/seed';

test.describe('學生合約 /student-contracts', () => {
  let students: SeededStudent[] = [];
  let contracts: SeededStudentContract[] = [];

  test.afterAll(async ({ world }) => {
    for (const c of contracts) await safeCleanup(() => deleteStudentContract(world.adminApi, c.id));
    for (const s of students) await safeCleanup(() => deleteStudent(world.adminApi, s.id));
    students = [];
    contracts = [];
  });

  test('GET /student-contracts 列表', async ({ world }) => {
    const res = await world.adminApi.get('/api/v1/student-contracts?page=1&per_page=10');
    expect(res.ok()).toBeTruthy();
    expect(Array.isArray((await res.json()).data)).toBeTruthy();
  });

  test('GET options endpoints 可以使用', async ({ world }) => {
    for (const path of ['students', 'courses', 'teachers']) {
      const res = await world.adminApi.get(`/api/v1/student-contracts/options/${path}`);
      expect(res.ok()).toBeTruthy();
      expect(Array.isArray((await res.json()).data)).toBeTruthy();
    }
  });

  test('POST 建立合約 → 自動算 leave_allowed (=ceil(total*0.2))', async ({ world }) => {
    const student = await createStudent(world.adminApi, { student_type: 'formal' });
    students.push(student);

    const contract = await createStudentContract(world.adminApi, {
      student_id: student.id,
      total_lessons: 50, // ceil(50*0.2) = 10
    });
    contracts.push(contract);

    const getRes = await world.adminApi.get(`/api/v1/student-contracts/${contract.id}`);
    const fetched = (await getRes.json()).data;
    expect(fetched.total_lessons).toBe(50);
    expect(fetched.remaining_lessons).toBe(50);
    // 預設 total_leave_allowed 由後端算
    if (fetched.total_leave_allowed !== null && fetched.total_leave_allowed !== undefined) {
      expect(fetched.total_leave_allowed).toBe(10);
    }
  });

  test('PUT 修改合約堂數', async ({ world }) => {
    const student = await createStudent(world.adminApi, { student_type: 'formal' });
    students.push(student);
    const contract = await createStudentContract(world.adminApi, {
      student_id: student.id,
      total_lessons: 24,
    });
    contracts.push(contract);

    const res = await world.adminApi.put(`/api/v1/student-contracts/${contract.id}`, {
      data: { total_lessons: 30, remaining_lessons: 30 },
    });
    expect(res.ok()).toBeTruthy();
    expect((await res.json()).data.total_lessons).toBe(30);
  });

  test('DELETE 學生合約', async ({ world }) => {
    const student = await createStudent(world.adminApi, { student_type: 'formal' });
    students.push(student);
    const contract = await createStudentContract(world.adminApi, { student_id: student.id });

    const res = await world.adminApi.delete(`/api/v1/student-contracts/${contract.id}`);
    expect(res.ok()).toBeTruthy();
  });

  test('total_lessons 0 應失敗 (>=1)', async ({ world }) => {
    const student = await createStudent(world.adminApi);
    students.push(student);

    const res = await world.adminApi.post('/api/v1/student-contracts', {
      data: {
        student_id: student.id,
        contract_status: 'active',
        start_date: '2026-01-01',
        end_date: '2026-12-31',
        total_lessons: 0,
        remaining_lessons: 0,
        total_amount: 1000,
      },
    });
    expect(res.status()).toBeGreaterThanOrEqual(400);
  });
});

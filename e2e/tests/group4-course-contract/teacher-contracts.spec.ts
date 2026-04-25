import { test, expect } from '../_fixtures/world';
import {
  createTeacher,
  createTeacherContract,
  deleteTeacher,
  deleteTeacherContract,
  safeCleanup,
  SeededTeacher,
  SeededTeacherContract,
} from '../helpers/seed';

test.describe('教師合約 /teacher-contracts', () => {
  let teachers: SeededTeacher[] = [];
  let contracts: SeededTeacherContract[] = [];

  test.afterAll(async ({ world }) => {
    for (const c of contracts) await safeCleanup(() => deleteTeacherContract(world.adminApi, c.id));
    for (const t of teachers) await safeCleanup(() => deleteTeacher(world.adminApi, t.id));
    teachers = [];
    contracts = [];
  });

  test('GET /teacher-contracts 回傳列表', async ({ world }) => {
    const res = await world.adminApi.get('/api/v1/teacher-contracts?page=1&per_page=10');
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(Array.isArray(body.data)).toBeTruthy();
  });

  test('GET /teacher-contracts/options/teachers 列出可指派教師', async ({ world }) => {
    const res = await world.adminApi.get('/api/v1/teacher-contracts/options/teachers');
    expect(res.ok()).toBeTruthy();
    expect(Array.isArray((await res.json()).data)).toBeTruthy();
  });

  test('GET /teacher-contracts/options/courses 列出可選課程', async ({ world }) => {
    const res = await world.adminApi.get('/api/v1/teacher-contracts/options/courses');
    expect(res.ok()).toBeTruthy();
    expect(Array.isArray((await res.json()).data)).toBeTruthy();
  });

  test('POST → GET → PUT → DELETE 教師合約', async ({ world }) => {
    const teacher = await createTeacher(world.adminApi);
    teachers.push(teacher);

    const contract = await createTeacherContract(world.adminApi, { teacher_id: teacher.id });
    contracts.push(contract);

    const getRes = await world.adminApi.get(`/api/v1/teacher-contracts/${contract.id}`);
    expect(getRes.ok()).toBeTruthy();
    const fetched = (await getRes.json()).data;
    expect(fetched.teacher_id).toBe(teacher.id);
    expect(fetched.contract_no).toMatch(/^TC/);

    const putRes = await world.adminApi.put(`/api/v1/teacher-contracts/${contract.id}`, {
      data: { trial_completed_bonus: 250 },
    });
    expect(putRes.ok()).toBeTruthy();
    expect((await putRes.json()).data.trial_completed_bonus).toBe(250);

    const delRes = await world.adminApi.delete(`/api/v1/teacher-contracts/${contract.id}`);
    expect(delRes.ok()).toBeTruthy();
    contracts = contracts.filter((c) => c.id !== contract.id);
  });

  test('teacher_id 不存在應失敗', async ({ world }) => {
    const res = await world.adminApi.post('/api/v1/teacher-contracts', {
      data: {
        teacher_id: '00000000-0000-0000-0000-000000000000',
        contract_status: 'active',
        start_date: '2026-01-01',
        end_date: '2026-12-31',
        employment_type: 'hourly',
      },
    });
    expect(res.status()).toBeGreaterThanOrEqual(400);
  });
});

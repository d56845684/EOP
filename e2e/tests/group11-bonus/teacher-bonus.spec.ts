import { test, expect } from '../_fixtures/world';
import {
  createTeacher,
  deleteTeacher,
  safeCleanup,
  SeededTeacher,
} from '../helpers/seed';

test.describe('教師獎金 /teacher-bonus', () => {
  let teachers: SeededTeacher[] = [];
  let bonusIds: string[] = [];

  test.afterAll(async ({ world }) => {
    for (const id of bonusIds) {
      await safeCleanup(async () => {
        await world.adminApi.delete(`/api/v1/teacher-bonus/${id}`);
      });
    }
    for (const t of teachers) await safeCleanup(() => deleteTeacher(world.adminApi, t.id));
  });

  test('GET /teacher-bonus 列表', async ({ world }) => {
    const res = await world.adminApi.get('/api/v1/teacher-bonus?page=1&per_page=10');
    expect(res.ok()).toBeTruthy();
  });

  test('GET /teacher-bonus/options/teachers', async ({ world }) => {
    const res = await world.adminApi.get('/api/v1/teacher-bonus/options/teachers');
    expect(res.ok()).toBeTruthy();
    expect(Array.isArray((await res.json()).data)).toBeTruthy();
  });

  test('POST 手動建立 performance 獎金 → PUT → DELETE', async ({ world }) => {
    const t = await createTeacher(world.adminApi);
    teachers.push(t);

    const today = new Date().toISOString().slice(0, 10);
    const res = await world.adminApi.post('/api/v1/teacher-bonus', {
      data: {
        teacher_id: t.id,
        bonus_type: 'performance',
        amount: 1000,
        bonus_date: today,
        description: 'e2e performance bonus',
      },
    });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    bonusIds.push(body.data.id);
    expect(body.data.amount).toBe(1000);

    const putRes = await world.adminApi.put(`/api/v1/teacher-bonus/${body.data.id}`, {
      data: { amount: 1500 },
    });
    expect(putRes.ok()).toBeTruthy();
    expect((await putRes.json()).data.amount).toBe(1500);

    const delRes = await world.adminApi.delete(`/api/v1/teacher-bonus/${body.data.id}`);
    expect(delRes.ok()).toBeTruthy();
    bonusIds = bonusIds.filter((x) => x !== body.data.id);
  });

  test('amount 負數應失敗', async ({ world }) => {
    const t = await createTeacher(world.adminApi);
    teachers.push(t);
    const res = await world.adminApi.post('/api/v1/teacher-bonus', {
      data: {
        teacher_id: t.id,
        bonus_type: 'performance',
        amount: -100,
      },
    });
    expect(res.status()).toBeGreaterThanOrEqual(400);
  });
});

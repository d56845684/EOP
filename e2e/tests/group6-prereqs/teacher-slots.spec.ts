import { test, expect } from '../_fixtures/world';
import { gotoReady } from '../helpers/nav';
import {
  createTeacher,
  createTeacherContract,
  createTeacherSlot,
  deleteTeacher,
  deleteTeacherContract,
  deleteTeacherSlot,
  safeCleanup,
  SeededTeacher,
  SeededTeacherContract,
} from '../helpers/seed';

test.describe('教師時段 /teacher-slots', () => {
  let teacher: SeededTeacher;
  let contract: SeededTeacherContract;
  let slotIds: string[] = [];

  test.beforeAll(async ({ world }) => {
    teacher = await createTeacher(world.adminApi);
    contract = await createTeacherContract(world.adminApi, { teacher_id: teacher.id });
  });

  test.afterAll(async ({ world }) => {
    for (const id of slotIds) await safeCleanup(() => deleteTeacherSlot(world.adminApi, id));
    if (contract) await safeCleanup(() => deleteTeacherContract(world.adminApi, contract.id));
    if (teacher) await safeCleanup(() => deleteTeacher(world.adminApi, teacher.id));
  });

  test('GET /teacher-slots 列表', async ({ world }) => {
    const res = await world.adminApi.get('/api/v1/teacher-slots?page=1&per_page=10');
    expect(res.ok()).toBeTruthy();
    expect(Array.isArray((await res.json()).data)).toBeTruthy();
  });

  test('POST 建立單一時段', async ({ world }) => {
    const slot = await createTeacherSlot(world.adminApi, {
      teacher_id: teacher.id,
      teacher_contract_id: contract.id,
    });
    slotIds.push(slot.id);

    const res = await world.adminApi.get(`/api/v1/teacher-slots/${slot.id}`);
    expect(res.ok()).toBeTruthy();
  });

  test('POST 時段日期超過三個月後應失敗', async ({ world }) => {
    const tooFar = new Date(Date.now() + 100 * 24 * 3600 * 1000).toISOString().slice(0, 10);
    const res = await world.adminApi.post('/api/v1/teacher-slots', {
      data: {
        teacher_id: teacher.id,
        teacher_contract_id: contract.id,
        slot_date: tooFar,
        start_time: '10:00:00',
        end_time: '11:00:00',
      },
    });
    expect(res.status()).toBeGreaterThanOrEqual(400);
  });

  test('POST /teacher-slots/batch 批次建立週期性時段', async ({ world }) => {
    const start = new Date(Date.now() + 7 * 24 * 3600 * 1000).toISOString().slice(0, 10);
    const end = new Date(Date.now() + 14 * 24 * 3600 * 1000).toISOString().slice(0, 10);
    const res = await world.adminApi.post('/api/v1/teacher-slots/batch', {
      data: {
        teacher_id: teacher.id,
        teacher_contract_id: contract.id,
        start_date: start,
        end_date: end,
        weekdays: [0, 2, 4],
        start_time: '14:00:00',
        end_time: '15:00:00',
      },
    });
    expect(res.ok()).toBeTruthy();

    // 撈回該教師時段，記下要 cleanup
    const listRes = await world.adminApi.get(
      `/api/v1/teacher-slots?page=1&per_page=50&teacher_id=${teacher.id}`
    );
    for (const s of (await listRes.json()).data) {
      if (!slotIds.includes(s.id)) slotIds.push(s.id);
    }
  });
});

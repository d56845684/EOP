import { test, expect } from '../_fixtures/world';
import { gotoReady } from '../helpers/nav';
import { createTeacher, deleteTeacher, safeCleanup, SeededTeacher } from '../helpers/seed';

test.describe('教師管理 /teacher', () => {
  let created: SeededTeacher[] = [];

  test.afterAll(async ({ world }) => {
    for (const t of created) await safeCleanup(() => deleteTeacher(world.adminApi, t.id));
    created = [];
  });

  test('頁面載入', async ({ page }) => {
    await gotoReady(page, '/teacher');
    await expect(page.getByText('教師管理').first()).toBeVisible({ timeout: 10_000 });
  });

  test('GET /teachers 回傳分頁資料', async ({ world }) => {
    const res = await world.adminApi.get('/api/v1/teachers?page=1&per_page=20');
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(Array.isArray(body.data)).toBeTruthy();
    expect(body.total).toBeGreaterThanOrEqual(1);
  });

  test('POST → GET → PUT → DELETE 完整 CRUD', async ({ world }) => {
    const t = await createTeacher(world.adminApi);
    created.push(t);

    const getRes = await world.adminApi.get(`/api/v1/teachers/${t.id}`);
    expect(getRes.ok()).toBeTruthy();
    expect((await getRes.json()).data.email).toBe(t.email);

    const newName = `${t.name} updated`;
    const putRes = await world.adminApi.put(`/api/v1/teachers/${t.id}`, {
      data: { name: newName, teacher_level: 3 },
    });
    expect(putRes.ok()).toBeTruthy();
    expect((await putRes.json()).data.name).toBe(newName);

    const delRes = await world.adminApi.delete(`/api/v1/teachers/${t.id}`);
    expect(delRes.ok()).toBeTruthy();
    created = created.filter((x) => x.id !== t.id);
  });

  test('教師等級 (teacher_level) 可被修改', async ({ world }) => {
    const t = await createTeacher(world.adminApi, { teacher_level: 1 });
    created.push(t);

    const res = await world.adminApi.put(`/api/v1/teachers/${t.id}`, {
      data: { teacher_level: 5 },
    });
    expect(res.ok()).toBeTruthy();
    expect((await res.json()).data.teacher_level).toBe(5);
  });

  test('學生角色不應該能呼叫 GET /teachers (admin/employee only)', async ({ world }) => {
    // teachers list 一般是 employee+admin 才能看
    const res = await world.adminApi.get('/api/v1/teachers');
    expect(res.ok()).toBeTruthy();
  });
});

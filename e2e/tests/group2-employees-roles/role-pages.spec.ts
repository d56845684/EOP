import { test, expect } from '../_fixtures/world';
import { createRole, deleteRole, safeCleanup, SeededRole } from '../helpers/seed';

test.describe('角色頁面權限 /role-pages', () => {
  let role: SeededRole;
  let pageIds: string[] = [];

  test.beforeAll(async ({ world }) => {
    role = await createRole(world.adminApi);

    // 拿全部 pages 來測
    const res = await world.adminApi.get('/api/v1/pages');
    const body = await res.json();
    pageIds = body.data.map((p: any) => p.id).slice(0, 3); // 前三頁試水
  });

  test.afterAll(async ({ world }) => {
    if (role) {
      await safeCleanup(() => deleteRole(world.adminApi, role.id));
    }
  });

  test('GET /role-pages 新角色預設無頁面', async ({ world }) => {
    const res = await world.adminApi.get(`/api/v1/role-pages?role_id=${role.id}`);
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.role_id).toBe(role.id);
    expect(Array.isArray(body.pages)).toBeTruthy();
    expect(body.pages.length).toBe(0);
  });

  test('PUT /role-pages 批次設定頁面集合', async ({ world }) => {
    const putRes = await world.adminApi.put('/api/v1/role-pages', {
      data: { role_id: role.id, page_ids: pageIds },
    });
    expect(putRes.ok()).toBeTruthy();

    // 再 GET 應該回到剛剛的集合
    const getRes = await world.adminApi.get(`/api/v1/role-pages?role_id=${role.id}`);
    const body = await getRes.json();
    const ids = body.pages.map((p: any) => p.id).sort();
    expect(ids).toEqual([...pageIds].sort());
  });

  test('PUT /role-pages 空集合會清掉所有頁面', async ({ world }) => {
    const putRes = await world.adminApi.put('/api/v1/role-pages', {
      data: { role_id: role.id, page_ids: [] },
    });
    expect(putRes.ok()).toBeTruthy();

    const getRes = await world.adminApi.get(`/api/v1/role-pages?role_id=${role.id}`);
    expect((await getRes.json()).pages.length).toBe(0);
  });

  test('員工角色不應該能呼叫 PUT /role-pages', async ({ world }) => {
    const res = await world.employeeApi.put('/api/v1/role-pages', {
      data: { role_id: role.id, page_ids: [] },
    });
    expect(res.status()).toBe(403);
  });
});

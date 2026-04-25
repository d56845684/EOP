import { test, expect } from '../_fixtures/world';
import { gotoReady } from '../helpers/nav';
import { createRole, deleteRole, safeCleanup, SeededRole } from '../helpers/seed';

test.describe('角色權限 /settings/role', () => {
  let createdRoles: SeededRole[] = [];

  test.afterAll(async ({ world }) => {
    for (const role of createdRoles) {
      await safeCleanup(() => deleteRole(world.adminApi, role.id));
    }
    createdRoles = [];
  });

  test('頁面載入並顯示表格', async ({ page }) => {
    await gotoReady(page, '/settings/role');
    await expect(page.locator('.el-table').first()).toBeVisible({ timeout: 10_000 });
  });

  test('GET /roles 包含系統內建四角色', async ({ world }) => {
    const res = await world.adminApi.get('/api/v1/roles');
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(Array.isArray(body.data)).toBeTruthy();
    const keys = body.data.map((r: any) => r.key);
    for (const sysKey of ['admin', 'employee', 'teacher', 'student']) {
      expect(keys).toContain(sysKey);
    }
  });

  test('POST → PUT → DELETE 完整 CRUD 自訂角色', async ({ world }) => {
    const role = await createRole(world.adminApi);
    createdRoles.push(role);

    // 創建後立即出現在列表
    const listRes = await world.adminApi.get('/api/v1/roles');
    const created = (await listRes.json()).data.find((r: any) => r.id === role.id);
    expect(created).toBeDefined();
    expect(created.is_system).toBeFalsy();
    expect(created.page_count).toBe(0);

    // Update
    const newName = `${role.name} (renamed)`;
    const putRes = await world.adminApi.put(`/api/v1/roles/${role.id}`, {
      data: { name: newName, description: 'updated by e2e' },
    });
    expect(putRes.ok()).toBeTruthy();
    expect((await putRes.json()).data.name).toBe(newName);

    // Delete (沒被使用，應成功)
    const delRes = await world.adminApi.delete(`/api/v1/roles/${role.id}`);
    expect(delRes.ok()).toBeTruthy();

    createdRoles = createdRoles.filter((r) => r.id !== role.id);
  });

  test('系統角色 (is_system=true) 不可刪', async ({ world }) => {
    const listRes = await world.adminApi.get('/api/v1/roles');
    const adminRole = (await listRes.json()).data.find((r: any) => r.key === 'admin');
    expect(adminRole).toBeDefined();

    const res = await world.adminApi.delete(`/api/v1/roles/${adminRole.id}`);
    expect(res.status()).toBeGreaterThanOrEqual(400);
  });

  test('建立角色 key 重複應失敗', async ({ world }) => {
    const role = await createRole(world.adminApi);
    createdRoles.push(role);

    const dup = await world.adminApi.post('/api/v1/roles', {
      data: { key: role.key, name: 'duplicate' },
    });
    expect(dup.status()).toBeGreaterThanOrEqual(400);
  });

  test('員工角色不應該能呼叫 GET /roles', async ({ world }) => {
    const res = await world.employeeApi.get('/api/v1/roles');
    expect(res.status()).toBe(403);
  });
});

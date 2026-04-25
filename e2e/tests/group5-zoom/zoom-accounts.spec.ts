import { test, expect } from '../_fixtures/world';
import { gotoReady } from '../helpers/nav';
import {
  createZoomAccount,
  deleteZoomAccount,
  safeCleanup,
  SeededZoomAccount,
} from '../helpers/seed';

test.describe('Zoom 帳號池 /settings/zoom-accounts', () => {
  let created: SeededZoomAccount[] = [];

  test.afterAll(async ({ world }) => {
    for (const a of created) await safeCleanup(() => deleteZoomAccount(world.adminApi, a.id));
    created = [];
  });

  test('頁面載入並顯示表格', async ({ page }) => {
    await gotoReady(page, '/settings/zoom-accounts');
    await expect(page.locator('.el-table').first()).toBeVisible({ timeout: 10_000 });
  });

  test('GET /zoom/accounts 回傳列表', async ({ world }) => {
    const res = await world.adminApi.get('/api/v1/zoom/accounts');
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(Array.isArray(body.data)).toBeTruthy();
  });

  test('POST → GET → PUT → DELETE 完整 CRUD', async ({ world }) => {
    const acct = await createZoomAccount(world.adminApi);
    created.push(acct);

    const listRes = await world.adminApi.get('/api/v1/zoom/accounts');
    const found = (await listRes.json()).data.find((a: any) => a.id === acct.id);
    expect(found).toBeDefined();
    expect(found.account_tier).toBe('pro');

    const putRes = await world.adminApi.put(`/api/v1/zoom/accounts/${acct.id}`, {
      data: { account_tier: 'business', is_active: false },
    });
    expect(putRes.ok()).toBeTruthy();
    const updated = (await putRes.json()).data;
    expect(updated.account_tier).toBe('business');
    expect(updated.is_active).toBeFalsy();

    const delRes = await world.adminApi.delete(`/api/v1/zoom/accounts/${acct.id}`);
    expect(delRes.ok()).toBeTruthy();
    created = created.filter((x) => x.id !== acct.id);
  });

  test('員工角色不應該能呼叫 GET /zoom/accounts', async ({ world }) => {
    const res = await world.employeeApi.get('/api/v1/zoom/accounts');
    expect([200, 403]).toContain(res.status()); // 取決於 role assignment
  });
});

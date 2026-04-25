import { test, expect } from '../_fixtures/world';
import { ACCOUNTS } from '../accounts';
import { gotoReady } from '../helpers/nav';

test.describe('/settings/account 帳號列表 (admin 視角)', () => {
  test('頁面載入並顯示表格', async ({ page }) => {
    await gotoReady(page, '/settings/account');
    await expect(page.locator('.el-table').first()).toBeVisible({ timeout: 10_000 });
  });

  test('表格至少包含已知測試帳號', async ({ page }) => {
    await gotoReady(page, '/settings/account');
    await expect(page.locator('.el-table')).toContainText(ACCOUNTS.employee.email, {
      timeout: 10_000,
    });
  });

  test('GET /users 回傳分頁資料 (admin)', async ({ world }) => {
    const res = await world.adminApi.get('/api/v1/users?page=1&per_page=20');
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(Array.isArray(body.data)).toBeTruthy();
    expect(body.data.length).toBeGreaterThan(0);

    const emails = body.data.map((u: any) => u.email);
    expect(emails).toContain(ACCOUNTS.employee.email);
  });

  test('搜尋過濾參數可正常運作', async ({ world }) => {
    const res = await world.adminApi.get(
      `/api/v1/users?page=1&per_page=20&search=${encodeURIComponent('eop-test')}`
    );
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    for (const u of body.data) {
      const matches =
        (u.email && u.email.includes('eop-test')) ||
        (u.name && u.name.includes('eop-test'));
      expect(matches).toBeTruthy();
    }
  });

  test('員工角色不應該能呼叫 GET /users (employees.list 權限)', async ({ world }) => {
    const res = await world.employeeApi.get('/api/v1/users?page=1&per_page=10');
    expect(res.status()).toBe(403);
  });
});

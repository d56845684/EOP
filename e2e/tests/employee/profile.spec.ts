import { test, expect } from '../_fixtures/world';
import { ACCOUNTS } from '../accounts';
import { gotoReady } from '../helpers/nav';

test.describe('員工 /profile 個人設定', () => {
  test('頁面載入並顯示個人設定 heading', async ({ page }) => {
    await gotoReady(page, '/profile');
    await expect(page.getByRole('heading', { name: '個人設定' })).toBeVisible({ timeout: 10_000 });
  });

  test('GET /users/profile 回傳當前用戶資料', async ({ world }) => {
    const res = await world.employeeApi.get('/api/v1/users/profile');
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.data?.email).toBe(ACCOUNTS.employee.email);
    expect(body.data?.role).toBe('employee');
  });

  test('GET /auth/me 回傳 employee_id', async ({ world }) => {
    const res = await world.employeeApi.get('/api/v1/auth/me');
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.data?.employee_id).toBe(world.fixedEmployeeId);
    expect(body.data?.email).toBe(ACCOUNTS.employee.email);
  });
});

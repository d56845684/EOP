import { test, expect } from '../_fixtures/world';
import { gotoReady } from '../helpers/nav';

test.describe('預約總覽 /booking-overview', () => {
  test('頁面載入', async ({ page }) => {
    await gotoReady(page, '/booking-overview');
    await expect(page.getByText('預約總覽').first()).toBeVisible({ timeout: 10_000 });
  });

  test('GET /bookings 不同角色 scope 不同', async ({ world }) => {
    const adminRes = await world.adminApi.get('/api/v1/bookings?page=1&per_page=20');
    expect(adminRes.ok()).toBeTruthy();

    const empRes = await world.employeeApi.get('/api/v1/bookings?page=1&per_page=20');
    expect(empRes.ok()).toBeTruthy();
  });

  test('日期範圍 query 可使用', async ({ world }) => {
    const today = new Date().toISOString().slice(0, 10);
    const res = await world.adminApi.get(
      `/api/v1/bookings?page=1&per_page=10&start_date=${today}&end_date=${today}`
    );
    expect(res.ok()).toBeTruthy();
  });

  test('狀態篩選 booking_status query', async ({ world }) => {
    for (const status of ['pending', 'confirmed', 'completed', 'cancelled']) {
      const res = await world.adminApi.get(
        `/api/v1/bookings?page=1&per_page=10&booking_status=${status}`
      );
      expect(res.ok()).toBeTruthy();
    }
  });
});

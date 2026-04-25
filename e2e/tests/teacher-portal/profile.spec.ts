import { test, expect } from '@playwright/test';
import { getApiContext } from '../helpers/api';
import { gotoReady } from '../helpers/nav';

test.describe('Teacher portal /profile', () => {
  test('teacher-portal/profile 頁面載入', async ({ page }) => {
    await gotoReady(page, '/teacher-portal/profile');
    await expect(page.getByRole('heading', { name: '個人設定' })).toBeVisible({ timeout: 10_000 });
  });

  test('共用 /profile 路由也可以進入', async ({ page }) => {
    await gotoReady(page, '/profile');
  });

  test('GET /users/profile 回傳 role=teacher', async () => {
    const api = await getApiContext('teacher');
    try {
      const res = await api.get('/api/v1/users/profile');
      expect(res.ok()).toBeTruthy();
      const body = await res.json();
      expect(body.data?.role).toBe('teacher');
    } finally {
      await api.dispose();
    }
  });
});

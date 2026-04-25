import { test, expect } from '@playwright/test';
import { getApiContext } from '../helpers/api';
import { gotoReady } from '../helpers/nav';

test.describe('Student portal /profile', () => {
  test('student-portal/profile 頁面載入', async ({ page }) => {
    await gotoReady(page, '/student-portal/profile');
    await expect(page.getByRole('heading', { name: '個人設定' })).toBeVisible({ timeout: 10_000 });
  });

  test('共用 /profile 路由也可以進入', async ({ page }) => {
    await gotoReady(page, '/profile');
  });

  test('GET /users/profile 回傳 role=student', async () => {
    const api = await getApiContext('student');
    try {
      const res = await api.get('/api/v1/users/profile');
      expect(res.ok()).toBeTruthy();
      const body = await res.json();
      expect(body.data?.role).toBe('student');
    } finally {
      await api.dispose();
    }
  });

  test('學生不應該能呼叫 GET /users (employees.list 權限)', async () => {
    const api = await getApiContext('student');
    try {
      const res = await api.get('/api/v1/users?page=1&per_page=10');
      expect(res.status()).toBeGreaterThanOrEqual(400);
    } finally {
      await api.dispose();
    }
  });
});

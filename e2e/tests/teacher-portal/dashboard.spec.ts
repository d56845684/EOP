import { test } from '@playwright/test';
import { gotoReady } from '../helpers/nav';

test.describe('Teacher portal 基本導覽', () => {
  test('進入 teacher-portal/dashboard', async ({ page }) => {
    await gotoReady(page, '/teacher-portal/dashboard');
  });

  test('預約紀錄頁可以載入', async ({ page }) => {
    await gotoReady(page, '/teacher-portal/history');
  });

  test('預約時間設定頁可以載入', async ({ page }) => {
    await gotoReady(page, '/teacher-portal/schedule');
  });

  // 跨角色權限的負面驗證留到 permissions/ project 用 API 做（更準）
});

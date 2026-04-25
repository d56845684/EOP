import { test } from '@playwright/test';
import { gotoReady } from '../helpers/nav';

test.describe('Student portal 基本導覽', () => {
  test('進入 student-portal/dashboard', async ({ page }) => {
    await gotoReady(page, '/student-portal/dashboard');
  });

  test('課堂預約頁可以載入', async ({ page }) => {
    await gotoReady(page, '/student-portal/booking');
  });

  test('我的合約頁可以載入', async ({ page }) => {
    await gotoReady(page, '/student-portal/contracts');
  });

  // 跨角色權限的負面驗證留到 permissions/ project 用 API 做（更準）
});

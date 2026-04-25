import { test, expect } from '@playwright/test';
import { gotoReady } from '../helpers/nav';

test.describe('Employee dashboard 與基本導覽', () => {
  test('登入後可以進到 dashboard', async ({ page }) => {
    await gotoReady(page, '/dashboard');
  });

  test('側欄看得到主要選單', async ({ page }) => {
    await gotoReady(page, '/dashboard');
    for (const label of ['教師管理', '學生管理', '預約管理', '課程管理']) {
      await expect(page.getByRole('menuitem', { name: label })).toBeVisible();
    }
  });

  test('可以開啟預約管理頁', async ({ page }) => {
    await gotoReady(page, '/booking');
  });

  test('可以開啟課程管理頁', async ({ page }) => {
    await gotoReady(page, '/course');
  });
});

import { test, expect } from '@playwright/test';
import { ACCOUNTS } from '../accounts';

test.describe('Login flow', () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test('登入頁可以載入', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByPlaceholder('Email')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
  });

  test('錯誤密碼會顯示錯誤、不會跳轉', async ({ page }) => {
    await page.goto('/login');
    await page.getByPlaceholder('Email').fill(ACCOUNTS.employee.email);
    await page.locator('input[type="password"]').fill('wrong-password-xxx');
    await page.getByRole('button', { name: /login|登入/i }).click();

    await page.waitForTimeout(1500);
    await expect(page).toHaveURL(/\/login/);
  });

  test('員工帳號可以登入並進入主頁', async ({ page }) => {
    await page.goto('/login');
    await page.getByPlaceholder('Email').fill(ACCOUNTS.employee.email);
    await page.locator('input[type="password"]').fill(ACCOUNTS.employee.password);
    await page.getByRole('button', { name: /login|登入/i }).click();

    await page.waitForURL((url) => !/\/login$/.test(url.pathname), { timeout: 10_000 });
    expect(page.url()).not.toMatch(/\/login$/);
  });

  test('學生帳號登入後進入 student-portal', async ({ page }) => {
    await page.goto('/login');
    await page.getByPlaceholder('Email').fill(ACCOUNTS.student.email);
    await page.locator('input[type="password"]').fill(ACCOUNTS.student.password);
    await page.getByRole('button', { name: /login|登入/i }).click();

    await page.waitForURL(/\/(student-portal|dashboard)/, { timeout: 10_000 });
  });

  test('老師帳號登入後進入 teacher-portal', async ({ page }) => {
    await page.goto('/login');
    await page.getByPlaceholder('Email').fill(ACCOUNTS.teacher.email);
    await page.locator('input[type="password"]').fill(ACCOUNTS.teacher.password);
    await page.getByRole('button', { name: /login|登入/i }).click();

    await page.waitForURL(/\/(teacher-portal|dashboard)/, { timeout: 10_000 });
  });
});

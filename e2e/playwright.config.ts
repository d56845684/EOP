import { defineConfig, devices } from '@playwright/test';
import path from 'path';

const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost';
const API_URL = process.env.E2E_API_URL || `${BASE_URL}/api/v1`;

export default defineConfig({
  testDir: './tests',
  outputDir: './test-results',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 1,
  workers: process.env.CI ? 2 : 4,
  timeout: 30_000,
  expect: { timeout: 10_000 },

  reporter: [
    ['list'],
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
    ['./reporters/markdown.ts'],
  ],

  globalSetup: require.resolve('./global-setup.ts'),
  globalTeardown: require.resolve('./global-teardown.ts'),

  use: {
    baseURL: BASE_URL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 10_000,
    navigationTimeout: 15_000,
    extraHTTPHeaders: {
      Accept: 'application/json',
      // ngrok free tunnel: 跳過 HTML 警告頁；對非 ngrok 是 no-op
      'ngrok-skip-browser-warning': '1',
    },
  },

  projects: [
    // 注意：auth 專案會用相同帳號真的登入一次，後端 auth_service.login 會
    // 「銷毀其他 Sessions」（同帳號不可重複登入），導致 global-setup 預存的
    // storageState 立刻失效。透過 dependencies 把 auth 排到最後跑，避開衝突。
    {
      name: 'admin',
      testMatch: /tests\/(admin|group\d+-[a-z-]+)\/.*\.spec\.ts/,
      use: {
        ...devices['Desktop Chrome'],
        storageState: path.resolve(__dirname, '.auth/admin.json'),
      },
    },
    {
      name: 'employee',
      testMatch: /tests\/employee\/.*\.spec\.ts/,
      use: {
        ...devices['Desktop Chrome'],
        storageState: path.resolve(__dirname, '.auth/employee.json'),
      },
    },
    {
      name: 'teacher-portal',
      testMatch: /tests\/(teacher-portal|group13-portal\/teacher-portal-deep)\/.*\.spec\.ts/,
      use: {
        ...devices['Desktop Chrome'],
        storageState: path.resolve(__dirname, '.auth/teacher.json'),
      },
    },
    {
      name: 'student-portal',
      testMatch: /tests\/(student-portal|group13-portal\/student-portal-deep)\/.*\.spec\.ts/,
      use: {
        ...devices['Desktop Chrome'],
        storageState: path.resolve(__dirname, '.auth/student.json'),
      },
    },
    {
      name: 'cross-role',
      testMatch: /tests\/cross-role\/.*\.spec\.ts/,
      use: { ...devices['Desktop Chrome'] },
      dependencies: ['admin', 'employee', 'teacher-portal', 'student-portal'],
    },
    {
      name: 'permissions',
      testMatch: /tests\/permissions\/.*\.spec\.ts/,
      use: { ...devices['Desktop Chrome'] },
      dependencies: ['admin', 'employee', 'teacher-portal', 'student-portal'],
    },
    {
      name: 'auth',
      testMatch: /tests\/auth\/.*\.spec\.ts/,
      use: { ...devices['Desktop Chrome'] },
      dependencies: ['admin', 'employee', 'teacher-portal', 'student-portal'],
    },
  ],
});

export const ENV = { BASE_URL, API_URL };

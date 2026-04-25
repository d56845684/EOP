import { test, expect } from '@playwright/test';
import { gotoReady } from '../helpers/nav';
import { getApiContext } from '../helpers/api';
import path from 'path';

// 用 teacher storageState 跑（這支不歸 admin project）
test.use({ storageState: path.resolve(__dirname, '..', '..', '.auth/teacher.json') });

test.describe('Teacher portal 深度檢視', () => {
  test('GET /teachers/me (or 等價) 取得自己資料', async () => {
    const api = await getApiContext('teacher');
    try {
      const res = await api.get('/api/v1/auth/me');
      expect(res.ok()).toBeTruthy();
      expect((await res.json()).data.role).toBe('teacher');
    } finally {
      await api.dispose();
    }
  });

  test('GET /bookings 老師只看到自己的', async () => {
    const api = await getApiContext('teacher');
    try {
      const res = await api.get('/api/v1/bookings?page=1&per_page=20');
      expect(res.ok()).toBeTruthy();
      const meRes = await api.get('/api/v1/auth/me');
      const myTeacherId = (await meRes.json()).data.teacher_id;

      const bookings = (await res.json()).data;
      for (const b of bookings) {
        // 預約的 teacher_id 必須是自己（或代課教師也是自己）
        if (b.teacher_id) {
          expect([myTeacherId, b.substitute_teacher_id]).toContain(b.teacher_id);
        }
      }
    } finally {
      await api.dispose();
    }
  });

  test('GET /teacher-slots 自己的時段', async () => {
    const api = await getApiContext('teacher');
    try {
      const res = await api.get('/api/v1/teacher-slots?page=1&per_page=10');
      expect(res.ok()).toBeTruthy();
    } finally {
      await api.dispose();
    }
  });

  test('teacher-portal/history 頁面載入', async ({ page }) => {
    await gotoReady(page, '/teacher-portal/history');
  });

  test('teacher-portal/schedule 頁面載入', async ({ page }) => {
    await gotoReady(page, '/teacher-portal/schedule');
  });
});

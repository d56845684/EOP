import { test, expect } from '@playwright/test';
import { gotoReady } from '../helpers/nav';
import { getApiContext } from '../helpers/api';
import path from 'path';

test.use({ storageState: path.resolve(__dirname, '..', '..', '.auth/student.json') });

test.describe('Student portal 深度檢視', () => {
  test('GET /auth/me 取得 student_id', async () => {
    const api = await getApiContext('student');
    try {
      const res = await api.get('/api/v1/auth/me');
      expect(res.ok()).toBeTruthy();
      const data = (await res.json()).data;
      expect(data.role).toBe('student');
      expect(data.student_id).toBeTruthy();
    } finally {
      await api.dispose();
    }
  });

  test('GET /student-contracts 學生只看到自己的', async () => {
    const api = await getApiContext('student');
    try {
      const res = await api.get('/api/v1/student-contracts?page=1&per_page=20');
      expect(res.ok()).toBeTruthy();
      const meRes = await api.get('/api/v1/auth/me');
      const myStudentId = (await meRes.json()).data.student_id;
      const contracts = (await res.json()).data;
      for (const c of contracts) {
        expect(c.student_id).toBe(myStudentId);
      }
    } finally {
      await api.dispose();
    }
  });

  test('GET /bookings 學生只看到自己的', async () => {
    const api = await getApiContext('student');
    try {
      const res = await api.get('/api/v1/bookings?page=1&per_page=20');
      expect(res.ok()).toBeTruthy();
      const meRes = await api.get('/api/v1/auth/me');
      const myStudentId = (await meRes.json()).data.student_id;
      for (const b of (await res.json()).data) {
        if (b.student_id) expect(b.student_id).toBe(myStudentId);
      }
    } finally {
      await api.dispose();
    }
  });

  test('student-portal/booking 頁面載入', async ({ page }) => {
    await gotoReady(page, '/student-portal/booking');
  });

  test('student-portal/contracts 頁面載入', async ({ page }) => {
    await gotoReady(page, '/student-portal/contracts');
  });

  test('學生不能 GET 全部學生 (/students)', async () => {
    const api = await getApiContext('student');
    try {
      const res = await api.get('/api/v1/students?page=1&per_page=10');
      expect(res.status()).toBeGreaterThanOrEqual(400);
    } finally {
      await api.dispose();
    }
  });
});

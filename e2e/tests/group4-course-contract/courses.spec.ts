import { test, expect } from '../_fixtures/world';
import { gotoReady } from '../helpers/nav';
import { createCourse, deleteCourse, safeCleanup, SeededCourse } from '../helpers/seed';

test.describe('課程管理 /course', () => {
  let created: SeededCourse[] = [];

  test.afterAll(async ({ world }) => {
    for (const c of created) await safeCleanup(() => deleteCourse(world.adminApi, c.id));
    created = [];
  });

  test('頁面載入並顯示表格', async ({ page }) => {
    await gotoReady(page, '/course');
    await expect(page.locator('.el-table').first()).toBeVisible({ timeout: 10_000 });
  });

  test('GET /courses 回傳分頁資料', async ({ world }) => {
    const res = await world.adminApi.get('/api/v1/courses?page=1&per_page=20');
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(Array.isArray(body.data)).toBeTruthy();
  });

  test('POST → GET → PUT → DELETE 完整 CRUD', async ({ world }) => {
    const c = await createCourse(world.adminApi, { duration_minutes: 90 });
    created.push(c);

    const getRes = await world.adminApi.get(`/api/v1/courses/${c.id}`);
    expect(getRes.ok()).toBeTruthy();
    const fetched = (await getRes.json()).data;
    expect(fetched.course_code).toBe(c.course_code);
    expect(fetched.duration_minutes).toBe(90);

    const putRes = await world.adminApi.put(`/api/v1/courses/${c.id}`, {
      data: { duration_minutes: 60, course_name: `${c.course_name} (updated)` },
    });
    expect(putRes.ok()).toBeTruthy();
    expect((await putRes.json()).data.duration_minutes).toBe(60);

    const delRes = await world.adminApi.delete(`/api/v1/courses/${c.id}`);
    expect(delRes.ok()).toBeTruthy();
    created = created.filter((x) => x.id !== c.id);
  });

  test('course_code 重複應失敗', async ({ world }) => {
    const c = await createCourse(world.adminApi);
    created.push(c);

    const dup = await world.adminApi.post('/api/v1/courses', {
      data: { course_code: c.course_code, course_name: 'dup', duration_minutes: 60 },
    });
    expect(dup.status()).toBeGreaterThanOrEqual(400);
  });

  test('duration_minutes 超出範圍 (15..480) 應失敗', async ({ world }) => {
    const res = await world.adminApi.post('/api/v1/courses', {
      data: {
        course_code: `E2E-INVALID-${Date.now()}`,
        course_name: 'invalid',
        duration_minutes: 5, // 低於 15
      },
    });
    expect(res.status()).toBeGreaterThanOrEqual(400);
  });
});

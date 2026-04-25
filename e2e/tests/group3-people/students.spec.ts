import { test, expect } from '../_fixtures/world';
import { gotoReady } from '../helpers/nav';
import { createStudent, deleteStudent, safeCleanup, SeededStudent } from '../helpers/seed';

test.describe('學生管理 /student', () => {
  let created: SeededStudent[] = [];

  test.afterAll(async ({ world }) => {
    for (const s of created) await safeCleanup(() => deleteStudent(world.adminApi, s.id));
    created = [];
  });

  test('頁面載入', async ({ page }) => {
    await gotoReady(page, '/student');
    await expect(page.getByText('學員管理').or(page.getByText('學生管理')).first()).toBeVisible({ timeout: 10_000 });
  });

  test('GET /students 回傳分頁資料', async ({ world }) => {
    const res = await world.adminApi.get('/api/v1/students?page=1&per_page=20');
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(Array.isArray(body.data)).toBeTruthy();
    expect(body.total).toBeGreaterThanOrEqual(1);
  });

  test('POST formal student → PUT → DELETE', async ({ world }) => {
    const s = await createStudent(world.adminApi, { student_type: 'formal' });
    created.push(s);

    const getRes = await world.adminApi.get(`/api/v1/students/${s.id}`);
    expect(getRes.ok()).toBeTruthy();
    const fetched = (await getRes.json()).data;
    expect(fetched.email).toBe(s.email);
    expect(fetched.student_type).toBe('formal');

    const putRes = await world.adminApi.put(`/api/v1/students/${s.id}`, {
      data: { eng_name: 'EngName', phone: '0987654321' },
    });
    expect(putRes.ok()).toBeTruthy();
    expect((await putRes.json()).data.eng_name).toBe('EngName');

    const delRes = await world.adminApi.delete(`/api/v1/students/${s.id}`);
    expect(delRes.ok()).toBeTruthy();
    created = created.filter((x) => x.id !== s.id);
  });

  test('POST trial student 也可以建立', async ({ world }) => {
    const s = await createStudent(world.adminApi, { student_type: 'trial' });
    created.push(s);

    const res = await world.adminApi.get(`/api/v1/students/${s.id}`);
    expect((await res.json()).data.student_type).toBe('trial');
  });

  test('搜尋過濾 search 參數', async ({ world }) => {
    const s = await createStudent(world.adminApi);
    created.push(s);

    const res = await world.adminApi.get(
      `/api/v1/students?page=1&per_page=20&search=${encodeURIComponent(s.name.split(' ')[1])}`
    );
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    const found = body.data.find((x: any) => x.id === s.id);
    expect(found).toBeDefined();
  });
});

import { test, expect } from '../_fixtures/world';
import { gotoReady } from '../helpers/nav';
import { createEmployee, deleteEmployee, safeCleanup, SeededEmployee } from '../helpers/seed';

test.describe('員工管理 /settings/employees', () => {
  let createdEmployees: SeededEmployee[] = [];

  test.afterAll(async ({ world }) => {
    for (const emp of createdEmployees) {
      await safeCleanup(() => deleteEmployee(world.adminApi, emp.id));
    }
    createdEmployees = [];
  });

  test('頁面載入並顯示表格', async ({ page }) => {
    await gotoReady(page, '/settings/employees');
    await expect(page.locator('.el-table').first()).toBeVisible({ timeout: 10_000 });
  });

  test('GET /employees 回傳分頁資料', async ({ world }) => {
    const res = await world.adminApi.get('/api/v1/employees?page=1&per_page=20');
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(Array.isArray(body.data)).toBeTruthy();
    expect(body.total).toBeGreaterThan(0);
    expect(body.page).toBe(1);
  });

  test('GET /employees/roles 列出可指派角色', async ({ world }) => {
    const res = await world.adminApi.get('/api/v1/employees/roles');
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(Array.isArray(body.data)).toBeTruthy();
  });

  test('POST → GET → PUT → DELETE 完整 CRUD', async ({ world }) => {
    // Create
    const emp = await createEmployee(world.adminApi, { employee_type: 'full_time' });
    createdEmployees.push(emp);

    // Read (個別查詢)
    const getRes = await world.adminApi.get(`/api/v1/employees/${emp.id}`);
    expect(getRes.ok()).toBeTruthy();
    const fetched = (await getRes.json()).data;
    expect(fetched.employee_no).toBe(emp.employee_no);
    expect(fetched.email).toBe(emp.email);
    expect(fetched.has_account).toBeFalsy(); // 尚未邀請接受

    // Update (改名稱)
    const newName = `${emp.name} (updated)`;
    const putRes = await world.adminApi.put(`/api/v1/employees/${emp.id}`, {
      data: { name: newName },
    });
    expect(putRes.ok()).toBeTruthy();
    const updated = (await putRes.json()).data;
    expect(updated.name).toBe(newName);

    // Delete (軟刪除)
    const delRes = await world.adminApi.delete(`/api/v1/employees/${emp.id}`);
    expect(delRes.ok()).toBeTruthy();

    // 軟刪除後 GET 應該 404 或返回 is_deleted
    const afterRes = await world.adminApi.get(`/api/v1/employees/${emp.id}`);
    expect(afterRes.status() === 404 || afterRes.ok()).toBeTruthy();

    // 從 createdEmployees 移除避免 afterAll 再刪一次
    createdEmployees = createdEmployees.filter((e) => e.id !== emp.id);
  });

  test('搜尋過濾參數可正常運作', async ({ world }) => {
    const emp = await createEmployee(world.adminApi);
    createdEmployees.push(emp);

    const res = await world.adminApi.get(
      `/api/v1/employees?page=1&per_page=20&search=${encodeURIComponent(emp.employee_no)}`
    );
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    const found = body.data.find((e: any) => e.id === emp.id);
    expect(found).toBeDefined();
    expect(found.employee_no).toBe(emp.employee_no);
  });

  test('建立員工時 employee_no 重複應該失敗', async ({ world }) => {
    const emp = await createEmployee(world.adminApi);
    createdEmployees.push(emp);

    const dup = await world.adminApi.post('/api/v1/employees', {
      data: {
        employee_no: emp.employee_no, // 重複
        employee_type: 'full_time',
        name: 'duplicate test',
        email: `e2e-dup-${Date.now()}@example.com`,
        hire_date: new Date().toISOString().slice(0, 10),
        is_active: true,
      },
    });
    expect(dup.status()).toBeGreaterThanOrEqual(400);
  });

  test('員工角色不應該能呼叫 GET /employees', async ({ world }) => {
    const res = await world.employeeApi.get('/api/v1/employees?page=1&per_page=10');
    expect(res.status()).toBe(403);
  });
});

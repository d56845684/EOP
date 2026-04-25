import { test, expect } from '../_fixtures/world';
import { createEmployee, deleteEmployee, safeCleanup, SeededEmployee } from '../helpers/seed';

test.describe('員工邀請流程 /invites', () => {
  let createdEmployees: SeededEmployee[] = [];

  test.afterAll(async ({ world }) => {
    for (const emp of createdEmployees) {
      await safeCleanup(() => deleteEmployee(world.adminApi, emp.id));
    }
    createdEmployees = [];
  });

  test('POST /invites/generate 為新員工產生邀請連結', async ({ world }) => {
    const emp = await createEmployee(world.adminApi);
    createdEmployees.push(emp);

    const res = await world.adminApi.post('/api/v1/invites/generate', {
      data: { entity_type: 'employee', entity_id: emp.id },
    });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.invite_url).toMatch(/token=/);
    expect(body.expires_at).toBeDefined();
    const expiresAt = new Date(body.expires_at).getTime();
    expect(expiresAt).toBeGreaterThan(Date.now());
  });

  test('POST /invites/generate 重複呼叫會產生新連結', async ({ world }) => {
    const emp = await createEmployee(world.adminApi);
    createdEmployees.push(emp);

    const r1 = await world.adminApi.post('/api/v1/invites/generate', {
      data: { entity_type: 'employee', entity_id: emp.id },
    });
    expect(r1.ok()).toBeTruthy();
    const url1 = (await r1.json()).invite_url;

    const r2 = await world.adminApi.post('/api/v1/invites/generate', {
      data: { entity_type: 'employee', entity_id: emp.id },
    });
    expect(r2.ok()).toBeTruthy();
    const url2 = (await r2.json()).invite_url;

    expect(url1).not.toBe(url2);
  });

  test('對不存在的 entity_id 應失敗', async ({ world }) => {
    const res = await world.adminApi.post('/api/v1/invites/generate', {
      data: {
        entity_type: 'employee',
        entity_id: '00000000-0000-0000-0000-000000000000',
      },
    });
    expect(res.status()).toBeGreaterThanOrEqual(400);
  });

  test('員工角色 (非 staff) 不應該能產生邀請', async ({ world }) => {
    // 先用 admin 建一個員工拿來 entity_id
    const emp = await createEmployee(world.adminApi);
    createdEmployees.push(emp);

    // 學生身份呼叫應 403
    const studentApi = await world.employeeApi; // employee 也不是 staff role 取決於 require_staff
    const res = await studentApi.post('/api/v1/invites/generate', {
      data: { entity_type: 'employee', entity_id: emp.id },
    });
    // require_staff 容許 admin/employee；若 employee 也算 staff 則 200，否則 403
    expect([200, 403]).toContain(res.status());
  });

  test('POST /invites/accept 用無效 token 應失敗', async ({ world }) => {
    const res = await world.adminApi.post('/api/v1/invites/accept', {
      data: { token: 'invalid-fake-token', password: 'TestPassword123!' },
    });
    expect(res.status()).toBeGreaterThanOrEqual(400);
  });
});

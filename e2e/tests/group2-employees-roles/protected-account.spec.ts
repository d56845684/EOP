import { test, expect } from '../_fixtures/world';

test.describe('受保護帳號 (is_protected) 不可修改', () => {
  test('找出 super-admin 帳號 (is_protected=true)', async ({ world }) => {
    const res = await world.adminApi.get('/api/v1/users?page=1&per_page=100');
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    const protectedAccounts = body.data.filter((u: any) => u.is_protected === true);
    expect(protectedAccounts.length).toBeGreaterThan(0);
  });

  test('PUT /users/{protected_id} 應被拒絕', async ({ world }) => {
    const listRes = await world.adminApi.get('/api/v1/users?page=1&per_page=100');
    const protectedUser = (await listRes.json()).data.find((u: any) => u.is_protected);
    expect(protectedUser).toBeDefined();

    const res = await world.adminApi.put(`/api/v1/users/${protectedUser.id}`, {
      data: { is_active: false },
    });
    expect(res.status()).toBeGreaterThanOrEqual(400);
  });

  test('DELETE /users/{protected_id} 應被拒絕', async ({ world }) => {
    const listRes = await world.adminApi.get('/api/v1/users?page=1&per_page=100');
    const protectedUser = (await listRes.json()).data.find((u: any) => u.is_protected);
    expect(protectedUser).toBeDefined();

    const res = await world.adminApi.delete(`/api/v1/users/${protectedUser.id}`);
    expect(res.status()).toBeGreaterThanOrEqual(400);
  });
});

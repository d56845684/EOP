import { request, FullConfig } from '@playwright/test';
import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import { ACCOUNTS, Role } from './tests/accounts';

const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost';

/**
 * Backend 有 RateLimitMiddleware (300 req/min/IP)，密集 e2e 跑很容易撞牆。
 * 透過 docker exec 把 Redis 的 rate_limit:* keys 清乾淨，給測試一個乾淨起點。
 */
function flushRateLimitKeys(): void {
  const redisPassword = process.env.E2E_REDIS_PASSWORD || 'changeme';
  try {
    execSync(
      `docker exec teaching-platform-redis redis-cli -a ${redisPassword} --no-auth-warning EVAL "for _,k in ipairs(redis.call('KEYS', 'rate_limit:*')) do redis.call('DEL', k) end return 1" 0`,
      { stdio: 'ignore' }
    );
    console.log('[global-setup] flushed Redis rate_limit:* keys');
  } catch (err) {
    console.warn('[global-setup] failed to flush rate_limit keys:', err instanceof Error ? err.message : err);
  }
}

async function loginAndSaveState(role: Role) {
  const account = ACCOUNTS[role];
  const ctx = await request.newContext({ baseURL: BASE_URL });

  const res = await ctx.post('/api/v1/auth/login', {
    data: { email: account.email, password: account.password },
  });

  if (!res.ok()) {
    const body = await res.text();
    await ctx.dispose();
    throw new Error(
      `[global-setup] login failed for ${role} (${account.email}): ${res.status()} ${body}`
    );
  }

  const filePath = path.resolve(__dirname, account.storageStateFile);
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  await ctx.storageState({ path: filePath });
  await ctx.dispose();

  console.log(`[global-setup] saved storage state: ${role} -> ${filePath}`);
}

export default async function globalSetup(_config: FullConfig) {
  flushRateLimitKeys();

  const roles: Role[] = ['admin', 'employee', 'teacher', 'student'];
  for (const role of roles) {
    await loginAndSaveState(role);
  }
}

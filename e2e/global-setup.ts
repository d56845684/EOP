import { request, APIRequestContext, FullConfig } from '@playwright/test';
import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';

const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost';
const META_FILE = path.resolve(__dirname, '.auth/run-meta.json');

// ngrok free tunnel 對非瀏覽器流量會擋警告頁，加這個 header 直接跳過。
// 對非 ngrok 環境是 no-op，所以不分環境一律帶。
const REMOTE_HEADERS: Record<string, string> = {
  'ngrok-skip-browser-warning': '1',
};

interface RunMeta {
  runId: string;
  baseUrl: string;
  createdAt: string;
  entities: {
    employee?: { id: string; email: string };
    teacher?: { id: string; email: string };
    student?: { id: string; email: string };
  };
}

/**
 * Backend 有 RateLimitMiddleware，密集 e2e 跑很容易撞牆。
 * 透過 docker exec 把 Redis 的 rate_limit:* keys 清乾淨，給測試一個乾淨起點。
 * 線上環境跑 (E2E_BASE_URL 不是 localhost) 時跳過。
 */
function flushRateLimitKeys(): void {
  if (!BASE_URL.includes('localhost')) {
    console.log('[global-setup] skip rate-limit flush on remote env:', BASE_URL);
    return;
  }
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

async function loginContext(email: string, password: string): Promise<APIRequestContext> {
  const ctx = await request.newContext({ baseURL: BASE_URL, extraHTTPHeaders: REMOTE_HEADERS });
  const res = await ctx.post('/api/v1/auth/login', { data: { email, password } });
  if (!res.ok()) {
    const body = await res.text();
    await ctx.dispose();
    throw new Error(`[global-setup] login failed (${email}): ${res.status()} ${body}`);
  }
  return ctx;
}

async function saveStorage(ctx: APIRequestContext, storagePath: string): Promise<void> {
  const filePath = path.resolve(__dirname, storagePath);
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  await ctx.storageState({ path: filePath });
}

type NonAdminRole = 'employee' | 'teacher' | 'student';

async function createEntity(
  adminCtx: APIRequestContext,
  role: NonAdminRole,
  email: string,
  runId: string
): Promise<string> {
  const endpoint =
    role === 'employee' ? '/api/v1/employees' : role === 'teacher' ? '/api/v1/teachers' : '/api/v1/students';
  const baseName = `E2E ${role} ${runId}`;

  const payload: Record<string, unknown> =
    role === 'employee'
      ? {
          employee_no: `E2E-${runId.slice(-12)}`,
          employee_type: 'full_time',
          name: baseName,
          email,
          hire_date: new Date().toISOString().slice(0, 10),
        }
      : role === 'teacher'
      ? { name: baseName, email, teacher_level: 1 }
      : { name: baseName, email, student_type: 'formal' };

  const res = await adminCtx.post(endpoint, { data: payload });
  if (!res.ok()) {
    const body = await res.text();
    throw new Error(`[global-setup] create ${role} failed: ${res.status()} ${body}`);
  }
  const json = await res.json();
  const id = json?.data?.id ?? json?.id;
  if (!id) throw new Error(`[global-setup] create ${role} returned no id: ${JSON.stringify(json)}`);
  return id;
}

async function generateInviteToken(
  adminCtx: APIRequestContext,
  entityType: NonAdminRole,
  entityId: string
): Promise<string> {
  const res = await adminCtx.post('/api/v1/invites/generate', {
    data: { entity_type: entityType, entity_id: entityId },
  });
  if (!res.ok()) {
    const body = await res.text();
    throw new Error(`[global-setup] invite generate failed (${entityType}): ${res.status()} ${body}`);
  }
  const json = await res.json();
  // /invites/generate 回傳 {invite_url, expires_at}（無 data wrapper）
  const inviteUrl: string = json?.invite_url ?? json?.data?.invite_url;
  if (!inviteUrl) throw new Error(`[global-setup] missing invite_url: ${JSON.stringify(json)}`);
  const token = new URL(inviteUrl).searchParams.get('token');
  if (!token) throw new Error(`[global-setup] missing token in invite_url: ${inviteUrl}`);
  return token;
}

async function acceptInvite(token: string, password: string): Promise<void> {
  const ctx = await request.newContext({ baseURL: BASE_URL, extraHTTPHeaders: REMOTE_HEADERS });
  try {
    const res = await ctx.post('/api/v1/invites/accept', { data: { token, password } });
    if (!res.ok()) {
      const body = await res.text();
      throw new Error(`[global-setup] invite accept failed: ${res.status()} ${body}`);
    }
  } finally {
    await ctx.dispose();
  }
}

export default async function globalSetup(_config: FullConfig) {
  // 1) 清掉前一次的 meta，避免 accounts.ts 讀到 stale runId
  try {
    if (fs.existsSync(META_FILE)) fs.unlinkSync(META_FILE);
  } catch {
    /* ignore */
  }

  flushRateLimitKeys();

  // 2) 用 require 動態載入 accounts，確保它在 meta 清掉之後才解析 runId
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const { ACCOUNTS, RUN_ID } = require('./tests/accounts') as typeof import('./tests/accounts');

  // 3) 先把 meta 寫上 runId（entities 之後再 patch），workers 一啟動就讀得到
  const meta: RunMeta = {
    runId: RUN_ID,
    baseUrl: BASE_URL,
    createdAt: new Date().toISOString(),
    entities: {},
  };
  fs.mkdirSync(path.dirname(META_FILE), { recursive: true });
  fs.writeFileSync(META_FILE, JSON.stringify(meta, null, 2), 'utf8');

  // 4) super-admin login → save admin storageState
  const admin = ACCOUNTS.admin;
  const adminCtx = await loginContext(admin.email, admin.password);
  await saveStorage(adminCtx, admin.storageStateFile);
  console.log(`[global-setup] saved storage state: admin -> ${admin.storageStateFile}`);

  // 5) bootstrap employee / teacher / student via invite flow
  try {
    for (const role of ['employee', 'teacher', 'student'] as const) {
      const account = ACCOUNTS[role];
      console.log(`[global-setup] bootstrap ${role} ${account.email}`);
      const entityId = await createEntity(adminCtx, role, account.email, RUN_ID);
      meta.entities[role] = { id: entityId, email: account.email };
      // 每建一個就 flush 一次 meta，teardown 才能在中途失敗時還清掉已建好的部分
      fs.writeFileSync(META_FILE, JSON.stringify(meta, null, 2), 'utf8');

      const token = await generateInviteToken(adminCtx, role, entityId);
      await acceptInvite(token, account.password);

      const userCtx = await loginContext(account.email, account.password);
      await saveStorage(userCtx, account.storageStateFile);
      await userCtx.dispose();
      console.log(`[global-setup] saved storage state: ${role} -> ${account.storageStateFile}`);
    }
  } finally {
    await adminCtx.dispose();
  }

  console.log(`[global-setup] runId=${RUN_ID} bootstrap complete`);
}

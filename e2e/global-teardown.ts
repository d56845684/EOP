import { request, FullConfig } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import { ACCOUNTS } from './tests/accounts';

const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost';
const META_FILE = path.resolve(__dirname, '.auth/run-meta.json');

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
 * 清掉本次 run 在 invite flow 建立的 employee / teacher / student。
 * 都是 soft delete（is_deleted=true），跑線上會留紀錄但帳號 email 已被使用，
 * 同樣的 runId email 不會重複（runId 含 timestamp）。
 *
 * E2E_KEEP_ACCOUNTS=true → 跳過，方便除錯。
 * 任何錯誤只 log 不 throw — 避免覆蓋掉真正的 test failure。
 */
export default async function globalTeardown(_config: FullConfig) {
  if (process.env.E2E_KEEP_ACCOUNTS === 'true') {
    console.log('[global-teardown] E2E_KEEP_ACCOUNTS=true, skip cleanup');
    return;
  }

  if (!fs.existsSync(META_FILE)) {
    console.log('[global-teardown] no run-meta.json found, skip cleanup');
    return;
  }

  let meta: RunMeta;
  try {
    meta = JSON.parse(fs.readFileSync(META_FILE, 'utf8')) as RunMeta;
  } catch (err) {
    console.warn('[global-teardown] failed to parse run-meta.json:', err);
    return;
  }

  const admin = ACCOUNTS.admin;
  const ctx = await request.newContext({
    baseURL: BASE_URL,
    extraHTTPHeaders: { 'ngrok-skip-browser-warning': '1' },
  });
  try {
    const loginRes = await ctx.post('/api/v1/auth/login', {
      data: { email: admin.email, password: admin.password },
    });
    if (!loginRes.ok()) {
      console.warn(
        `[global-teardown] super-admin login failed (${loginRes.status()}), skip cleanup`
      );
      return;
    }

    const tasks: Array<{ role: string; endpoint: string }> = [];
    if (meta.entities.employee) {
      tasks.push({ role: 'employee', endpoint: `/api/v1/employees/${meta.entities.employee.id}` });
    }
    if (meta.entities.teacher) {
      tasks.push({ role: 'teacher', endpoint: `/api/v1/teachers/${meta.entities.teacher.id}` });
    }
    if (meta.entities.student) {
      tasks.push({ role: 'student', endpoint: `/api/v1/students/${meta.entities.student.id}` });
    }

    for (const t of tasks) {
      try {
        const res = await ctx.delete(t.endpoint);
        if (res.ok()) {
          console.log(`[global-teardown] deleted ${t.role}: ${t.endpoint}`);
        } else {
          const body = await res.text();
          console.warn(`[global-teardown] delete ${t.role} failed: ${res.status()} ${body}`);
        }
      } catch (err) {
        console.warn(`[global-teardown] delete ${t.role} error:`, err);
      }
    }
  } finally {
    await ctx.dispose();
    // 清掉 meta，避免下次 setup 撞到 stale state
    try {
      fs.unlinkSync(META_FILE);
    } catch {
      /* noop */
    }
  }

  console.log(`[global-teardown] runId=${meta.runId} cleanup done`);
}

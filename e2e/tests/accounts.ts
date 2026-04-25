import crypto from 'crypto';
import fs from 'fs';
import path from 'path';

export type Role = 'admin' | 'employee' | 'teacher' | 'student';

export interface Account {
  role: Role;
  email: string;
  password: string;
  storageStateFile: string;
}

const META_FILE = path.resolve(__dirname, '..', '.auth', 'run-meta.json');

function generateRunId(): string {
  const ts = new Date()
    .toISOString()
    .replace(/[-:T.Z]/g, '')
    .slice(0, 14); // YYYYMMDDHHMMSS
  const rand = crypto.randomBytes(2).toString('hex');
  return `${ts}-${rand}`;
}

/**
 * RUN_ID 取得順序：
 *   1) E2E_RUN_ID env (允許從外部固定 runId)
 *   2) .auth/run-meta.json 已存在的 runId (workers / teardown 走這條)
 *   3) 自行產生新的 (global-setup 第一次跑)
 *
 * global-setup 會在開頭刪除 stale meta 檔，所以 setup 那次必走 (3)；
 * 完成後寫入 meta，後續 workers 一律走 (2)，達到全跑共用同一個 runId。
 */
function resolveRunId(): string {
  if (process.env.E2E_RUN_ID) return process.env.E2E_RUN_ID;
  try {
    if (fs.existsSync(META_FILE)) {
      const meta = JSON.parse(fs.readFileSync(META_FILE, 'utf8'));
      if (meta?.runId) return meta.runId;
    }
  } catch {
    /* ignore */
  }
  return generateRunId();
}

export const RUN_ID: string = resolveRunId();

const superEmail =
  process.env.E2E_ADMIN_EMAIL || process.env.SUPER_ADMIN_EMAIL || 'eopAdmin@example.com';
const superPassword =
  process.env.E2E_ADMIN_PASSWORD || process.env.SUPER_ADMIN_PASSWORD || 'eopsuper888';

const bootstrapPassword = process.env.E2E_BOOTSTRAP_PASSWORD || 'E2eTestPwd123!';
const emailDomain = process.env.E2E_EMAIL_DOMAIN || 'eop-test.com';

export const ACCOUNTS: Record<Role, Account> = {
  admin: {
    role: 'admin',
    email: superEmail,
    password: superPassword,
    storageStateFile: '.auth/admin.json',
  },
  employee: {
    role: 'employee',
    email: `e2e-employee-${RUN_ID}@${emailDomain}`,
    password: bootstrapPassword,
    storageStateFile: '.auth/employee.json',
  },
  teacher: {
    role: 'teacher',
    email: `e2e-teacher-${RUN_ID}@${emailDomain}`,
    password: bootstrapPassword,
    storageStateFile: '.auth/teacher.json',
  },
  student: {
    role: 'student',
    email: `e2e-student-${RUN_ID}@${emailDomain}`,
    password: bootstrapPassword,
    storageStateFile: '.auth/student.json',
  },
};

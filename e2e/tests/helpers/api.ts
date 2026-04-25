import { request, APIRequestContext } from '@playwright/test';
import path from 'path';
import { ACCOUNTS, Role } from '../accounts';

const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost';

/**
 * 取得已登入的 APIRequestContext。
 *
 * 重要：直接重用 global-setup 預存的 storageState（cookies），不重新登入。
 *
 * 為什麼：backend `auth_service.login` 會「同帳號不可重複登入：銷毀其他 Sessions」，
 * 每次新登入都會把同帳號的舊 session 全部踢掉。如果 worker 各自重新登入，
 * 後 worker 會把前 worker 的 session 弄壞，連帶讓 storageState 失效。
 *
 * 透過共用同一份 cookies，所有 worker 都用 global-setup 建立的那一個 session。
 */
export async function getApiContext(role: Role): Promise<APIRequestContext> {
  const account = ACCOUNTS[role];
  const storageStatePath = path.resolve(__dirname, '..', '..', account.storageStateFile);

  return request.newContext({
    baseURL: BASE_URL,
    storageState: storageStatePath,
  });
}

export async function parseJson<T = unknown>(
  res: Awaited<ReturnType<APIRequestContext['get']>>
): Promise<T> {
  if (!res.ok()) {
    throw new Error(`HTTP ${res.status()}: ${await res.text()}`);
  }
  return (await res.json()) as T;
}

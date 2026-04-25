import { Page } from '@playwright/test';

/**
 * 導航到指定路徑並等到 SPA 真的落在那個 pathname 上。
 *
 * 為什麼需要這個：Vue 路由守衛在 cold start 會先 fetch /auth/me + /permissions/me
 * + 動態註冊路由，期間 URL 可能短暫卡在 /login?redirect=...。直接 goto 後立刻
 * 斷言內容容易在 parallel run 下抓到 login form。
 */
export async function gotoReady(
  page: Page,
  path: string,
  opts: { timeout?: number } = {}
): Promise<void> {
  const timeout = opts.timeout ?? 15_000;
  await page.goto(path);
  await page.waitForURL(
    (url) => {
      const u = typeof url === 'string' ? new URL(url) : url;
      return u.pathname === path.split('?')[0];
    },
    { timeout }
  );
  await page.waitForLoadState('networkidle', { timeout });
}

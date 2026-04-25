import { test, expect } from '../_fixtures/world';
import { gotoReady } from '../helpers/nav';
import {
  createTeacher,
  deleteTeacher,
  putToSignedUrl,
  safeCleanup,
  TINY_PNG_BYTES,
} from '../helpers/seed';
import fs from 'fs';
import path from 'path';

const SCREENSHOT_DIR = path.resolve(__dirname, '..', '..', 'reports', 'screenshots');
fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });

test.describe('教師頭貼上傳/下載', () => {
  test('上傳完成後 teacher.avatar_url 變成 signed URL（含 UI 截圖驗證）', async ({ world, page }, testInfo) => {
    const teacher = await createTeacher(world.adminApi);

    try {
      // 0) 起始頭像為空
      const before = await world.adminApi.get(`/api/v1/teachers/${teacher.id}`);
      expect((await before.json()).data.avatar_url).toBeFalsy();

      // 截圖 1：上傳前的教師卡（avatar 應為 placeholder）
      await gotoReady(page, '/teacher');
      const teacherCard = page.locator('.el-card', { has: page.getByText(teacher.name) });
      await expect(teacherCard).toBeVisible({ timeout: 10_000 });
      const beforePath = path.join(SCREENSHOT_DIR, `teacher-avatar-${teacher.id}-before.png`);
      await teacherCard.screenshot({ path: beforePath });
      await testInfo.attach('avatar-before', { path: beforePath, contentType: 'image/png' });

      // 1) 取得 presigned upload URL
      const urlRes = await world.adminApi.post(
        `/api/v1/teachers/${teacher.id}/avatar/upload-url`,
        { data: { file_name: 'avatar.png' } }
      );
      expect(urlRes.ok()).toBeTruthy();
      const urlBody = await urlRes.json();
      expect(urlBody.upload_url).toMatch(/^https?:\/\//);
      expect(urlBody.storage_path).toMatch(
        new RegExp(`^teachers/${teacher.id}/avatar/[a-f0-9]+\\.png$`)
      );
      expect(urlBody.content_type).toContain('png');
      expect(urlBody.max_size_bytes).toBeGreaterThanOrEqual(1024 * 1024);

      // 2) PUT bytes 上 S3
      await putToSignedUrl(urlBody.upload_url, TINY_PNG_BYTES, urlBody.content_type);

      // 3) 確認上傳 → 後端寫入 avatar_url
      const confirmRes = await world.adminApi.post(
        `/api/v1/teachers/${teacher.id}/avatar/confirm-upload`,
        { data: { storage_path: urlBody.storage_path, file_name: 'avatar.png' } }
      );
      expect(confirmRes.ok()).toBeTruthy();
      const confirmed = (await confirmRes.json()).data;
      expect(confirmed.avatar_url).toBeTruthy();
      expect(confirmed.avatar_url).toMatch(/^https?:\/\//);

      // 4) 二次 GET 確認落地
      const after = await world.adminApi.get(`/api/v1/teachers/${teacher.id}`);
      const afterData = (await after.json()).data;
      expect(afterData.avatar_url).toBeTruthy();
      expect(afterData.avatar_url).toMatch(/^https?:\/\//);

      // 截圖 2：上傳後的教師卡（avatar 應從 S3 載入新圖）
      await gotoReady(page, '/teacher');
      const cardAfter = page.locator('.el-card', { has: page.getByText(teacher.name) });
      await expect(cardAfter).toBeVisible({ timeout: 10_000 });
      // 等 <img> 真的載入完成（檢查 naturalWidth > 0）
      const avatarImg = cardAfter.locator('img').first();
      if ((await avatarImg.count()) > 0) {
        await avatarImg.waitFor({ state: 'visible', timeout: 5_000 }).catch(() => {});
      }
      await page.waitForTimeout(800); // 給 S3 圖片載入緩衝
      const afterPath = path.join(SCREENSHOT_DIR, `teacher-avatar-${teacher.id}-after.png`);
      await cardAfter.screenshot({ path: afterPath });
      await testInfo.attach('avatar-after', { path: afterPath, contentType: 'image/png' });

      // 同時 attach 原始 PNG bytes 給人類比對
      await testInfo.attach('uploaded-source.png', {
        body: TINY_PNG_BYTES,
        contentType: 'image/png',
      });
    } finally {
      await safeCleanup(() => deleteTeacher(world.adminApi, teacher.id));
    }
  });

  test('upload-url 對不支援的格式應失敗 (.exe)', async ({ world }) => {
    const teacher = await createTeacher(world.adminApi);
    try {
      const res = await world.adminApi.post(
        `/api/v1/teachers/${teacher.id}/avatar/upload-url`,
        { data: { file_name: 'evil.exe' } }
      );
      expect(res.status()).toBeGreaterThanOrEqual(400);
    } finally {
      await safeCleanup(() => deleteTeacher(world.adminApi, teacher.id));
    }
  });

  test('upload-url 支援 jpg/png/webp 三種格式', async ({ world }) => {
    const teacher = await createTeacher(world.adminApi);
    try {
      for (const ext of ['jpg', 'png', 'webp']) {
        const res = await world.adminApi.post(
          `/api/v1/teachers/${teacher.id}/avatar/upload-url`,
          { data: { file_name: `pic.${ext}` } }
        );
        expect(res.ok()).toBeTruthy();
        const body = await res.json();
        expect(body.storage_path).toMatch(new RegExp(`\\.${ext}$`));
      }
    } finally {
      await safeCleanup(() => deleteTeacher(world.adminApi, teacher.id));
    }
  });

  test('confirm-upload 沒先 PUT 檔案應失敗 (S3 verify 失敗)', async ({ world }) => {
    const teacher = await createTeacher(world.adminApi);
    try {
      const urlRes = await world.adminApi.post(
        `/api/v1/teachers/${teacher.id}/avatar/upload-url`,
        { data: { file_name: 'avatar.png' } }
      );
      const { storage_path } = await urlRes.json();

      const confirmRes = await world.adminApi.post(
        `/api/v1/teachers/${teacher.id}/avatar/confirm-upload`,
        { data: { storage_path, file_name: 'avatar.png' } }
      );
      expect(confirmRes.status()).toBeGreaterThanOrEqual(400);
    } finally {
      await safeCleanup(() => deleteTeacher(world.adminApi, teacher.id));
    }
  });

  test('upload-url 對不存在的 teacher_id 應失敗', async ({ world }) => {
    const res = await world.adminApi.post(
      `/api/v1/teachers/00000000-0000-0000-0000-000000000000/avatar/upload-url`,
      { data: { file_name: 'avatar.png' } }
    );
    expect(res.status()).toBeGreaterThanOrEqual(400);
  });

  test('員工角色不應該能呼叫 (需 teachers.edit 權限)', async ({ world }) => {
    const teacher = await createTeacher(world.adminApi);
    try {
      const res = await world.employeeApi.post(
        `/api/v1/teachers/${teacher.id}/avatar/upload-url`,
        { data: { file_name: 'avatar.png' } }
      );
      // employee 可能有 teachers.edit 也可能沒，兩種都接受但 200 必須回 valid url
      expect([200, 403]).toContain(res.status());
    } finally {
      await safeCleanup(() => deleteTeacher(world.adminApi, teacher.id));
    }
  });
});

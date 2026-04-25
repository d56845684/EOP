import { test, expect } from '../_fixtures/world';
import {
  createTeacher,
  createTeacherContract,
  deleteTeacher,
  deleteTeacherContract,
  putToSignedUrl,
  safeCleanup,
  TINY_PDF_BYTES,
} from '../helpers/seed';

test.describe('教師合約檔案上傳/下載 + 狀態變更', () => {
  test('上傳完成後 contract_status 從 pending 變 active，並可拿到 download URL', async ({ world }) => {
    const teacher = await createTeacher(world.adminApi);
    const contract = await createTeacherContract(world.adminApi, {
      teacher_id: teacher.id,
      contract_status: 'pending', // 起始 pending，等上傳完成才 active
    });

    try {
      // 0) 確認起始狀態是 pending
      const before = await world.adminApi.get(`/api/v1/teacher-contracts/${contract.id}`);
      expect((await before.json()).data.contract_status).toBe('pending');

      // 1) 取得 presigned upload URL
      const urlRes = await world.adminApi.post(
        `/api/v1/teacher-contracts/${contract.id}/upload-url`
      );
      expect(urlRes.ok()).toBeTruthy();
      const urlBody = await urlRes.json();
      expect(urlBody.upload_url).toMatch(/^https?:\/\//);
      expect(urlBody.storage_path).toMatch(/^teacher-contracts\/[a-f0-9-]+\/[a-f0-9]+\.pdf$/);
      expect(urlBody.content_type).toBe('application/pdf');

      // 2) PUT bytes 到 S3
      await putToSignedUrl(urlBody.upload_url, TINY_PDF_BYTES, urlBody.content_type);

      // 3) 確認上傳 → 後端應更新檔案資訊 + 狀態 active
      const confirmRes = await world.adminApi.post(
        `/api/v1/teacher-contracts/${contract.id}/confirm-upload`,
        {
          data: { storage_path: urlBody.storage_path, file_name: 'e2e-teacher-contract.pdf' },
        }
      );
      expect(confirmRes.ok()).toBeTruthy();
      const confirmed = (await confirmRes.json()).data;

      // 核心驗證：狀態真的變了
      expect(confirmed.contract_status).toBe('active');
      expect(confirmed.contract_file_path).toBe(urlBody.storage_path);
      expect(confirmed.contract_file_name).toBe('e2e-teacher-contract.pdf');
      expect(confirmed.contract_file_uploaded_at).toBeTruthy();

      // 4) 再 GET 一次 DB 雙重確認狀態落地
      const after = await world.adminApi.get(`/api/v1/teacher-contracts/${contract.id}`);
      const afterBody = (await after.json()).data;
      expect(afterBody.contract_status).toBe('active');
      expect(afterBody.contract_file_path).toBe(urlBody.storage_path);

      // 5) 拿 download URL
      const dlRes = await world.adminApi.get(
        `/api/v1/teacher-contracts/${contract.id}/download-url`
      );
      expect(dlRes.ok()).toBeTruthy();
      const dlBody = await dlRes.json();
      expect(dlBody.download_url).toMatch(/^https?:\/\//);
      expect(dlBody.file_name).toBe('e2e-teacher-contract.pdf');
    } finally {
      await safeCleanup(() => deleteTeacherContract(world.adminApi, contract.id));
      await safeCleanup(() => deleteTeacher(world.adminApi, teacher.id));
    }
  });

  test('confirm-upload 沒先 PUT 檔案應失敗 (S3 找不到物件)', async ({ world }) => {
    const teacher = await createTeacher(world.adminApi);
    const contract = await createTeacherContract(world.adminApi, {
      teacher_id: teacher.id,
      contract_status: 'pending',
    });

    try {
      const urlRes = await world.adminApi.post(
        `/api/v1/teacher-contracts/${contract.id}/upload-url`
      );
      const { storage_path } = await urlRes.json();

      // 直接 confirm，跳過 PUT
      const confirmRes = await world.adminApi.post(
        `/api/v1/teacher-contracts/${contract.id}/confirm-upload`,
        { data: { storage_path, file_name: 'should-fail.pdf' } }
      );
      expect(confirmRes.status()).toBeGreaterThanOrEqual(400);
    } finally {
      await safeCleanup(() => deleteTeacherContract(world.adminApi, contract.id));
      await safeCleanup(() => deleteTeacher(world.adminApi, teacher.id));
    }
  });

  test('confirm-upload 用偽造的 storage_path 應失敗', async ({ world }) => {
    const teacher = await createTeacher(world.adminApi);
    const contract = await createTeacherContract(world.adminApi, {
      teacher_id: teacher.id,
      contract_status: 'pending',
    });

    try {
      const res = await world.adminApi.post(
        `/api/v1/teacher-contracts/${contract.id}/confirm-upload`,
        {
          data: {
            storage_path: 'malicious/path/../../etc/passwd',
            file_name: 'evil.pdf',
          },
        }
      );
      expect(res.status()).toBeGreaterThanOrEqual(400);
    } finally {
      await safeCleanup(() => deleteTeacherContract(world.adminApi, contract.id));
      await safeCleanup(() => deleteTeacher(world.adminApi, teacher.id));
    }
  });

  test('沒有檔案時 GET download-url 應失敗', async ({ world }) => {
    const teacher = await createTeacher(world.adminApi);
    const contract = await createTeacherContract(world.adminApi, {
      teacher_id: teacher.id,
      contract_status: 'pending',
    });

    try {
      const res = await world.adminApi.get(
        `/api/v1/teacher-contracts/${contract.id}/download-url`
      );
      expect(res.status()).toBeGreaterThanOrEqual(400);
    } finally {
      await safeCleanup(() => deleteTeacherContract(world.adminApi, contract.id));
      await safeCleanup(() => deleteTeacher(world.adminApi, teacher.id));
    }
  });
});

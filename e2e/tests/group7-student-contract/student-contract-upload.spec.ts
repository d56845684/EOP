import { test, expect } from '../_fixtures/world';
import {
  createStudent,
  createStudentContract,
  deleteStudent,
  deleteStudentContract,
  putToSignedUrl,
  safeCleanup,
  TINY_PDF_BYTES,
} from '../helpers/seed';

test.describe('學生合約檔案上傳/下載 + 狀態變更', () => {
  test('上傳完成後 contract_status 從 pending 變 active，並可拿到 download URL', async ({ world }) => {
    const student = await createStudent(world.adminApi, { student_type: 'formal' });
    const contract = await createStudentContract(world.adminApi, {
      student_id: student.id,
      contract_status: 'pending',
    });

    try {
      // 0) 起始狀態
      const before = await world.adminApi.get(`/api/v1/student-contracts/${contract.id}`);
      expect((await before.json()).data.contract_status).toBe('pending');

      // 1) 取得 upload URL
      const urlRes = await world.adminApi.post(
        `/api/v1/student-contracts/${contract.id}/upload-url`
      );
      expect(urlRes.ok()).toBeTruthy();
      const urlBody = await urlRes.json();
      expect(urlBody.upload_url).toMatch(/^https?:\/\//);
      expect(urlBody.storage_path).toMatch(/^student-contracts\/[a-f0-9-]+\/[a-f0-9]+\.pdf$/);

      // 2) PUT 到 S3
      await putToSignedUrl(urlBody.upload_url, TINY_PDF_BYTES, urlBody.content_type);

      // 3) 確認上傳 → 狀態變 active
      const confirmRes = await world.adminApi.post(
        `/api/v1/student-contracts/${contract.id}/confirm-upload`,
        {
          data: { storage_path: urlBody.storage_path, file_name: 'e2e-student-contract.pdf' },
        }
      );
      expect(confirmRes.ok()).toBeTruthy();
      const confirmed = (await confirmRes.json()).data;
      expect(confirmed.contract_status).toBe('active');
      expect(confirmed.contract_file_path).toBe(urlBody.storage_path);
      expect(confirmed.contract_file_name).toBe('e2e-student-contract.pdf');
      expect(confirmed.contract_file_uploaded_at).toBeTruthy();

      // 4) DB 二次確認
      const after = await world.adminApi.get(`/api/v1/student-contracts/${contract.id}`);
      expect((await after.json()).data.contract_status).toBe('active');

      // 5) Download URL
      const dlRes = await world.adminApi.get(
        `/api/v1/student-contracts/${contract.id}/download-url`
      );
      expect(dlRes.ok()).toBeTruthy();
      expect((await dlRes.json()).download_url).toMatch(/^https?:\/\//);
    } finally {
      await safeCleanup(() => deleteStudentContract(world.adminApi, contract.id));
      await safeCleanup(() => deleteStudent(world.adminApi, student.id));
    }
  });

  test('upload-url 支援 file_ext=docx', async ({ world }) => {
    const student = await createStudent(world.adminApi, { student_type: 'formal' });
    const contract = await createStudentContract(world.adminApi, {
      student_id: student.id,
      contract_status: 'pending',
    });

    try {
      const res = await world.adminApi.post(
        `/api/v1/student-contracts/${contract.id}/upload-url?file_ext=docx`
      );
      expect(res.ok()).toBeTruthy();
      const body = await res.json();
      expect(body.storage_path).toMatch(/\.docx$/);
      expect(body.content_type).toContain('word');
    } finally {
      await safeCleanup(() => deleteStudentContract(world.adminApi, contract.id));
      await safeCleanup(() => deleteStudent(world.adminApi, student.id));
    }
  });

  test('upload-url 不支援的格式應失敗', async ({ world }) => {
    const student = await createStudent(world.adminApi, { student_type: 'formal' });
    const contract = await createStudentContract(world.adminApi, {
      student_id: student.id,
      contract_status: 'pending',
    });

    try {
      const res = await world.adminApi.post(
        `/api/v1/student-contracts/${contract.id}/upload-url?file_ext=exe`
      );
      expect(res.status()).toBeGreaterThanOrEqual(400);
    } finally {
      await safeCleanup(() => deleteStudentContract(world.adminApi, contract.id));
      await safeCleanup(() => deleteStudent(world.adminApi, student.id));
    }
  });

  test('confirm-upload 用偽造路徑應失敗', async ({ world }) => {
    const student = await createStudent(world.adminApi, { student_type: 'formal' });
    const contract = await createStudentContract(world.adminApi, {
      student_id: student.id,
      contract_status: 'pending',
    });

    try {
      const res = await world.adminApi.post(
        `/api/v1/student-contracts/${contract.id}/confirm-upload`,
        {
          data: {
            storage_path: '../etc/passwd',
            file_name: 'evil.pdf',
          },
        }
      );
      expect(res.status()).toBeGreaterThanOrEqual(400);
    } finally {
      await safeCleanup(() => deleteStudentContract(world.adminApi, contract.id));
      await safeCleanup(() => deleteStudent(world.adminApi, student.id));
    }
  });
});

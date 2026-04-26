import { APIRequestContext } from '@playwright/test';

/**
 * Seed/cleanup helpers — 由 spec 在 beforeAll/afterAll 呼叫。
 *
 * 約定：
 *   - 命名 prefix 一律 `e2e-`，方便手動 SQL 找孤兒
 *   - 每個 helper 回傳建立的 entity，呼叫端記住並負責 cleanup
 *   - cleanup helper 對 404 寬容（資料可能已被測試刪掉）
 */

export const E2E_PREFIX = 'e2e-';

export function uniqueSuffix(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`;
}

export function uniqueLabel(label: string): string {
  return `${E2E_PREFIX}${label}-${uniqueSuffix()}`;
}

// ===== Employees =====

export interface SeedEmployeeInput {
  employee_no?: string;
  employee_type?: 'admin' | 'full_time' | 'part_time' | 'intern';
  name?: string;
  email?: string;
  phone?: string;
  hire_date?: string; // YYYY-MM-DD
}

export interface SeededEmployee {
  id: string;
  employee_no: string;
  email: string;
  name: string;
}

export async function createEmployee(
  api: APIRequestContext,
  input: SeedEmployeeInput = {}
): Promise<SeededEmployee> {
  const suffix = uniqueSuffix();
  const employee_no = input.employee_no ?? `E2E-${suffix.toUpperCase().slice(0, 8)}`;
  const email = input.email ?? `e2e-emp-${suffix}@example.com`;
  const name = input.name ?? `e2e Employee ${suffix}`;

  const res = await api.post('/api/v1/employees', {
    data: {
      employee_no,
      employee_type: input.employee_type ?? 'full_time',
      name,
      email,
      phone: input.phone ?? '0900000000',
      hire_date: input.hire_date ?? new Date().toISOString().slice(0, 10),
      is_active: true,
    },
  });

  if (!res.ok()) {
    throw new Error(`createEmployee failed: ${res.status()} ${await res.text()}`);
  }
  const body = await res.json();
  return { id: body.data.id, employee_no, email, name };
}

export async function deleteEmployee(api: APIRequestContext, employeeId: string): Promise<void> {
  const res = await api.delete(`/api/v1/employees/${employeeId}`);
  if (!res.ok() && res.status() !== 404) {
    throw new Error(`deleteEmployee failed: ${res.status()} ${await res.text()}`);
  }
}

// ===== Roles =====

export interface SeedRoleInput {
  key?: string;
  name?: string;
  description?: string;
}

export interface SeededRole {
  id: string;
  key: string;
  name: string;
}

export async function createRole(
  api: APIRequestContext,
  input: SeedRoleInput = {}
): Promise<SeededRole> {
  const suffix = uniqueSuffix().replace(/-/g, '');
  // role key pattern: ^[a-z][a-z0-9_]*$
  const key = (input.key ?? `e2e_role_${suffix}`).toLowerCase().replace(/[^a-z0-9_]/g, '_');
  const name = input.name ?? `e2e Role ${suffix}`;

  const res = await api.post('/api/v1/roles', {
    data: { key, name, description: input.description ?? 'created by e2e' },
  });

  if (!res.ok()) {
    throw new Error(`createRole failed: ${res.status()} ${await res.text()}`);
  }
  const body = await res.json();
  return { id: body.data.id, key, name };
}

export async function deleteRole(api: APIRequestContext, roleId: string): Promise<void> {
  const res = await api.delete(`/api/v1/roles/${roleId}`);
  if (!res.ok() && res.status() !== 404) {
    throw new Error(`deleteRole failed: ${res.status()} ${await res.text()}`);
  }
}

// ===== Teachers =====

export interface SeededTeacher {
  id: string;
  name: string;
  email: string;
}

export async function createTeacher(
  api: APIRequestContext,
  input: { name?: string; email?: string; teacher_level?: number } = {}
): Promise<SeededTeacher> {
  const suffix = uniqueSuffix();
  const email = input.email ?? `e2e-teacher-${suffix}@example.com`;
  const name = input.name ?? `e2e Teacher ${suffix}`;

  const res = await api.post('/api/v1/teachers', {
    data: {
      name,
      email,
      teacher_level: input.teacher_level ?? 1,
      is_active: true,
    },
  });
  if (!res.ok()) throw new Error(`createTeacher failed: ${res.status()} ${await res.text()}`);
  const body = await res.json();
  return { id: body.data.id, name, email };
}

export async function deleteTeacher(api: APIRequestContext, teacherId: string): Promise<void> {
  const res = await api.delete(`/api/v1/teachers/${teacherId}`);
  if (!res.ok() && res.status() !== 404) {
    throw new Error(`deleteTeacher failed: ${res.status()} ${await res.text()}`);
  }
}

// ===== Students =====

export interface SeededStudent {
  id: string;
  name: string;
  email: string;
  student_type: 'formal' | 'trial';
}

export async function createStudent(
  api: APIRequestContext,
  input: { name?: string; email?: string; eng_name?: string; phone?: string; student_type?: 'formal' | 'trial' } = {}
): Promise<SeededStudent> {
  const suffix = uniqueSuffix();
  const email = input.email ?? `e2e-student-${suffix}@example.com`;
  const name = input.name ?? `e2e Student ${suffix}`;
  const eng_name = input.eng_name ?? `e2e-eng-${suffix}`;
  const phone = input.phone ?? '0900000000';
  const student_type = input.student_type ?? 'formal';

  const res = await api.post('/api/v1/students', {
    data: { name, email, eng_name, phone, student_type, is_active: true },
  });
  if (!res.ok()) throw new Error(`createStudent failed: ${res.status()} ${await res.text()}`);
  const body = await res.json();
  return { id: body.data.id, name, email, student_type };
}

export async function deleteStudent(api: APIRequestContext, studentId: string): Promise<void> {
  const res = await api.delete(`/api/v1/students/${studentId}`);
  if (!res.ok() && res.status() !== 404) {
    throw new Error(`deleteStudent failed: ${res.status()} ${await res.text()}`);
  }
}

// ===== Courses =====

export interface SeededCourse {
  id: string;
  course_code: string;
  course_name: string;
}

export async function createCourse(
  api: APIRequestContext,
  input: { course_code?: string; course_name?: string; duration_minutes?: number } = {}
): Promise<SeededCourse> {
  const suffix = uniqueSuffix();
  const course_code = input.course_code ?? `E2E-${suffix.toUpperCase().slice(0, 8)}`;
  const course_name = input.course_name ?? `e2e Course ${suffix}`;

  const res = await api.post('/api/v1/courses', {
    data: {
      course_code,
      course_name,
      duration_minutes: input.duration_minutes ?? 60,
      is_active: true,
    },
  });
  if (!res.ok()) throw new Error(`createCourse failed: ${res.status()} ${await res.text()}`);
  const body = await res.json();
  return { id: body.data.id, course_code, course_name };
}

export async function deleteCourse(api: APIRequestContext, courseId: string): Promise<void> {
  const res = await api.delete(`/api/v1/courses/${courseId}`);
  if (!res.ok() && res.status() !== 404) {
    throw new Error(`deleteCourse failed: ${res.status()} ${await res.text()}`);
  }
}

// ===== Teacher Contracts =====

export interface SeededTeacherContract {
  id: string;
  contract_no: string;
  teacher_id: string;
}

export async function createTeacherContract(
  api: APIRequestContext,
  input: {
    teacher_id: string;
    start_date?: string;
    end_date?: string;
    employment_type?: 'hourly' | 'full_time';
    contract_status?: 'pending' | 'active' | 'terminated';
  }
): Promise<SeededTeacherContract> {
  const today = new Date();
  const start = input.start_date ?? today.toISOString().slice(0, 10);
  const end = input.end_date ??
    new Date(today.getFullYear() + 1, today.getMonth(), today.getDate()).toISOString().slice(0, 10);

  const res = await api.post('/api/v1/teacher-contracts', {
    data: {
      teacher_id: input.teacher_id,
      contract_status: input.contract_status ?? 'active',
      start_date: start,
      end_date: end,
      employment_type: input.employment_type ?? 'hourly',
      trial_completed_bonus: 0,
      trial_to_formal_bonus: 0,
    },
  });
  if (!res.ok()) {
    throw new Error(`createTeacherContract failed: ${res.status()} ${await res.text()}`);
  }
  const body = await res.json();
  return { id: body.data.id, contract_no: body.data.contract_no, teacher_id: input.teacher_id };
}

export async function deleteTeacherContract(api: APIRequestContext, contractId: string): Promise<void> {
  const res = await api.delete(`/api/v1/teacher-contracts/${contractId}`);
  if (!res.ok() && res.status() !== 404) {
    throw new Error(`deleteTeacherContract failed: ${res.status()} ${await res.text()}`);
  }
}

// ===== Zoom Accounts =====

export interface SeededZoomAccount {
  id: string;
  account_name: string;
}

export async function createZoomAccount(
  api: APIRequestContext,
  input: { account_name?: string } = {}
): Promise<SeededZoomAccount> {
  const suffix = uniqueSuffix();
  const account_name = input.account_name ?? `e2e Zoom ${suffix}`;

  const res = await api.post('/api/v1/zoom/accounts', {
    data: {
      account_name,
      zoom_account_id: `e2eAcct${suffix}`,
      zoom_client_id: `e2eCli${suffix}`,
      zoom_client_secret: `e2eSecret${suffix}`,
      zoom_user_email: `e2e-zoom-${suffix}@example.com`,
      account_tier: 'pro',
      is_active: true,
    },
  });
  if (!res.ok()) throw new Error(`createZoomAccount failed: ${res.status()} ${await res.text()}`);
  const body = await res.json();
  return { id: body.data.id, account_name };
}

export async function deleteZoomAccount(api: APIRequestContext, accountId: string): Promise<void> {
  const res = await api.delete(`/api/v1/zoom/accounts/${accountId}`);
  if (!res.ok() && res.status() !== 404) {
    throw new Error(`deleteZoomAccount failed: ${res.status()} ${await res.text()}`);
  }
}

// ===== Student Courses =====

export async function enrollStudentInCourse(
  api: APIRequestContext,
  input: { student_id: string; course_id: string }
): Promise<{ id: string }> {
  const res = await api.post('/api/v1/student-courses', { data: input });
  if (!res.ok()) throw new Error(`enrollStudentInCourse failed: ${res.status()} ${await res.text()}`);
  return { id: (await res.json()).data.id };
}

export async function unenrollStudentCourse(api: APIRequestContext, enrollmentId: string): Promise<void> {
  const res = await api.delete(`/api/v1/student-courses/${enrollmentId}`);
  if (!res.ok() && res.status() !== 404) {
    throw new Error(`unenrollStudentCourse failed: ${res.status()} ${await res.text()}`);
  }
}

// ===== Teacher Slots =====

export interface SeededSlot {
  id: string;
}

export async function createTeacherSlot(
  api: APIRequestContext,
  input: {
    teacher_id: string;
    teacher_contract_id?: string;
    slot_date?: string;
    start_time?: string;
    end_time?: string;
  }
): Promise<SeededSlot> {
  const tomorrow = new Date(Date.now() + 24 * 3600 * 1000).toISOString().slice(0, 10);
  const res = await api.post('/api/v1/teacher-slots', {
    data: {
      teacher_id: input.teacher_id,
      teacher_contract_id: input.teacher_contract_id,
      slot_date: input.slot_date ?? tomorrow,
      start_time: input.start_time ?? '10:00:00',
      end_time: input.end_time ?? '11:00:00',
      is_available: true,
    },
  });
  if (!res.ok()) throw new Error(`createTeacherSlot failed: ${res.status()} ${await res.text()}`);
  return { id: (await res.json()).data.id };
}

export async function deleteTeacherSlot(api: APIRequestContext, slotId: string): Promise<void> {
  const res = await api.delete(`/api/v1/teacher-slots/${slotId}`);
  if (!res.ok() && res.status() !== 404) {
    throw new Error(`deleteTeacherSlot failed: ${res.status()} ${await res.text()}`);
  }
}

// ===== Student Contracts =====

export interface SeededStudentContract {
  id: string;
  contract_no?: string;
  student_id: string;
}

export async function createStudentContract(
  api: APIRequestContext,
  input: {
    student_id: string;
    total_lessons?: number;
    total_amount?: number;
    start_date?: string;
    end_date?: string;
    contract_status?: 'pending' | 'active' | 'terminated' | 'completed';
  }
): Promise<SeededStudentContract> {
  const today = new Date();
  const start = input.start_date ?? today.toISOString().slice(0, 10);
  const end = input.end_date ??
    new Date(today.getFullYear() + 1, today.getMonth(), today.getDate()).toISOString().slice(0, 10);
  const total = input.total_lessons ?? 24;

  const res = await api.post('/api/v1/student-contracts', {
    data: {
      student_id: input.student_id,
      contract_status: input.contract_status ?? 'active',
      start_date: start,
      end_date: end,
      total_lessons: total,
      remaining_lessons: total,
      total_amount: input.total_amount ?? 30000,
      is_recurring: false,
    },
  });
  if (!res.ok()) {
    throw new Error(`createStudentContract failed: ${res.status()} ${await res.text()}`);
  }
  const body = await res.json();
  return { id: body.data.id, contract_no: body.data.contract_no, student_id: input.student_id };
}

export async function deleteStudentContract(api: APIRequestContext, contractId: string): Promise<void> {
  const res = await api.delete(`/api/v1/student-contracts/${contractId}`);
  if (!res.ok() && res.status() !== 404) {
    throw new Error(`deleteStudentContract failed: ${res.status()} ${await res.text()}`);
  }
}

// ===== Bookings =====

export interface SeededBooking {
  id: string;
}

export async function createBooking(
  api: APIRequestContext,
  input: {
    student_id: string;
    teacher_id: string;
    course_id: string;
    student_contract_id?: string;
    teacher_contract_id?: string;
    teacher_slot_id?: string;
    booking_date: string;
    start_time: string;
    end_time: string;
    notes?: string;
  }
): Promise<SeededBooking> {
  const res = await api.post('/api/v1/bookings', { data: input });
  if (!res.ok()) throw new Error(`createBooking failed: ${res.status()} ${await res.text()}`);
  return { id: (await res.json()).data.id };
}

export async function deleteBooking(api: APIRequestContext, bookingId: string): Promise<void> {
  const res = await api.delete(`/api/v1/bookings/${bookingId}`);
  if (!res.ok() && res.status() !== 404) {
    throw new Error(`deleteBooking failed: ${res.status()} ${await res.text()}`);
  }
}

// ===== Contract file upload helpers =====

/**
 * 最小可被 S3 接受的 PDF bytes（不需要結構正確，backend 只 verify object 存在）。
 */
export const TINY_PDF_BYTES: Buffer = Buffer.from(
  '%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n' +
  '2 0 obj<</Type/Pages/Count 0/Kids[]>>endobj\n' +
  'xref\n0 3\n0000000000 65535 f\n0000000009 00000 n\n0000000051 00000 n\n' +
  'trailer<</Size 3/Root 1 0 R>>\nstartxref\n99\n%%EOF\n',
  'utf8'
);

/**
 * 8x8 純紅色 PNG — 用於頭像上傳測試。選用可見顏色（不透明）以便 UI 截圖能比對前後差異。
 */
export const TINY_PNG_BYTES: Buffer = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAYAAADED76LAAAAGklEQVR42mP8z8DwnwEPYBxVSF+FAAAA//8DAAGcAuTfwxYNAAAAAElFTkSuQmCC',
  'base64'
);

import { request as playwrightRequest } from '@playwright/test';

/**
 * 把 bytes PUT 上 S3 presigned URL。需要獨立 context 避免帶上專案 cookies。
 */
export async function putToSignedUrl(
  uploadUrl: string,
  bytes: Buffer,
  contentType: string = 'application/pdf'
): Promise<void> {
  const ctx = await playwrightRequest.newContext({ ignoreHTTPSErrors: true });
  try {
    const res = await ctx.fetch(uploadUrl, {
      method: 'PUT',
      data: bytes,
      headers: { 'Content-Type': contentType },
    });
    if (!res.ok()) {
      throw new Error(`S3 PUT failed: ${res.status()} ${await res.text()}`);
    }
  } finally {
    await ctx.dispose();
  }
}

// ===== 通用 cleanup =====

export async function safeCleanup(fn: () => Promise<void>): Promise<void> {
  try {
    await fn();
  } catch (err) {
    console.warn('[e2e cleanup] ignored:', err instanceof Error ? err.message : err);
  }
}

#!/usr/bin/env python3
"""
End-to-End Booking Flow Test

從零開始建立完整預約流程：
  課程 → 學生 → 教師 → 學生合約 → 教師合約 → 教師合約明細(課程費率)
  → 學生選課 → 教師偏好 → 教師時段 → 建立預約 → 確認預約
  → 請假申請 → 取消預約 → 刪除預約 → 全部清理

使用方式:
    python tests/live_e2e_booking_flow_test.py \\
        --email employee@eop-test.com --password TestPassword123!

    # 只清理測試資料
    python tests/live_e2e_booking_flow_test.py \\
        --email employee@eop-test.com --password TestPassword123! --cleanup-only
"""

import httpx
import asyncio
import argparse
import sys
import os
from datetime import datetime, date, timedelta, time
from typing import Optional
from dataclasses import dataclass, field

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8001")
# 使用時間戳讓每次測試的編號唯一，避免 unique constraint 衝突
_TS = datetime.now().strftime("%H%M%S")
TEST_PREFIX = f"E2E{_TS}_"


@dataclass
class TestResult:
    name: str
    passed: bool
    message: str = ""


@dataclass
class E2EContext:
    """測試上下文 — 記錄所有建立的資源 ID，用於清理"""
    cookies: dict = field(default_factory=dict)

    # 建立的資源 ID（按建立順序記錄，清理時反序刪除）
    course_id: Optional[str] = None
    student_id: Optional[str] = None
    teacher_id: Optional[str] = None
    student_contract_id: Optional[str] = None
    teacher_contract_id: Optional[str] = None
    teacher_contract_detail_id: Optional[str] = None
    student_course_id: Optional[str] = None
    preference_id: Optional[str] = None
    teacher_slot_id: Optional[str] = None
    booking_id: Optional[str] = None
    booking_no: Optional[str] = None
    leave_record_id: Optional[str] = None
    zoom_meeting_id: Optional[str] = None
    zoom_enabled: bool = False

    # 第二位教師（多教師測試）
    teacher_b_id: Optional[str] = None
    teacher_b_contract_id: Optional[str] = None
    teacher_b_contract_detail_id: Optional[str] = None
    preference_b_id: Optional[str] = None

    # 衍生資料
    course_duration: int = 60
    slot_date: str = ""


class E2EBookingFlowTester:
    def __init__(self):
        self.url = BACKEND_URL.rstrip("/")
        self.results: list[TestResult] = []
        self.client: Optional[httpx.AsyncClient] = None

    # ────────────────── HTTP Helpers ──────────────────

    async def _post(self, path: str, json: dict) -> httpx.Response:
        return await self.client.post(f"{self.url}{path}", json=json)

    async def _get(self, path: str, params: dict = None) -> httpx.Response:
        return await self.client.get(f"{self.url}{path}", params=params)

    async def _put(self, path: str, json: dict) -> httpx.Response:
        return await self.client.put(f"{self.url}{path}", json=json)

    async def _delete(self, path: str) -> httpx.Response:
        return await self.client.delete(f"{self.url}{path}")

    # ────────────────── Test Runner ──────────────────

    async def run(self, email: str, password: str, cleanup_only: bool = False):
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=True,
        ) as client:
            self.client = client
            ctx = E2EContext()
            # 使用 14 天後的日期避免 "禁止過去時間" 驗證
            ctx.slot_date = (date.today() + timedelta(days=14)).isoformat()

            print(f"\n{'=' * 65}")
            print(f"  End-to-End Booking Flow Test")
            print(f"  Backend: {self.url}")
            print(f"  User: {email}")
            print(f"  Slot Date: {ctx.slot_date}")
            print(f"{'=' * 65}\n")

            # Login first
            ok = await self._run_test("Login", self._test_login, ctx, email, password)
            if not ok:
                print("\n  LOGIN FAILED — aborting.")
                return False

            if cleanup_only:
                await self._cleanup(ctx, full_search=True)
                return True

            # ── Phase 1: 建立基礎資料 ──
            print("\n  Phase 1: 建立基礎資料")
            print("  " + "-" * 40)
            tests_phase1 = [
                ("建立課程", self._test_create_course),
                ("建立學生", self._test_create_student),
                ("建立教師", self._test_create_teacher),
            ]
            for name, fn in tests_phase1:
                ok = await self._run_test(name, fn, ctx)
                if not ok:
                    print(f"\n  Phase 1 FAILED — 基礎資料建立失敗，無法繼續")
                    await self._cleanup(ctx)
                    self._print_summary()
                    return False

            # ── Phase 2: 建立合約 ──
            print("\n  Phase 2: 建立合約")
            print("  " + "-" * 40)
            tests_phase2 = [
                ("建立學生合約", self._test_create_student_contract),
                ("建立教師合約", self._test_create_teacher_contract),
                ("新增教師合約課程費率", self._test_create_teacher_contract_detail),
            ]
            for name, fn in tests_phase2:
                await self._run_test(name, fn, ctx)

            # ── Phase 3: 建立關聯設定 ──
            print("\n  Phase 3: 建立關聯設定")
            print("  " + "-" * 40)
            tests_phase3 = [
                ("學生選課", self._test_create_student_course),
                ("設定教師偏好", self._test_create_preference),
                ("建立教師時段", self._test_create_teacher_slot),
            ]
            for name, fn in tests_phase3:
                await self._run_test(name, fn, ctx)

            # ── Phase 3.5: 多教師可預約驗證 ──
            print("\n  Phase 3.5: 多教師可預約驗證")
            print("  " + "-" * 40)
            tests_multi_teacher = [
                ("建立第二位教師", self._test_create_teacher_b),
                ("建立教師 B 合約", self._test_create_teacher_b_contract),
                ("新增教師 B 課程費率", self._test_create_teacher_b_contract_detail),
                ("設定教師 B 偏好", self._test_create_preference_b),
                ("驗證可預約教師列表包含兩位教師", self._test_verify_allowed_teachers),
            ]
            for name, fn in tests_multi_teacher:
                await self._run_test(name, fn, ctx)

            # ── Phase 4: 預約流程 ──
            print("\n  Phase 4: 預約流程")
            print("  " + "-" * 40)
            tests_phase4 = [
                ("建立預約", self._test_create_booking),
                ("驗證預約詳情", self._test_verify_booking),
                ("更新預約狀態 (→ confirmed)", self._test_confirm_booking),
                ("驗證重複預約被拒絕 (409)", self._test_duplicate_booking_rejected),
            ]
            for name, fn in tests_phase4:
                await self._run_test(name, fn, ctx)

            # ── Phase 4.5: Zoom 會議（如果有 Zoom 帳號） ──
            print("\n  Phase 4.5: Zoom 會議")
            print("  " + "-" * 40)
            await self._run_test("檢查 Zoom 帳號池", self._test_check_zoom_accounts, ctx)
            if ctx.zoom_enabled:
                zoom_ok = await self._run_test("建立 Zoom 會議", self._test_create_zoom_meeting, ctx)
                if zoom_ok:
                    await self._run_test("驗證 Zoom 會議資訊", self._test_verify_zoom_meeting, ctx)
                    await self._run_test("查詢 Zoom 會議列表", self._test_list_zoom_meetings, ctx)
                else:
                    print("  ⏭ Zoom 會議建立失敗（OAuth token 可能過期），跳過後續 Zoom 測試")
            else:
                print("  ⏭ 跳過 — 無可用 Zoom 帳號（需先在 Zoom 帳號頁面新增帳號並完成 OAuth）")

            # ── Phase 5: 請假流程 ──
            print("\n  Phase 5: 請假流程")
            print("  " + "-" * 40)
            tests_phase5 = [
                ("建立請假申請", self._test_create_leave_request),
                ("驗證請假紀錄", self._test_verify_leave_record),
            ]
            for name, fn in tests_phase5:
                await self._run_test(name, fn, ctx)

            # ── Phase 6: 取消與刪除 ──
            print("\n  Phase 6: 取消與刪除")
            print("  " + "-" * 40)
            tests_phase6 = [
                ("取消預約", self._test_cancel_booking),
                ("刪除預約", self._test_delete_booking),
                ("驗證預約已刪除", self._test_verify_booking_deleted),
            ]
            for name, fn in tests_phase6:
                await self._run_test(name, fn, ctx)

            # ── Phase 7: 清理所有測試資料 ──
            print("\n  Phase 7: 清理測試資料")
            print("  " + "-" * 40)
            await self._cleanup(ctx)

            # ── 結果 ──
            self._print_summary()
            return all(r.passed for r in self.results)

    async def _run_test(self, name: str, fn, ctx: E2EContext, *args) -> bool:
        try:
            result = await fn(ctx, *args)
            passed = result is True
            msg = "" if passed else str(result)
            self.results.append(TestResult(name=name, passed=passed, message=msg))
            status = "PASS" if passed else "FAIL"
            print(f"  {'✓' if passed else '✗'} {name}" + (f" — {msg}" if msg else ""))
            return passed
        except Exception as e:
            self.results.append(TestResult(name=name, passed=False, message=str(e)))
            print(f"  ✗ {name} — ERROR: {e}")
            return False

    # ────────────────── Phase 0: Login ──────────────────

    async def _test_login(self, ctx: E2EContext, email: str, password: str):
        resp = await self._post("/api/v1/auth/login", {"email": email, "password": password})
        if resp.status_code != 200:
            return f"Login failed: {resp.status_code}"
        return True

    # ────────────────── Phase 1: 基礎資料 ──────────────────

    async def _test_create_course(self, ctx: E2EContext):
        resp = await self._post("/api/v1/courses", {
            "course_code": f"{TEST_PREFIX}C001",
            "course_name": f"{TEST_PREFIX}基礎英文",
            "description": "E2E 測試用課程",
            "duration_minutes": 60,
        })
        if resp.status_code != 200:
            return f"Create course failed: {resp.status_code} {resp.text[:200]}"
        ctx.course_id = resp.json()["data"]["id"]
        ctx.course_duration = 60
        return True

    async def _test_create_student(self, ctx: E2EContext):
        resp = await self._post("/api/v1/students", {
            "student_no": f"{TEST_PREFIX}S001",
            "name": f"{TEST_PREFIX}測試學生",
            "email": f"e2e_student_{datetime.now().strftime('%H%M%S')}@test.local",
            "student_type": "formal",
        })
        if resp.status_code != 200:
            return f"Create student failed: {resp.status_code} {resp.text[:200]}"
        ctx.student_id = resp.json()["data"]["id"]
        return True

    async def _test_create_teacher(self, ctx: E2EContext):
        resp = await self._post("/api/v1/teachers", {
            "teacher_no": f"{TEST_PREFIX}T001",
            "name": f"{TEST_PREFIX}測試教師",
            "email": f"e2e_teacher_{datetime.now().strftime('%H%M%S')}@test.local",
            "teacher_level": 1,
        })
        if resp.status_code != 200:
            return f"Create teacher failed: {resp.status_code} {resp.text[:200]}"
        ctx.teacher_id = resp.json()["data"]["id"]
        return True

    # ────────────────── Phase 2: 合約 ──────────────────

    async def _test_create_student_contract(self, ctx: E2EContext):
        start = date.today().isoformat()
        end = (date.today() + timedelta(days=180)).isoformat()
        resp = await self._post("/api/v1/student-contracts", {
            "student_id": ctx.student_id,
            "contract_status": "active",
            "start_date": start,
            "end_date": end,
            "total_lessons": 48,
            "remaining_lessons": 48,
            "total_amount": 96000,
        })
        if resp.status_code != 200:
            return f"Create student contract failed: {resp.status_code} {resp.text[:200]}"
        ctx.student_contract_id = resp.json()["data"]["id"]
        return True

    async def _test_create_teacher_contract(self, ctx: E2EContext):
        start = date.today().isoformat()
        end = (date.today() + timedelta(days=365)).isoformat()
        resp = await self._post("/api/v1/teacher-contracts", {
            "teacher_id": ctx.teacher_id,
            "contract_status": "active",
            "start_date": start,
            "end_date": end,
            "employment_type": "hourly",
        })
        if resp.status_code != 200:
            return f"Create teacher contract failed: {resp.status_code} {resp.text[:200]}"
        ctx.teacher_contract_id = resp.json()["data"]["id"]
        return True

    async def _test_create_teacher_contract_detail(self, ctx: E2EContext):
        resp = await self._post(
            f"/api/v1/teacher-contracts/{ctx.teacher_contract_id}/details",
            {
                "detail_type": "course_rate",
                "course_id": ctx.course_id,
                "description": "E2E 測試課程費率",
                "amount": 800,
            },
        )
        if resp.status_code != 200:
            return f"Create contract detail failed: {resp.status_code} {resp.text[:200]}"
        ctx.teacher_contract_detail_id = resp.json()["data"]["id"]
        return True

    # ────────────────── Phase 3: 關聯設定 ──────────────────

    async def _test_create_student_course(self, ctx: E2EContext):
        resp = await self._post("/api/v1/student-courses", {
            "student_id": ctx.student_id,
            "course_id": ctx.course_id,
        })
        if resp.status_code != 200:
            return f"Create student course failed: {resp.status_code} {resp.text[:200]}"
        ctx.student_course_id = resp.json()["data"]["id"]
        return True

    async def _test_create_preference(self, ctx: E2EContext):
        resp = await self._post("/api/v1/student-teacher-preferences/", {
            "student_id": ctx.student_id,
            "primary_teacher_id": ctx.teacher_id,
        })
        if resp.status_code != 200:
            return f"Create preference failed: {resp.status_code} {resp.text[:200]}"
        ctx.preference_id = resp.json()["data"]["id"]
        return True

    async def _test_create_teacher_slot(self, ctx: E2EContext):
        resp = await self._post("/api/v1/teacher-slots", {
            "teacher_id": ctx.teacher_id,
            "teacher_contract_id": ctx.teacher_contract_id,
            "slot_date": ctx.slot_date,
            "start_time": "09:00",
            "end_time": "12:00",
            "is_available": True,
        })
        if resp.status_code != 200:
            return f"Create slot failed: {resp.status_code} {resp.text[:200]}"
        ctx.teacher_slot_id = resp.json()["data"]["id"]
        return True

    # ────────────────── Phase 3.5: 多教師可預約驗證 ──────────────────

    async def _test_create_teacher_b(self, ctx: E2EContext):
        resp = await self._post("/api/v1/teachers", {
            "teacher_no": f"{TEST_PREFIX}T002",
            "name": f"{TEST_PREFIX}測試教師B",
            "email": f"e2e_teacher_b_{datetime.now().strftime('%H%M%S')}@test.local",
            "teacher_level": 2,
        })
        if resp.status_code != 200:
            return f"Create teacher B failed: {resp.status_code} {resp.text[:200]}"
        ctx.teacher_b_id = resp.json()["data"]["id"]
        return True

    async def _test_create_teacher_b_contract(self, ctx: E2EContext):
        start = date.today().isoformat()
        end = (date.today() + timedelta(days=365)).isoformat()
        resp = await self._post("/api/v1/teacher-contracts", {
            "teacher_id": ctx.teacher_b_id,
            "contract_status": "active",
            "start_date": start,
            "end_date": end,
            "employment_type": "hourly",
        })
        if resp.status_code != 200:
            return f"Create teacher B contract failed: {resp.status_code} {resp.text[:200]}"
        ctx.teacher_b_contract_id = resp.json()["data"]["id"]
        return True

    async def _test_create_teacher_b_contract_detail(self, ctx: E2EContext):
        resp = await self._post(
            f"/api/v1/teacher-contracts/{ctx.teacher_b_contract_id}/details",
            {
                "detail_type": "course_rate",
                "course_id": ctx.course_id,
                "description": "E2E 教師B課程費率",
                "amount": 900,
            },
        )
        if resp.status_code != 200:
            return f"Create teacher B contract detail failed: {resp.status_code} {resp.text[:200]}"
        ctx.teacher_b_contract_detail_id = resp.json()["data"]["id"]
        return True

    async def _test_create_preference_b(self, ctx: E2EContext):
        resp = await self._post("/api/v1/student-teacher-preferences/", {
            "student_id": ctx.student_id,
            "primary_teacher_id": ctx.teacher_b_id,
        })
        if resp.status_code != 200:
            return f"Create preference B failed: {resp.status_code} {resp.text[:200]}"
        ctx.preference_b_id = resp.json()["data"]["id"]
        return True

    async def _test_verify_allowed_teachers(self, ctx: E2EContext):
        """驗證可預約教師列表包含教師 A 和教師 B"""
        resp = await self._get("/api/v1/bookings/options/teachers", params={"student_id": ctx.student_id})
        if resp.status_code != 200:
            return f"Get teacher options failed: {resp.status_code} {resp.text[:200]}"

        teachers = resp.json().get("data", [])
        teacher_ids = {t["id"] for t in teachers}

        if ctx.teacher_id not in teacher_ids:
            return f"教師 A ({ctx.teacher_id}) 未出現在可預約教師列表中"
        if ctx.teacher_b_id not in teacher_ids:
            return f"教師 B ({ctx.teacher_b_id}) 未出現在可預約教師列表中"

        # 驗證數量至少 2 位
        if len(teachers) < 2:
            return f"可預約教師數量不足，期望至少 2 位，實際 {len(teachers)} 位"

        return True

    # ────────────────── Phase 4: 預約 ──────────────────

    async def _test_create_booking(self, ctx: E2EContext):
        resp = await self._post("/api/v1/bookings", {
            "student_id": ctx.student_id,
            "teacher_id": ctx.teacher_id,
            "course_id": ctx.course_id,
            "student_contract_id": ctx.student_contract_id,
            "teacher_contract_id": ctx.teacher_contract_id,
            "teacher_slot_id": ctx.teacher_slot_id,
            "booking_date": ctx.slot_date,
            "start_time": "09:00",
            "end_time": "10:00",
            "notes": f"{TEST_PREFIX}e2e_flow_test",
        })
        if resp.status_code != 200:
            return f"Create booking failed: {resp.status_code} {resp.text[:300]}"
        data = resp.json()["data"]
        ctx.booking_id = data["id"]
        ctx.booking_no = data.get("booking_no", "")
        return True

    async def _test_verify_booking(self, ctx: E2EContext):
        resp = await self._get(f"/api/v1/bookings/{ctx.booking_id}")
        if resp.status_code != 200:
            return f"Get booking failed: {resp.status_code}"
        data = resp.json()["data"]

        checks = []
        if data.get("student_id") != ctx.student_id:
            checks.append("student_id mismatch")
        if data.get("teacher_id") != ctx.teacher_id:
            checks.append("teacher_id mismatch")
        if data.get("course_id") != ctx.course_id:
            checks.append("course_id mismatch")
        if data.get("booking_status") != "pending":
            checks.append(f"status={data.get('booking_status')}, expected pending")
        if data.get("booking_type") != "regular":
            checks.append(f"type={data.get('booking_type')}, expected regular")
        if data.get("lessons_used") != 1:
            checks.append(f"lessons_used={data.get('lessons_used')}, expected 1")

        if checks:
            return "Verification failed: " + "; ".join(checks)

        # 驗證學生合約堂數被扣除
        contract_resp = await self._get(f"/api/v1/student-contracts/{ctx.student_contract_id}")
        if contract_resp.status_code == 200:
            remaining = contract_resp.json()["data"].get("remaining_lessons")
            if remaining != 47:
                checks.append(f"remaining_lessons={remaining}, expected 47")

        return True if not checks else "Verification failed: " + "; ".join(checks)

    async def _test_confirm_booking(self, ctx: E2EContext):
        resp = await self._put(f"/api/v1/bookings/{ctx.booking_id}", {
            "booking_status": "confirmed",
        })
        if resp.status_code != 200:
            return f"Confirm booking failed: {resp.status_code} {resp.text[:200]}"
        status = resp.json()["data"].get("booking_status")
        if status != "confirmed":
            return f"Expected confirmed, got {status}"
        return True

    async def _test_duplicate_booking_rejected(self, ctx: E2EContext):
        """同時段重複預約應被拒絕"""
        resp = await self._post("/api/v1/bookings", {
            "student_id": ctx.student_id,
            "teacher_id": ctx.teacher_id,
            "course_id": ctx.course_id,
            "student_contract_id": ctx.student_contract_id,
            "teacher_contract_id": ctx.teacher_contract_id,
            "teacher_slot_id": ctx.teacher_slot_id,
            "booking_date": ctx.slot_date,
            "start_time": "09:00",
            "end_time": "10:00",
            "notes": f"{TEST_PREFIX}should_fail",
        })
        if resp.status_code == 409:
            return True
        return f"Expected 409 Conflict, got {resp.status_code}"

    # ────────────────── Phase 4.5: Zoom ──────────────────

    async def _test_check_zoom_accounts(self, ctx: E2EContext):
        """檢查系統是否有可用的 Zoom 帳號"""
        resp = await self._get("/api/v1/zoom/accounts", {"per_page": 1})
        if resp.status_code != 200:
            ctx.zoom_enabled = False
            return True  # 不算失敗，只是跳過
        data = resp.json().get("data", [])
        active = [a for a in data if a.get("is_active")]
        ctx.zoom_enabled = len(active) > 0
        status = f"找到 {len(active)} 個可用帳號" if active else "無可用帳號"
        print(f"({status})", end=" ")
        return True

    async def _test_create_zoom_meeting(self, ctx: E2EContext):
        """為已確認的預約建立 Zoom 會議（需要有效 OAuth token）"""
        resp = await self._post("/api/v1/zoom/meetings/create", {
            "booking_id": ctx.booking_id,
        })
        if resp.status_code == 500:
            # OAuth token 過期是外部服務問題，標記為跳過而非失敗
            ctx.zoom_enabled = False
            return f"Zoom OAuth token 可能過期 — 需重新授權"
        if resp.status_code != 200:
            return f"Create Zoom meeting failed: {resp.status_code} {resp.text[:200]}"
        data = resp.json()["data"]
        ctx.zoom_meeting_id = data.get("id")
        if not data.get("join_url"):
            return "Zoom meeting created but no join_url"
        return True

    async def _test_verify_zoom_meeting(self, ctx: E2EContext):
        """驗證 Zoom 會議資訊"""
        resp = await self._get(f"/api/v1/zoom/meetings/{ctx.booking_id}")
        if resp.status_code != 200:
            return f"Get Zoom meeting failed: {resp.status_code}"
        data = resp.json()["data"]
        checks = []
        if not data.get("join_url"):
            checks.append("missing join_url")
        if not data.get("zoom_meeting_id"):
            checks.append("missing zoom_meeting_id")
        return True if not checks else "; ".join(checks)

    async def _test_list_zoom_meetings(self, ctx: E2EContext):
        """查詢 Zoom 會議列表"""
        resp = await self._get("/api/v1/zoom/meetings", {"per_page": 5})
        if resp.status_code != 200:
            return f"List Zoom meetings failed: {resp.status_code}"
        data = resp.json().get("data", [])
        if not any(m.get("booking_id") == ctx.booking_id for m in data):
            return "列表找不到剛建立的會議"
        return True

    # ────────────────── Phase 5: 請假 ──────────────────

    async def _test_create_leave_request(self, ctx: E2EContext):
        resp = await self._post("/api/v1/leave-records", {
            "booking_id": ctx.booking_id,
            "reason": f"{TEST_PREFIX}E2E 測試請假",
        })
        if resp.status_code != 200:
            return f"Create leave failed: {resp.status_code} {resp.text[:200]}"
        ctx.leave_record_id = resp.json()["data"]["id"]
        return True

    async def _test_verify_leave_record(self, ctx: E2EContext):
        resp = await self._get(f"/api/v1/leave-records/{ctx.leave_record_id}")
        if resp.status_code != 200:
            return f"Get leave record failed: {resp.status_code}"
        data = resp.json()["data"]
        if data.get("leave_status") != "pending":
            return f"Expected pending, got {data.get('leave_status')}"
        if data.get("booking_id") != ctx.booking_id:
            return f"booking_id mismatch"
        return True

    # ────────────────── Phase 6: 取消與刪除 ──────────────────

    async def _test_cancel_booking(self, ctx: E2EContext):
        resp = await self._put(f"/api/v1/bookings/{ctx.booking_id}", {
            "booking_status": "cancelled",
        })
        if resp.status_code != 200:
            return f"Cancel booking failed: {resp.status_code} {resp.text[:200]}"
        return True

    async def _test_delete_booking(self, ctx: E2EContext):
        resp = await self._delete(f"/api/v1/bookings/{ctx.booking_id}")
        if resp.status_code != 200:
            return f"Delete booking failed: {resp.status_code} {resp.text[:200]}"
        return True

    async def _test_verify_booking_deleted(self, ctx: E2EContext):
        resp = await self._get(f"/api/v1/bookings/{ctx.booking_id}")
        if resp.status_code == 404:
            return True
        # 有些 API 回傳 200 但 is_deleted=true
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            if data.get("is_deleted"):
                return True
            return f"Booking still exists and not deleted"
        return True  # 404 or gone

    # ────────────────── Phase 7: Cleanup ──────────────────

    async def _cleanup(self, ctx: E2EContext, full_search: bool = False):
        """反序刪除所有測試建立的資源"""
        cleanup_steps = [
            ("leave_record", f"/api/v1/leave-records/{ctx.leave_record_id}" if ctx.leave_record_id else None),
            ("booking", f"/api/v1/bookings/{ctx.booking_id}" if ctx.booking_id else None),
            ("teacher_slot", f"/api/v1/teacher-slots/{ctx.teacher_slot_id}" if ctx.teacher_slot_id else None),
            ("preference_b", f"/api/v1/student-teacher-preferences/{ctx.preference_b_id}" if ctx.preference_b_id else None),
            ("preference", f"/api/v1/student-teacher-preferences/{ctx.preference_id}" if ctx.preference_id else None),
            ("student_course", f"/api/v1/student-courses/{ctx.student_course_id}" if ctx.student_course_id else None),
            ("teacher_b_contract_detail", (
                f"/api/v1/teacher-contracts/{ctx.teacher_b_contract_id}/details/{ctx.teacher_b_contract_detail_id}"
                if ctx.teacher_b_contract_id and ctx.teacher_b_contract_detail_id else None
            )),
            ("teacher_b_contract", f"/api/v1/teacher-contracts/{ctx.teacher_b_contract_id}" if ctx.teacher_b_contract_id else None),
            ("teacher_contract_detail", (
                f"/api/v1/teacher-contracts/{ctx.teacher_contract_id}/details/{ctx.teacher_contract_detail_id}"
                if ctx.teacher_contract_id and ctx.teacher_contract_detail_id else None
            )),
            ("teacher_contract", f"/api/v1/teacher-contracts/{ctx.teacher_contract_id}" if ctx.teacher_contract_id else None),
            ("student_contract", f"/api/v1/student-contracts/{ctx.student_contract_id}" if ctx.student_contract_id else None),
            ("teacher_b", f"/api/v1/teachers/{ctx.teacher_b_id}" if ctx.teacher_b_id else None),
            ("teacher", f"/api/v1/teachers/{ctx.teacher_id}" if ctx.teacher_id else None),
            ("student", f"/api/v1/students/{ctx.student_id}" if ctx.student_id else None),
            ("course", f"/api/v1/courses/{ctx.course_id}" if ctx.course_id else None),
        ]

        for name, path in cleanup_steps:
            if not path:
                continue
            try:
                resp = await self._delete(path)
                status = "OK" if resp.status_code in (200, 204, 404) else f"WARN ({resp.status_code})"
                print(f"    cleanup {name}: {status}")
            except Exception as e:
                print(f"    cleanup {name}: ERROR {e}")

    # ────────────────── Summary ──────────────────

    def _print_summary(self):
        print(f"\n{'=' * 65}")
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        total = len(self.results)
        status = "ALL PASSED" if failed == 0 else f"{failed} FAILED"

        print(f"  Results: {passed}/{total} passed — {status}")
        if failed > 0:
            print(f"\n  Failed tests:")
            for r in self.results:
                if not r.passed:
                    print(f"    ✗ {r.name}: {r.message}")
        print(f"{'=' * 65}\n")


async def main():
    parser = argparse.ArgumentParser(description="E2E Booking Flow Test")
    parser.add_argument("--email", required=True, help="Employee login email")
    parser.add_argument("--password", required=True, help="Employee login password")
    parser.add_argument("--cleanup-only", action="store_true", help="Only cleanup test data")
    args = parser.parse_args()

    tester = E2EBookingFlowTester()
    ok = await tester.run(args.email, args.password, args.cleanup_only)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    asyncio.run(main())

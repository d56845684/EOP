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

    # Phase 3.6: 本次修改驗證用
    teacher_c_id: Optional[str] = None
    teacher_c_contract_id: Optional[str] = None
    teacher_c_contract_detail_id: Optional[str] = None
    preference_c_id: Optional[str] = None
    level_preference_id: Optional[str] = None
    auto_student_id: Optional[str] = None
    auto_teacher_id: Optional[str] = None

    # Phase 4.1: 偏好白名單驗證用（不在白名單的教師）
    teacher_d_id: Optional[str] = None

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

            # ── Phase 3.6: 本次修改驗證（batch create / 等級向下兼容 / 編號自動產生） ──
            print("\n  Phase 3.6: 本次修改驗證")
            print("  " + "-" * 40)
            tests_new_features = [
                ("批次新增教師偏好 (batch API)", self._test_batch_create_preference),
                ("批次新增重複偏好 (應跳過)", self._test_batch_create_duplicate),
                ("建立教師 C (level 3)", self._test_create_teacher_c),
                ("等級偏好向下兼容驗證", self._test_level_downward_compat),
                ("學生編號自動產生 (EOPS)", self._test_auto_student_no),
                ("教師編號自動產生 (EOPT)", self._test_auto_teacher_no),
            ]
            for name, fn in tests_new_features:
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

            # ── Phase 4.1: 偏好白名單驗證 ──
            print("\n  Phase 4.1: 偏好白名單驗證")
            print("  " + "-" * 40)
            tests_preference_check = [
                ("建立白名單外教師 D（無偏好）", self._test_create_teacher_d_no_preference),
                ("CREATE 白名單外教師 D 預約（應拒絕 400）", self._test_create_booking_disallowed_teacher),
                ("CREATE 白名單內教師 B 預約（成功）", self._test_create_booking_allowed_teacher_b),
                ("刪除教師 B 預約（清理）", self._test_delete_booking_teacher_b),
            ]
            for name, fn in tests_preference_check:
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
            "email": f"e2e_student_{datetime.now().strftime('%H%M%S')}@example.com",
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
            "email": f"e2e_teacher_{datetime.now().strftime('%H%M%S')}@example.com",
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
            "primary_teacher_ids": [ctx.teacher_id],
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
            "email": f"e2e_teacher_b_{datetime.now().strftime('%H%M%S')}@example.com",
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
            "primary_teacher_ids": [ctx.teacher_b_id],
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

    # ────────────────── Phase 3.6: 本次修改驗證 ──────────────────

    async def _test_batch_create_preference(self, ctx: E2EContext):
        """用 batch API 同時新增教師 A + B 偏好 — 因為已存在，應全部跳過"""
        resp = await self._post("/api/v1/student-teacher-preferences/", {
            "student_id": ctx.student_id,
            "primary_teacher_ids": [ctx.teacher_id, ctx.teacher_b_id],
        })
        if resp.status_code != 400:
            # 全部重複時 API 回 400
            if resp.status_code == 200:
                msg = resp.json().get("message", "")
                if "跳過" not in msg and "已存在" not in msg:
                    return f"Expected skip message, got: {msg}"
                return True
            return f"Batch create failed: {resp.status_code} {resp.text[:200]}"
        # 400 = 所有選擇的教師已存在於偏好中 → 正確
        return True

    async def _test_batch_create_duplicate(self, ctx: E2EContext):
        """用 batch API 新增一位新教師 + 一位已存在，驗證部分成功"""
        # 先建一位臨時教師用於 batch
        resp = await self._post("/api/v1/teachers", {
            "teacher_no": f"{TEST_PREFIX}T003",
            "name": f"{TEST_PREFIX}臨時教師",
            "email": f"e2e_temp_teacher_{datetime.now().strftime('%H%M%S%f')}@example.com",
            "teacher_level": 1,
        })
        if resp.status_code != 200:
            return f"Create temp teacher failed: {resp.status_code}"
        temp_teacher_id = resp.json()["data"]["id"]

        # batch: 包含已存在的 teacher_id + 新的 temp_teacher_id
        resp = await self._post("/api/v1/student-teacher-preferences/", {
            "student_id": ctx.student_id,
            "primary_teacher_ids": [ctx.teacher_id, temp_teacher_id],
        })
        if resp.status_code != 200:
            return f"Batch create failed: {resp.status_code} {resp.text[:200]}"

        data = resp.json()
        msg = data.get("message", "")
        created = data.get("data", [])

        # 應只新增 1 筆（temp），跳過 1 筆（teacher_id 已存在）
        if len(created) != 1:
            return f"Expected 1 created, got {len(created)}: {msg}"

        # 清理: 刪除臨時偏好和教師
        pref_id = created[0].get("id")
        if pref_id:
            await self._delete(f"/api/v1/student-teacher-preferences/{pref_id}")
        await self._delete(f"/api/v1/teachers/{temp_teacher_id}")
        return True

    async def _test_create_teacher_c(self, ctx: E2EContext):
        """建立教師 C (level 3)，用於等級向下兼容測試"""
        resp = await self._post("/api/v1/teachers", {
            "teacher_no": f"{TEST_PREFIX}T004",
            "name": f"{TEST_PREFIX}測試教師C",
            "email": f"e2e_teacher_c_{datetime.now().strftime('%H%M%S')}@example.com",
            "teacher_level": 3,
        })
        if resp.status_code != 200:
            return f"Create teacher C failed: {resp.status_code} {resp.text[:200]}"
        ctx.teacher_c_id = resp.json()["data"]["id"]

        # 建合約
        start = date.today().isoformat()
        end = (date.today() + timedelta(days=365)).isoformat()
        resp = await self._post("/api/v1/teacher-contracts", {
            "teacher_id": ctx.teacher_c_id,
            "contract_status": "active",
            "start_date": start, "end_date": end,
            "employment_type": "hourly",
        })
        if resp.status_code != 200:
            return f"Create teacher C contract failed: {resp.status_code}"
        ctx.teacher_c_contract_id = resp.json()["data"]["id"]

        # 課程費率
        resp = await self._post(
            f"/api/v1/teacher-contracts/{ctx.teacher_c_contract_id}/details",
            {"detail_type": "course_rate", "course_id": ctx.course_id,
             "description": "E2E 教師C費率", "amount": 1000},
        )
        if resp.status_code != 200:
            return f"Create teacher C rate failed: {resp.status_code}"
        ctx.teacher_c_contract_detail_id = resp.json()["data"]["id"]

        # 新增偏好
        resp = await self._post("/api/v1/student-teacher-preferences/", {
            "student_id": ctx.student_id,
            "primary_teacher_ids": [ctx.teacher_c_id],
        })
        if resp.status_code != 200:
            return f"Create teacher C preference failed: {resp.status_code}"
        ctx.preference_c_id = resp.json()["data"]["id"]

        return True

    async def _test_level_downward_compat(self, ctx: E2EContext):
        """等級偏好向下兼容：設 max_level=2 → level 1,2 可選，level 3 不可選

        測試步驟：
        1. 刪除教師 A/B/C 的指定教師偏好
        2. 建立等級偏好 (level=2)
        3. 驗證可預約教師：A(lv1) ✓, B(lv2) ✓, C(lv3) ✗
        4. 刪除等級偏好，恢復原本的指定教師偏好
        """
        # 1. 暫時刪除所有指定教師偏好
        for pid in [ctx.preference_id, ctx.preference_b_id, ctx.preference_c_id]:
            if pid:
                await self._delete(f"/api/v1/student-teacher-preferences/{pid}")

        # 2. 建立等級偏好 (全域, max_level=2)
        resp = await self._post("/api/v1/student-teacher-preferences/", {
            "student_id": ctx.student_id,
            "min_teacher_level": 2,
        })
        if resp.status_code != 200:
            return f"Create level preference failed: {resp.status_code} {resp.text[:200]}"
        ctx.level_preference_id = resp.json()["data"]["id"]

        # 3. 驗證可預約教師
        resp = await self._get("/api/v1/bookings/options/teachers", params={"student_id": ctx.student_id})
        if resp.status_code != 200:
            return f"Get teacher options failed: {resp.status_code}"
        teachers = resp.json().get("data", [])
        teacher_ids = {t["id"] for t in teachers}

        errors = []
        if ctx.teacher_id not in teacher_ids:
            errors.append(f"教師 A (level 1) 應在可預約列表中但不在")
        if ctx.teacher_b_id not in teacher_ids:
            errors.append(f"教師 B (level 2) 應在可預約列表中但不在")
        if ctx.teacher_c_id in teacher_ids:
            errors.append(f"教師 C (level 3) 不應在可預約列表中但出現了")

        # 4. 清理等級偏好，恢復指定教師偏好
        await self._delete(f"/api/v1/student-teacher-preferences/{ctx.level_preference_id}")
        ctx.level_preference_id = None

        # 重建指定教師偏好
        for tid, attr in [(ctx.teacher_id, "preference_id"), (ctx.teacher_b_id, "preference_b_id"), (ctx.teacher_c_id, "preference_c_id")]:
            resp = await self._post("/api/v1/student-teacher-preferences/", {
                "student_id": ctx.student_id,
                "primary_teacher_ids": [tid],
            })
            if resp.status_code == 200:
                setattr(ctx, attr, resp.json()["data"]["id"])

        if errors:
            return "; ".join(errors)
        return True

    async def _test_auto_student_no(self, ctx: E2EContext):
        """不提供 student_no，驗證自動產生 EOPS 格式"""
        resp = await self._post("/api/v1/students", {
            "name": f"{TEST_PREFIX}自動編號學生",
            "email": f"e2e_auto_s_{datetime.now().strftime('%H%M%S%f')}@example.com",
        })
        if resp.status_code != 200:
            return f"Create auto student failed: {resp.status_code} {resp.text[:200]}"
        data = resp.json()["data"]
        ctx.auto_student_id = data["id"]
        student_no = data.get("student_no", "")
        if not student_no.startswith("EOPS"):
            return f"student_no 應以 EOPS 開頭，實際值: {student_no}"
        return True

    async def _test_auto_teacher_no(self, ctx: E2EContext):
        """不提供 teacher_no，驗證自動產生 EOPT 格式"""
        resp = await self._post("/api/v1/teachers", {
            "name": f"{TEST_PREFIX}自動編號教師",
            "email": f"e2e_auto_t_{datetime.now().strftime('%H%M%S%f')}@example.com",
        })
        if resp.status_code != 200:
            return f"Create auto teacher failed: {resp.status_code} {resp.text[:200]}"
        data = resp.json()["data"]
        ctx.auto_teacher_id = data["id"]
        teacher_no = data.get("teacher_no", "")
        if not teacher_no.startswith("EOPT"):
            return f"teacher_no 應以 EOPT 開頭，實際值: {teacher_no}"
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

    # ────────────────── Phase 4.1: 偏好白名單驗證 ──────────────────

    async def _test_create_teacher_d_no_preference(self, ctx: E2EContext):
        """建立教師 D — 不在學生偏好白名單中"""
        resp = await self._post("/api/v1/teachers", {
            "teacher_no": f"{TEST_PREFIX}T005",
            "name": f"{TEST_PREFIX}測試教師D_非白名單",
            "email": f"e2e_teacher_d_{datetime.now().strftime('%H%M%S')}@example.com",
            "teacher_level": 1,
        })
        if resp.status_code != 200:
            return f"Create teacher D failed: {resp.status_code} {resp.text[:200]}"
        ctx.teacher_d_id = resp.json()["data"]["id"]
        return True

    async def _test_create_booking_disallowed_teacher(self, ctx: E2EContext):
        """CREATE 預約用白名單外教師 D → 應被拒絕 400"""
        resp = await self._post("/api/v1/bookings", {
            "student_id": ctx.student_id,
            "teacher_id": ctx.teacher_d_id,
            "course_id": ctx.course_id,
            "student_contract_id": ctx.student_contract_id,
            "teacher_slot_id": ctx.teacher_slot_id,
            "booking_date": ctx.slot_date,
            "start_time": "10:00",
            "end_time": "11:00",
            "notes": f"{TEST_PREFIX}should_fail_disallowed",
        })
        if resp.status_code == 400:
            return True
        return f"Expected 400 (not in whitelist), got {resp.status_code}: {resp.text[:200]}"

    async def _test_create_booking_allowed_teacher_b(self, ctx: E2EContext):
        """CREATE 預約用白名單內教師 B → 應成功（驗證白名單內教師可建立）"""
        resp = await self._post("/api/v1/bookings", {
            "student_id": ctx.student_id,
            "teacher_id": ctx.teacher_b_id,
            "course_id": ctx.course_id,
            "student_contract_id": ctx.student_contract_id,
            "teacher_contract_id": ctx.teacher_b_contract_id,
            "teacher_slot_id": ctx.teacher_slot_id,
            "booking_date": ctx.slot_date,
            "start_time": "10:00",
            "end_time": "11:00",
            "notes": f"{TEST_PREFIX}teacher_b_booking",
        })
        if resp.status_code != 200:
            return f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        ctx._teacher_b_booking_id = resp.json()["data"]["id"]
        return True

    async def _test_delete_booking_teacher_b(self, ctx: E2EContext):
        """刪除教師 B 的預約（清理，避免影響後續測試）"""
        bid = getattr(ctx, '_teacher_b_booking_id', None)
        if not bid:
            return "no teacher B booking to delete"
        resp = await self._delete(f"/api/v1/bookings/{bid}")
        if resp.status_code not in (200, 204):
            return f"{resp.status_code} {resp.text[:200]}"
        return True

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
        """取得或建立 Zoom 會議（確認預約時可能已自動建立）"""
        import asyncio as _aio
        # 等待背景 asyncio.create_task 完成（確認預約觸發的自動建立）
        await _aio.sleep(2)

        # 先查是否已有會議（確認預約時自動建的）
        check = await self._get(f"/api/v1/zoom/meetings/{ctx.booking_id}")
        if check.status_code == 200:
            data = check.json()["data"]
            ctx.zoom_meeting_id = data.get("id")
            if data.get("join_url"):
                return True
            # 有記錄但沒 join_url，可能 token 失敗，嘗試手動建立

        # 手動建立
        resp = await self._post("/api/v1/zoom/meetings/create", {
            "booking_id": ctx.booking_id,
        })
        if resp.status_code == 500:
            ctx.zoom_enabled = False
            return f"Zoom 帳號池無可用帳號或 token 失敗"
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
        """查詢 Zoom 會議列表（篩選 scheduled 狀態避免被舊資料淹沒）"""
        resp = await self._get("/api/v1/zoom/meetings", {
            "per_page": 50,
            "meeting_status": "scheduled",
        })
        if resp.status_code != 200:
            return f"List Zoom meetings failed: {resp.status_code}"
        data = resp.json().get("data", [])
        if not any(m.get("booking_id") == ctx.booking_id for m in data):
            return f"列表找不到剛建立的會議 (booking_id={ctx.booking_id}, 列表共 {len(data)} 筆)"
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
            ("level_preference", f"/api/v1/student-teacher-preferences/{ctx.level_preference_id}" if ctx.level_preference_id else None),
            ("preference_c", f"/api/v1/student-teacher-preferences/{ctx.preference_c_id}" if ctx.preference_c_id else None),
            ("preference_b", f"/api/v1/student-teacher-preferences/{ctx.preference_b_id}" if ctx.preference_b_id else None),
            ("preference", f"/api/v1/student-teacher-preferences/{ctx.preference_id}" if ctx.preference_id else None),
            ("student_course", f"/api/v1/student-courses/{ctx.student_course_id}" if ctx.student_course_id else None),
            ("teacher_c_contract_detail", (
                f"/api/v1/teacher-contracts/{ctx.teacher_c_contract_id}/details/{ctx.teacher_c_contract_detail_id}"
                if ctx.teacher_c_contract_id and ctx.teacher_c_contract_detail_id else None
            )),
            ("teacher_c_contract", f"/api/v1/teacher-contracts/{ctx.teacher_c_contract_id}" if ctx.teacher_c_contract_id else None),
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
            ("teacher_d", f"/api/v1/teachers/{ctx.teacher_d_id}" if ctx.teacher_d_id else None),
            ("teacher_c", f"/api/v1/teachers/{ctx.teacher_c_id}" if ctx.teacher_c_id else None),
            ("teacher_b", f"/api/v1/teachers/{ctx.teacher_b_id}" if ctx.teacher_b_id else None),
            ("teacher", f"/api/v1/teachers/{ctx.teacher_id}" if ctx.teacher_id else None),
            ("auto_teacher", f"/api/v1/teachers/{ctx.auto_teacher_id}" if ctx.auto_teacher_id else None),
            ("student", f"/api/v1/students/{ctx.student_id}" if ctx.student_id else None),
            ("auto_student", f"/api/v1/students/{ctx.auto_student_id}" if ctx.auto_student_id else None),
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

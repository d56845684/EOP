#!/usr/bin/env python3
"""
End-to-End Overtime Pay Test

測試全職教師加班費完整流程：
  1. 建立課程 → 學生 → 教師（全職）
  2. 建立學生合約 → 教師合約（full_time）
  3. 新增課程費率 + 加班費明細（overtime_rate）
  4. 驗證加班費不可重複
  5. 設定工作時段（例如 09:00–12:00）
  6. 建立教師時段 + 學生選課 + 教師偏好
  7. 建立正班預約（09:00–10:00）→ 驗證 overtime_pay=None
  8. 建立加班預約（13:00–14:00）→ 驗證 overtime_pay 正確計算
  9. 驗證列表 API 批次計算也正確
  10. 清理所有測試資料

使用方式:
    python tests/live_e2e_overtime_test.py \\
        --email employee@eop-test.com --password TestPassword123!
"""

import httpx
import asyncio
import argparse
import sys
import os
from datetime import datetime, date, timedelta
from typing import Optional
from dataclasses import dataclass, field

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8001")
_TS = datetime.now().strftime("%H%M%S")
TEST_PREFIX = f"OT{_TS}_"

OVERTIME_RATE = 150  # 每堂加班費
COURSE_RATE = 800    # 課程時薪
COURSE_DURATION = 60 # 課程時長（分鐘）


@dataclass
class TestResult:
    name: str
    passed: bool
    message: str = ""


@dataclass
class OTContext:
    """測試上下文"""
    cookies: dict = field(default_factory=dict)

    course_id: Optional[str] = None
    student_id: Optional[str] = None
    teacher_id: Optional[str] = None
    student_contract_id: Optional[str] = None
    teacher_contract_id: Optional[str] = None
    course_rate_detail_id: Optional[str] = None
    overtime_rate_detail_id: Optional[str] = None
    student_course_id: Optional[str] = None
    preference_id: Optional[str] = None
    teacher_slot_id: Optional[str] = None

    # 兩筆預約
    regular_booking_id: Optional[str] = None   # 正班
    overtime_booking_id: Optional[str] = None   # 加班

    slot_date: str = ""


class E2EOvertimePayTester:
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
            ctx = OTContext()
            # 使用 14 天後的週一，確保 weekday=0 對應工作時段
            target = date.today() + timedelta(days=14)
            # 調整到下一個週一 (isoweekday: 1=Mon)
            days_until_monday = (8 - target.isoweekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 7
            ctx.slot_date = (target + timedelta(days=days_until_monday)).isoformat()

            print(f"\n{'=' * 65}")
            print(f"  E2E Overtime Pay Test")
            print(f"  Backend: {self.url}")
            print(f"  User: {email}")
            print(f"  Slot Date: {ctx.slot_date} (Monday)")
            print(f"  Overtime Rate: {OVERTIME_RATE}/堂")
            print(f"{'=' * 65}\n")

            # Login
            ok = await self._run_test("Login", self._test_login, ctx, email, password)
            if not ok:
                print("\n  LOGIN FAILED — aborting.")
                return False

            if cleanup_only:
                await self._cleanup(ctx)
                return True

            # ── Phase 1: 建立基礎資料 ──
            print("\n  Phase 1: 建立基礎資料")
            print("  " + "-" * 40)
            phase1 = [
                ("建立課程 (60min)", self._test_create_course),
                ("建立學生", self._test_create_student),
                ("建立教師", self._test_create_teacher),
            ]
            for name, fn in phase1:
                ok = await self._run_test(name, fn, ctx)
                if not ok:
                    await self._cleanup(ctx)
                    self._print_summary()
                    return False

            # ── Phase 2: 全職合約 + 加班費 ──
            print("\n  Phase 2: 全職合約 + 加班費")
            print("  " + "-" * 40)
            phase2 = [
                ("建立學生合約", self._test_create_student_contract),
                ("建立教師合約 (full_time)", self._test_create_teacher_contract),
                ("新增課程費率", self._test_create_course_rate),
                ("新增加班費 (overtime_rate)", self._test_create_overtime_rate),
                ("驗證加班費不可重複", self._test_duplicate_overtime_rate_rejected),
                ("設定工作時段 (週一 09:00-12:00)", self._test_set_work_schedules),
            ]
            for name, fn in phase2:
                await self._run_test(name, fn, ctx)

            # ── Phase 3: 關聯設定 ──
            print("\n  Phase 3: 關聯設定")
            print("  " + "-" * 40)
            phase3 = [
                ("學生選課", self._test_create_student_course),
                ("設定教師偏好", self._test_create_preference),
                ("建立教師時段 (08:00-18:00)", self._test_create_teacher_slot),
            ]
            for name, fn in phase3:
                await self._run_test(name, fn, ctx)

            # ── Phase 4: 預約 + 加班費驗證 ──
            print("\n  Phase 4: 預約 + 加班費驗證")
            print("  " + "-" * 40)
            phase4 = [
                ("建立正班預約 (09:00-10:00)", self._test_create_regular_booking),
                ("驗證正班預約 (overtime_pay=None)", self._test_verify_regular_booking),
                ("建立加班預約 (13:00-14:00)", self._test_create_overtime_booking),
                ("驗證加班預約 (overtime_pay 正確計算)", self._test_verify_overtime_booking),
                ("驗證列表 API 批次計算", self._test_verify_list_overtime),
            ]
            for name, fn in phase4:
                await self._run_test(name, fn, ctx)

            # ── Phase 5: 清理 ──
            print("\n  Phase 5: 清理測試資料")
            print("  " + "-" * 40)
            await self._cleanup(ctx)

            self._print_summary()
            return all(r.passed for r in self.results)

    async def _run_test(self, name: str, fn, ctx: OTContext, *args) -> bool:
        try:
            result = await fn(ctx, *args)
            passed = result is True
            msg = "" if passed else str(result)
            self.results.append(TestResult(name=name, passed=passed, message=msg))
            print(f"  {'✓' if passed else '✗'} {name}" + (f" — {msg}" if msg else ""))
            return passed
        except Exception as e:
            self.results.append(TestResult(name=name, passed=False, message=str(e)))
            print(f"  ✗ {name} — ERROR: {e}")
            return False

    # ────────────────── Phase 0: Login ──────────────────

    async def _test_login(self, ctx: OTContext, email: str, password: str):
        resp = await self._post("/api/v1/auth/login", {"email": email, "password": password})
        if resp.status_code != 200:
            return f"Login failed: {resp.status_code}"
        return True

    # ────────────────── Phase 1: 基礎資料 ──────────────────

    async def _test_create_course(self, ctx: OTContext):
        resp = await self._post("/api/v1/courses", {
            "course_code": f"{TEST_PREFIX}C001",
            "course_name": f"{TEST_PREFIX}加班費測試課程",
            "description": "E2E 加班費測試用",
            "duration_minutes": COURSE_DURATION,
        })
        if resp.status_code != 200:
            return f"Create course failed: {resp.status_code} {resp.text[:200]}"
        ctx.course_id = resp.json()["data"]["id"]
        return True

    async def _test_create_student(self, ctx: OTContext):
        resp = await self._post("/api/v1/students", {
            "student_no": f"{TEST_PREFIX}S001",
            "name": f"{TEST_PREFIX}加班費測試學生",
            "email": f"ot_student_{_TS}@example.com",
            "student_type": "formal",
        })
        if resp.status_code != 200:
            return f"Create student failed: {resp.status_code} {resp.text[:200]}"
        ctx.student_id = resp.json()["data"]["id"]
        return True

    async def _test_create_teacher(self, ctx: OTContext):
        resp = await self._post("/api/v1/teachers", {
            "teacher_no": f"{TEST_PREFIX}T001",
            "name": f"{TEST_PREFIX}加班費測試教師",
            "email": f"ot_teacher_{_TS}@example.com",
            "teacher_level": 1,
        })
        if resp.status_code != 200:
            return f"Create teacher failed: {resp.status_code} {resp.text[:200]}"
        ctx.teacher_id = resp.json()["data"]["id"]
        return True

    # ────────────────── Phase 2: 全職合約 + 加班費 ──────────────────

    async def _test_create_student_contract(self, ctx: OTContext):
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

    async def _test_create_teacher_contract(self, ctx: OTContext):
        """建立 full_time 教師合約"""
        start = date.today().isoformat()
        end = (date.today() + timedelta(days=365)).isoformat()
        resp = await self._post("/api/v1/teacher-contracts", {
            "teacher_id": ctx.teacher_id,
            "contract_status": "active",
            "start_date": start,
            "end_date": end,
            "employment_type": "full_time",
        })
        if resp.status_code != 200:
            return f"Create teacher contract failed: {resp.status_code} {resp.text[:200]}"
        data = resp.json()["data"]
        ctx.teacher_contract_id = data["id"]
        if data.get("employment_type") != "full_time":
            return f"Expected full_time, got {data.get('employment_type')}"
        return True

    async def _test_create_course_rate(self, ctx: OTContext):
        resp = await self._post(
            f"/api/v1/teacher-contracts/{ctx.teacher_contract_id}/details",
            {
                "detail_type": "course_rate",
                "course_id": ctx.course_id,
                "description": "E2E 加班費測試",
                "amount": COURSE_RATE,
            },
        )
        if resp.status_code != 200:
            return f"Create course rate failed: {resp.status_code} {resp.text[:200]}"
        ctx.course_rate_detail_id = resp.json()["data"]["id"]
        return True

    async def _test_create_overtime_rate(self, ctx: OTContext):
        """新增加班費明細"""
        resp = await self._post(
            f"/api/v1/teacher-contracts/{ctx.teacher_contract_id}/details",
            {
                "detail_type": "overtime_rate",
                "description": "平日加班費",
                "amount": OVERTIME_RATE,
                "notes": "E2E 測試加班費",
            },
        )
        if resp.status_code != 200:
            return f"Create overtime rate failed: {resp.status_code} {resp.text[:200]}"
        data = resp.json()["data"]
        ctx.overtime_rate_detail_id = data["id"]
        if data.get("detail_type") != "overtime_rate":
            return f"Expected overtime_rate, got {data.get('detail_type')}"
        if data.get("amount") != OVERTIME_RATE:
            return f"Expected amount={OVERTIME_RATE}, got {data.get('amount')}"
        return True

    async def _test_duplicate_overtime_rate_rejected(self, ctx: OTContext):
        """重複新增加班費應被拒絕"""
        resp = await self._post(
            f"/api/v1/teacher-contracts/{ctx.teacher_contract_id}/details",
            {
                "detail_type": "overtime_rate",
                "description": "第二筆加班費",
                "amount": 200,
            },
        )
        if resp.status_code == 400:
            return True
        return f"Expected 400, got {resp.status_code} {resp.text[:200]}"

    async def _test_set_work_schedules(self, ctx: OTContext):
        """設定週一工作時段 09:00-12:00"""
        resp = await self._put(
            f"/api/v1/teacher-contracts/{ctx.teacher_contract_id}/work-schedules",
            {
                "schedules": [
                    {"weekday": 0, "start_time": "09:00", "end_time": "12:00"},
                ]
            },
        )
        if resp.status_code != 200:
            return f"Set work schedules failed: {resp.status_code} {resp.text[:200]}"
        schedules = resp.json().get("data", [])
        if len(schedules) != 1:
            return f"Expected 1 schedule, got {len(schedules)}"
        return True

    # ────────────────── Phase 3: 關聯設定 ──────────────────

    async def _test_create_student_course(self, ctx: OTContext):
        resp = await self._post("/api/v1/student-courses", {
            "student_id": ctx.student_id,
            "course_id": ctx.course_id,
        })
        if resp.status_code != 200:
            return f"Create student course failed: {resp.status_code} {resp.text[:200]}"
        ctx.student_course_id = resp.json()["data"]["id"]
        return True

    async def _test_create_preference(self, ctx: OTContext):
        resp = await self._post("/api/v1/student-teacher-preferences/", {
            "student_id": ctx.student_id,
            "primary_teacher_ids": [ctx.teacher_id],
        })
        if resp.status_code != 200:
            return f"Create preference failed: {resp.status_code} {resp.text[:200]}"
        ctx.preference_id = resp.json()["data"]["id"]
        return True

    async def _test_create_teacher_slot(self, ctx: OTContext):
        """建立時段 08:00-18:00 — 涵蓋正班和加班時間"""
        resp = await self._post("/api/v1/teacher-slots", {
            "teacher_id": ctx.teacher_id,
            "teacher_contract_id": ctx.teacher_contract_id,
            "slot_date": ctx.slot_date,
            "start_time": "08:00",
            "end_time": "18:00",
            "is_available": True,
        })
        if resp.status_code != 200:
            return f"Create slot failed: {resp.status_code} {resp.text[:200]}"
        ctx.teacher_slot_id = resp.json()["data"]["id"]
        return True

    # ────────────────── Phase 4: 預約 + 加班費驗證 ──────────────────

    async def _test_create_regular_booking(self, ctx: OTContext):
        """建立正班預約 09:00-10:00（落在工作時段 09:00-12:00 內）"""
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
            "notes": f"{TEST_PREFIX}正班預約",
        })
        if resp.status_code != 200:
            return f"Create regular booking failed: {resp.status_code} {resp.text[:300]}"
        ctx.regular_booking_id = resp.json()["data"]["id"]
        return True

    async def _test_verify_regular_booking(self, ctx: OTContext):
        """正班預約：regular_lessons=1, overtime_lessons=0, overtime_pay=None"""
        resp = await self._get(f"/api/v1/bookings/{ctx.regular_booking_id}")
        if resp.status_code != 200:
            return f"Get booking failed: {resp.status_code}"
        data = resp.json()["data"]

        checks = []
        if data.get("is_overtime") is not False:
            checks.append(f"is_overtime={data.get('is_overtime')}, expected False")
        if data.get("regular_lessons") != 1:
            checks.append(f"regular_lessons={data.get('regular_lessons')}, expected 1")
        if data.get("overtime_lessons") != 0:
            checks.append(f"overtime_lessons={data.get('overtime_lessons')}, expected 0")
        if data.get("overtime_pay") is not None:
            checks.append(f"overtime_pay={data.get('overtime_pay')}, expected None")

        return True if not checks else "Verification failed: " + "; ".join(checks)

    async def _test_create_overtime_booking(self, ctx: OTContext):
        """建立加班預約 13:00-14:00（落在工作時段 09:00-12:00 外）"""
        resp = await self._post("/api/v1/bookings", {
            "student_id": ctx.student_id,
            "teacher_id": ctx.teacher_id,
            "course_id": ctx.course_id,
            "student_contract_id": ctx.student_contract_id,
            "teacher_contract_id": ctx.teacher_contract_id,
            "teacher_slot_id": ctx.teacher_slot_id,
            "booking_date": ctx.slot_date,
            "start_time": "13:00",
            "end_time": "14:00",
            "notes": f"{TEST_PREFIX}加班預約",
        })
        if resp.status_code != 200:
            return f"Create overtime booking failed: {resp.status_code} {resp.text[:300]}"
        ctx.overtime_booking_id = resp.json()["data"]["id"]
        return True

    async def _test_verify_overtime_booking(self, ctx: OTContext):
        """加班預約：overtime_lessons=1, overtime_pay = 1 * OVERTIME_RATE"""
        resp = await self._get(f"/api/v1/bookings/{ctx.overtime_booking_id}")
        if resp.status_code != 200:
            return f"Get booking failed: {resp.status_code}"
        data = resp.json()["data"]

        expected_pay = 1 * OVERTIME_RATE  # 1 堂 * 150 = 150

        checks = []
        if data.get("is_overtime") is not True:
            checks.append(f"is_overtime={data.get('is_overtime')}, expected True")
        if data.get("regular_lessons") != 0:
            checks.append(f"regular_lessons={data.get('regular_lessons')}, expected 0")
        if data.get("overtime_lessons") != 1:
            checks.append(f"overtime_lessons={data.get('overtime_lessons')}, expected 1")
        if data.get("overtime_pay") != expected_pay:
            checks.append(f"overtime_pay={data.get('overtime_pay')}, expected {expected_pay}")

        return True if not checks else "Verification failed: " + "; ".join(checks)

    async def _test_verify_list_overtime(self, ctx: OTContext):
        """驗證列表 API 的批次加班費計算也正確"""
        resp = await self._get("/api/v1/bookings", params={
            "teacher_id": ctx.teacher_id,
            "per_page": 10,
        })
        if resp.status_code != 200:
            return f"List bookings failed: {resp.status_code}"
        bookings = resp.json()["data"]

        checks = []
        regular_found = False
        overtime_found = False

        for b in bookings:
            if b["id"] == ctx.regular_booking_id:
                regular_found = True
                if b.get("is_overtime") is not False:
                    checks.append(f"list: regular booking is_overtime={b.get('is_overtime')}")
                if b.get("overtime_pay") is not None:
                    checks.append(f"list: regular booking overtime_pay={b.get('overtime_pay')}")
            elif b["id"] == ctx.overtime_booking_id:
                overtime_found = True
                if b.get("is_overtime") is not True:
                    checks.append(f"list: overtime booking is_overtime={b.get('is_overtime')}")
                expected_pay = 1 * OVERTIME_RATE
                if b.get("overtime_pay") != expected_pay:
                    checks.append(f"list: overtime booking overtime_pay={b.get('overtime_pay')}, expected {expected_pay}")

        if not regular_found:
            checks.append("regular booking not found in list")
        if not overtime_found:
            checks.append("overtime booking not found in list")

        return True if not checks else "Verification failed: " + "; ".join(checks)

    # ────────────────── Phase 5: Cleanup ──────────────────

    async def _cleanup(self, ctx: OTContext):
        """反序刪除所有測試建立的資源"""
        cleanup_steps = [
            ("overtime_booking", f"/api/v1/bookings/{ctx.overtime_booking_id}" if ctx.overtime_booking_id else None),
            ("regular_booking", f"/api/v1/bookings/{ctx.regular_booking_id}" if ctx.regular_booking_id else None),
            ("teacher_slot", f"/api/v1/teacher-slots/{ctx.teacher_slot_id}" if ctx.teacher_slot_id else None),
            ("preference", f"/api/v1/student-teacher-preferences/{ctx.preference_id}" if ctx.preference_id else None),
            ("student_course", f"/api/v1/student-courses/{ctx.student_course_id}" if ctx.student_course_id else None),
            ("overtime_rate_detail", (
                f"/api/v1/teacher-contracts/{ctx.teacher_contract_id}/details/{ctx.overtime_rate_detail_id}"
                if ctx.teacher_contract_id and ctx.overtime_rate_detail_id else None
            )),
            ("course_rate_detail", (
                f"/api/v1/teacher-contracts/{ctx.teacher_contract_id}/details/{ctx.course_rate_detail_id}"
                if ctx.teacher_contract_id and ctx.course_rate_detail_id else None
            )),
            ("teacher_contract", f"/api/v1/teacher-contracts/{ctx.teacher_contract_id}" if ctx.teacher_contract_id else None),
            ("student_contract", f"/api/v1/student-contracts/{ctx.student_contract_id}" if ctx.student_contract_id else None),
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
    parser = argparse.ArgumentParser(description="E2E Overtime Pay Test")
    parser.add_argument("--email", required=True, help="Employee login email")
    parser.add_argument("--password", required=True, help="Employee login password")
    parser.add_argument("--cleanup-only", action="store_true", help="Only cleanup test data")
    args = parser.parse_args()

    tester = E2EOvertimePayTester()
    ok = await tester.run(args.email, args.password, args.cleanup_only)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    asyncio.run(main())

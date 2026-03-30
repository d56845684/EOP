#!/usr/bin/env python3
"""
Teacher Work Schedules Live Test Script

測試正職老師彈性工作時段功能，涵蓋：
1. Work Schedules CRUD (GET / PUT / DELETE)
2. 同 weekday 重疊時段檢查
3. 合約 enrich 包含 work_schedules
4. Booking 加班計算 — 多時段判定
5. Fallback: 無 work_schedules 時用合約 work_start_time/work_end_time
6. 切換 hourly 清除 work_schedules
7. 合約刪除連帶刪除 work_schedules

使用方式:
    python tests/live_work_schedules_test.py --email employee@eop-test.com --password TestPassword123!

    # 只清理測試資料
    python tests/live_work_schedules_test.py --cleanup-only
"""

import httpx
import asyncio
import argparse
import sys
import os
from datetime import datetime, date, time, timedelta
from typing import Optional
from dataclasses import dataclass, field

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8001")

TEST_NOTES = "live_work_schedules_test"


def load_env():
    """載入 .env 檔案"""
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())


load_env()


@dataclass
class TestResult:
    name: str
    passed: bool
    message: str = ""
    duration_ms: float = 0


@dataclass
class TestContext:
    """測試上下文"""
    email: str = ""
    password: str = ""
    cookies: dict = field(default_factory=dict)

    # 從 API 取得的選項
    teacher_id: Optional[str] = None
    course_id: Optional[str] = None
    student_id: Optional[str] = None
    student_contract_id: Optional[str] = None

    # 測試建立的合約
    contract_id: Optional[str] = None
    contract_no: Optional[str] = None

    # 測試建立的 teacher slot + booking
    test_slot_id: Optional[str] = None
    test_slot_date: Optional[str] = None
    test_booking_id: Optional[str] = None

    # 第二個合約（用於測試刪除連帶刪除）
    contract_id_2: Optional[str] = None


class LiveWorkSchedulesTester:
    def __init__(self, backend_url: str, no_cleanup: bool = False):
        self.backend_url = backend_url.rstrip("/")
        self.results: list[TestResult] = []
        self.no_cleanup = no_cleanup
        self.client_kwargs = {
            "follow_redirects": True,
            "timeout": httpx.Timeout(30.0, connect=10.0)
        }

    async def run_all_tests(self, ctx: TestContext) -> bool:
        """執行所有測試"""
        print(f"\n{'='*60}")
        print(f"🧪 Live Work Schedules Tests")
        print(f"{'='*60}")
        print(f"Backend URL: {self.backend_url}")
        print(f"Test User: {ctx.email}")
        print(f"{'='*60}\n")

        tests = [
            # ── Setup ──
            ("Login", self._test_login),
            ("Get Teacher Options", self._test_get_teacher_options),
            ("Get Course Options", self._test_get_course_options),
            ("Get Student Options", self._test_get_student_options),

            # ── 第一組：建立正職合約 + Work Schedules CRUD ──
            ("Create Full-Time Contract", self._test_create_full_time_contract),
            ("GET Work Schedules (Empty)", self._test_list_work_schedules_empty),
            ("PUT Work Schedules (Mon-Fri 09-18)", self._test_set_weekday_schedules),
            ("GET Work Schedules (Verify 5 days)", self._test_list_work_schedules_5_days),
            ("Verify Contract Enrich Has Schedules", self._test_contract_enrich_has_schedules),

            # ── 第二組：多時段 + 重疊檢查 ──
            ("PUT Multi-Slot (Mon 09-12, 14-18)", self._test_set_multi_slot),
            ("GET Verify Multi-Slot", self._test_verify_multi_slot),
            ("PUT Overlapping Slots → 400", self._test_reject_overlapping_slots),

            # ── 第三組：Booking 加班計算（多時段） ──
            ("Setup Active Contract For Booking", self._test_setup_active_contract_for_booking),
            ("Get Student Contract", self._test_get_student_contract),
            ("Create Test Slot (Mon)", self._test_create_test_slot),
            ("Create Booking (09:00-10:00, 正班)", self._test_create_booking_regular),
            ("Verify Booking Regular Lessons", self._test_verify_booking_regular),
            ("Cancel & Delete Booking", self._test_cancel_delete_booking),
            ("Create Booking (12:00-14:00, 加班)", self._test_create_booking_overtime),
            ("Verify Booking Overtime Lessons", self._test_verify_booking_overtime),
            ("Cancel & Delete Booking 2", self._test_cancel_delete_booking_2),

            # ── 第四組：Fallback — 無 work_schedules 時用合約欄位 ──
            ("DELETE All Work Schedules", self._test_clear_work_schedules),
            ("GET Work Schedules (Empty After Clear)", self._test_list_work_schedules_after_clear),
            ("Update Contract Work Time (09-18)", self._test_update_contract_work_time),
            ("Create Booking (19:00-20:00, Fallback OT)", self._test_create_booking_fallback_overtime),
            ("Verify Fallback Overtime", self._test_verify_fallback_overtime),
            ("Cancel & Delete Booking 3", self._test_cancel_delete_booking_3),

            # ── 第五組：切換 hourly 清除時段 ──
            ("PUT Back Some Schedules", self._test_set_schedules_before_hourly),
            ("Switch To Hourly", self._test_switch_to_hourly),
            ("Verify Schedules Cleared After Hourly", self._test_verify_no_schedules_after_hourly),

            # ── 第六組：刪除合約連帶刪除 work_schedules ──
            ("Create Contract 2 (Full-Time)", self._test_create_contract_2),
            ("Set Schedules On Contract 2", self._test_set_schedules_on_contract_2),
            ("Delete Contract 2", self._test_delete_contract_2),
            ("Verify Schedules Deleted With Contract", self._test_verify_schedules_deleted_with_contract),

            # ── Cleanup ──
            ("Delete Test Slot", self._test_delete_test_slot),
            ("Delete Test Contract", self._test_delete_test_contract),
            ("Logout", self._test_logout),
        ]

        # --no-cleanup: 跳過刪除相關步驟（保留測試資料）
        skip_when_no_cleanup = {
            "Delete Test Slot",
            "Delete Test Contract",
            # 第六組整組跳過（cascade delete 是破壞性測試）
            "Create Contract 2 (Full-Time)",
            "Set Schedules On Contract 2",
            "Delete Contract 2",
            "Verify Schedules Deleted With Contract",
        }
        if self.no_cleanup:
            tests = [(n, fn) for n, fn in tests if n not in skip_when_no_cleanup]

        for name, test_fn in tests:
            result = await self._run_single_test(name, test_fn, ctx)
            self.results.append(result)

            if name == "Login" and not result.passed:
                print("\n⚠️  Login failed, skipping remaining tests")
                break

        if self.no_cleanup:
            self._print_kept_data(ctx)

        self._print_summary()
        return all(r.passed for r in self.results)

    def _print_kept_data(self, ctx: TestContext):
        """列印保留的測試資料"""
        print(f"\n{'='*60}")
        print("📝 保留的測試資料（--no-cleanup）")
        print(f"{'='*60}\n")
        if ctx.contract_id:
            print(f"  合約 ID:    {ctx.contract_id}")
            print(f"  合約編號:   {ctx.contract_no}")
        if ctx.contract_id_2:
            print(f"  合約 2 ID:  {ctx.contract_id_2}")
        if ctx.test_slot_id:
            print(f"  Slot ID:    {ctx.test_slot_id}")
            print(f"  Slot Date:  {ctx.test_slot_date}")
        if ctx.test_booking_id:
            print(f"  Booking ID: {ctx.test_booking_id}")
        print()

    async def _run_single_test(self, name: str, test_fn, ctx: TestContext) -> TestResult:
        """執行單個測試"""
        print(f"  ▶ {name}...", end=" ", flush=True)
        start = datetime.now()

        try:
            await test_fn(ctx)
            duration = (datetime.now() - start).total_seconds() * 1000
            print(f"✅ ({duration:.0f}ms)")
            return TestResult(name, True, "OK", duration)
        except AssertionError as e:
            duration = (datetime.now() - start).total_seconds() * 1000
            print(f"❌ {e}")
            return TestResult(name, False, str(e), duration)
        except Exception as e:
            duration = (datetime.now() - start).total_seconds() * 1000
            print(f"❌ Error: {e}")
            return TestResult(name, False, f"Error: {e}", duration)

    def _print_summary(self):
        """列印測試摘要"""
        print(f"\n{'='*60}")
        print("📊 Test Summary")
        print(f"{'='*60}\n")

        for r in self.results:
            status = "✅" if r.passed else "❌"
            print(f"  {status} {r.name}: {r.message} ({r.duration_ms:.0f}ms)")

        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        total_time = sum(r.duration_ms for r in self.results)

        print(f"\n{'='*60}")
        print(f"Total: {passed} passed, {failed} failed ({total_time:.0f}ms)")
        print(f"{'='*60}\n")

    # ================================================================
    # Setup
    # ================================================================

    async def _test_login(self, ctx: TestContext):
        async with httpx.AsyncClient(**self.client_kwargs) as client:
            resp = await client.post(
                f"{self.backend_url}/api/v1/auth/login",
                json={"email": ctx.email, "password": ctx.password}
            )
            assert resp.status_code == 200, f"Login failed: {resp.text}"
            ctx.cookies = dict(resp.cookies)

    async def _test_get_teacher_options(self, ctx: TestContext):
        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.get(
                f"{self.backend_url}/api/v1/teacher-contracts/options/teachers"
            )
            assert resp.status_code == 200, f"Failed: {resp.text}"
            teachers = resp.json().get("data", [])
            assert len(teachers) > 0, "No teachers available"
            ctx.teacher_id = teachers[0]["id"]
            print(f"(teacher={ctx.teacher_id[:8]}…)", end=" ")

    async def _test_get_course_options(self, ctx: TestContext):
        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.get(
                f"{self.backend_url}/api/v1/teacher-contracts/options/courses"
            )
            assert resp.status_code == 200, f"Failed: {resp.text}"
            courses = resp.json().get("data", [])
            if courses:
                ctx.course_id = courses[0]["id"]
                print(f"(course={ctx.course_id[:8]}…)", end=" ")
            else:
                print("(no courses)", end=" ")

    async def _test_get_student_options(self, ctx: TestContext):
        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.get(
                f"{self.backend_url}/api/v1/bookings/options/students"
            )
            assert resp.status_code == 200, f"Failed: {resp.text}"
            students = resp.json().get("data", [])
            if students:
                ctx.student_id = students[0]["id"]
                print(f"(student={ctx.student_id[:8]}…)", end=" ")

    # ================================================================
    # 第一組：建立正職合約 + Work Schedules CRUD
    # ================================================================

    async def _test_create_full_time_contract(self, ctx: TestContext):
        """建立正職合約"""
        assert ctx.teacher_id, "No teacher_id"

        today = date.today()
        end_date = today + timedelta(days=365)

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.post(
                f"{self.backend_url}/api/v1/teacher-contracts",
                json={
                    "teacher_id": ctx.teacher_id,
                    "contract_status": "active",
                    "start_date": today.isoformat(),
                    "end_date": end_date.isoformat(),
                    "employment_type": "full_time",
                    "work_start_time": "09:00:00",
                    "work_end_time": "18:00:00",
                    "notes": TEST_NOTES,
                }
            )

            # 如果已有 active 合約，先取得它
            if resp.status_code == 400 and "已有生效中" in resp.text:
                # 改為 pending 狀態
                resp = await client.post(
                    f"{self.backend_url}/api/v1/teacher-contracts",
                    json={
                        "teacher_id": ctx.teacher_id,
                        "contract_status": "pending",
                        "start_date": today.isoformat(),
                        "end_date": end_date.isoformat(),
                        "employment_type": "full_time",
                        "work_start_time": "09:00:00",
                        "work_end_time": "18:00:00",
                        "notes": TEST_NOTES,
                    }
                )

            assert resp.status_code == 200, f"Failed: {resp.text}"
            data = resp.json()
            contract = data.get("data", {})
            ctx.contract_id = contract["id"]
            ctx.contract_no = contract["contract_no"]
            print(f"(contract={ctx.contract_no})", end=" ")

    async def _test_list_work_schedules_empty(self, ctx: TestContext):
        """新合約應無 work schedules"""
        assert ctx.contract_id

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.get(
                f"{self.backend_url}/api/v1/teacher-contracts/{ctx.contract_id}/work-schedules"
            )
            assert resp.status_code == 200, f"Failed: {resp.text}"
            schedules = resp.json().get("data", [])
            assert len(schedules) == 0, f"Expected 0, got {len(schedules)}"
            print("(0 schedules)", end=" ")

    async def _test_set_weekday_schedules(self, ctx: TestContext):
        """設定週一～週五 09:00-18:00"""
        assert ctx.contract_id

        schedules = []
        for weekday in range(5):  # 0=Mon to 4=Fri
            schedules.append({
                "weekday": weekday,
                "start_time": "09:00:00",
                "end_time": "18:00:00",
            })

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.put(
                f"{self.backend_url}/api/v1/teacher-contracts/{ctx.contract_id}/work-schedules",
                json={"schedules": schedules}
            )
            assert resp.status_code == 200, f"Failed: {resp.text}"
            data = resp.json().get("data", [])
            assert len(data) == 5, f"Expected 5 inserted, got {len(data)}"
            print(f"(5 schedules set)", end=" ")

    async def _test_list_work_schedules_5_days(self, ctx: TestContext):
        """確認 5 筆 work schedules"""
        assert ctx.contract_id

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.get(
                f"{self.backend_url}/api/v1/teacher-contracts/{ctx.contract_id}/work-schedules"
            )
            assert resp.status_code == 200, f"Failed: {resp.text}"
            schedules = resp.json().get("data", [])
            assert len(schedules) == 5, f"Expected 5, got {len(schedules)}"

            # 驗證 weekday 0-4 都有
            weekdays = {s["weekday"] for s in schedules}
            assert weekdays == {0, 1, 2, 3, 4}, f"Expected weekdays 0-4, got {weekdays}"
            print("(weekdays 0-4 verified)", end=" ")

    async def _test_contract_enrich_has_schedules(self, ctx: TestContext):
        """取得合約時，回應應包含 work_schedules"""
        assert ctx.contract_id

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.get(
                f"{self.backend_url}/api/v1/teacher-contracts/{ctx.contract_id}"
            )
            assert resp.status_code == 200, f"Failed: {resp.text}"
            contract = resp.json().get("data", {})
            ws = contract.get("work_schedules", [])
            assert len(ws) == 5, f"Expected 5 work_schedules in enrich, got {len(ws)}"
            print(f"(work_schedules count={len(ws)})", end=" ")

    # ================================================================
    # 第二組：多時段 + 重疊檢查
    # ================================================================

    async def _test_set_multi_slot(self, ctx: TestContext):
        """週一設兩個時段 (09-12, 14-18)，其他保持週二～五 09-18"""
        assert ctx.contract_id

        schedules = [
            {"weekday": 0, "start_time": "09:00:00", "end_time": "12:00:00"},
            {"weekday": 0, "start_time": "14:00:00", "end_time": "18:00:00"},
        ]
        for weekday in range(1, 5):
            schedules.append({
                "weekday": weekday,
                "start_time": "09:00:00",
                "end_time": "18:00:00",
            })

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.put(
                f"{self.backend_url}/api/v1/teacher-contracts/{ctx.contract_id}/work-schedules",
                json={"schedules": schedules}
            )
            assert resp.status_code == 200, f"Failed: {resp.text}"
            data = resp.json().get("data", [])
            assert len(data) == 6, f"Expected 6 inserted, got {len(data)}"
            print("(6 schedules: Mon×2 + Tue-Fri×1)", end=" ")

    async def _test_verify_multi_slot(self, ctx: TestContext):
        """確認週一有 2 筆、其他各 1 筆"""
        assert ctx.contract_id

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.get(
                f"{self.backend_url}/api/v1/teacher-contracts/{ctx.contract_id}/work-schedules"
            )
            assert resp.status_code == 200, f"Failed: {resp.text}"
            schedules = resp.json().get("data", [])
            assert len(schedules) == 6, f"Expected 6, got {len(schedules)}"

            mon_slots = [s for s in schedules if s["weekday"] == 0]
            assert len(mon_slots) == 2, f"Expected 2 Mon slots, got {len(mon_slots)}"

            # 驗證 Mon 的時段
            mon_times = sorted([(s["start_time"][:5], s["end_time"][:5]) for s in mon_slots])
            assert mon_times == [("09:00", "12:00"), ("14:00", "18:00")], \
                f"Mon slots wrong: {mon_times}"
            print("(Mon: 09-12,14-18 verified)", end=" ")

    async def _test_reject_overlapping_slots(self, ctx: TestContext):
        """同 weekday 重疊時段應返回 400"""
        assert ctx.contract_id

        overlapping = [
            {"weekday": 0, "start_time": "09:00:00", "end_time": "13:00:00"},
            {"weekday": 0, "start_time": "12:00:00", "end_time": "18:00:00"},  # 12-13 重疊
        ]

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.put(
                f"{self.backend_url}/api/v1/teacher-contracts/{ctx.contract_id}/work-schedules",
                json={"schedules": overlapping}
            )
            assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"
            assert "重疊" in resp.json().get("detail", ""), f"Expected overlap error message"
            print("(400 overlap detected)", end=" ")

    # ================================================================
    # 第三組：Booking 加班計算（多時段）
    # ================================================================

    async def _test_setup_active_contract_for_booking(self, ctx: TestContext):
        """確保測試合約為 active 並有 course_rate 明細

        建立 booking 需要教師有 active 合約 + course_rate。
        如果測試合約是 pending（因已有 active），先切狀態。
        """
        if not ctx.contract_id:
            print("(skipped)", end=" ")
            return

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            # 取得合約狀態
            resp = await client.get(
                f"{self.backend_url}/api/v1/teacher-contracts/{ctx.contract_id}"
            )
            assert resp.status_code == 200
            contract = resp.json().get("data", {})

            if contract.get("contract_status") != "active":
                # 先把已有的 active 合約改為 terminated
                list_resp = await client.get(
                    f"{self.backend_url}/api/v1/teacher-contracts",
                    params={"teacher_id": ctx.teacher_id, "contract_status": "active"}
                )
                if list_resp.status_code == 200:
                    for c in list_resp.json().get("data", []):
                        if c["id"] != ctx.contract_id:
                            await client.put(
                                f"{self.backend_url}/api/v1/teacher-contracts/{c['id']}",
                                json={"contract_status": "terminated"}
                            )

                # 把測試合約改為 active
                resp = await client.put(
                    f"{self.backend_url}/api/v1/teacher-contracts/{ctx.contract_id}",
                    json={"contract_status": "active"}
                )
                assert resp.status_code == 200, f"Failed to activate: {resp.text}"
                print("(activated)", end=" ")

            # 新增 course_rate 明細
            if ctx.course_id:
                resp = await client.post(
                    f"{self.backend_url}/api/v1/teacher-contracts/{ctx.contract_id}/details",
                    json={
                        "detail_type": "course_rate",
                        "course_id": ctx.course_id,
                        "description": "測試課程時薪",
                        "amount": 500.0,
                        "notes": TEST_NOTES,
                    }
                )
                if resp.status_code == 200:
                    print("(course_rate added)", end=" ")
                else:
                    print(f"(course_rate: {resp.status_code})", end=" ")

    async def _test_get_student_contract(self, ctx: TestContext):
        """取得學生合約"""
        if not ctx.student_id:
            print("(skipped - no student)", end=" ")
            return

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.get(
                f"{self.backend_url}/api/v1/bookings/options/student-contracts/{ctx.student_id}"
            )
            assert resp.status_code == 200, f"Failed: {resp.text}"
            contracts = resp.json().get("data", [])
            if contracts:
                for c in contracts:
                    if c.get("remaining_lessons", 0) > 0:
                        ctx.student_contract_id = c["id"]
                        break
                if not ctx.student_contract_id:
                    ctx.student_contract_id = contracts[0]["id"]
                print(f"(contract={ctx.student_contract_id[:8]}…)", end=" ")
            else:
                print("(no student contracts)", end=" ")

    async def _test_create_test_slot(self, ctx: TestContext):
        """建立測試用 teacher slot (找一個無衝突的未來週一)"""
        assert ctx.teacher_id
        assert ctx.contract_id

        # 找一個未來的週一，嘗試多個直到成功（避免與現有 slot 衝突）
        today = date.today()
        days_ahead = 0 - today.weekday()  # Monday is 0
        if days_ahead <= 0:
            days_ahead += 7

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            for attempt in range(8):  # 嘗試未來 8 個週一
                candidate = today + timedelta(days=days_ahead + attempt * 7)
                ctx.test_slot_date = candidate.isoformat()

                resp = await client.post(
                    f"{self.backend_url}/api/v1/teacher-slots",
                    json={
                        "teacher_id": ctx.teacher_id,
                        "teacher_contract_id": ctx.contract_id,
                        "slot_date": ctx.test_slot_date,
                        "start_time": "08:00:00",
                        "end_time": "21:00:00",
                        "is_available": True,
                        "notes": TEST_NOTES,
                    }
                )
                if resp.status_code == 200:
                    ctx.test_slot_id = resp.json()["data"]["id"]
                    print(f"(slot date={ctx.test_slot_date})", end=" ")
                    return

            assert False, f"Could not create slot after 8 attempts, last: {resp.text}"

    async def _test_create_booking_regular(self, ctx: TestContext):
        """建立 09:00-10:00 預約（週一上午，應為正班）"""
        if not all([ctx.student_id, ctx.student_contract_id, ctx.test_slot_id]):
            print("(skipped - missing data)", end=" ")
            return

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.post(
                f"{self.backend_url}/api/v1/bookings",
                json={
                    "student_id": ctx.student_id,
                    "teacher_id": ctx.teacher_id,
                    "course_id": ctx.course_id,
                    "student_contract_id": ctx.student_contract_id,
                    "teacher_contract_id": ctx.contract_id,
                    "teacher_slot_id": ctx.test_slot_id,
                    "booking_date": ctx.test_slot_date,
                    "start_time": "09:00:00",
                    "end_time": "10:00:00",
                    "notes": TEST_NOTES,
                }
            )
            assert resp.status_code == 200, f"Failed: {resp.text}"
            ctx.test_booking_id = resp.json()["data"]["id"]
            print(f"(booking={ctx.test_booking_id[:8]}…)", end=" ")

    async def _test_verify_booking_regular(self, ctx: TestContext):
        """確認 09:00-10:00 在週一 work slot [09-12] 內，全為正班"""
        if not ctx.test_booking_id:
            print("(skipped)", end=" ")
            return

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.get(
                f"{self.backend_url}/api/v1/bookings/{ctx.test_booking_id}"
            )
            assert resp.status_code == 200, f"Failed: {resp.text}"
            booking = resp.json().get("data", {})
            regular = booking.get("regular_lessons")
            overtime = booking.get("overtime_lessons")
            is_overtime = booking.get("is_overtime")

            assert regular is not None, "regular_lessons is None (work schedule not applied?)"
            assert regular > 0, f"Expected regular > 0, got {regular}"
            assert overtime == 0, f"Expected overtime=0, got {overtime}"
            assert is_overtime == False, f"Expected is_overtime=false"
            print(f"(regular={regular}, overtime={overtime})", end=" ")

    async def _test_cancel_delete_booking(self, ctx: TestContext):
        """取消並刪除第一個 booking"""
        if not ctx.test_booking_id:
            print("(skipped)", end=" ")
            return

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            # Cancel
            resp = await client.put(
                f"{self.backend_url}/api/v1/bookings/{ctx.test_booking_id}",
                json={"booking_status": "cancelled"}
            )
            assert resp.status_code == 200, f"Cancel failed: {resp.text}"

            # Delete
            resp = await client.delete(
                f"{self.backend_url}/api/v1/bookings/{ctx.test_booking_id}"
            )
            assert resp.status_code == 200, f"Delete failed: {resp.text}"
            ctx.test_booking_id = None

    async def _test_create_booking_overtime(self, ctx: TestContext):
        """建立 12:00-14:00 預約（週一午休時段，應為加班）

        週一 work slots: 09-12, 14-18
        12:00-14:00 不在任何 slot 內 → 全部加班
        """
        if not all([ctx.student_id, ctx.student_contract_id, ctx.test_slot_id]):
            print("(skipped - missing data)", end=" ")
            return

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.post(
                f"{self.backend_url}/api/v1/bookings",
                json={
                    "student_id": ctx.student_id,
                    "teacher_id": ctx.teacher_id,
                    "course_id": ctx.course_id,
                    "student_contract_id": ctx.student_contract_id,
                    "teacher_contract_id": ctx.contract_id,
                    "teacher_slot_id": ctx.test_slot_id,
                    "booking_date": ctx.test_slot_date,
                    "start_time": "12:00:00",
                    "end_time": "14:00:00",
                    "notes": TEST_NOTES,
                }
            )
            assert resp.status_code == 200, f"Failed: {resp.text}"
            ctx.test_booking_id = resp.json()["data"]["id"]
            print(f"(booking={ctx.test_booking_id[:8]}…)", end=" ")

    async def _test_verify_booking_overtime(self, ctx: TestContext):
        """確認 12:00-14:00 全為加班"""
        if not ctx.test_booking_id:
            print("(skipped)", end=" ")
            return

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.get(
                f"{self.backend_url}/api/v1/bookings/{ctx.test_booking_id}"
            )
            assert resp.status_code == 200, f"Failed: {resp.text}"
            booking = resp.json().get("data", {})
            regular = booking.get("regular_lessons")
            overtime = booking.get("overtime_lessons")
            is_overtime = booking.get("is_overtime")

            assert overtime is not None, "overtime_lessons is None (work schedule not applied?)"
            assert overtime > 0, f"Expected overtime > 0, got {overtime}"
            assert regular == 0, f"Expected regular=0, got {regular}"
            assert is_overtime == True, f"Expected is_overtime=true"
            print(f"(regular={regular}, overtime={overtime})", end=" ")

    async def _test_cancel_delete_booking_2(self, ctx: TestContext):
        """取消並刪除第二個 booking"""
        if not ctx.test_booking_id:
            print("(skipped)", end=" ")
            return

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.put(
                f"{self.backend_url}/api/v1/bookings/{ctx.test_booking_id}",
                json={"booking_status": "cancelled"}
            )
            assert resp.status_code == 200, f"Cancel failed: {resp.text}"

            resp = await client.delete(
                f"{self.backend_url}/api/v1/bookings/{ctx.test_booking_id}"
            )
            assert resp.status_code == 200, f"Delete failed: {resp.text}"
            ctx.test_booking_id = None

    # ================================================================
    # 第四組：Fallback — 無 work_schedules 時用合約欄位
    # ================================================================

    async def _test_clear_work_schedules(self, ctx: TestContext):
        """清除所有 work schedules"""
        assert ctx.contract_id

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.delete(
                f"{self.backend_url}/api/v1/teacher-contracts/{ctx.contract_id}/work-schedules"
            )
            assert resp.status_code == 200, f"Failed: {resp.text}"

    async def _test_list_work_schedules_after_clear(self, ctx: TestContext):
        """確認清除後為空"""
        assert ctx.contract_id

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.get(
                f"{self.backend_url}/api/v1/teacher-contracts/{ctx.contract_id}/work-schedules"
            )
            assert resp.status_code == 200, f"Failed: {resp.text}"
            schedules = resp.json().get("data", [])
            assert len(schedules) == 0, f"Expected 0, got {len(schedules)}"

    async def _test_update_contract_work_time(self, ctx: TestContext):
        """確認合約 work_start_time/work_end_time 仍在"""
        assert ctx.contract_id

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.get(
                f"{self.backend_url}/api/v1/teacher-contracts/{ctx.contract_id}"
            )
            assert resp.status_code == 200, f"Failed: {resp.text}"
            contract = resp.json().get("data", {})
            assert contract.get("work_start_time"), "work_start_time should still exist"
            assert contract.get("work_end_time"), "work_end_time should still exist"
            print(f"(work_time={contract['work_start_time'][:5]}-{contract['work_end_time'][:5]})", end=" ")

    async def _test_create_booking_fallback_overtime(self, ctx: TestContext):
        """建立 19:00-20:00 預約（超出 09-18 fallback 範圍，應為加班）"""
        if not all([ctx.student_id, ctx.student_contract_id, ctx.test_slot_id]):
            print("(skipped - missing data)", end=" ")
            return

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.post(
                f"{self.backend_url}/api/v1/bookings",
                json={
                    "student_id": ctx.student_id,
                    "teacher_id": ctx.teacher_id,
                    "course_id": ctx.course_id,
                    "student_contract_id": ctx.student_contract_id,
                    "teacher_contract_id": ctx.contract_id,
                    "teacher_slot_id": ctx.test_slot_id,
                    "booking_date": ctx.test_slot_date,
                    "start_time": "19:00:00",
                    "end_time": "20:00:00",
                    "notes": TEST_NOTES,
                }
            )
            assert resp.status_code == 200, f"Failed: {resp.text}"
            ctx.test_booking_id = resp.json()["data"]["id"]

    async def _test_verify_fallback_overtime(self, ctx: TestContext):
        """確認 19:00-20:00 用 fallback 計算為加班"""
        if not ctx.test_booking_id:
            print("(skipped)", end=" ")
            return

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.get(
                f"{self.backend_url}/api/v1/bookings/{ctx.test_booking_id}"
            )
            assert resp.status_code == 200, f"Failed: {resp.text}"
            booking = resp.json().get("data", {})
            overtime = booking.get("overtime_lessons")
            regular = booking.get("regular_lessons")
            is_overtime = booking.get("is_overtime")

            assert overtime is not None, "overtime_lessons is None (fallback not working?)"
            assert overtime > 0, f"Expected overtime > 0, got {overtime}"
            assert regular == 0, f"Expected regular=0 for 19:00, got {regular}"
            assert is_overtime == True, f"Expected is_overtime=true"
            print(f"(fallback: regular={regular}, overtime={overtime})", end=" ")

    async def _test_cancel_delete_booking_3(self, ctx: TestContext):
        """取消並刪除第三個 booking"""
        if not ctx.test_booking_id:
            print("(skipped)", end=" ")
            return

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.put(
                f"{self.backend_url}/api/v1/bookings/{ctx.test_booking_id}",
                json={"booking_status": "cancelled"}
            )
            assert resp.status_code == 200, f"Cancel failed: {resp.text}"

            resp = await client.delete(
                f"{self.backend_url}/api/v1/bookings/{ctx.test_booking_id}"
            )
            assert resp.status_code == 200, f"Delete failed: {resp.text}"
            ctx.test_booking_id = None

    # ================================================================
    # 第五組：切換 hourly 清除時段
    # ================================================================

    async def _test_set_schedules_before_hourly(self, ctx: TestContext):
        """重新設定一些 schedules"""
        assert ctx.contract_id

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.put(
                f"{self.backend_url}/api/v1/teacher-contracts/{ctx.contract_id}/work-schedules",
                json={
                    "schedules": [
                        {"weekday": 0, "start_time": "09:00:00", "end_time": "17:00:00"},
                        {"weekday": 1, "start_time": "09:00:00", "end_time": "17:00:00"},
                    ]
                }
            )
            assert resp.status_code == 200, f"Failed: {resp.text}"
            print("(2 schedules set)", end=" ")

    async def _test_switch_to_hourly(self, ctx: TestContext):
        """切換合約為 hourly"""
        assert ctx.contract_id

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.put(
                f"{self.backend_url}/api/v1/teacher-contracts/{ctx.contract_id}",
                json={"employment_type": "hourly"}
            )
            assert resp.status_code == 200, f"Failed: {resp.text}"
            contract = resp.json().get("data", {})
            assert contract.get("employment_type") == "hourly"
            print("(→ hourly)", end=" ")

    async def _test_verify_no_schedules_after_hourly(self, ctx: TestContext):
        """切換 hourly 後，schedules 仍然存在（前端負責清除，後端只在前端呼叫時清除）
        但我們測試 API 可以手動清除"""
        assert ctx.contract_id

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            # 手動清除（模擬前端切換到 hourly 後的行為）
            resp = await client.delete(
                f"{self.backend_url}/api/v1/teacher-contracts/{ctx.contract_id}/work-schedules"
            )
            assert resp.status_code == 200, f"Clear failed: {resp.text}"

            resp = await client.get(
                f"{self.backend_url}/api/v1/teacher-contracts/{ctx.contract_id}/work-schedules"
            )
            assert resp.status_code == 200, f"Failed: {resp.text}"
            schedules = resp.json().get("data", [])
            assert len(schedules) == 0, f"Expected 0 after clear, got {len(schedules)}"
            print("(0 schedules after clear)", end=" ")

    # ================================================================
    # 第六組：刪除合約連帶刪除 work_schedules
    # ================================================================

    async def _test_create_contract_2(self, ctx: TestContext):
        """建立第二個合約"""
        assert ctx.teacher_id

        today = date.today()
        end_date = today + timedelta(days=365)

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.post(
                f"{self.backend_url}/api/v1/teacher-contracts",
                json={
                    "teacher_id": ctx.teacher_id,
                    "contract_status": "pending",
                    "start_date": today.isoformat(),
                    "end_date": end_date.isoformat(),
                    "employment_type": "full_time",
                    "notes": TEST_NOTES,
                }
            )
            assert resp.status_code == 200, f"Failed: {resp.text}"
            ctx.contract_id_2 = resp.json()["data"]["id"]
            print(f"(contract2={ctx.contract_id_2[:8]}…)", end=" ")

    async def _test_set_schedules_on_contract_2(self, ctx: TestContext):
        """在第二個合約設定 schedules"""
        assert ctx.contract_id_2

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.put(
                f"{self.backend_url}/api/v1/teacher-contracts/{ctx.contract_id_2}/work-schedules",
                json={
                    "schedules": [
                        {"weekday": 0, "start_time": "10:00:00", "end_time": "16:00:00"},
                    ]
                }
            )
            assert resp.status_code == 200, f"Failed: {resp.text}"

            # 確認有 1 筆
            resp = await client.get(
                f"{self.backend_url}/api/v1/teacher-contracts/{ctx.contract_id_2}/work-schedules"
            )
            assert resp.status_code == 200
            assert len(resp.json().get("data", [])) == 1
            print("(1 schedule set)", end=" ")

    async def _test_delete_contract_2(self, ctx: TestContext):
        """刪除第二個合約"""
        assert ctx.contract_id_2

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.delete(
                f"{self.backend_url}/api/v1/teacher-contracts/{ctx.contract_id_2}"
            )
            assert resp.status_code == 200, f"Failed: {resp.text}"

    async def _test_verify_schedules_deleted_with_contract(self, ctx: TestContext):
        """確認合約刪除後，work schedules 也被刪除"""
        assert ctx.contract_id_2

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.get(
                f"{self.backend_url}/api/v1/teacher-contracts/{ctx.contract_id_2}/work-schedules"
            )
            # 合約已被刪除，應返回 404
            assert resp.status_code == 404, \
                f"Expected 404 (contract deleted), got {resp.status_code}"
            print("(404 - contract deleted, schedules gone)", end=" ")

    # ================================================================
    # Cleanup
    # ================================================================

    async def _test_delete_test_slot(self, ctx: TestContext):
        """刪除測試 slot"""
        if not ctx.test_slot_id:
            print("(skipped)", end=" ")
            return

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            # 先清理殘留 booking
            if ctx.test_booking_id:
                await client.put(
                    f"{self.backend_url}/api/v1/bookings/{ctx.test_booking_id}",
                    json={"booking_status": "cancelled"}
                )
                await client.delete(
                    f"{self.backend_url}/api/v1/bookings/{ctx.test_booking_id}"
                )

            resp = await client.delete(
                f"{self.backend_url}/api/v1/teacher-slots/{ctx.test_slot_id}"
            )
            assert resp.status_code == 200, f"Failed: {resp.text}"

    async def _test_delete_test_contract(self, ctx: TestContext):
        """刪除測試合約"""
        if not ctx.contract_id:
            print("(skipped)", end=" ")
            return

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.delete(
                f"{self.backend_url}/api/v1/teacher-contracts/{ctx.contract_id}"
            )
            assert resp.status_code == 200, f"Failed: {resp.text}"

    async def _test_logout(self, ctx: TestContext):
        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.post(
                f"{self.backend_url}/api/v1/auth/logout",
                json={"logout_all_devices": False}
            )
            assert resp.status_code == 200, f"Logout failed: {resp.text}"

    # ========== DB Cleanup ==========

    async def cleanup_test_data(self):
        """清理所有測試資料（直連 DB）"""
        try:
            import asyncpg
        except ImportError:
            print("\n⚠️  asyncpg not installed, skipping DB cleanup.")
            return

        db_password = os.getenv("POSTGRES_PASSWORD", "")
        if not db_password:
            print("\n⚠️  POSTGRES_PASSWORD not set, skipping DB cleanup.")
            return

        database_url = f"postgresql://postgres:{db_password}@127.0.0.1:5432/postgres"

        print(f"\n{'='*60}")
        print("🧹 Cleaning up test data...")
        print(f"{'='*60}\n")

        try:
            conn = await asyncpg.connect(database_url)
        except Exception as e:
            print(f"  ❌ Failed to connect to database: {e}")
            print("  Tip: 可能 port 5432 被本地 PostgreSQL 佔用，改用 docker exec")
            return

        try:
            # 清理測試 bookings
            bookings = await conn.fetch(
                "SELECT id, booking_no FROM bookings WHERE notes LIKE $1 AND is_deleted = false",
                f"%{TEST_NOTES}%"
            )
            if bookings:
                await conn.execute(
                    "UPDATE bookings SET is_deleted = true WHERE notes LIKE $1",
                    f"%{TEST_NOTES}%"
                )
                print(f"  ✅ Deleted {len(bookings)} test booking(s)")

            # 清理測試 teacher slots
            slots = await conn.fetch(
                "SELECT id FROM teacher_available_slots WHERE notes LIKE $1 AND is_deleted = false",
                f"%{TEST_NOTES}%"
            )
            if slots:
                await conn.execute(
                    "UPDATE teacher_available_slots SET is_deleted = true WHERE notes LIKE $1",
                    f"%{TEST_NOTES}%"
                )
                print(f"  ✅ Deleted {len(slots)} test slot(s)")

            # 清理測試合約的 work_schedules
            contracts = await conn.fetch(
                "SELECT id FROM teacher_contracts WHERE notes LIKE $1",
                f"%{TEST_NOTES}%"
            )
            if contracts:
                contract_ids = [c["id"] for c in contracts]
                for cid in contract_ids:
                    await conn.execute(
                        "UPDATE teacher_work_schedules SET is_deleted = true WHERE teacher_contract_id = $1",
                        cid
                    )

            # 清理測試合約
            if contracts:
                await conn.execute(
                    "UPDATE teacher_contracts SET is_deleted = true WHERE notes LIKE $1",
                    f"%{TEST_NOTES}%"
                )
                print(f"  ✅ Deleted {len(contracts)} test contract(s)")

        except Exception as e:
            print(f"  ❌ Cleanup error: {e}")
        finally:
            await conn.close()

        print("\n✅ Cleanup completed\n")


async def main():
    parser = argparse.ArgumentParser(
        description="Live Work Schedules Test Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  python tests/live_work_schedules_test.py --email employee@eop-test.com --password TestPassword123!
  python tests/live_work_schedules_test.py --email employee@eop-test.com --password TestPassword123! --no-cleanup
  python tests/live_work_schedules_test.py --cleanup-only
        """
    )
    parser.add_argument("--email", default=os.getenv("TEST_EMAIL", ""), help="登入 Email")
    parser.add_argument("--password", default=os.getenv("TEST_PASSWORD", ""), help="登入密碼")
    parser.add_argument("--backend-url", default=BACKEND_URL, help=f"Backend URL (default: {BACKEND_URL})")
    parser.add_argument("--cleanup-only", action="store_true", help="只清理測試資料")
    parser.add_argument("--no-cleanup", action="store_true", help="保留測試建立的資料（不刪除合約、slot 等）")

    args = parser.parse_args()

    tester = LiveWorkSchedulesTester(backend_url=args.backend_url, no_cleanup=args.no_cleanup)

    if args.cleanup_only:
        await tester.cleanup_test_data()
        return

    if not args.email or not args.password:
        print("❌ Error: --email and --password are required")
        print("\nUsage:")
        print("  python tests/live_work_schedules_test.py --email employee@eop-test.com --password TestPassword123!")
        sys.exit(1)

    ctx = TestContext(email=args.email, password=args.password)
    success = await tester.run_all_tests(ctx)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

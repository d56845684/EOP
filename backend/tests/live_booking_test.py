#!/usr/bin/env python3
"""
Live Booking Test Script

測試真實運行中的預約服務，涵蓋 30 分鐘區塊多預約系統。

使用方式:
    # 執行所有測試
    python tests/live_booking_test.py --email admin@example.com --password yourpassword

    # 只清理測試資料
    python tests/live_booking_test.py --cleanup-only
"""

import httpx
import asyncio
import argparse
import sys
import os
from datetime import datetime, date, time, timedelta
from typing import Optional
from dataclasses import dataclass, field

# 設定 (使用 127.0.0.1 避免 IPv6 問題)
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8001")
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://127.0.0.1:8000")
SERVICE_ROLE_KEY = os.getenv("SERVICE_ROLE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoic2VydmljZV9yb2xlIiwiaXNzIjoic3VwYWJhc2UiLCJpYXQiOjE3NjczMjM3NDcsImV4cCI6MTkyNTAwMzc0N30.h8XFj9oZdc0ZaiczkL83AkQtf6zKDTrdTO3SxtrZVU8")

# 測試標記 — cleanup 用此字串篩選
TEST_NOTES = "live_booking_test"


@dataclass
class TestResult:
    name: str
    passed: bool
    message: str = ""
    duration_ms: float = 0


@dataclass
class TestContext:
    """測試上下文"""
    # 登入資訊
    email: str = ""
    password: str = ""
    cookies: dict = field(default_factory=dict)
    user_id: Optional[str] = None

    # 選項資料 (從 API 取得)
    student_id: Optional[str] = None
    teacher_id: Optional[str] = None
    course_id: Optional[str] = None
    student_contract_id: Optional[str] = None
    teacher_contract_id: Optional[str] = None

    # 測試建立的 teacher slot（自行建立，確保乾淨的 3 小時 slot）
    test_slot_id: Optional[str] = None
    test_slot_date: Optional[str] = None  # ISO format

    # Booking A
    created_booking_id: Optional[str] = None
    created_booking_no: Optional[str] = None
    # Booking B（測試多預約）
    created_booking_id_2: Optional[str] = None
    created_booking_no_2: Optional[str] = None
    # Booking C（測試 is_booked 滿）
    created_booking_id_3: Optional[str] = None
    created_booking_no_3: Optional[str] = None


class LiveBookingTester:
    def __init__(self, backend_url: str, supabase_url: str, service_role_key: str):
        self.backend_url = backend_url.rstrip("/")
        self.supabase_url = supabase_url.rstrip("/")
        self.service_role_key = service_role_key
        self.results: list[TestResult] = []

        self.client_kwargs = {
            "follow_redirects": True,
            "timeout": httpx.Timeout(30.0, connect=10.0)
        }

    async def run_all_tests(self, ctx: TestContext) -> bool:
        """執行所有測試"""
        print(f"\n{'='*60}")
        print(f"🧪 Live Booking Tests (30-min Block Multi-Booking)")
        print(f"{'='*60}")
        print(f"Backend URL: {self.backend_url}")
        print(f"Test User: {ctx.email}")
        print(f"{'='*60}\n")

        tests = [
            # ── 第一組：Setup 與基礎選項 ──
            ("Health Check", self._test_health_check),
            ("Login", self._test_login),
            ("Get Options - Students", self._test_get_student_options),
            ("Get Options - Teachers", self._test_get_teacher_options),
            ("Get Options - Courses", self._test_get_course_options),
            ("Get Options - Student Contracts", self._test_get_student_contracts),
            ("Get Options - Teacher Contracts", self._test_get_teacher_contracts),
            ("Create Test Slot (09:00-12:00)", self._test_create_test_slot),
            ("Get Slot Availability (Empty)", self._test_slot_availability_empty),

            # ── 第二組：30 分鐘邊界驗證 ──
            ("Reject Non-30min Boundary", self._test_reject_non_30min_boundary),
            ("Reject Duration Not Multiple of 30", self._test_reject_non_multiple_30),

            # ── 第三組：多預約與重疊檢測 ──
            ("Create Booking A (09:00-10:00)", self._test_create_booking_a),
            ("Get Slot Availability (After A)", self._test_slot_availability_after_a),
            ("Create Booking B (10:00-11:00)", self._test_create_booking_b),
            ("Reject Overlapping Booking", self._test_reject_overlapping),
            ("Get Slot Availability (After B)", self._test_slot_availability_after_b),

            # ── 第四組：預約已滿（is_booked）狀態 ──
            ("Check Slot NOT Fully Booked", self._test_slot_not_fully_booked),
            ("Create Booking C (11:00-12:00)", self._test_create_booking_c),
            ("Check Slot Fully Booked", self._test_slot_fully_booked),
            ("Cancel Booking C", self._test_cancel_booking_c),
            ("Check Slot NOT Fully Booked Again", self._test_slot_not_fully_booked_again),

            # ── 第五組：Update & Delete ──
            ("Get Single Booking", self._test_get_booking),
            ("Update Booking A (→confirmed)", self._test_update_booking_confirmed),
            ("List Bookings (After Create)", self._test_list_bookings_after_create),
            ("Cancel Booking A (for deletion)", self._test_cancel_booking_a),
            ("Delete Booking A", self._test_delete_booking_a),
            ("Delete Booking B", self._test_delete_booking_b),
            ("Verify Deletion", self._test_verify_deletion),

            # ── 第六組：清理與登出 ──
            ("Delete Test Slot", self._test_delete_test_slot),
            ("Logout", self._test_logout),
        ]

        for name, test_fn in tests:
            result = await self._run_single_test(name, test_fn, ctx)
            self.results.append(result)

            # 如果登入失敗，跳過後續測試
            if name == "Login" and not result.passed:
                print("\n⚠️  Login failed, skipping remaining tests")
                break

            # 如果缺少必要選項，跳過後續測試
            if name == "Get Options - Teacher Contracts" and not all([
                ctx.student_id, ctx.teacher_id, ctx.course_id,
                ctx.student_contract_id, ctx.teacher_contract_id
            ]):
                print("\n⚠️  Missing required options, skipping to logout")
                logout_result = await self._run_single_test("Logout", self._test_logout, ctx)
                self.results.append(logout_result)
                break

        self._print_summary()
        return all(r.passed for r in self.results)

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

    # ========== 共用 helper ==========

    def _booking_base_data(self, ctx: TestContext) -> dict:
        """產生預約的共用基礎資料"""
        return {
            "student_id": ctx.student_id,
            "teacher_id": ctx.teacher_id,
            "course_id": ctx.course_id,
            "student_contract_id": ctx.student_contract_id,
            "teacher_contract_id": ctx.teacher_contract_id,
            "teacher_slot_id": ctx.test_slot_id,
            "booking_date": ctx.test_slot_date,
            "notes": TEST_NOTES,
        }

    # ================================================================
    # 第一組：Setup 與基礎選項
    # ================================================================

    async def _test_health_check(self, ctx: TestContext):
        """測試健康檢查"""
        async with httpx.AsyncClient(**self.client_kwargs) as client:
            resp = await client.get(f"{self.backend_url}/api/v1/health")
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    async def _test_login(self, ctx: TestContext):
        """登入取得認證"""
        async with httpx.AsyncClient(**self.client_kwargs) as client:
            resp = await client.post(
                f"{self.backend_url}/api/v1/auth/login",
                json={"email": ctx.email, "password": ctx.password}
            )

            assert resp.status_code == 200, f"Login failed: {resp.text}"
            data = resp.json()
            assert data.get("success"), f"Login not successful: {data}"

            ctx.cookies = dict(resp.cookies)
            if "user" in data:
                ctx.user_id = data["user"].get("id")

    async def _test_get_student_options(self, ctx: TestContext):
        """取得學生選項"""
        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.get(f"{self.backend_url}/api/v1/bookings/options/students")

            assert resp.status_code == 200, f"Failed: {resp.text}"
            students = resp.json().get("data", [])

            if students:
                ctx.student_id = students[0]["id"]
                print(f"(found {len(students)} students)", end=" ")
            else:
                print("(no students found)", end=" ")

    async def _test_get_teacher_options(self, ctx: TestContext):
        """取得教師選項"""
        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.get(f"{self.backend_url}/api/v1/bookings/options/teachers")

            assert resp.status_code == 200, f"Failed: {resp.text}"
            teachers = resp.json().get("data", [])

            if teachers:
                ctx.teacher_id = teachers[0]["id"]
                print(f"(found {len(teachers)} teachers)", end=" ")
            else:
                print("(no teachers found)", end=" ")

    async def _test_get_course_options(self, ctx: TestContext):
        """取得課程選項"""
        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.get(f"{self.backend_url}/api/v1/bookings/options/courses")

            assert resp.status_code == 200, f"Failed: {resp.text}"
            courses = resp.json().get("data", [])

            if courses:
                ctx.course_id = courses[0]["id"]
                print(f"(found {len(courses)} courses)", end=" ")
            else:
                print("(no courses found)", end=" ")

    async def _test_get_student_contracts(self, ctx: TestContext):
        """取得學生合約選項"""
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
                # 選擇有剩餘堂數的合約
                for c in contracts:
                    if c.get("remaining_lessons", 0) > 0:
                        ctx.student_contract_id = c["id"]
                        break
                if not ctx.student_contract_id and contracts:
                    ctx.student_contract_id = contracts[0]["id"]
                print(f"(found {len(contracts)} contracts)", end=" ")
            else:
                print("(no contracts found)", end=" ")

    async def _test_get_teacher_contracts(self, ctx: TestContext):
        """取得教師合約選項"""
        if not ctx.teacher_id:
            print("(skipped - no teacher)", end=" ")
            return

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.get(
                f"{self.backend_url}/api/v1/bookings/options/teacher-contracts/{ctx.teacher_id}"
            )

            assert resp.status_code == 200, f"Failed: {resp.text}"
            contracts = resp.json().get("data", [])

            if contracts:
                ctx.teacher_contract_id = contracts[0]["id"]
                print(f"(found {len(contracts)} contracts)", end=" ")
            else:
                print("(no contracts found)", end=" ")

    async def _test_create_test_slot(self, ctx: TestContext):
        """建立 3 小時測試 slot (09:00-12:00)，確保乾淨的測試環境"""
        missing = []
        if not ctx.teacher_id:
            missing.append("teacher")
        if not ctx.teacher_contract_id:
            missing.append("teacher_contract")
        if missing:
            raise AssertionError(f"Missing required data: {', '.join(missing)}")

        # 使用明天的日期，確保未來日期
        test_date = (date.today() + timedelta(days=1)).isoformat()
        ctx.test_slot_date = test_date

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.post(
                f"{self.backend_url}/api/v1/teacher-slots",
                json={
                    "teacher_id": ctx.teacher_id,
                    "teacher_contract_id": ctx.teacher_contract_id,
                    "slot_date": test_date,
                    "start_time": "09:00:00",
                    "end_time": "12:00:00",
                    "is_available": True,
                    "notes": TEST_NOTES,
                }
            )

            assert resp.status_code == 200, f"Failed to create slot: {resp.text}"
            data = resp.json()
            assert data.get("data"), f"No slot data returned: {data}"

            ctx.test_slot_id = data["data"]["id"]
            print(f"(slot={ctx.test_slot_id[:8]}… date={test_date})", end=" ")

    async def _test_slot_availability_empty(self, ctx: TestContext):
        """確認所有 6 個 30 分鐘區塊都 is_available=true"""
        assert ctx.test_slot_id, "No test slot created"

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.get(
                f"{self.backend_url}/api/v1/bookings/slot-availability/{ctx.test_slot_id}"
            )

            assert resp.status_code == 200, f"Failed: {resp.text}"
            blocks = resp.json().get("data", {}).get("blocks", [])

            assert len(blocks) == 6, f"Expected 6 blocks, got {len(blocks)}"
            all_available = all(b["is_available"] for b in blocks)
            assert all_available, "Expected all blocks available"
            print("(6 blocks, all available)", end=" ")

    # ================================================================
    # 第二組：30 分鐘邊界驗證
    # ================================================================

    async def _test_reject_non_30min_boundary(self, ctx: TestContext):
        """提交 start_time='09:15' 的預約，預期 422"""
        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            booking_data = self._booking_base_data(ctx)
            booking_data["start_time"] = "09:15:00"
            booking_data["end_time"] = "10:00:00"

            resp = await client.post(
                f"{self.backend_url}/api/v1/bookings",
                json=booking_data
            )

            assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"
            print("(422 as expected)", end=" ")

    async def _test_reject_non_multiple_30(self, ctx: TestContext):
        """提交 end_time='09:45' 的預約（非 30 分鐘邊界），預期 422"""
        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            booking_data = self._booking_base_data(ctx)
            booking_data["start_time"] = "09:00:00"
            booking_data["end_time"] = "09:45:00"

            resp = await client.post(
                f"{self.backend_url}/api/v1/bookings",
                json=booking_data
            )

            assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"
            print("(422 as expected)", end=" ")

    # ================================================================
    # 第三組：多預約與重疊檢測
    # ================================================================

    async def _test_create_booking_a(self, ctx: TestContext):
        """建立 Booking A (09:00-10:00)，佔用前 2 個區塊"""
        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            booking_data = self._booking_base_data(ctx)
            booking_data["start_time"] = "09:00:00"
            booking_data["end_time"] = "10:00:00"

            resp = await client.post(
                f"{self.backend_url}/api/v1/bookings",
                json=booking_data
            )

            assert resp.status_code == 200, f"Failed: {resp.text}"
            data = resp.json()
            assert data.get("data"), f"No booking data returned: {data}"

            ctx.created_booking_id = data["data"]["id"]
            ctx.created_booking_no = data["data"]["booking_no"]
            print(f"(A={ctx.created_booking_no})", end=" ")

    async def _test_slot_availability_after_a(self, ctx: TestContext):
        """確認 09:00-10:00 的 2 個區塊 unavailable，其餘 4 個 available"""
        assert ctx.test_slot_id, "No test slot"

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.get(
                f"{self.backend_url}/api/v1/bookings/slot-availability/{ctx.test_slot_id}"
            )

            assert resp.status_code == 200, f"Failed: {resp.text}"
            blocks = resp.json().get("data", {}).get("blocks", [])
            assert len(blocks) == 6, f"Expected 6 blocks, got {len(blocks)}"

            # blocks[0]: 09:00-09:30 → unavailable
            # blocks[1]: 09:30-10:00 → unavailable
            # blocks[2-5]: available
            assert not blocks[0]["is_available"], "Block 09:00-09:30 should be unavailable"
            assert not blocks[1]["is_available"], "Block 09:30-10:00 should be unavailable"
            assert blocks[2]["is_available"], "Block 10:00-10:30 should be available"
            assert blocks[3]["is_available"], "Block 10:30-11:00 should be available"
            assert blocks[4]["is_available"], "Block 11:00-11:30 should be available"
            assert blocks[5]["is_available"], "Block 11:30-12:00 should be available"
            print("(2 unavailable, 4 available)", end=" ")

    async def _test_create_booking_b(self, ctx: TestContext):
        """建立 Booking B (10:00-11:00) — 同一 slot 不重疊，應成功"""
        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            booking_data = self._booking_base_data(ctx)
            booking_data["start_time"] = "10:00:00"
            booking_data["end_time"] = "11:00:00"

            resp = await client.post(
                f"{self.backend_url}/api/v1/bookings",
                json=booking_data
            )

            assert resp.status_code == 200, f"Failed: {resp.text}"
            data = resp.json()
            assert data.get("data"), f"No booking data returned: {data}"

            ctx.created_booking_id_2 = data["data"]["id"]
            ctx.created_booking_no_2 = data["data"]["booking_no"]
            print(f"(B={ctx.created_booking_no_2})", end=" ")

    async def _test_reject_overlapping(self, ctx: TestContext):
        """嘗試建立 09:30-10:30 的預約，預期 409 衝突"""
        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            booking_data = self._booking_base_data(ctx)
            booking_data["start_time"] = "09:30:00"
            booking_data["end_time"] = "10:30:00"

            resp = await client.post(
                f"{self.backend_url}/api/v1/bookings",
                json=booking_data
            )

            assert resp.status_code == 409, f"Expected 409, got {resp.status_code}: {resp.text}"
            print("(409 conflict as expected)", end=" ")

    async def _test_slot_availability_after_b(self, ctx: TestContext):
        """確認 09:00-11:00 四個區塊被佔用，11:00-12:00 可用"""
        assert ctx.test_slot_id, "No test slot"

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.get(
                f"{self.backend_url}/api/v1/bookings/slot-availability/{ctx.test_slot_id}"
            )

            assert resp.status_code == 200, f"Failed: {resp.text}"
            blocks = resp.json().get("data", {}).get("blocks", [])
            assert len(blocks) == 6, f"Expected 6 blocks, got {len(blocks)}"

            for i in range(4):
                assert not blocks[i]["is_available"], f"Block {i} should be unavailable"
            for i in range(4, 6):
                assert blocks[i]["is_available"], f"Block {i} should be available"

            print("(4 unavailable, 2 available)", end=" ")

    # ================================================================
    # 第四組：預約已滿（is_booked）狀態
    # ================================================================

    async def _test_slot_not_fully_booked(self, ctx: TestContext):
        """查詢 teacher-slots/{slot_id}，確認 is_booked=false（還有空位）"""
        assert ctx.test_slot_id, "No test slot"

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.get(
                f"{self.backend_url}/api/v1/teacher-slots/{ctx.test_slot_id}"
            )

            assert resp.status_code == 200, f"Failed: {resp.text}"
            data = resp.json().get("data", {})
            assert data.get("is_booked") == False, \
                f"Expected is_booked=false, got {data.get('is_booked')}"
            print("(is_booked=false)", end=" ")

    async def _test_create_booking_c(self, ctx: TestContext):
        """建立 Booking C (11:00-12:00) — 填滿最後 2 個區塊"""
        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            booking_data = self._booking_base_data(ctx)
            booking_data["start_time"] = "11:00:00"
            booking_data["end_time"] = "12:00:00"

            resp = await client.post(
                f"{self.backend_url}/api/v1/bookings",
                json=booking_data
            )

            assert resp.status_code == 200, f"Failed: {resp.text}"
            data = resp.json()
            assert data.get("data"), f"No booking data returned: {data}"

            ctx.created_booking_id_3 = data["data"]["id"]
            ctx.created_booking_no_3 = data["data"]["booking_no"]
            print(f"(C={ctx.created_booking_no_3})", end=" ")

    async def _test_slot_fully_booked(self, ctx: TestContext):
        """確認 is_booked=true（預約已滿，全部 6 個區塊都佔用）"""
        assert ctx.test_slot_id, "No test slot"

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.get(
                f"{self.backend_url}/api/v1/teacher-slots/{ctx.test_slot_id}"
            )

            assert resp.status_code == 200, f"Failed: {resp.text}"
            data = resp.json().get("data", {})
            assert data.get("is_booked") == True, \
                f"Expected is_booked=true, got {data.get('is_booked')}"
            print("(is_booked=true)", end=" ")

    async def _test_cancel_booking_c(self, ctx: TestContext):
        """取消 Booking C（釋放 11:00-12:00 區塊）"""
        assert ctx.created_booking_id_3, "No booking C"

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.put(
                f"{self.backend_url}/api/v1/bookings/{ctx.created_booking_id_3}",
                json={"booking_status": "cancelled"}
            )

            assert resp.status_code == 200, f"Failed: {resp.text}"
            data = resp.json()
            assert data.get("data", {}).get("booking_status") == "cancelled"
            print("(C → cancelled)", end=" ")

    async def _test_slot_not_fully_booked_again(self, ctx: TestContext):
        """確認 is_booked 恢復為 false（取消 C 後有空位）"""
        assert ctx.test_slot_id, "No test slot"

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.get(
                f"{self.backend_url}/api/v1/teacher-slots/{ctx.test_slot_id}"
            )

            assert resp.status_code == 200, f"Failed: {resp.text}"
            data = resp.json().get("data", {})
            assert data.get("is_booked") == False, \
                f"Expected is_booked=false, got {data.get('is_booked')}"
            print("(is_booked=false)", end=" ")

    # ================================================================
    # 第五組：Update & Delete
    # ================================================================

    async def _test_get_booking(self, ctx: TestContext):
        """取得 Booking A 的詳細資料"""
        assert ctx.created_booking_id, "No booking A"

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.get(
                f"{self.backend_url}/api/v1/bookings/{ctx.created_booking_id}"
            )

            assert resp.status_code == 200, f"Failed: {resp.text}"
            data = resp.json()
            assert data.get("data", {}).get("id") == ctx.created_booking_id

    async def _test_update_booking_confirmed(self, ctx: TestContext):
        """更新 Booking A 狀態 → confirmed"""
        assert ctx.created_booking_id, "No booking A"

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.put(
                f"{self.backend_url}/api/v1/bookings/{ctx.created_booking_id}",
                json={
                    "booking_status": "confirmed",
                    "notes": f"{TEST_NOTES} - confirmed"
                }
            )

            assert resp.status_code == 200, f"Failed: {resp.text}"
            data = resp.json()
            assert data.get("data", {}).get("booking_status") == "confirmed"
            print("(A → confirmed)", end=" ")

    async def _test_list_bookings_after_create(self, ctx: TestContext):
        """確認 Booking A、B 都在列表中"""
        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.get(f"{self.backend_url}/api/v1/bookings")

            assert resp.status_code == 200, f"Failed: {resp.text}"
            data = resp.json()

            booking_ids = [b["id"] for b in data.get("data", [])]
            if ctx.created_booking_id:
                assert ctx.created_booking_id in booking_ids, "Booking A not in list"
            if ctx.created_booking_id_2:
                assert ctx.created_booking_id_2 in booking_ids, "Booking B not in list"
            print("(A, B found in list)", end=" ")

    async def _test_cancel_booking_a(self, ctx: TestContext):
        """取消 Booking A（confirmed → cancelled，以便後續刪除）"""
        assert ctx.created_booking_id, "No booking A"

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.put(
                f"{self.backend_url}/api/v1/bookings/{ctx.created_booking_id}",
                json={"booking_status": "cancelled"}
            )

            assert resp.status_code == 200, f"Failed: {resp.text}"
            data = resp.json()
            assert data.get("data", {}).get("booking_status") == "cancelled"
            print("(A → cancelled)", end=" ")

    async def _test_delete_booking_a(self, ctx: TestContext):
        """刪除 Booking A（已取消，可刪除）"""
        assert ctx.created_booking_id, "No booking A"

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.delete(
                f"{self.backend_url}/api/v1/bookings/{ctx.created_booking_id}"
            )

            assert resp.status_code == 200, f"Failed: {resp.text}"

    async def _test_delete_booking_b(self, ctx: TestContext):
        """刪除 Booking B（pending 狀態，可直接刪除）"""
        assert ctx.created_booking_id_2, "No booking B"

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.delete(
                f"{self.backend_url}/api/v1/bookings/{ctx.created_booking_id_2}"
            )

            assert resp.status_code == 200, f"Failed: {resp.text}"

    async def _test_verify_deletion(self, ctx: TestContext):
        """確認已刪除的 Booking A 返回 404"""
        assert ctx.created_booking_id, "No booking A"

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.get(
                f"{self.backend_url}/api/v1/bookings/{ctx.created_booking_id}"
            )

            assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"

    # ================================================================
    # 第六組：清理與登出
    # ================================================================

    async def _test_delete_test_slot(self, ctx: TestContext):
        """刪除測試用的 teacher slot（先清理殘留 booking C）"""
        if not ctx.test_slot_id:
            print("(skipped - no test slot)", end=" ")
            return

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            # 先刪除已取消的 Booking C（清理殘留資料）
            if ctx.created_booking_id_3:
                await client.delete(
                    f"{self.backend_url}/api/v1/bookings/{ctx.created_booking_id_3}"
                )

            # 刪除測試 slot
            resp = await client.delete(
                f"{self.backend_url}/api/v1/teacher-slots/{ctx.test_slot_id}"
            )

            assert resp.status_code == 200, f"Failed: {resp.text}"

    async def _test_logout(self, ctx: TestContext):
        """登出"""
        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.post(
                f"{self.backend_url}/api/v1/auth/logout",
                json={"logout_all_devices": False}
            )

            assert resp.status_code == 200, f"Logout failed: {resp.text}"

    # ========== 清理功能 ==========

    async def cleanup_test_bookings(self):
        """清理所有測試預約和測試 teacher slots（透過 Supabase service role）"""
        print(f"\n{'='*60}")
        print("🧹 Cleaning up test data...")
        print(f"{'='*60}\n")

        headers_ro = {
            "Authorization": f"Bearer {self.service_role_key}",
            "apikey": self.service_role_key,
        }
        headers_rw = {
            **headers_ro,
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }

        async with httpx.AsyncClient(**self.client_kwargs) as client:
            # --- 清理測試 bookings ---
            resp = await client.get(
                f"{self.supabase_url}/rest/v1/bookings"
                f"?notes=like.*{TEST_NOTES}*&select=id,booking_no",
                headers=headers_ro,
            )

            if resp.status_code == 200:
                bookings = resp.json()
                if bookings:
                    print(f"  Found {len(bookings)} test booking(s)")
                    for b in bookings:
                        del_resp = await client.patch(
                            f"{self.supabase_url}/rest/v1/bookings?id=eq.{b['id']}",
                            headers=headers_rw,
                            json={"is_deleted": True},
                        )
                        status = "✅" if del_resp.status_code in (200, 204) else "❌"
                        print(f"    {status} Deleted booking {b.get('booking_no', b['id'])}")
                else:
                    print("  No test bookings found")
            else:
                print(f"  ❌ Failed to query bookings: {resp.status_code}")

            # --- 清理測試 teacher slots ---
            resp = await client.get(
                f"{self.supabase_url}/rest/v1/teacher_available_slots"
                f"?notes=like.*{TEST_NOTES}*&select=id",
                headers=headers_ro,
            )

            if resp.status_code == 200:
                slots = resp.json()
                if slots:
                    print(f"  Found {len(slots)} test slot(s)")
                    for s in slots:
                        del_resp = await client.patch(
                            f"{self.supabase_url}/rest/v1/teacher_available_slots?id=eq.{s['id']}",
                            headers=headers_rw,
                            json={"is_deleted": True},
                        )
                        status = "✅" if del_resp.status_code in (200, 204) else "❌"
                        print(f"    {status} Deleted slot {s['id']}")
                else:
                    print("  No test slots found")
            else:
                print(f"  ❌ Failed to query slots: {resp.status_code}")

        print("\n✅ Cleanup completed\n")


async def main():
    parser = argparse.ArgumentParser(description="Live Booking Test Script")
    parser.add_argument(
        "--email",
        default=os.getenv("TEST_EMAIL", ""),
        help="Test user email (must be employee/admin)",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("TEST_PASSWORD", ""),
        help="Test user password",
    )
    parser.add_argument(
        "--cleanup-only",
        action="store_true",
        help="Only cleanup test data",
    )
    parser.add_argument(
        "--backend-url",
        default=BACKEND_URL,
        help=f"Backend URL (default: {BACKEND_URL})",
    )

    args = parser.parse_args()

    tester = LiveBookingTester(
        backend_url=args.backend_url,
        supabase_url=SUPABASE_URL,
        service_role_key=SERVICE_ROLE_KEY,
    )

    if args.cleanup_only:
        await tester.cleanup_test_bookings()
        return

    # 檢查必要參數
    if not args.email or not args.password:
        print("❌ Error: --email and --password are required")
        print("\nUsage:")
        print("  python tests/live_booking_test.py --email admin@example.com --password yourpassword")
        print("\nOr set environment variables:")
        print("  export TEST_EMAIL=admin@example.com")
        print("  export TEST_PASSWORD=yourpassword")
        sys.exit(1)

    ctx = TestContext(
        email=args.email,
        password=args.password,
    )

    success = await tester.run_all_tests(ctx)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

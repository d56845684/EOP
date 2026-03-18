#!/usr/bin/env python3
"""
Live Leave Emergency Quota Test Script

測試請假時間限制 + 緊急請假額度邏輯：
  1. 正常請假（課程前 ≥ 24h）→ leave_type=normal, deduct_lesson=false
  2. 緊急請假（<24h, ≥30min, 額度內）→ leave_type=emergency, deduct_lesson=false
  3. 緊急請假（額度已滿）→ leave_type=emergency, deduct_lesson=true
  4. 禁止請假（<30min）→ 400 錯誤
  5. 核准正常請假 → 堂數恢復
  6. 核准緊急請假（不扣堂）→ 堂數恢復 + emergency_count +1
  7. 核准緊急請假（扣堂）→ 堂數不恢復 + emergency_count +1
  8. 列表 / 單筆查詢包含 leave_type, deduct_lesson 欄位
  9. 學生合約 API 回傳 emergency_leave_quota 計算欄位

使用方式:
    python3 tests/live_leave_emergency_test.py \\
        --email employee@eop-test.com --password TestPassword123!

    # 保留測試資料
    python3 tests/live_leave_emergency_test.py \\
        --email employee@eop-test.com --password TestPassword123! --keep-data

    # 只清理
    python3 tests/live_leave_emergency_test.py --cleanup-only
"""

import httpx
import asyncio
import subprocess
import argparse
import json
import sys
import os
from datetime import date, datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8001")
DB_CONTAINER = os.getenv("DB_CONTAINER", "teaching-platform-db")

TEST_PREFIX = "live_leave_emer"


# ── DB helpers via docker exec ──

def db_query(sql: str) -> list[dict]:
    """Run SQL via docker exec and return rows as list of dicts."""
    result = subprocess.run(
        [
            "docker", "exec", DB_CONTAINER,
            "psql", "-U", "postgres", "-t", "-A", "-F", "\t",
            "-c", f"SELECT row_to_json(t) FROM ({sql}) t",
        ],
        capture_output=True, text=True, timeout=15,
    )
    if result.returncode != 0:
        raise RuntimeError(f"DB error: {result.stderr.strip()}")

    rows = []
    for line in result.stdout.strip().split("\n"):
        if line:
            rows.append(json.loads(line))
    return rows


def db_exec(sql: str) -> str:
    """Run SQL statement (INSERT/UPDATE/DELETE) via docker exec."""
    result = subprocess.run(
        [
            "docker", "exec", DB_CONTAINER,
            "psql", "-U", "postgres", "-c", sql,
        ],
        capture_output=True, text=True, timeout=15,
    )
    if result.returncode != 0:
        raise RuntimeError(f"DB error: {result.stderr.strip()}")
    return result.stdout.strip()


def db_query_value(sql: str) -> Optional[str]:
    """Run SQL and return single value (first col, first row)."""
    result = subprocess.run(
        [
            "docker", "exec", DB_CONTAINER,
            "psql", "-U", "postgres", "-t", "-A", "-c", sql,
        ],
        capture_output=True, text=True, timeout=15,
    )
    if result.returncode != 0:
        raise RuntimeError(f"DB error: {result.stderr.strip()}")
    lines = [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]
    return lines[0] if lines else None


def get_contract_state(contract_id: str) -> dict:
    """取得合約當前狀態"""
    rows = db_query(
        f"SELECT remaining_lessons, used_leave_count, used_emergency_leave_count "
        f"FROM student_contracts WHERE id = '{contract_id}'"
    )
    assert rows, f"Contract {contract_id} not found"
    return rows[0]


@dataclass
class TestResult:
    name: str
    passed: bool
    message: str = ""
    duration_ms: float = 0


@dataclass
class Ctx:
    email: str = ""
    password: str = ""
    cookies: dict = field(default_factory=dict)

    # 基礎資料
    student_id: Optional[str] = None
    teacher_id: Optional[str] = None
    course_id: Optional[str] = None
    student_contract_id: Optional[str] = None
    teacher_contract_id: Optional[str] = None

    # 日期
    normal_date: str = ""  # 7 天後（正常請假）
    today_date: str = ""   # 今天（緊急 / 禁止）

    # Teacher slots
    normal_slot_id: Optional[str] = None

    # Bookings (all confirmed)
    booking_a_id: Optional[str] = None  # 正常請假 (遠期)
    booking_b_id: Optional[str] = None  # 緊急請假 - 額度內 (~2h later)
    booking_c_id: Optional[str] = None  # 緊急請假 - 超額 (~3h later)
    booking_d_id: Optional[str] = None  # 禁止請假 (~10min later)

    # 緊急請假時間
    emergency_start_b: str = ""  # HH:MM:SS
    emergency_start_c: str = ""
    blocked_start_d: str = ""

    # Leave records created
    leave_a_id: Optional[str] = None
    leave_b_id: Optional[str] = None
    leave_c_id: Optional[str] = None


class LiveLeaveEmergencyTester:
    def __init__(self, backend_url: str):
        self.backend_url = backend_url.rstrip("/")
        self.results: list[TestResult] = []
        self.client_kwargs = {
            "follow_redirects": True,
            "timeout": httpx.Timeout(30.0, connect=10.0),
        }

    # ── runner ──

    async def run_all_tests(self, ctx: Ctx, keep_data: bool = False) -> bool:
        print(f"\n{'='*60}")
        print("🧪 Live Leave Emergency Quota Tests")
        print(f"{'='*60}")
        print(f"Backend:  {self.backend_url}")
        print(f"DB:       docker exec {DB_CONTAINER}")
        print(f"User:     {ctx.email}")
        if keep_data:
            print(f"Mode:     --keep-data")
        print(f"{'='*60}\n")

        tests = [
            # ── Setup ──
            ("Login", self._test_login),
            ("Seed test data", self._seed_test_data),

            # ── 正常請假 (≥24h) ──
            ("Create normal leave (≥24h)", self._test_create_normal_leave),
            ("Approve normal leave", self._test_approve_normal_leave),

            # ── 緊急請假：額度內 (<24h, ≥30min) ──
            ("Create emergency leave (within quota)", self._test_create_emergency_within_quota),
            ("Approve emergency leave (no deduct)", self._test_approve_emergency_no_deduct),

            # ── 緊急請假：超額 → 拒絕 ──
            ("Emergency leave over quota (rejected)", self._test_emergency_over_quota_rejected),

            # ── 禁止請假 (<30min) ──
            ("Blocked leave (<30min)", self._test_blocked_leave),

            # ── 查詢驗證 ──
            ("List leaves: verify leave_type field", self._test_list_includes_leave_type),
            ("Get single leave: verify fields", self._test_get_single_leave),
            ("Student contract: emergency_leave_quota", self._test_contract_quota_field),
        ]

        if not keep_data:
            tests.append(("Cleanup test data", self._cleanup))

        tests.append(("Logout", self._test_logout))

        for name, fn in tests:
            result = await self._run(name, fn, ctx)
            self.results.append(result)
            if name == "Login" and not result.passed:
                print("\n⚠️  Login failed, aborting")
                break
            if name == "Seed test data" and not result.passed:
                print("\n⚠️  Seed failed, running cleanup then aborting")
                self.results.append(await self._run("Cleanup", self._cleanup, ctx))
                break

        self._summary()
        return all(r.passed for r in self.results)

    async def _run(self, name: str, fn, ctx: Ctx) -> TestResult:
        print(f"  ▶ {name}...", end=" ", flush=True)
        t0 = datetime.now()
        try:
            await fn(ctx)
            ms = (datetime.now() - t0).total_seconds() * 1000
            print(f"✅ ({ms:.0f}ms)")
            return TestResult(name, True, "OK", ms)
        except AssertionError as e:
            ms = (datetime.now() - t0).total_seconds() * 1000
            print(f"❌ {e}")
            return TestResult(name, False, str(e), ms)
        except Exception as e:
            ms = (datetime.now() - t0).total_seconds() * 1000
            print(f"❌ Error: {e}")
            return TestResult(name, False, str(e), ms)

    def _summary(self):
        print(f"\n{'='*60}")
        print("📊 Test Summary")
        print(f"{'='*60}\n")
        for r in self.results:
            s = "✅" if r.passed else "❌"
            print(f"  {s} {r.name}: {r.message} ({r.duration_ms:.0f}ms)")
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        total_ms = sum(r.duration_ms for r in self.results)
        print(f"\n{'='*60}")
        print(f"Total: {passed} passed, {failed} failed ({total_ms:.0f}ms)")
        print(f"{'='*60}\n")

    # ── login / logout ──

    async def _test_login(self, ctx: Ctx):
        async with httpx.AsyncClient(**self.client_kwargs) as c:
            resp = await c.post(
                f"{self.backend_url}/api/v1/auth/login",
                json={"email": ctx.email, "password": ctx.password},
            )
            assert resp.status_code == 200, f"Login failed: {resp.text}"
            ctx.cookies = dict(resp.cookies)

    async def _test_logout(self, ctx: Ctx):
        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as c:
            resp = await c.post(
                f"{self.backend_url}/api/v1/auth/logout",
                json={"logout_all_devices": False},
            )
            assert resp.status_code == 200, f"Logout failed: {resp.text}"

    # ── seed ──

    async def _seed_test_data(self, ctx: Ctx):
        """透過 docker exec psql 建立完整測試資料

        建立架構：
          - 1 student, 1 teacher, 1 course
          - 1 student_contract: total_lessons=5 → quota = ceil(5*0.2) = 1
          - 1 teacher_contract
          - 2 teacher_slots (normal_date / today)
          - 4 confirmed bookings:
              A = 7 天後 10:00 (正常請假)
              B = 今天 ~2h 後 (緊急請假, 額度內)
              C = 今天 ~3h 後 (緊急請假, 超額)
              D = 今天 ~10min 後 (禁止請假)
        """
        # 計算時間 (UTC+8)
        now_tw = datetime.utcnow() + timedelta(hours=8)
        ctx.normal_date = (now_tw + timedelta(days=7)).strftime("%Y-%m-%d")

        # 緊急請假時間：2 小時後（注意跨日）
        emergency_b_dt = now_tw + timedelta(hours=2)
        emergency_b_date = emergency_b_dt.strftime("%Y-%m-%d")
        ctx.emergency_start_b = emergency_b_dt.strftime("%H:00:00")
        emergency_b_end = (emergency_b_dt + timedelta(hours=1)).strftime("%H:00:00")

        # 緊急請假時間：3 小時後
        emergency_c_dt = now_tw + timedelta(hours=3)
        emergency_c_date = emergency_c_dt.strftime("%Y-%m-%d")
        ctx.emergency_start_c = emergency_c_dt.strftime("%H:00:00")
        emergency_c_end = (emergency_c_dt + timedelta(hours=1)).strftime("%H:00:00")

        # 禁止請假時間：10 分鐘後
        blocked_dt = now_tw + timedelta(minutes=10)
        blocked_date = blocked_dt.strftime("%Y-%m-%d")
        ctx.blocked_start_d = blocked_dt.strftime("%H:%M:00")
        blocked_d_end = (blocked_dt + timedelta(hours=1)).strftime("%H:%M:00")

        # 每個日期各需要一個 slot
        # 收集唯一日期
        date_set = {emergency_b_date, emergency_c_date, blocked_date}
        ctx.today_date = blocked_date  # for reference

        # slot 用寬範圍覆蓋
        today_slot_start = "00:00"
        today_slot_end = "23:59"

        # 1. Course
        ctx.course_id = db_query_value(
            f"INSERT INTO courses (course_code, course_name, duration_minutes, is_active) "
            f"VALUES ('{TEST_PREFIX}_C1', '{TEST_PREFIX}_測試課程', 60, true) RETURNING id"
        )
        assert ctx.course_id, "Failed to create course"

        # 2. Student
        ctx.student_id = db_query_value(
            f"INSERT INTO students (student_no, name, email, phone, is_active) "
            f"VALUES ('{TEST_PREFIX}_S1', '{TEST_PREFIX}_學生', "
            f"'{TEST_PREFIX}_s1@test.com', '0900000099', true) RETURNING id"
        )
        assert ctx.student_id, "Failed to create student"

        # 3. Teacher
        ctx.teacher_id = db_query_value(
            f"INSERT INTO teachers (teacher_no, name, email, phone, is_active, teacher_level) "
            f"VALUES ('{TEST_PREFIX}_T1', '{TEST_PREFIX}_教師', "
            f"'{TEST_PREFIX}_t1@test.com', '0900000098', true, 3) RETURNING id"
        )
        assert ctx.teacher_id, "Failed to create teacher"

        # 4. Student contract: total_lessons=5 → quota = ceil(5*0.2) = 1
        #    建 4 筆 booking 各 lessons_used=1，remaining = 5 - 4 = 1（模擬真實扣堂）
        ctx.student_contract_id = db_query_value(
            f"INSERT INTO student_contracts "
            f"(contract_no, student_id, contract_status, start_date, end_date, "
            f"total_lessons, remaining_lessons, total_amount, total_leave_allowed, "
            f"used_emergency_leave_count, notes) "
            f"VALUES ('{TEST_PREFIX}_SC1', '{ctx.student_id}', 'active', "
            f"'{date.today().isoformat()}', '{(date.today() + timedelta(days=365)).isoformat()}', "
            f"5, 1, 10000, 1, 0, '{TEST_PREFIX}') RETURNING id"
        )
        assert ctx.student_contract_id, "Failed to create student contract"

        # 5. Teacher contract
        ctx.teacher_contract_id = db_query_value(
            f"INSERT INTO teacher_contracts "
            f"(contract_no, teacher_id, start_date, end_date, employment_type, contract_status, notes) "
            f"VALUES ('{TEST_PREFIX}_TC1', '{ctx.teacher_id}', "
            f"'{date.today().isoformat()}', '{(date.today() + timedelta(days=365)).isoformat()}', "
            f"'hourly', 'active', '{TEST_PREFIX}') RETURNING id"
        )
        assert ctx.teacher_contract_id, "Failed to create teacher contract"

        # 6. Teacher slots — 每個唯一日期建一個 slot
        # Normal date slot (09:00-12:00)
        ctx.normal_slot_id = db_query_value(
            f"INSERT INTO teacher_available_slots "
            f"(teacher_id, teacher_contract_id, slot_date, start_time, end_time, is_available, notes) "
            f"VALUES ('{ctx.teacher_id}', '{ctx.teacher_contract_id}', "
            f"'{ctx.normal_date}', '09:00', '12:00', true, '{TEST_PREFIX}') RETURNING id"
        )
        assert ctx.normal_slot_id, "Failed to create normal slot"

        # 為緊急/禁止日期各建立寬範圍 slot
        slot_by_date = {}
        for d in date_set:
            slot_id = db_query_value(
                f"INSERT INTO teacher_available_slots "
                f"(teacher_id, teacher_contract_id, slot_date, start_time, end_time, is_available, notes) "
                f"VALUES ('{ctx.teacher_id}', '{ctx.teacher_contract_id}', "
                f"'{d}', '{today_slot_start}', '{today_slot_end}', true, '{TEST_PREFIX}') RETURNING id"
            )
            assert slot_id, f"Failed to create slot for {d}"
            slot_by_date[d] = slot_id

        # 7. Bookings (all confirmed)
        booking_base = (
            f"student_id, teacher_id, course_id, student_contract_id, "
            f"teacher_contract_id, teacher_hourly_rate, "
            f"booking_status, lessons_used, notes"
        )
        booking_vals = (
            f"'{ctx.student_id}', '{ctx.teacher_id}', '{ctx.course_id}', '{ctx.student_contract_id}', "
            f"'{ctx.teacher_contract_id}', 500, "
            f"'confirmed', 1, '{TEST_PREFIX}'"
        )

        # Booking A: 正常請假 (7 天後 10:00-11:00)
        ctx.booking_a_id = db_query_value(
            f"INSERT INTO bookings "
            f"(booking_no, {booking_base}, teacher_slot_id, booking_date, start_time, end_time) "
            f"VALUES ('{TEST_PREFIX}_BKA', {booking_vals}, "
            f"'{ctx.normal_slot_id}', '{ctx.normal_date}', '10:00', '11:00') RETURNING id"
        )
        assert ctx.booking_a_id, "Failed to create booking A"

        # Booking B: 緊急請假 - 額度內 (~2h 後)
        ctx.booking_b_id = db_query_value(
            f"INSERT INTO bookings "
            f"(booking_no, {booking_base}, teacher_slot_id, booking_date, start_time, end_time) "
            f"VALUES ('{TEST_PREFIX}_BKB', {booking_vals}, "
            f"'{slot_by_date[emergency_b_date]}', '{emergency_b_date}', '{ctx.emergency_start_b}', '{emergency_b_end}') RETURNING id"
        )
        assert ctx.booking_b_id, "Failed to create booking B"

        # Booking C: 緊急請假 - 超額 (~3h 後)
        ctx.booking_c_id = db_query_value(
            f"INSERT INTO bookings "
            f"(booking_no, {booking_base}, teacher_slot_id, booking_date, start_time, end_time) "
            f"VALUES ('{TEST_PREFIX}_BKC', {booking_vals}, "
            f"'{slot_by_date[emergency_c_date]}', '{emergency_c_date}', '{ctx.emergency_start_c}', '{emergency_c_end}') RETURNING id"
        )
        assert ctx.booking_c_id, "Failed to create booking C"

        # Booking D: 禁止請假 (~10min 後)
        ctx.booking_d_id = db_query_value(
            f"INSERT INTO bookings "
            f"(booking_no, {booking_base}, teacher_slot_id, booking_date, start_time, end_time) "
            f"VALUES ('{TEST_PREFIX}_BKD', {booking_vals}, "
            f"'{slot_by_date[blocked_date]}', '{blocked_date}', '{ctx.blocked_start_d}', '{blocked_d_end}') RETURNING id"
        )
        assert ctx.booking_d_id, "Failed to create booking D"

        print(
            f"(quota=1, "
            f"B={emergency_b_date} {ctx.emergency_start_b}, "
            f"C={emergency_c_date} {ctx.emergency_start_c}, "
            f"D={blocked_date} {ctx.blocked_start_d})",
            end=" ",
        )

    # ================================================================
    # 正常請假 (≥24h)
    # ================================================================

    async def _test_create_normal_leave(self, ctx: Ctx):
        """Booking A (7 天後) → leave_type=normal, deduct_lesson=false"""
        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as c:
            resp = await c.post(
                f"{self.backend_url}/api/v1/leave-records",
                json={"booking_id": ctx.booking_a_id, "reason": f"{TEST_PREFIX} 正常請假"},
            )
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
            data = resp.json().get("data", {})
            ctx.leave_a_id = data.get("id")
            assert ctx.leave_a_id, f"No leave id: {resp.json()}"

            assert data.get("leave_type") == "normal", \
                f"Expected leave_type=normal, got {data.get('leave_type')}"
            assert data.get("deduct_lesson") == False, \
                f"Expected deduct_lesson=false, got {data.get('deduct_lesson')}"

            print(f"(leave_type=normal, deduct=false, id={ctx.leave_a_id[:8]}…)", end=" ")

    async def _test_approve_normal_leave(self, ctx: Ctx):
        """核准正常請假 → 堂數恢復, emergency_count 不變"""
        before = get_contract_state(ctx.student_contract_id)

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as c:
            resp = await c.post(
                f"{self.backend_url}/api/v1/leave-records/{ctx.leave_a_id}/approve",
            )
            assert resp.status_code == 200, f"Approve failed: {resp.text}"
            data = resp.json().get("data", {})
            assert data.get("leave_status") == "approved", \
                f"Expected approved, got {data.get('leave_status')}"

        after = get_contract_state(ctx.student_contract_id)

        # remaining_lessons should increase by 1 (restored)
        expected_remaining = before["remaining_lessons"] + 1
        assert after["remaining_lessons"] == expected_remaining, \
            f"remaining_lessons: expected {expected_remaining}, got {after['remaining_lessons']}"

        # used_emergency_leave_count unchanged
        assert after["used_emergency_leave_count"] == before["used_emergency_leave_count"], \
            f"emergency_count should be unchanged, was {before['used_emergency_leave_count']}, now {after['used_emergency_leave_count']}"

        # used_leave_count incremented
        assert after["used_leave_count"] == before["used_leave_count"] + 1, \
            f"used_leave_count: expected {before['used_leave_count'] + 1}, got {after['used_leave_count']}"

        print(
            f"(remaining: {before['remaining_lessons']}→{after['remaining_lessons']}, "
            f"emergency: {after['used_emergency_leave_count']})",
            end=" ",
        )

    # ================================================================
    # 緊急請假：額度內 (<24h, ≥30min)
    # ================================================================

    async def _test_create_emergency_within_quota(self, ctx: Ctx):
        """Booking B (~2h 後) → leave_type=emergency, deduct_lesson=false, quota info"""
        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as c:
            resp = await c.post(
                f"{self.backend_url}/api/v1/leave-records",
                json={"booking_id": ctx.booking_b_id, "reason": f"{TEST_PREFIX} 緊急請假(額度內)"},
            )
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
            data = resp.json().get("data", {})
            ctx.leave_b_id = data.get("id")
            assert ctx.leave_b_id, f"No leave id: {resp.json()}"

            assert data.get("leave_type") == "emergency", \
                f"Expected leave_type=emergency, got {data.get('leave_type')}"
            assert data.get("deduct_lesson") == False, \
                f"Expected deduct_lesson=false (within quota), got {data.get('deduct_lesson')}"

            # 驗證額度資訊
            assert data.get("emergency_quota") == 1, \
                f"Expected quota=1 (ceil(5*0.2)), got {data.get('emergency_quota')}"
            assert data.get("used_emergency_count") == 0, \
                f"Expected used=0, got {data.get('used_emergency_count')}"

            print(
                f"(emergency, deduct=false, quota={data.get('emergency_quota')}, "
                f"used={data.get('used_emergency_count')})",
                end=" ",
            )

    async def _test_approve_emergency_no_deduct(self, ctx: Ctx):
        """核准緊急請假(不扣堂) → 堂數恢復 + emergency_count +1"""
        before = get_contract_state(ctx.student_contract_id)

        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as c:
            resp = await c.post(
                f"{self.backend_url}/api/v1/leave-records/{ctx.leave_b_id}/approve",
            )
            assert resp.status_code == 200, f"Approve failed: {resp.text}"

        after = get_contract_state(ctx.student_contract_id)

        # remaining_lessons restored (+1, no deduction)
        expected_remaining = before["remaining_lessons"] + 1
        assert after["remaining_lessons"] == expected_remaining, \
            f"remaining_lessons: expected {expected_remaining}, got {after['remaining_lessons']}"

        # emergency_count +1
        expected_emergency = before["used_emergency_leave_count"] + 1
        assert after["used_emergency_leave_count"] == expected_emergency, \
            f"emergency_count: expected {expected_emergency}, got {after['used_emergency_leave_count']}"

        print(
            f"(remaining: {before['remaining_lessons']}→{after['remaining_lessons']}, "
            f"emergency: {before['used_emergency_leave_count']}→{after['used_emergency_leave_count']})",
            end=" ",
        )

    # ================================================================
    # 緊急請假：超額 → 直接拒絕
    # ================================================================

    async def _test_emergency_over_quota_rejected(self, ctx: Ctx):
        """Booking C (~3h 後), used_emergency=1 >= quota=1 → 400 拒絕"""
        # 此時 used_emergency_leave_count 已被上一個 approve +1 變為 1, 等於 quota=1
        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as c:
            resp = await c.post(
                f"{self.backend_url}/api/v1/leave-records",
                json={"booking_id": ctx.booking_c_id, "reason": f"{TEST_PREFIX} 緊急請假(超額)"},
            )
            assert resp.status_code == 400, \
                f"Expected 400 for over-quota emergency, got {resp.status_code}: {resp.text}"
            detail = resp.json().get("detail", "")
            assert "額度已用完" in detail, f"Error should mention 額度已用完: {detail}"
            print(f"(400: {detail})", end=" ")

    # ================================================================
    # 禁止請假 (<30min)
    # ================================================================

    async def _test_blocked_leave(self, ctx: Ctx):
        """Booking D (~10min 後) → 400 課程開始前 30 分鐘內無法請假"""
        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as c:
            resp = await c.post(
                f"{self.backend_url}/api/v1/leave-records",
                json={"booking_id": ctx.booking_d_id, "reason": f"{TEST_PREFIX} 應被拒絕"},
            )
            assert resp.status_code == 400, \
                f"Expected 400 for blocked leave, got {resp.status_code}: {resp.text}"
            detail = resp.json().get("detail", "")
            assert "30 分鐘" in detail, f"Error should mention 30 分鐘: {detail}"
            print(f"(400: {detail})", end=" ")

    # ================================================================
    # 查詢驗證
    # ================================================================

    async def _test_list_includes_leave_type(self, ctx: Ctx):
        """GET /leave-records 列表應包含 leave_type, deduct_lesson 欄位"""
        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as c:
            resp = await c.get(f"{self.backend_url}/api/v1/leave-records")
            assert resp.status_code == 200, f"Expected 200: {resp.text}"
            records = resp.json().get("data", [])

            # 找到我們建立的 leave records (leave_c 被拒絕不會建立)
            our_ids = {ctx.leave_a_id, ctx.leave_b_id}
            our_records = [r for r in records if r.get("id") in our_ids]
            assert len(our_records) >= 1, \
                f"Expected at least 1 of our leaves in list, found {len(our_records)}"

            for r in our_records:
                assert "leave_type" in r, f"Missing leave_type in list record: {r.get('leave_no')}"
                assert "deduct_lesson" in r, f"Missing deduct_lesson in list record: {r.get('leave_no')}"

            print(f"(found {len(our_records)} records with leave_type/deduct_lesson)", end=" ")

    async def _test_get_single_leave(self, ctx: Ctx):
        """GET /leave-records/:id 單筆應包含 leave_type, deduct_lesson"""
        # 取 leave_b (emergency, approved)
        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as c:
            resp = await c.get(f"{self.backend_url}/api/v1/leave-records/{ctx.leave_b_id}")
            assert resp.status_code == 200, f"Expected 200: {resp.text}"
            data = resp.json().get("data", {})

            assert data.get("leave_type") == "emergency", \
                f"Expected emergency, got {data.get('leave_type')}"
            assert data.get("deduct_lesson") == False, \
                f"Expected deduct_lesson=false, got {data.get('deduct_lesson')}"
            assert data.get("leave_status") == "approved", \
                f"Expected approved, got {data.get('leave_status')}"

            print(f"(leave_type={data.get('leave_type')}, deduct={data.get('deduct_lesson')})", end=" ")

    async def _test_contract_quota_field(self, ctx: Ctx):
        """GET /student-contracts/:id 應回傳 emergency_leave_quota (計算欄位)"""
        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as c:
            resp = await c.get(
                f"{self.backend_url}/api/v1/student-contracts/{ctx.student_contract_id}"
            )
            assert resp.status_code == 200, f"Expected 200: {resp.text}"
            data = resp.json().get("data", {})

            assert data.get("emergency_leave_quota") == 1, \
                f"Expected emergency_leave_quota=1 (ceil(5*0.2)), got {data.get('emergency_leave_quota')}"
            # 只有 1 次緊急請假核准（leave_b），leave_c 被拒絕不計入
            assert data.get("used_emergency_leave_count") == 1, \
                f"Expected used_emergency_leave_count=1, got {data.get('used_emergency_leave_count')}"
            assert data.get("total_lessons") == 5, \
                f"Expected total_lessons=5, got {data.get('total_lessons')}"

            print(
                f"(quota={data.get('emergency_leave_quota')}, "
                f"used={data.get('used_emergency_leave_count')}, "
                f"total={data.get('total_lessons')})",
                end=" ",
            )

    # ── cleanup ──

    async def _cleanup(self, ctx: Ctx):
        """清理所有測試資料（依外鍵順序刪除）"""
        # 用 booking_no 前綴找測試 booking（比 notes 更可靠，notes 可能被 API 覆寫）
        booking_subq = f"SELECT id FROM bookings WHERE booking_no LIKE '{TEST_PREFIX}%'"
        contract_subq = f"SELECT id FROM student_contracts WHERE notes = '{TEST_PREFIX}'"
        cleanup_sqls = [
            # 1. leave_records (FK → bookings)
            f"DELETE FROM leave_records WHERE booking_id IN ({booking_subq})",
            # 2. student_contract_leave_records (FK → student_contracts)
            f"DELETE FROM student_contract_leave_records WHERE student_contract_id IN ({contract_subq})",
            # 3. substitute_details (FK → bookings)
            f"DELETE FROM substitute_details WHERE booking_id IN ({booking_subq})",
            # 4. booking_details (FK → bookings)
            f"DELETE FROM booking_details WHERE booking_id IN ({booking_subq})",
            # 5. zoom_meeting_logs (FK → bookings)
            f"DELETE FROM zoom_meeting_logs WHERE booking_id IN ({booking_subq})",
            # 6. teacher_bonus_records (FK → bookings)
            f"DELETE FROM teacher_bonus_records WHERE related_booking_id IN ({booking_subq})",
            # 7. bookings (FK → teacher_available_slots, student_contracts)
            f"DELETE FROM bookings WHERE booking_no LIKE '{TEST_PREFIX}%'",
            # 8. teacher_available_slots
            f"DELETE FROM teacher_available_slots WHERE notes = '{TEST_PREFIX}'",
            # 9. student_contracts
            f"DELETE FROM student_contracts WHERE notes = '{TEST_PREFIX}'",
            # 10. teacher_contracts
            f"DELETE FROM teacher_contracts WHERE notes = '{TEST_PREFIX}'",
            # 11. teachers
            f"DELETE FROM teachers WHERE teacher_no LIKE '{TEST_PREFIX}%'",
            # 12. students
            f"DELETE FROM students WHERE student_no LIKE '{TEST_PREFIX}%'",
            # 13. courses
            f"DELETE FROM courses WHERE course_code LIKE '{TEST_PREFIX}%'",
        ]
        for sql in cleanup_sqls:
            db_exec(sql)
        print("(cleaned)", end=" ")

    async def cleanup_only(self):
        """只執行清理"""
        print(f"\n🧹 Cleaning up {TEST_PREFIX} test data...")
        ctx = Ctx()
        await self._cleanup(ctx)
        print("\n✅ Done\n")


async def main():
    parser = argparse.ArgumentParser(description="Live Leave Emergency Quota Test")
    parser.add_argument("--email", default=os.getenv("TEST_EMAIL", ""))
    parser.add_argument("--password", default=os.getenv("TEST_PASSWORD", ""))
    parser.add_argument("--cleanup-only", action="store_true", help="Only cleanup test data")
    parser.add_argument("--keep-data", action="store_true", help="Skip cleanup, keep test data")
    parser.add_argument("--backend-url", default=BACKEND_URL)
    args = parser.parse_args()

    tester = LiveLeaveEmergencyTester(args.backend_url)

    if args.cleanup_only:
        await tester.cleanup_only()
        return

    if not args.email or not args.password:
        print("❌ --email and --password required")
        print("\nUsage:")
        print(f"  python3 tests/live_leave_emergency_test.py --email employee@eop-test.com --password TestPassword123!")
        sys.exit(1)

    ctx = Ctx(email=args.email, password=args.password)
    success = await tester.run_all_tests(ctx, keep_data=args.keep_data)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

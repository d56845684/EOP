#!/usr/bin/env python3
"""
Live Trial Bonus Test Script

驗證試上課獎金流程：
  1. 試上 booking 建立時 teacher_hourly_rate = 0（不以時薪計薪）
  2. 試上 booking → completed 時自動寫入 trial_completed 獎金紀錄
  3. 試上轉正時寫入差額獎金（trial_to_formal_bonus - trial_completed_bonus）
  4. 驗證 DB 中獎金紀錄正確

使用方式:
    python3 tests/live_trial_bonus_test.py \
        --email employee@eop-test.com --password TestPassword123!

    # 只清理
    python3 tests/live_trial_bonus_test.py --cleanup-only
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

TEST_PREFIX = "live_trial_bonus"

# 測試用獎金金額
TRIAL_COMPLETED_BONUS = 300
TRIAL_TO_FORMAL_BONUS = 500
EXPECTED_DIFF_BONUS = TRIAL_TO_FORMAL_BONUS - TRIAL_COMPLETED_BONUS  # 200


# ── DB helper via docker exec ──

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

    # DB-seeded IDs
    trial_student_id: Optional[str] = None
    teacher_id: Optional[str] = None
    teacher_contract_id: Optional[str] = None
    course_id: Optional[str] = None
    teacher_slot_id: Optional[str] = None

    # bookings (seeded via DB with status=pending, updated via API)
    trial_booking_id: Optional[str] = None

    # original bonus values (to restore)
    original_completed_bonus: Optional[str] = None
    original_formal_bonus: Optional[str] = None


class LiveTrialBonusTester:
    def __init__(self, backend_url: str):
        self.backend_url = backend_url.rstrip("/")
        self.results: list[TestResult] = []
        self.client_kwargs = {
            "follow_redirects": True,
            "timeout": httpx.Timeout(30.0, connect=10.0),
        }

    # ── runner ──

    async def run_all_tests(self, ctx: Ctx) -> bool:
        print(f"\n{'='*60}")
        print("🧪 Live Trial Bonus Tests")
        print(f"{'='*60}")
        print(f"Backend:  {self.backend_url}")
        print(f"DB:       docker exec {DB_CONTAINER}")
        print(f"User:     {ctx.email}")
        print(f"Bonus:    completed={TRIAL_COMPLETED_BONUS}, formal={TRIAL_TO_FORMAL_BONUS}, diff={EXPECTED_DIFF_BONUS}")
        print(f"{'='*60}\n")

        tests = [
            ("Login", self._test_login),
            ("Seed test data via DB", self._seed_test_data),
            # ── 試上 booking 建立：hourly_rate=0 ──
            ("Verify trial booking hourly_rate=0", self._test_trial_booking_hourly_rate_zero),
            # ── 試上完成 → 自動寫 trial_completed 獎金 ──
            ("Update booking → completed (trigger bonus)", self._test_complete_trial_booking),
            ("Verify trial_completed bonus in DB", self._test_verify_trial_completed_bonus),
            # ── 試上轉正 → 差額獎金 ──
            ("Convert student to formal", self._test_convert_to_formal),
            ("Verify trial_to_formal diff bonus in DB", self._test_verify_formal_diff_bonus),
            # ── 彙總驗證 ──
            ("Verify total bonus = trial_to_formal_bonus", self._test_verify_total_bonus),
            # ── cleanup ──
            ("Cleanup test data", self._cleanup),
            ("Logout", self._test_logout),
        ]

        for name, fn in tests:
            result = await self._run(name, fn, ctx)
            self.results.append(result)
            if name == "Login" and not result.passed:
                print("\n⚠️  Login failed, aborting")
                break
            if name == "Seed test data via DB" and not result.passed:
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
        print(f"\n{'='*60}")
        print(f"Total: {passed} passed, {failed} failed")
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
        """透過 docker exec psql 建立測試資料"""
        # 1. 取得 teacher + active contract
        rows = db_query(
            "SELECT t.id AS teacher_id, tc.id AS tc_id, "
            "tc.trial_to_formal_bonus, tc.trial_completed_bonus "
            "FROM teachers t "
            "JOIN teacher_contracts tc ON tc.teacher_id = t.id "
            "AND tc.contract_status = 'active' AND tc.is_deleted = FALSE "
            "WHERE t.is_deleted = FALSE LIMIT 1"
        )
        assert rows, "No teacher with active contract found"
        ctx.teacher_id = rows[0]["teacher_id"]
        ctx.teacher_contract_id = rows[0]["tc_id"]
        ctx.original_formal_bonus = str(rows[0]["trial_to_formal_bonus"]) if rows[0]["trial_to_formal_bonus"] is not None else "0"
        ctx.original_completed_bonus = str(rows[0]["trial_completed_bonus"]) if rows[0]["trial_completed_bonus"] is not None else "0"

        # 2. 設定獎金金額
        db_exec(
            f"UPDATE teacher_contracts SET "
            f"trial_completed_bonus = {TRIAL_COMPLETED_BONUS}, "
            f"trial_to_formal_bonus = {TRIAL_TO_FORMAL_BONUS} "
            f"WHERE id = '{ctx.teacher_contract_id}'"
        )

        # 3. 取得 course
        rows = db_query("SELECT id FROM courses WHERE is_deleted = FALSE LIMIT 1")
        assert rows, "No course found"
        ctx.course_id = rows[0]["id"]

        # 4. 建立 trial student
        ctx.trial_student_id = db_query_value(
            f"INSERT INTO students (student_no, name, email, phone, student_type, is_active) "
            f"VALUES ('{TEST_PREFIX}_S1', '{TEST_PREFIX}_試上生', '{TEST_PREFIX}_s1@test.com', "
            f"'0900000099', 'trial', true) RETURNING id"
        )
        assert ctx.trial_student_id, "Failed to create trial student"

        # 5. 建立 teacher slot (30 天後)
        slot_date = (date.today() + timedelta(days=30)).isoformat()
        ctx.teacher_slot_id = db_query_value(
            f"INSERT INTO teacher_available_slots "
            f"(teacher_id, teacher_contract_id, slot_date, start_time, end_time, is_available, notes) "
            f"VALUES ('{ctx.teacher_id}', '{ctx.teacher_contract_id}', '{slot_date}', "
            f"'09:00', '15:00', true, '{TEST_PREFIX}') RETURNING id"
        )
        assert ctx.teacher_slot_id, "Failed to create teacher slot"

        # 6. 建立 trial booking (status=pending, teacher_hourly_rate=0)
        ctx.trial_booking_id = db_query_value(
            f"INSERT INTO bookings "
            f"(booking_no, student_id, teacher_id, course_id, "
            f"teacher_contract_id, teacher_hourly_rate, "
            f"teacher_slot_id, booking_date, start_time, end_time, "
            f"booking_status, booking_type, notes) "
            f"VALUES ('{TEST_PREFIX}_BK1', '{ctx.trial_student_id}', '{ctx.teacher_id}', "
            f"'{ctx.course_id}', '{ctx.teacher_contract_id}', 0, "
            f"'{ctx.teacher_slot_id}', '{slot_date}', '09:00', '09:30', "
            f"'pending', 'trial', '{TEST_PREFIX}') RETURNING id"
        )
        assert ctx.trial_booking_id, "Failed to create trial booking"

        print(
            f"(student={ctx.trial_student_id[:8]}… "
            f"booking={ctx.trial_booking_id[:8]}… "
            f"bonus: completed={TRIAL_COMPLETED_BONUS}, formal={TRIAL_TO_FORMAL_BONUS})",
            end=" ",
        )

    # ── test cases ──

    async def _test_trial_booking_hourly_rate_zero(self, ctx: Ctx):
        """驗證試上 booking 的 teacher_hourly_rate = 0"""
        rows = db_query(
            f"SELECT teacher_hourly_rate, booking_type FROM bookings "
            f"WHERE id = '{ctx.trial_booking_id}' AND is_deleted = FALSE"
        )
        assert rows, "Booking not found"
        assert rows[0]["booking_type"] == "trial", \
            f"Expected booking_type='trial', got '{rows[0]['booking_type']}'"
        rate = float(rows[0]["teacher_hourly_rate"])
        assert rate == 0, f"Expected teacher_hourly_rate=0 for trial, got {rate}"
        print("(hourly_rate=0, booking_type=trial)", end=" ")

    async def _test_complete_trial_booking(self, ctx: Ctx):
        """透過 API 將 trial booking 狀態改為 completed，觸發 trial_completed 獎金"""
        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as c:
            resp = await c.put(
                f"{self.backend_url}/api/v1/bookings/{ctx.trial_booking_id}",
                json={"booking_status": "completed"},
            )
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
            data = resp.json()
            assert data.get("data", {}).get("booking_status") == "completed", \
                f"booking_status should be completed: {data}"
            print("(booking → completed)", end=" ")

    async def _test_verify_trial_completed_bonus(self, ctx: Ctx):
        """驗證 DB: trial_completed 獎金紀錄已自動建立"""
        rows = db_query(
            f"SELECT bonus_type, amount, description FROM teacher_bonus_records "
            f"WHERE related_booking_id = '{ctx.trial_booking_id}' "
            f"AND bonus_type = 'trial_completed' AND is_deleted = FALSE"
        )
        assert rows, "No trial_completed bonus record found"
        amount = float(rows[0]["amount"])
        assert amount == TRIAL_COMPLETED_BONUS, \
            f"Expected trial_completed amount={TRIAL_COMPLETED_BONUS}, got {amount}"
        assert "試上完成" in rows[0]["description"], \
            f"Description should contain '試上完成': {rows[0]['description']}"
        print(f"(trial_completed bonus={amount})", end=" ")

    async def _test_convert_to_formal(self, ctx: Ctx):
        """透過 API 將試上學生轉正，觸發差額獎金"""
        payload = {
            "contract_no": f"{TEST_PREFIX}_C001",
            "total_lessons": 10,
            "total_amount": 10000,
            "start_date": date.today().isoformat(),
            "end_date": (date.today() + timedelta(days=180)).isoformat(),
            "teacher_id": ctx.teacher_id,
            "booking_id": ctx.trial_booking_id,
            "notes": TEST_PREFIX,
        }
        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as c:
            resp = await c.post(
                f"{self.backend_url}/api/v1/students/{ctx.trial_student_id}/convert-to-formal",
                json=payload,
            )
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
            data = resp.json()
            assert data.get("student", {}).get("student_type") == "formal", \
                f"student_type should be formal: {data}"
            assert data.get("bonus_recorded") is True, \
                f"bonus_recorded should be True: {data}"
            # API 回傳的 bonus_amount 是差額
            assert data.get("bonus_amount") == EXPECTED_DIFF_BONUS, \
                f"bonus_amount should be {EXPECTED_DIFF_BONUS}, got {data.get('bonus_amount')}"
            print(f"(student → formal, diff bonus={EXPECTED_DIFF_BONUS})", end=" ")

    async def _test_verify_formal_diff_bonus(self, ctx: Ctx):
        """驗證 DB: trial_to_formal 差額獎金紀錄"""
        rows = db_query(
            f"SELECT bonus_type, amount, description FROM teacher_bonus_records "
            f"WHERE related_booking_id = '{ctx.trial_booking_id}' "
            f"AND bonus_type = 'trial_to_formal' AND is_deleted = FALSE"
        )
        assert rows, "No trial_to_formal bonus record found"
        amount = float(rows[0]["amount"])
        assert amount == EXPECTED_DIFF_BONUS, \
            f"Expected trial_to_formal diff amount={EXPECTED_DIFF_BONUS}, got {amount}"
        assert "差額" in rows[0]["description"], \
            f"Description should contain '差額': {rows[0]['description']}"
        print(f"(trial_to_formal diff bonus={amount})", end=" ")

    async def _test_verify_total_bonus(self, ctx: Ctx):
        """驗證兩筆獎金合計 = trial_to_formal_bonus"""
        rows = db_query(
            f"SELECT SUM(amount) AS total FROM teacher_bonus_records "
            f"WHERE related_booking_id = '{ctx.trial_booking_id}' "
            f"AND bonus_type IN ('trial_completed', 'trial_to_formal') "
            f"AND is_deleted = FALSE"
        )
        assert rows, "No bonus records found"
        total = float(rows[0]["total"])
        assert total == TRIAL_TO_FORMAL_BONUS, \
            f"Total bonus should be {TRIAL_TO_FORMAL_BONUS} (={TRIAL_COMPLETED_BONUS}+{EXPECTED_DIFF_BONUS}), got {total}"

        # 也驗證 bookings_view.is_trial_to_formal
        rows2 = db_query(
            f"SELECT is_trial_to_formal FROM bookings_view "
            f"WHERE id = '{ctx.trial_booking_id}'"
        )
        assert rows2, "Booking not found in bookings_view"
        assert rows2[0]["is_trial_to_formal"] is True, \
            f"is_trial_to_formal should be True, got {rows2[0]['is_trial_to_formal']}"

        print(f"(total={total}, is_trial_to_formal=true)", end=" ")

    # ── cleanup ──

    async def _cleanup(self, ctx: Ctx):
        cleanup_sqls = [
            f"DELETE FROM teacher_bonus_records WHERE "
            f"related_student_id IN (SELECT id FROM students WHERE student_no LIKE '{TEST_PREFIX}%') "
            f"OR description LIKE '%{TEST_PREFIX}%'",
            f"DELETE FROM student_contracts WHERE contract_no LIKE '{TEST_PREFIX}%'",
            f"DELETE FROM bookings WHERE notes = '{TEST_PREFIX}'",
            f"DELETE FROM teacher_available_slots WHERE notes = '{TEST_PREFIX}'",
            f"DELETE FROM students WHERE student_no LIKE '{TEST_PREFIX}%'",
        ]
        for sql in cleanup_sqls:
            db_exec(sql)

        # 恢復 teacher_contract bonus 值
        if ctx.teacher_contract_id:
            completed_val = ctx.original_completed_bonus if ctx.original_completed_bonus and ctx.original_completed_bonus != "None" else "0"
            formal_val = ctx.original_formal_bonus if ctx.original_formal_bonus and ctx.original_formal_bonus != "None" else "0"
            db_exec(
                f"UPDATE teacher_contracts SET "
                f"trial_completed_bonus = {completed_val}, "
                f"trial_to_formal_bonus = {formal_val} "
                f"WHERE id = '{ctx.teacher_contract_id}'"
            )
        print("(cleaned)", end=" ")

    async def cleanup_only(self):
        print(f"\n🧹 Cleaning up {TEST_PREFIX} test data...")
        tables = [
            ("teacher_bonus_records", "description", f"%{TEST_PREFIX}%"),
            ("student_contracts", "contract_no", f"{TEST_PREFIX}%"),
            ("bookings", "notes", TEST_PREFIX),
            ("teacher_available_slots", "notes", TEST_PREFIX),
            ("students", "student_no", f"{TEST_PREFIX}%"),
        ]
        for table, col, pattern in tables:
            if "%" in pattern:
                r = db_exec(f"DELETE FROM {table} WHERE {col} LIKE '{pattern}'")
            else:
                r = db_exec(f"DELETE FROM {table} WHERE {col} = '{pattern}'")
            print(f"  {table}: {r}")
        print("✅ Done\n")


async def main():
    parser = argparse.ArgumentParser(description="Live Trial Bonus Test")
    parser.add_argument("--email", default=os.getenv("TEST_EMAIL", ""))
    parser.add_argument("--password", default=os.getenv("TEST_PASSWORD", ""))
    parser.add_argument("--cleanup-only", action="store_true")
    parser.add_argument("--backend-url", default=BACKEND_URL)
    args = parser.parse_args()

    tester = LiveTrialBonusTester(args.backend_url)

    if args.cleanup_only:
        await tester.cleanup_only()
        return

    if not args.email or not args.password:
        print("❌ --email and --password required")
        sys.exit(1)

    ctx = Ctx(email=args.email, password=args.password)
    success = await tester.run_all_tests(ctx)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

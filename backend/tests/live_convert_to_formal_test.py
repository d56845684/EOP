#!/usr/bin/env python3
"""
Live Convert-to-Formal Test Script

驗證試上轉正端點的 booking 驗證邏輯：
  1. booking_type = 'regular' → 400
  2. booking_status != 'completed' → 400
  3. 已轉正的 booking → 400
  4. bonus=0 也能寫入 teacher_bonus_records，is_trial_to_formal=true

使用方式:
    python3 tests/live_convert_to_formal_test.py \
        --email employee@eop-test.com --password TestPassword123!

    # 只清理
    python3 tests/live_convert_to_formal_test.py --cleanup-only
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

TEST_PREFIX = "live_cvt_formal"


# ── DB helper via docker exec ──

def db_query(sql: str) -> list[dict]:
    """Run SQL via docker exec and return rows as list of dicts."""
    result = subprocess.run(
        [
            "docker", "exec", DB_CONTAINER,
            "psql", "-U", "postgres", "-t", "-A", "-F", "\t",
            "--pset", "null=__NULL__",
            "-c", sql,
        ],
        capture_output=True, text=True, timeout=15,
    )
    if result.returncode != 0:
        raise RuntimeError(f"DB error: {result.stderr.strip()}")

    lines = [l for l in result.stdout.strip().split("\n") if l]
    if not lines:
        return []

    # We need column names — run again with header
    header_result = subprocess.run(
        [
            "docker", "exec", DB_CONTAINER,
            "psql", "-U", "postgres", "-t", "-A", "-F", "\t",
            "-c", f"SELECT row_to_json(t) FROM ({sql}) t",
        ],
        capture_output=True, text=True, timeout=15,
    )
    if header_result.returncode != 0:
        raise RuntimeError(f"DB error: {header_result.stderr.strip()}")

    rows = []
    for line in header_result.stdout.strip().split("\n"):
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
    # -t -A can still include trailing lines like "INSERT 0 1", take first line only
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

    # bookings
    trial_booking_id: Optional[str] = None        # trial + completed
    regular_booking_id: Optional[str] = None       # regular + completed
    pending_trial_booking_id: Optional[str] = None # trial + pending

    # second trial student for bonus=0 test
    trial_student_2_id: Optional[str] = None
    trial_booking_2_id: Optional[str] = None

    # original bonus value (to restore)
    original_bonus: Optional[str] = None


class LiveConvertToFormalTester:
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
        print("🧪 Live Convert-to-Formal Tests")
        print(f"{'='*60}")
        print(f"Backend:  {self.backend_url}")
        print(f"DB:       docker exec {DB_CONTAINER}")
        print(f"User:     {ctx.email}")
        print(f"{'='*60}\n")

        tests = [
            ("Login", self._test_login),
            ("Seed test data via DB", self._seed_test_data),
            # ── 驗證 booking_type ──
            ("Reject regular booking", self._test_reject_regular_booking),
            # ── 驗證 booking_status ──
            ("Reject pending booking", self._test_reject_pending_booking),
            # ── 驗證已轉正 ──
            ("Convert student 1 (create bonus record)", self._test_convert_student_1),
            ("Reject already converted booking", self._test_reject_already_converted),
            # ── bonus=0 也寫入 ──
            ("Convert student 2 (bonus=0)", self._test_convert_student_2_bonus_zero),
            ("Verify bonus=0 record exists", self._test_verify_bonus_zero_record),
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
            "SELECT t.id AS teacher_id, tc.id AS tc_id, tc.trial_to_formal_bonus "
            "FROM teachers t "
            "JOIN teacher_contracts tc ON tc.teacher_id = t.id "
            "AND tc.contract_status = 'active' AND tc.is_deleted = FALSE "
            "WHERE t.is_deleted = FALSE LIMIT 1"
        )
        assert rows, "No teacher with active contract found"
        ctx.teacher_id = rows[0]["teacher_id"]
        ctx.teacher_contract_id = rows[0]["tc_id"]
        ctx.original_bonus = str(rows[0]["trial_to_formal_bonus"]) if rows[0]["trial_to_formal_bonus"] is not None else None

        # 2. 取得 course
        rows = db_query("SELECT id FROM courses WHERE is_deleted = FALSE LIMIT 1")
        assert rows, "No course found"
        course_id = rows[0]["id"]

        # 3. 建立 trial students
        ctx.trial_student_id = db_query_value(
            f"INSERT INTO students (student_no, name, email, phone, student_type, is_active) "
            f"VALUES ('{TEST_PREFIX}_S1', '{TEST_PREFIX}_試上生1', '{TEST_PREFIX}_s1@test.com', "
            f"'0900000001', 'trial', true) RETURNING id"
        )
        assert ctx.trial_student_id, "Failed to create student 1"

        ctx.trial_student_2_id = db_query_value(
            f"INSERT INTO students (student_no, name, email, phone, student_type, is_active) "
            f"VALUES ('{TEST_PREFIX}_S2', '{TEST_PREFIX}_試上生2', '{TEST_PREFIX}_s2@test.com', "
            f"'0900000002', 'trial', true) RETURNING id"
        )
        assert ctx.trial_student_2_id, "Failed to create student 2"

        # 4. 建立 teacher slot (30 天後)
        slot_date = (date.today() + timedelta(days=30)).isoformat()
        ctx.teacher_slot_id = db_query_value(
            f"INSERT INTO teacher_available_slots "
            f"(teacher_id, teacher_contract_id, slot_date, start_time, end_time, is_available, notes) "
            f"VALUES ('{ctx.teacher_id}', '{ctx.teacher_contract_id}', '{slot_date}', "
            f"'09:00', '15:00', true, '{TEST_PREFIX}') RETURNING id"
        )
        assert ctx.teacher_slot_id, "Failed to create teacher slot"

        # 5. 建立 bookings
        def insert_booking(no, student_id, bk_date, start, end, status, bk_type):
            return db_query_value(
                f"INSERT INTO bookings "
                f"(booking_no, student_id, teacher_id, course_id, "
                f"teacher_contract_id, teacher_hourly_rate, "
                f"teacher_slot_id, booking_date, start_time, end_time, "
                f"booking_status, booking_type, notes) "
                f"VALUES ('{no}', '{student_id}', '{ctx.teacher_id}', '{course_id}', "
                f"'{ctx.teacher_contract_id}', 0, "
                f"'{ctx.teacher_slot_id}', '{bk_date}', '{start}', '{end}', "
                f"'{status}', '{bk_type}', '{TEST_PREFIX}') RETURNING id"
            )

        # A: trial + completed (正常)
        ctx.trial_booking_id = insert_booking(
            f"{TEST_PREFIX}_BKA", ctx.trial_student_id,
            slot_date, "09:00", "10:00", "completed", "trial",
        )
        # B: regular + completed (應被拒)
        ctx.regular_booking_id = insert_booking(
            f"{TEST_PREFIX}_BKB", ctx.trial_student_id,
            slot_date, "10:00", "11:00", "completed", "regular",
        )
        # C: trial + pending (應被拒)
        ctx.pending_trial_booking_id = insert_booking(
            f"{TEST_PREFIX}_BKC", ctx.trial_student_id,
            slot_date, "11:00", "12:00", "pending", "trial",
        )
        # D: trial + completed for student 2 (bonus=0 test)
        ctx.trial_booking_2_id = insert_booking(
            f"{TEST_PREFIX}_BKD", ctx.trial_student_2_id,
            slot_date, "13:00", "14:00", "completed", "trial",
        )

        assert all([ctx.trial_booking_id, ctx.regular_booking_id,
                     ctx.pending_trial_booking_id, ctx.trial_booking_2_id]), \
            "Failed to create some bookings"

        # 6. 把 teacher_contract bonus 設為 0
        db_exec(
            f"UPDATE teacher_contracts SET trial_to_formal_bonus = 0 "
            f"WHERE id = '{ctx.teacher_contract_id}'"
        )

        print(
            f"(s1={ctx.trial_student_id[:8]}… s2={ctx.trial_student_2_id[:8]}… "
            f"bookings=A,B,C,D)",
            end=" ",
        )

    # ── test cases ──

    def _convert_payload(self, ctx: Ctx, booking_id: str | None = None,
                         contract_no_suffix: str = "C001") -> dict:
        return {
            "contract_no": f"{TEST_PREFIX}_{contract_no_suffix}",
            "total_lessons": 10,
            "total_amount": 10000,
            "start_date": date.today().isoformat(),
            "end_date": (date.today() + timedelta(days=180)).isoformat(),
            "teacher_id": ctx.teacher_id,
            "booking_id": booking_id,
            "notes": TEST_PREFIX,
        }

    async def _test_reject_regular_booking(self, ctx: Ctx):
        """booking_type='regular' → 400"""
        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as c:
            resp = await c.post(
                f"{self.backend_url}/api/v1/students/{ctx.trial_student_id}/convert-to-formal",
                json=self._convert_payload(ctx, ctx.regular_booking_id),
            )
            assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"
            assert "試上類型" in resp.json().get("detail", ""), f"Wrong message: {resp.text}"
            print("(400 regular rejected)", end=" ")

    async def _test_reject_pending_booking(self, ctx: Ctx):
        """booking_status='pending' → 400"""
        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as c:
            resp = await c.post(
                f"{self.backend_url}/api/v1/students/{ctx.trial_student_id}/convert-to-formal",
                json=self._convert_payload(ctx, ctx.pending_trial_booking_id),
            )
            assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"
            assert "已完成" in resp.json().get("detail", ""), f"Wrong message: {resp.text}"
            print("(400 pending rejected)", end=" ")

    async def _test_convert_student_1(self, ctx: Ctx):
        """trial + completed → 轉正成功"""
        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as c:
            resp = await c.post(
                f"{self.backend_url}/api/v1/students/{ctx.trial_student_id}/convert-to-formal",
                json=self._convert_payload(ctx, ctx.trial_booking_id),
            )
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
            data = resp.json()
            assert data.get("student", {}).get("student_type") == "formal", \
                f"student_type should be formal: {data}"
            print("(student 1 → formal)", end=" ")

    async def _test_reject_already_converted(self, ctx: Ctx):
        """同一個 booking 已有 bonus record → 400"""
        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as c:
            resp = await c.post(
                f"{self.backend_url}/api/v1/students/{ctx.trial_student_2_id}/convert-to-formal",
                json=self._convert_payload(ctx, ctx.trial_booking_id, "C_DUP"),
            )
            assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"
            assert "已被標記為轉正" in resp.json().get("detail", ""), f"Wrong message: {resp.text}"
            print("(400 already converted)", end=" ")

    async def _test_convert_student_2_bonus_zero(self, ctx: Ctx):
        """bonus=0 也能成功轉正"""
        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as c:
            resp = await c.post(
                f"{self.backend_url}/api/v1/students/{ctx.trial_student_2_id}/convert-to-formal",
                json=self._convert_payload(ctx, ctx.trial_booking_2_id, "C002"),
            )
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
            data = resp.json()
            assert data.get("bonus_recorded") is True, f"bonus_recorded should be True: {data}"
            assert data.get("bonus_amount") == 0, f"bonus_amount should be 0: {data}"
            print("(student 2 → formal, bonus=0)", end=" ")

    async def _test_verify_bonus_zero_record(self, ctx: Ctx):
        """驗證 DB: bonus=0 記錄存在 + bookings_view.is_trial_to_formal=true"""
        # 1. teacher_bonus_records
        rows = db_query(
            f"SELECT amount FROM teacher_bonus_records "
            f"WHERE related_booking_id = '{ctx.trial_booking_2_id}' "
            f"AND bonus_type = 'trial_to_formal' AND is_deleted = FALSE"
        )
        assert rows, "No bonus record found for booking D"
        assert float(rows[0]["amount"]) == 0, f"amount should be 0, got {rows[0]['amount']}"

        # 2. bookings_view.is_trial_to_formal
        rows = db_query(
            f"SELECT is_trial_to_formal FROM bookings_view "
            f"WHERE id = '{ctx.trial_booking_2_id}'"
        )
        assert rows, "Booking D not found in bookings_view"
        assert rows[0]["is_trial_to_formal"] is True, \
            f"is_trial_to_formal should be True, got {rows[0]['is_trial_to_formal']}"

        print("(bonus=0 record + is_trial_to_formal=true)", end=" ")

    # ── cleanup ──

    async def _cleanup(self, ctx: Ctx):
        cleanup_sqls = [
            f"DELETE FROM teacher_bonus_records WHERE description LIKE '%{TEST_PREFIX}%' "
            f"OR related_student_id IN (SELECT id FROM students WHERE student_no LIKE '{TEST_PREFIX}%')",
            f"DELETE FROM student_contracts WHERE contract_no LIKE '{TEST_PREFIX}%'",
            f"DELETE FROM bookings WHERE notes = '{TEST_PREFIX}'",
            f"DELETE FROM teacher_available_slots WHERE notes = '{TEST_PREFIX}'",
            f"DELETE FROM students WHERE student_no LIKE '{TEST_PREFIX}%'",
        ]
        for sql in cleanup_sqls:
            db_exec(sql)

        # 恢復 teacher_contract bonus
        if ctx.teacher_contract_id:
            if ctx.original_bonus and ctx.original_bonus != "None":
                db_exec(
                    f"UPDATE teacher_contracts SET trial_to_formal_bonus = {ctx.original_bonus} "
                    f"WHERE id = '{ctx.teacher_contract_id}'"
                )
            else:
                db_exec(
                    f"UPDATE teacher_contracts SET trial_to_formal_bonus = NULL "
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
    parser = argparse.ArgumentParser(description="Live Convert-to-Formal Test")
    parser.add_argument("--email", default=os.getenv("TEST_EMAIL", ""))
    parser.add_argument("--password", default=os.getenv("TEST_PASSWORD", ""))
    parser.add_argument("--cleanup-only", action="store_true")
    parser.add_argument("--backend-url", default=BACKEND_URL)
    args = parser.parse_args()

    tester = LiveConvertToFormalTester(args.backend_url)

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

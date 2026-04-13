#!/usr/bin/env python3
"""
Live Substitute Teacher Test Script

測試代課教師完整流程：
  1. 代課教師選項端點 (GET /bookings/options/substitute-teachers)
     - 驗證三個硬條件篩選：slot 涵蓋、course_rate 存在、無衝堂
     - 驗證 is_preferred 偏好標記
  2. 指派代課 (POST /substitute-details)
     - 成功指派
     - 驗證：無 slot → 被拒
     - 驗證：合約無 course_rate → 被拒
     - 驗證：衝堂 → 被拒
  3. 取消代課 (DELETE /substitute-details/:id)

使用方式:
    python3 tests/live_substitute_test.py \
        --email employee@eop-test.com --password TestPassword123!

    # 保留測試資料（不執行 cleanup）
    python3 tests/live_substitute_test.py \
        --email employee@eop-test.com --password TestPassword123! --keep-data

    # 只清理測試資料
    python3 tests/live_substitute_test.py --cleanup-only
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

TEST_PREFIX = "live_sub_test"


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

    # 測試日期（明天）
    test_date: str = ""

    # 教師 A（原教師）
    teacher_a_id: Optional[str] = None
    teacher_a_contract_id: Optional[str] = None
    teacher_a_slot_id: Optional[str] = None

    # 教師 B（合格代課教師：有 slot + 有 course_rate + 無衝堂）
    teacher_b_id: Optional[str] = None
    teacher_b_contract_id: Optional[str] = None
    teacher_b_slot_id: Optional[str] = None

    # 教師 C（不合格：有 slot 但合約無 course_rate）
    teacher_c_id: Optional[str] = None
    teacher_c_contract_id: Optional[str] = None
    teacher_c_slot_id: Optional[str] = None

    # 教師 D（不合格：有 course_rate 但無 slot）
    teacher_d_id: Optional[str] = None
    teacher_d_contract_id: Optional[str] = None

    # 教師 E（不合格：有 slot + course_rate 但衝堂）
    teacher_e_id: Optional[str] = None
    teacher_e_contract_id: Optional[str] = None
    teacher_e_slot_id: Optional[str] = None
    teacher_e_conflict_booking_id: Optional[str] = None

    # 學生 + 課程
    student_id: Optional[str] = None
    course_id: Optional[str] = None

    # 預約（confirmed 狀態，供代課用）
    booking_id: Optional[str] = None

    # 代課紀錄
    substitute_detail_id: Optional[str] = None


class LiveSubstituteTester:
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
        print("🧪 Live Substitute Teacher Tests")
        print(f"{'='*60}")
        print(f"Backend:  {self.backend_url}")
        print(f"DB:       docker exec {DB_CONTAINER}")
        print(f"User:     {ctx.email}")
        if keep_data:
            print(f"Mode:     --keep-data (測試資料保留，下次用 --cleanup-only 清理)")
        print(f"{'='*60}\n")

        tests = [
            # ── Setup ──
            ("Login", self._test_login),
            ("Seed test data via DB", self._seed_test_data),

            # ── 代課教師選項端點 ──
            ("Options: eligible teachers returned", self._test_options_eligible),
            ("Options: teacher without slot excluded", self._test_options_no_slot_excluded),
            ("Options: teacher without course_rate excluded", self._test_options_no_course_excluded),
            ("Options: teacher with conflict excluded", self._test_options_conflict_excluded),
            ("Options: is_preferred marking", self._test_options_is_preferred),

            # ── 指派代課：驗證拒絕 ──
            ("Create sub: reject no slot", self._test_create_reject_no_slot),
            ("Create sub: reject no course_rate", self._test_create_reject_no_course),
            ("Create sub: reject conflict", self._test_create_reject_conflict),

            # ── 指派代課：成功 ──
            ("Create substitute detail (success)", self._test_create_substitute_success),
            ("Verify substitute in booking", self._test_verify_substitute_in_booking),
            ("List substitute details", self._test_list_substitute_details),
            ("Get single substitute detail", self._test_get_substitute_detail),

            # ── 取消代課 ──
            ("Cancel substitute detail", self._test_cancel_substitute),
            ("Verify booking cleared after cancel", self._test_verify_booking_cleared),
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
          - 1 個學生
          - 1 個課程
          - 5 個教師（A=原教師, B=合格代課, C=無course_rate, D=無slot, E=衝堂）
          - 每位教師各 1 份 active 合約
          - Teacher A/B/C/E 有 slot（D 故意沒有）
          - Teacher A/B/D/E 合約有 course_rate（C 故意沒有）
          - Teacher E 在測試時段有一筆 confirmed booking（衝堂）
          - 1 筆 confirmed booking（學生 + Teacher A）供代課測試
        """
        ctx.test_date = (date.today() + timedelta(days=7)).isoformat()
        test_date = ctx.test_date

        # 1. 建立課程
        ctx.course_id = db_query_value(
            f"INSERT INTO courses (course_code, course_name, duration_minutes, is_active) "
            f"VALUES ('{TEST_PREFIX}_C1', '{TEST_PREFIX}_測試課程', 60, true) RETURNING id"
        )
        assert ctx.course_id, "Failed to create course"

        # 2. 建立學生
        ctx.student_id = db_query_value(
            f"INSERT INTO students (student_no, name, email, phone, is_active) "
            f"VALUES ('{TEST_PREFIX}_S1', '{TEST_PREFIX}_學生', "
            f"'{TEST_PREFIX}_s1@test.com', '0900000001', true) RETURNING id"
        )
        assert ctx.student_id, "Failed to create student"

        # 3. 建立 5 位教師
        teacher_names = [
            ("TA", "原教師"),
            ("TB", "合格代課"),
            ("TC", "無課程教師"),
            ("TD", "無時段教師"),
            ("TE", "衝堂教師"),
        ]
        teacher_ids = []
        for code, name in teacher_names:
            tid = db_query_value(
                f"INSERT INTO teachers (teacher_no, name, email, phone, is_active, teacher_level) "
                f"VALUES ('{TEST_PREFIX}_{code}', '{TEST_PREFIX}_{name}', "
                f"'{TEST_PREFIX}_{code.lower()}@test.com', '09000000{code[-1:]}0', true, 3) "
                f"RETURNING id"
            )
            assert tid, f"Failed to create teacher {code}"
            teacher_ids.append(tid)

        ctx.teacher_a_id = teacher_ids[0]
        ctx.teacher_b_id = teacher_ids[1]
        ctx.teacher_c_id = teacher_ids[2]
        ctx.teacher_d_id = teacher_ids[3]
        ctx.teacher_e_id = teacher_ids[4]

        # 4. 為每位教師建立 active 合約
        for i, tid in enumerate(teacher_ids):
            code = teacher_names[i][0]
            cid = db_query_value(
                f"INSERT INTO teacher_contracts "
                f"(contract_no, teacher_id, start_date, end_date, employment_type, contract_status, notes) "
                f"VALUES ('{TEST_PREFIX}_{code}_CT', '{tid}', "
                f"'{date.today().isoformat()}', '{(date.today() + timedelta(days=365)).isoformat()}', "
                f"'hourly', 'active', '{TEST_PREFIX}') RETURNING id"
            )
            assert cid, f"Failed to create contract for {code}"
            if i == 0:
                ctx.teacher_a_contract_id = cid
            elif i == 1:
                ctx.teacher_b_contract_id = cid
            elif i == 2:
                ctx.teacher_c_contract_id = cid
            elif i == 3:
                ctx.teacher_d_contract_id = cid
            elif i == 4:
                ctx.teacher_e_contract_id = cid

        # 5. 為 A/B/D/E 合約建立 course_rate（C 故意不建）
        for cid in [
            ctx.teacher_a_contract_id,
            ctx.teacher_b_contract_id,
            ctx.teacher_d_contract_id,
            ctx.teacher_e_contract_id,
        ]:
            db_exec(
                f"INSERT INTO teacher_contract_details "
                f"(teacher_contract_id, detail_type, course_id, description, amount) "
                f"VALUES ('{cid}', 'course_rate', '{ctx.course_id}', "
                f"'{TEST_PREFIX} 時薪', 500)"
            )

        # 6. 為 A/B/C/E 建立涵蓋 09:00-12:00 的 slot（D 故意不建）
        for tid, cid, attr in [
            (ctx.teacher_a_id, ctx.teacher_a_contract_id, "teacher_a_slot_id"),
            (ctx.teacher_b_id, ctx.teacher_b_contract_id, "teacher_b_slot_id"),
            (ctx.teacher_c_id, ctx.teacher_c_contract_id, "teacher_c_slot_id"),
            (ctx.teacher_e_id, ctx.teacher_e_contract_id, "teacher_e_slot_id"),
        ]:
            slot_id = db_query_value(
                f"INSERT INTO teacher_available_slots "
                f"(teacher_id, teacher_contract_id, slot_date, start_time, end_time, is_available, notes) "
                f"VALUES ('{tid}', '{cid}', '{test_date}', '09:00', '12:00', true, '{TEST_PREFIX}') "
                f"RETURNING id"
            )
            assert slot_id, f"Failed to create slot for teacher"
            setattr(ctx, attr, slot_id)

        # 7. 為 Teacher E 在測試時段建立一筆 confirmed booking（造成衝堂）
        ctx.teacher_e_conflict_booking_id = db_query_value(
            f"INSERT INTO bookings "
            f"(booking_no, student_id, teacher_id, course_id, "
            f"teacher_contract_id, teacher_hourly_rate, "
            f"teacher_slot_id, booking_date, start_time, end_time, "
            f"booking_status, notes) "
            f"VALUES ('{TEST_PREFIX}_BK_CONF', '{ctx.student_id}', '{ctx.teacher_e_id}', "
            f"'{ctx.course_id}', '{ctx.teacher_e_contract_id}', 500, "
            f"'{ctx.teacher_e_slot_id}', '{test_date}', '09:00', '10:00', "
            f"'confirmed', '{TEST_PREFIX}') RETURNING id"
        )
        assert ctx.teacher_e_conflict_booking_id, "Failed to create conflict booking"

        # 8. 建立主要測試 booking（學生 + Teacher A, confirmed）
        ctx.booking_id = db_query_value(
            f"INSERT INTO bookings "
            f"(booking_no, student_id, teacher_id, course_id, "
            f"teacher_contract_id, teacher_hourly_rate, "
            f"teacher_slot_id, booking_date, start_time, end_time, "
            f"booking_status, notes) "
            f"VALUES ('{TEST_PREFIX}_BK_MAIN', '{ctx.student_id}', '{ctx.teacher_a_id}', "
            f"'{ctx.course_id}', '{ctx.teacher_a_contract_id}', 500, "
            f"'{ctx.teacher_a_slot_id}', '{test_date}', '09:00', '10:00', "
            f"'confirmed', '{TEST_PREFIX}') RETURNING id"
        )
        assert ctx.booking_id, "Failed to create main booking"

        print(
            f"(date={test_date} "
            f"booking={ctx.booking_id[:8]}… "
            f"teachers: A/B/C/D/E created)",
            end=" ",
        )

    # ================================================================
    # 代課教師選項端點 (GET /bookings/options/substitute-teachers)
    # ================================================================

    async def _get_substitute_options(self, ctx: Ctx) -> list[dict]:
        """Helper: 呼叫代課教師選項 API"""
        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as c:
            resp = await c.get(
                f"{self.backend_url}/api/v1/bookings/options/substitute-teachers",
                params={"booking_id": ctx.booking_id},
            )
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
            return resp.json().get("data", [])

    async def _test_options_eligible(self, ctx: Ctx):
        """Teacher B 應出現在選項中（滿足全部三個硬條件）"""
        options = await self._get_substitute_options(ctx)
        option_ids = [o["id"] for o in options]
        assert ctx.teacher_b_id in option_ids, \
            f"Teacher B (合格) should be in options, got ids: {[o.get('teacher_no') for o in options]}"
        print(f"(found {len(options)} eligible teacher(s), B included)", end=" ")

    async def _test_options_no_slot_excluded(self, ctx: Ctx):
        """Teacher D（無 slot）不應出現"""
        options = await self._get_substitute_options(ctx)
        option_ids = [o["id"] for o in options]
        assert ctx.teacher_d_id not in option_ids, \
            "Teacher D (no slot) should NOT be in options"
        print("(D excluded)", end=" ")

    async def _test_options_no_course_excluded(self, ctx: Ctx):
        """Teacher C（無 course_rate）不應出現"""
        options = await self._get_substitute_options(ctx)
        option_ids = [o["id"] for o in options]
        assert ctx.teacher_c_id not in option_ids, \
            "Teacher C (no course_rate) should NOT be in options"
        print("(C excluded)", end=" ")

    async def _test_options_conflict_excluded(self, ctx: Ctx):
        """Teacher E（衝堂）不應出現"""
        options = await self._get_substitute_options(ctx)
        option_ids = [o["id"] for o in options]
        assert ctx.teacher_e_id not in option_ids, \
            "Teacher E (conflict) should NOT be in options"
        print("(E excluded)", end=" ")

    async def _test_options_is_preferred(self, ctx: Ctx):
        """Teacher A（原教師）不應出現；驗證 is_preferred 欄位存在"""
        options = await self._get_substitute_options(ctx)
        option_ids = [o["id"] for o in options]

        # 原教師不應出現
        assert ctx.teacher_a_id not in option_ids, \
            "Teacher A (original) should NOT be in options"

        # 所有結果都應有 is_preferred 欄位
        for o in options:
            assert "is_preferred" in o, f"Missing is_preferred field in: {o}"

        print(f"(A excluded, is_preferred field present on all {len(options)} results)", end=" ")

    # ================================================================
    # 指派代課：驗證拒絕
    # ================================================================

    def _err_msg(self, resp) -> str:
        body = resp.json()
        return body.get("detail") or body.get("message") or str(body)

    async def _test_create_reject_no_slot(self, ctx: Ctx):
        """Teacher D 無 slot → 400"""
        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as c:
            resp = await c.post(
                f"{self.backend_url}/api/v1/substitute-details",
                json={
                    "booking_id": ctx.booking_id,
                    "substitute_teacher_id": ctx.teacher_d_id,
                    "substitute_contract_id": ctx.teacher_d_contract_id,
                    "reason": TEST_PREFIX,
                },
            )
            assert resp.status_code == 400, \
                f"Expected 400 for no-slot teacher, got {resp.status_code}: {resp.text}"
            msg = self._err_msg(resp)
            assert "時段" in msg, f"Error should mention 時段: {msg}"
            print(f"(400: {msg})", end=" ")

    async def _test_create_reject_no_course(self, ctx: Ctx):
        """Teacher C 合約無 course_rate → 400"""
        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as c:
            resp = await c.post(
                f"{self.backend_url}/api/v1/substitute-details",
                json={
                    "booking_id": ctx.booking_id,
                    "substitute_teacher_id": ctx.teacher_c_id,
                    "substitute_contract_id": ctx.teacher_c_contract_id,
                    "reason": TEST_PREFIX,
                },
            )
            assert resp.status_code == 400, \
                f"Expected 400 for no-course teacher, got {resp.status_code}: {resp.text}"
            msg = self._err_msg(resp)
            assert "課程" in msg, f"Error should mention 課程: {msg}"
            print(f"(400: {msg})", end=" ")

    async def _test_create_reject_conflict(self, ctx: Ctx):
        """Teacher E 衝堂 → 409"""
        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as c:
            resp = await c.post(
                f"{self.backend_url}/api/v1/substitute-details",
                json={
                    "booking_id": ctx.booking_id,
                    "substitute_teacher_id": ctx.teacher_e_id,
                    "substitute_contract_id": ctx.teacher_e_contract_id,
                    "reason": TEST_PREFIX,
                },
            )
            assert resp.status_code == 409, \
                f"Expected 409 for conflicting teacher, got {resp.status_code}: {resp.text}"
            msg = self._err_msg(resp)
            assert "衝突" in msg or "衝堂" in msg, f"Error should mention 衝突/衝堂: {msg}"
            print(f"(409: {msg})", end=" ")

    # ================================================================
    # 指派代課：成功
    # ================================================================

    async def _test_create_substitute_success(self, ctx: Ctx):
        """Teacher B 合格 → 成功指派"""
        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as c:
            resp = await c.post(
                f"{self.backend_url}/api/v1/substitute-details",
                json={
                    "booking_id": ctx.booking_id,
                    "substitute_teacher_id": ctx.teacher_b_id,
                    "substitute_contract_id": ctx.teacher_b_contract_id,
                    "reason": f"{TEST_PREFIX} 測試代課",
                },
            )
            assert resp.status_code == 200, \
                f"Expected 200, got {resp.status_code}: {resp.text}"
            data = resp.json().get("data", {})
            ctx.substitute_detail_id = data.get("id")
            assert ctx.substitute_detail_id, f"No substitute detail id returned: {resp.json()}"

            # 驗證回傳資料
            assert data.get("substitute_teacher_id") == ctx.teacher_b_id
            assert data.get("booking_id") == ctx.booking_id
            assert data.get("substitute_hourly_rate") is not None

            print(f"(sub_id={ctx.substitute_detail_id[:8]}… rate={data.get('substitute_hourly_rate')})", end=" ")

    async def _test_verify_substitute_in_booking(self, ctx: Ctx):
        """確認 booking.substitute_detail_id 已更新"""
        rows = db_query(
            f"SELECT substitute_detail_id FROM bookings WHERE id = '{ctx.booking_id}'"
        )
        assert rows, "Booking not found"
        assert rows[0]["substitute_detail_id"] == ctx.substitute_detail_id, \
            f"Expected substitute_detail_id={ctx.substitute_detail_id}, got {rows[0]['substitute_detail_id']}"
        print("(booking.substitute_detail_id set)", end=" ")

    async def _test_list_substitute_details(self, ctx: Ctx):
        """GET /substitute-details 列表應包含剛建立的紀錄"""
        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as c:
            resp = await c.get(f"{self.backend_url}/api/v1/substitute-details")
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
            data = resp.json().get("data", [])
            ids = [d["id"] for d in data]
            assert ctx.substitute_detail_id in ids, \
                "Substitute detail not found in list"
            print(f"(found in list, total={resp.json().get('total', '?')})", end=" ")

    async def _test_get_substitute_detail(self, ctx: Ctx):
        """GET /substitute-details/:id 取得單筆"""
        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as c:
            resp = await c.get(
                f"{self.backend_url}/api/v1/substitute-details/{ctx.substitute_detail_id}"
            )
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
            data = resp.json().get("data", {})
            assert data.get("id") == ctx.substitute_detail_id
            assert data.get("substitute_teacher_name") is not None
            assert data.get("booking_no") is not None
            print(
                f"(teacher={data.get('substitute_teacher_name')}, "
                f"booking={data.get('booking_no')})",
                end=" ",
            )

    # ================================================================
    # 取消代課
    # ================================================================

    async def _test_cancel_substitute(self, ctx: Ctx):
        """DELETE /substitute-details/:id 取消代課"""
        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as c:
            resp = await c.delete(
                f"{self.backend_url}/api/v1/substitute-details/{ctx.substitute_detail_id}"
            )
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
            print("(cancelled)", end=" ")

    async def _test_verify_booking_cleared(self, ctx: Ctx):
        """確認 booking.substitute_detail_id 已清空"""
        rows = db_query(
            f"SELECT substitute_detail_id, booking_status FROM bookings "
            f"WHERE id = '{ctx.booking_id}'"
        )
        assert rows, "Booking not found"
        assert rows[0]["substitute_detail_id"] is None, \
            f"Expected substitute_detail_id=NULL, got {rows[0]['substitute_detail_id']}"
        assert rows[0]["booking_status"] == "pending", \
            f"Expected booking_status=pending after cancel, got {rows[0]['booking_status']}"
        print("(substitute_detail_id=NULL, status=pending)", end=" ")

    # ── cleanup ──

    async def _cleanup(self, ctx: Ctx):
        """清理所有測試資料"""
        cleanup_sqls = [
            # 先刪代課紀錄（外鍵依賴）
            f"DELETE FROM substitute_details WHERE booking_id IN "
            f"(SELECT id FROM bookings WHERE notes = '{TEST_PREFIX}')",
            # 刪 bookings
            f"DELETE FROM bookings WHERE notes = '{TEST_PREFIX}'",
            # 刪 teacher slots
            f"DELETE FROM teacher_available_slots WHERE notes = '{TEST_PREFIX}'",
            # 刪 teacher contract details
            f"DELETE FROM teacher_contract_details WHERE description LIKE '{TEST_PREFIX}%'",
            # 刪 teacher contracts
            f"DELETE FROM teacher_contracts WHERE notes = '{TEST_PREFIX}'",
            # 刪 teachers
            f"DELETE FROM teachers WHERE teacher_no LIKE '{TEST_PREFIX}%'",
            # 刪 students
            f"DELETE FROM students WHERE student_no LIKE '{TEST_PREFIX}%'",
            # 刪 courses
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
    parser = argparse.ArgumentParser(description="Live Substitute Teacher Test")
    parser.add_argument("--email", default=os.getenv("TEST_EMAIL", ""))
    parser.add_argument("--password", default=os.getenv("TEST_PASSWORD", ""))
    parser.add_argument("--cleanup-only", action="store_true", help="Only cleanup test data")
    parser.add_argument("--keep-data", action="store_true", help="Skip cleanup, keep test data for inspection")
    parser.add_argument("--backend-url", default=BACKEND_URL)
    args = parser.parse_args()

    tester = LiveSubstituteTester(args.backend_url)

    if args.cleanup_only:
        await tester.cleanup_only()
        return

    if not args.email or not args.password:
        print("❌ --email and --password required")
        print("\nUsage:")
        print("  python3 tests/live_substitute_test.py --email employee@eop-test.com --password TestPassword123!")
        sys.exit(1)

    ctx = Ctx(email=args.email, password=args.password)
    success = await tester.run_all_tests(ctx, keep_data=args.keep_data)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

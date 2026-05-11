#!/usr/bin/env python3
"""
End-to-End Leave Request Flow Test

完整請假流程：
  正常請假（≥24h）→ 核准 → 堂數恢復
  緊急請假（<24h, 額度內）→ 核准 → 堂數恢復 + emergency_count +1
  緊急請假（超額）→ 400 拒絕
  禁止請假（<30min）→ 400 拒絕
  查詢驗證：leave_type / deduct_lesson / 合約 quota

使用方式:
    python tests/live_e2e_leave_flow_test.py \
        --email eopAdmin@example.com --password yourpassword

    # 只清理
    python tests/live_e2e_leave_flow_test.py --cleanup-only
"""

import httpx
import asyncio
import subprocess
import argparse
import json
import sys
import os
from datetime import date, datetime, timedelta
from typing import Optional

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8001")
DB_CONTAINER = os.getenv("DB_CONTAINER", "teaching-platform-db")
_TS = datetime.now().strftime("%H%M%S")
TEST_PREFIX = f"E2ELEAVE{_TS}_"


# ── DB helpers ──

def db_query(sql: str) -> list[dict]:
    result = subprocess.run(
        ["docker", "exec", DB_CONTAINER,
         "psql", "-U", "postgres", "-t", "-A", "-F", "\t",
         "-c", f"SELECT row_to_json(t) FROM ({sql}) t"],
        capture_output=True, text=True, timeout=15,
    )
    if result.returncode != 0:
        raise RuntimeError(f"DB error: {result.stderr.strip()}")
    return [json.loads(line) for line in result.stdout.strip().split("\n") if line]


def db_exec(sql: str) -> str:
    result = subprocess.run(
        ["docker", "exec", DB_CONTAINER, "psql", "-U", "postgres", "-c", sql],
        capture_output=True, text=True, timeout=15,
    )
    if result.returncode != 0:
        raise RuntimeError(f"DB error: {result.stderr.strip()}")
    return result.stdout.strip()


def db_value(sql: str) -> Optional[str]:
    result = subprocess.run(
        ["docker", "exec", DB_CONTAINER, "psql", "-U", "postgres", "-t", "-A", "-c", sql],
        capture_output=True, text=True, timeout=15,
    )
    if result.returncode != 0:
        raise RuntimeError(f"DB error: {result.stderr.strip()}")
    lines = [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]
    return lines[0] if lines else None


def get_contract_state(contract_id: str) -> dict:
    rows = db_query(
        f"SELECT remaining_lessons, used_leave_count, used_emergency_leave_count "
        f"FROM student_contracts WHERE id = '{contract_id}'"
    )
    assert rows, f"Contract {contract_id} not found"
    return rows[0]


class LeaveFlowTester:
    def __init__(self):
        self.url = BACKEND_URL.rstrip("/")
        self.results = []
        self.client = None

        # seeded IDs
        self.student_id = None
        self.teacher_id = None
        self.course_id = None
        self.student_contract_id = None
        self.teacher_contract_id = None
        self.normal_slot_id = None

        # booking IDs
        self.booking_a_id = None  # 正常請假 (7天後)
        self.booking_b_id = None  # 緊急請假, 額度內 (~2h後)
        self.booking_c_id = None  # 緊急請假, 超額 (~3h後)
        self.booking_d_id = None  # 禁止請假 (~10min後)

        # leave record IDs
        self.leave_a_id = None
        self.leave_b_id = None

        # dates
        self.normal_date = ""
        self.emergency_start_b = ""
        self.emergency_start_c = ""
        self.blocked_start_d = ""

    async def _post(self, path, json_data=None):
        return await self.client.post(f"{self.url}{path}", json=json_data)

    async def _get(self, path, params=None):
        return await self.client.get(f"{self.url}{path}", params=params)

    async def _test(self, name, fn):
        try:
            result = await fn()
            passed = result is True
            msg = "" if passed else str(result)
            self.results.append((name, passed, msg))
            print(f"  {'✓' if passed else '✗'} {name}" + (f" — {msg}" if msg else ""))
            return passed
        except Exception as e:
            self.results.append((name, False, str(e)))
            print(f"  ✗ {name} — ERROR: {e}")
            return False

    async def run(self, email: str, password: str):
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            self.client = client

            print(f"\n{'=' * 65}")
            print(f"  E2E Leave Request Flow Test")
            print(f"  Backend: {self.url}")
            print(f"{'=' * 65}")

            resp = await self._post("/api/v1/auth/login", {"email": email, "password": password})
            if resp.status_code != 200:
                print(f"\n  ✗ Login failed: {resp.status_code}")
                return False
            print(f"\n  ✓ Login")

            # Seed
            print(f"\n  Seed: 建立測試資料")
            print("  " + "-" * 40)
            seed_ok = await self._test("Seed 測試資料 (via DB)", self._seed)
            if not seed_ok:
                await self._cleanup()
                return False

            # Phase 1: 正常請假
            print(f"\n  Phase 1: 正常請假（≥24h）")
            print("  " + "-" * 40)
            await self._test("建立正常請假", self._create_normal_leave)
            await self._test("核准正常請假 → 堂數恢復", self._approve_normal_leave)

            # Phase 2: 緊急請假 (額度內)
            print(f"\n  Phase 2: 緊急請假（額度內）")
            print("  " + "-" * 40)
            await self._test("建立緊急請假（<24h, 額度內）", self._create_emergency_within_quota)
            await self._test("核准緊急請假 → 堂數恢復 + emergency +1", self._approve_emergency)

            # Phase 3: 錯誤場景
            print(f"\n  Phase 3: 拒絕場景")
            print("  " + "-" * 40)
            await self._test("緊急請假超額 → 400 拒絕", self._reject_over_quota)
            await self._test("課前 <30min → 400 禁止請假", self._reject_blocked)
            await self._test("員工沒帶 initiator_type → 400", self._reject_staff_no_initiator_type)

            # Phase 4: 查詢驗證
            print(f"\n  Phase 4: 查詢驗證")
            print("  " + "-" * 40)
            await self._test("列表包含 leave_type / deduct_lesson", self._verify_list)
            await self._test("單筆查詢欄位正確", self._verify_single)
            await self._test("合約 emergency_leave_quota 正確", self._verify_contract_quota)
            await self._test("補償堂數計入 emergency_leave_quota", self._verify_quota_with_compensation)

            # Phase 5: 員工代老師申請（豁免學生額度）
            print(f"\n  Phase 5: 員工代老師申請緊急請假（豁免學生額度）")
            print("  " + "-" * 40)
            await self._test("員工帶 initiator_type=teacher 緊急請假（quota 已滿）", self._create_staff_as_teacher_emergency)
            await self._test("核准員工代老師申請 → 不消耗學生額度", self._approve_staff_as_teacher_emergency)

            # Cleanup
            print(f"\n  Cleanup")
            print("  " + "-" * 40)
            await self._cleanup()

            passed = sum(1 for _, ok, _ in self.results if ok)
            failed = sum(1 for _, ok, _ in self.results if not ok)
            print(f"\n{'=' * 65}")
            print(f"  Results: {passed}/{len(self.results)} passed — {'ALL PASSED' if failed == 0 else f'{failed} FAILED'}")
            if failed:
                for name, ok, msg in self.results:
                    if not ok:
                        print(f"    ✗ {name}: {msg}")
            print(f"{'=' * 65}\n")
            return failed == 0

    # ── Seed ──

    async def _seed(self):
        now_tw = datetime.utcnow() + timedelta(hours=8)
        self.normal_date = (now_tw + timedelta(days=7)).strftime("%Y-%m-%d")

        # 緊急請假: 2h 後
        em_b = now_tw + timedelta(hours=2)
        em_b_date = em_b.strftime("%Y-%m-%d")
        self.emergency_start_b = em_b.strftime("%H:00:00")
        em_b_end = (em_b + timedelta(hours=1)).strftime("%H:00:00")

        # 緊急請假: 3h 後
        em_c = now_tw + timedelta(hours=3)
        em_c_date = em_c.strftime("%Y-%m-%d")
        self.emergency_start_c = em_c.strftime("%H:00:00")
        em_c_end = (em_c + timedelta(hours=1)).strftime("%H:00:00")

        # 禁止: 10min 後
        blk = now_tw + timedelta(minutes=10)
        blk_date = blk.strftime("%Y-%m-%d")
        self.blocked_start_d = blk.strftime("%H:%M:00")
        blk_end = (blk + timedelta(hours=1)).strftime("%H:%M:00")

        # Course
        self.course_id = db_value(
            f"INSERT INTO courses (course_code, course_name, duration_minutes, is_active) "
            f"VALUES ('{TEST_PREFIX}C1', '{TEST_PREFIX}課程', 60, true) RETURNING id"
        )
        # Student
        self.student_id = db_value(
            f"INSERT INTO students (student_no, name, email, phone, is_active) "
            f"VALUES ('{TEST_PREFIX}S1', '{TEST_PREFIX}學生', '{TEST_PREFIX}s@example.com', '0900111222', true) RETURNING id"
        )
        # Teacher
        self.teacher_id = db_value(
            f"INSERT INTO teachers (teacher_no, name, email, phone, is_active, teacher_level) "
            f"VALUES ('{TEST_PREFIX}T1', '{TEST_PREFIX}教師', '{TEST_PREFIX}t@example.com', '0900333444', true, 3) RETURNING id"
        )
        if not all([self.course_id, self.student_id, self.teacher_id]):
            return "Failed to create base data"

        # Student contract: total_lessons=5 → quota = ceil(5*0.2) = 1
        self.student_contract_id = db_value(
            f"INSERT INTO student_contracts "
            f"(contract_no, student_id, contract_status, start_date, end_date, "
            f"total_lessons, remaining_lessons, total_amount, total_leave_allowed, "
            f"used_emergency_leave_count, notes) "
            f"VALUES ('{TEST_PREFIX}SC1', '{self.student_id}', 'active', "
            f"'{date.today().isoformat()}', '{(date.today() + timedelta(days=365)).isoformat()}', "
            f"5, 1, 10000, 1, 0, '{TEST_PREFIX}') RETURNING id"
        )
        # Teacher contract
        self.teacher_contract_id = db_value(
            f"INSERT INTO teacher_contracts "
            f"(contract_no, teacher_id, start_date, end_date, employment_type, contract_status, notes) "
            f"VALUES ('{TEST_PREFIX}TC1', '{self.teacher_id}', "
            f"'{date.today().isoformat()}', '{(date.today() + timedelta(days=365)).isoformat()}', "
            f"'hourly', 'active', '{TEST_PREFIX}') RETURNING id"
        )
        if not self.student_contract_id or not self.teacher_contract_id:
            return "Failed to create contracts"

        # Teacher slots
        self.normal_slot_id = db_value(
            f"INSERT INTO teacher_available_slots "
            f"(teacher_id, teacher_contract_id, slot_date, start_time, end_time, is_available, notes) "
            f"VALUES ('{self.teacher_id}', '{self.teacher_contract_id}', "
            f"'{self.normal_date}', '09:00', '12:00', true, '{TEST_PREFIX}') RETURNING id"
        )
        # 為緊急/禁止日期建寬範圍 slot
        slot_by_date = {}
        for d in {em_b_date, em_c_date, blk_date}:
            sid = db_value(
                f"INSERT INTO teacher_available_slots "
                f"(teacher_id, teacher_contract_id, slot_date, start_time, end_time, is_available, notes) "
                f"VALUES ('{self.teacher_id}', '{self.teacher_contract_id}', "
                f"'{d}', '00:00', '23:59', true, '{TEST_PREFIX}') RETURNING id"
            )
            if not sid:
                return f"Failed to create slot for {d}"
            slot_by_date[d] = sid

        # Bookings (all confirmed)
        bk_cols = (
            f"student_id, teacher_id, course_id, student_contract_id, "
            f"teacher_contract_id, teacher_hourly_rate, booking_status, lessons_used, notes"
        )
        bk_vals = (
            f"'{self.student_id}', '{self.teacher_id}', '{self.course_id}', '{self.student_contract_id}', "
            f"'{self.teacher_contract_id}', 500, 'confirmed', 1, '{TEST_PREFIX}'"
        )

        self.booking_a_id = db_value(
            f"INSERT INTO bookings (booking_no, {bk_cols}, teacher_slot_id, booking_date, start_time, end_time) "
            f"VALUES ('{TEST_PREFIX}BKA', {bk_vals}, '{self.normal_slot_id}', '{self.normal_date}', '10:00', '11:00') RETURNING id"
        )
        self.booking_b_id = db_value(
            f"INSERT INTO bookings (booking_no, {bk_cols}, teacher_slot_id, booking_date, start_time, end_time) "
            f"VALUES ('{TEST_PREFIX}BKB', {bk_vals}, '{slot_by_date[em_b_date]}', '{em_b_date}', '{self.emergency_start_b}', '{em_b_end}') RETURNING id"
        )
        self.booking_c_id = db_value(
            f"INSERT INTO bookings (booking_no, {bk_cols}, teacher_slot_id, booking_date, start_time, end_time) "
            f"VALUES ('{TEST_PREFIX}BKC', {bk_vals}, '{slot_by_date[em_c_date]}', '{em_c_date}', '{self.emergency_start_c}', '{em_c_end}') RETURNING id"
        )
        self.booking_d_id = db_value(
            f"INSERT INTO bookings (booking_no, {bk_cols}, teacher_slot_id, booking_date, start_time, end_time) "
            f"VALUES ('{TEST_PREFIX}BKD', {bk_vals}, '{slot_by_date[blk_date]}', '{blk_date}', '{self.blocked_start_d}', '{blk_end}') RETURNING id"
        )
        if not all([self.booking_a_id, self.booking_b_id, self.booking_c_id, self.booking_d_id]):
            return "Failed to create bookings"
        return True

    # ── Phase 1: 正常請假 ──

    async def _create_normal_leave(self):
        resp = await self._post("/api/v1/leave-records", {
            "booking_id": self.booking_a_id, "reason": f"{TEST_PREFIX} 正常請假",
            "initiator_type": "student",
        })
        if resp.status_code != 200:
            return f"{resp.status_code} {resp.text[:200]}"
        data = resp.json().get("data", {})
        self.leave_a_id = data.get("id")
        if not self.leave_a_id:
            return "no leave id returned"
        if data.get("leave_type") != "normal":
            return f"leave_type={data.get('leave_type')}, expected normal"
        if data.get("deduct_lesson") is not False:
            return f"deduct_lesson={data.get('deduct_lesson')}, expected false"
        return True

    async def _approve_normal_leave(self):
        before = get_contract_state(self.student_contract_id)
        resp = await self._post(f"/api/v1/leave-records/{self.leave_a_id}/approve")
        if resp.status_code != 200:
            return f"approve failed: {resp.status_code} {resp.text[:200]}"
        after = get_contract_state(self.student_contract_id)
        if after["remaining_lessons"] != before["remaining_lessons"] + 1:
            return f"remaining: {before['remaining_lessons']}→{after['remaining_lessons']}, expected +1"
        if after["used_emergency_leave_count"] != before["used_emergency_leave_count"]:
            return f"emergency_count changed unexpectedly"
        return True

    # ── Phase 2: 緊急請假 (額度內) ──

    async def _create_emergency_within_quota(self):
        resp = await self._post("/api/v1/leave-records", {
            "booking_id": self.booking_b_id, "reason": f"{TEST_PREFIX} 緊急請假",
            "initiator_type": "student",
        })
        if resp.status_code != 200:
            return f"{resp.status_code} {resp.text[:200]}"
        data = resp.json().get("data", {})
        self.leave_b_id = data.get("id")
        if data.get("leave_type") != "emergency":
            return f"leave_type={data.get('leave_type')}, expected emergency"
        if data.get("deduct_lesson") is not False:
            return f"deduct_lesson={data.get('deduct_lesson')}, expected false (within quota)"
        return True

    async def _approve_emergency(self):
        before = get_contract_state(self.student_contract_id)
        resp = await self._post(f"/api/v1/leave-records/{self.leave_b_id}/approve")
        if resp.status_code != 200:
            return f"approve failed: {resp.status_code} {resp.text[:200]}"
        after = get_contract_state(self.student_contract_id)
        if after["remaining_lessons"] != before["remaining_lessons"] + 1:
            return f"remaining not restored: {before['remaining_lessons']}→{after['remaining_lessons']}"
        if after["used_emergency_leave_count"] != before["used_emergency_leave_count"] + 1:
            return f"emergency_count not incremented: {before['used_emergency_leave_count']}→{after['used_emergency_leave_count']}"
        return True

    # ── Phase 3: 拒絕場景 ──

    def _err_msg(self, resp) -> str:
        body = resp.json()
        return body.get("detail") or body.get("message") or str(body)

    async def _reject_over_quota(self):
        resp = await self._post("/api/v1/leave-records", {
            "booking_id": self.booking_c_id, "reason": f"{TEST_PREFIX} 超額",
            "initiator_type": "student",
        })
        if resp.status_code != 400:
            return f"expected 400, got {resp.status_code}: {resp.text[:200]}"
        msg = self._err_msg(resp)
        if "額度" not in msg:
            return f"wrong message: {msg}"
        return True

    async def _reject_blocked(self):
        resp = await self._post("/api/v1/leave-records", {
            "booking_id": self.booking_d_id, "reason": f"{TEST_PREFIX} 太晚",
            "initiator_type": "student",
        })
        if resp.status_code != 400:
            return f"expected 400, got {resp.status_code}: {resp.text[:200]}"
        msg = self._err_msg(resp)
        if "30" not in msg and "分鐘" not in msg:
            return f"wrong message: {msg}"
        return True

    async def _reject_staff_no_initiator_type(self):
        """員工 POST 不帶 initiator_type → 400（檢查順序：在時間/額度檢查前）"""
        resp = await self._post("/api/v1/leave-records", {
            "booking_id": self.booking_d_id, "reason": f"{TEST_PREFIX} no type",
            # 不帶 initiator_type
        })
        if resp.status_code != 400:
            return f"expected 400, got {resp.status_code}: {resp.text[:200]}"
        msg = self._err_msg(resp)
        if "initiator_type" not in msg:
            return f"wrong message: {msg}"
        return True

    # ── Phase 4: 查詢驗證 ──

    async def _verify_list(self):
        resp = await self._get("/api/v1/leave-records")
        if resp.status_code != 200:
            return f"{resp.status_code}"
        records = resp.json().get("data", [])
        our = [r for r in records if r.get("id") in {self.leave_a_id, self.leave_b_id}]
        if len(our) < 1:
            return f"found {len(our)} of our records in list"
        for r in our:
            if "leave_type" not in r:
                return f"missing leave_type in record"
            if "deduct_lesson" not in r:
                return f"missing deduct_lesson in record"
        return True

    async def _verify_single(self):
        resp = await self._get(f"/api/v1/leave-records/{self.leave_b_id}")
        if resp.status_code != 200:
            return f"{resp.status_code}"
        data = resp.json().get("data", {})
        if data.get("leave_type") != "emergency":
            return f"leave_type={data.get('leave_type')}"
        if data.get("leave_status") != "approved":
            return f"leave_status={data.get('leave_status')}"
        return True

    async def _verify_contract_quota(self):
        resp = await self._get(f"/api/v1/student-contracts/{self.student_contract_id}")
        if resp.status_code != 200:
            return f"{resp.status_code}"
        data = resp.json().get("data", {})
        if data.get("emergency_leave_quota") != 1:
            return f"quota={data.get('emergency_leave_quota')}, expected 1 (ceil(5*0.2))"
        if data.get("used_emergency_leave_count") != 1:
            return f"used={data.get('used_emergency_leave_count')}, expected 1"
        if data.get("remaining_emergency_leave_count") != 0:
            return f"remaining_em={data.get('remaining_emergency_leave_count')}, expected 0"
        return True

    async def _verify_quota_with_compensation(self):
        """補償堂數應計入 emergency_leave_quota = ceil((total_lessons + 補償) * 0.2)"""
        sc_id = self.student_contract_id
        # baseline: total_lessons=5, used_em=1, quota=1, remaining=0

        # +compensation 10 → effective=15, quota=ceil(15*0.2)=3, remaining=max(0,3-1)=2
        r = await self._post(f"/api/v1/student-contracts/{sc_id}/details", {
            "detail_type": "compensation", "description": f"{TEST_PREFIX}comp1", "amount": 10,
        })
        if r.status_code != 200:
            return f"add comp1: {r.status_code} {r.text[:200]}"
        comp1_id = r.json()["data"]["id"]

        r = await self._get(f"/api/v1/student-contracts/{sc_id}")
        d = r.json()["data"]
        if d.get("emergency_leave_quota") != 3:
            return f"+10: quota={d.get('emergency_leave_quota')}, expected 3"
        if d.get("remaining_emergency_leave_count") != 2:
            return f"+10: remaining_em={d.get('remaining_emergency_leave_count')}, expected 2"

        # +compensation 5 → effective=20, quota=4, remaining=3
        r = await self._post(f"/api/v1/student-contracts/{sc_id}/details", {
            "detail_type": "compensation", "description": f"{TEST_PREFIX}comp2", "amount": 5,
        })
        if r.status_code != 200:
            return f"add comp2: {r.status_code}"
        comp2_id = r.json()["data"]["id"]

        r = await self._get(f"/api/v1/student-contracts/{sc_id}")
        d = r.json()["data"]
        if d.get("emergency_leave_quota") != 4:
            return f"+15: quota={d.get('emergency_leave_quota')}, expected 4"
        if d.get("remaining_emergency_leave_count") != 3:
            return f"+15: remaining_em={d.get('remaining_emergency_leave_count')}, expected 3"

        # list endpoint 也應反映
        r = await self._get("/api/v1/student-contracts", params={"student_id": self.student_id})
        items = r.json().get("data", [])
        match = [x for x in items if x["id"] == sc_id]
        if not match:
            return "contract missing in list"
        if match[0].get("emergency_leave_quota") != 4:
            return f"list: quota={match[0].get('emergency_leave_quota')}, expected 4"
        if match[0].get("remaining_emergency_leave_count") != 3:
            return f"list: remaining_em={match[0].get('remaining_emergency_leave_count')}, expected 3"

        # 刪除補償 → quota 還原 (cleanup 也會兜底，這裡先驗證刪除路徑)
        await self.client.delete(f"{self.url}/api/v1/student-contracts/{sc_id}/details/{comp1_id}")
        await self.client.delete(f"{self.url}/api/v1/student-contracts/{sc_id}/details/{comp2_id}")
        r = await self._get(f"/api/v1/student-contracts/{sc_id}")
        d = r.json()["data"]
        if d.get("emergency_leave_quota") != 1:
            return f"after delete: quota={d.get('emergency_leave_quota')}, expected 1"
        return True

    # ── Phase 5: 員工代老師申請 ──

    async def _create_staff_as_teacher_emergency(self):
        """booking_c 學生 quota 已用完（_reject_over_quota 已驗證），
        但員工帶 initiator_type=teacher 應豁免合約檢查，直接成功"""
        resp = await self._post("/api/v1/leave-records", {
            "booking_id": self.booking_c_id, "reason": f"{TEST_PREFIX} 員工代老師申請",
            "initiator_type": "teacher",
        })
        if resp.status_code != 200:
            return f"{resp.status_code} {resp.text[:200]}"
        data = resp.json().get("data", {})
        self.leave_staff_teacher_id = data.get("id")
        if data.get("initiator_type") != "teacher":
            return f"initiator_type={data.get('initiator_type')}, expected teacher"
        if data.get("initiator_teacher_id") != self.teacher_id:
            return f"initiator_teacher_id={data.get('initiator_teacher_id')}, expected {self.teacher_id}"
        if data.get("initiator_student_id") is not None:
            return f"initiator_student_id should be None, got {data.get('initiator_student_id')}"
        if data.get("leave_type") != "emergency":
            return f"leave_type={data.get('leave_type')}, expected emergency"
        return True

    async def _approve_staff_as_teacher_emergency(self):
        """核准員工代老師申請的緊急請假 → 學生額度不消耗、不寫 student_contract_leave_records"""
        before = get_contract_state(self.student_contract_id)
        sclr_before = int(db_value(
            f"SELECT COUNT(*) FROM student_contract_leave_records "
            f"WHERE student_contract_id = '{self.student_contract_id}' AND is_deleted = FALSE"
        ) or 0)
        resp = await self._post(f"/api/v1/leave-records/{self.leave_staff_teacher_id}/approve")
        if resp.status_code != 200:
            return f"approve failed: {resp.status_code} {resp.text[:200]}"
        after = get_contract_state(self.student_contract_id)
        if after["used_emergency_leave_count"] != before["used_emergency_leave_count"]:
            return (
                f"used_emergency_leave_count changed: "
                f"{before['used_emergency_leave_count']}→{after['used_emergency_leave_count']}（teacher initiator 應豁免）"
            )
        sclr_after = int(db_value(
            f"SELECT COUNT(*) FROM student_contract_leave_records "
            f"WHERE student_contract_id = '{self.student_contract_id}' AND is_deleted = FALSE"
        ) or 0)
        if sclr_after != sclr_before:
            return f"student_contract_leave_records 不應新增（teacher initiator）: {sclr_before}→{sclr_after}"
        return True

    # ── Cleanup ──

    async def _cleanup(self):
        bk_sub = f"SELECT id FROM bookings WHERE booking_no LIKE '{TEST_PREFIX}%'"
        sc_sub = f"SELECT id FROM student_contracts WHERE notes = '{TEST_PREFIX}'"
        sqls = [
            f"DELETE FROM leave_records WHERE booking_id IN ({bk_sub})",
            f"DELETE FROM student_contract_leave_records WHERE student_contract_id IN ({sc_sub})",
            f"DELETE FROM student_contract_details WHERE student_contract_id IN ({sc_sub})",
            f"DELETE FROM substitute_details WHERE booking_id IN ({bk_sub})",
            f"DELETE FROM booking_details WHERE booking_id IN ({bk_sub})",
            f"DELETE FROM zoom_meeting_logs WHERE booking_id IN ({bk_sub})",
            f"DELETE FROM teacher_bonus_records WHERE related_booking_id IN ({bk_sub})",
            f"DELETE FROM bookings WHERE booking_no LIKE '{TEST_PREFIX}%'",
            f"DELETE FROM teacher_available_slots WHERE notes = '{TEST_PREFIX}'",
            f"DELETE FROM student_contracts WHERE notes = '{TEST_PREFIX}'",
            f"DELETE FROM teacher_contracts WHERE notes = '{TEST_PREFIX}'",
            f"DELETE FROM teachers WHERE teacher_no LIKE '{TEST_PREFIX}%'",
            f"DELETE FROM students WHERE student_no LIKE '{TEST_PREFIX}%'",
            f"DELETE FROM courses WHERE course_code LIKE '{TEST_PREFIX}%'",
        ]
        for sql in sqls:
            db_exec(sql)
        print("    cleaned")


async def main():
    parser = argparse.ArgumentParser(description="E2E Leave Request Flow Test")
    parser.add_argument("--email", required=True, help="Login email")
    parser.add_argument("--password", required=True, help="Login password")
    parser.add_argument("--cleanup-only", action="store_true")
    args = parser.parse_args()

    tester = LeaveFlowTester()

    if args.cleanup_only:
        await tester._cleanup()
        print("Cleanup done.")
        return

    ok = await tester.run(args.email, args.password)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    asyncio.run(main())

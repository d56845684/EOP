#!/usr/bin/env python3
"""
End-to-End Trial-to-Formal Student Flow Test

完整試上轉正流程：
  建立試上學生 → 建立試上預約 → 驗證 hourly_rate=0
  → 完成預約 → 驗證 trial_completed 獎金
  → 轉正 → 驗證差額獎金 + 總額
  → 錯誤場景驗證（regular/pending/已轉正）
  → bonus=0 邊界測試 → 清理

使用方式:
    python tests/live_e2e_trial_to_formal_test.py \
        --email eopAdmin@example.com --password yourpassword

    # 只清理測試資料
    python tests/live_e2e_trial_to_formal_test.py --cleanup-only
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
TEST_PREFIX = f"E2ETRIAL{_TS}_"

TRIAL_COMPLETED_BONUS = 300
TRIAL_TO_FORMAL_BONUS = 500
EXPECTED_DIFF_BONUS = TRIAL_TO_FORMAL_BONUS - TRIAL_COMPLETED_BONUS  # 200


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


class TrialToFormalTester:
    def __init__(self):
        self.url = BACKEND_URL.rstrip("/")
        self.results = []
        self.client = None
        self.slot_date = (date.today() + timedelta(days=30)).isoformat()

        # seeded IDs
        self.teacher_id = None
        self.teacher_contract_id = None
        self.course_id = None
        self.teacher_slot_id = None

        self.student_1_id = None  # trial student for main flow
        self.student_2_id = None  # trial student for bonus=0 test

        self.trial_booking_id = None       # trial + pending → completed
        self.regular_booking_id = None     # regular + completed (should reject)
        self.pending_booking_id = None     # trial + pending (should reject)
        self.trial_booking_2_id = None     # trial + completed for student 2

        # 新流程：必須預先有 pending 合約並上傳 PDF
        self.contract_1_id = None          # pending, student_1, with PDF
        self.contract_2_id = None          # pending, student_2, with PDF
        self.contract_no_pdf_id = None     # pending, student_2, no PDF (錯誤測試)

        self.original_completed_bonus = None
        self.original_formal_bonus = None

    async def _post(self, path, json_data):
        return await self.client.post(f"{self.url}{path}", json=json_data)

    async def _get(self, path, params=None):
        return await self.client.get(f"{self.url}{path}", params=params)

    async def _put(self, path, json_data):
        return await self.client.put(f"{self.url}{path}", json=json_data)

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
            print(f"  E2E Trial-to-Formal Flow Test")
            print(f"  Backend: {self.url}")
            print(f"  Bonus: completed={TRIAL_COMPLETED_BONUS}, formal={TRIAL_TO_FORMAL_BONUS}, diff={EXPECTED_DIFF_BONUS}")
            print(f"{'=' * 65}")

            # Login
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

            # Phase 1: 試上課完成 → 獎金
            print(f"\n  Phase 1: 試上課完成與獎金")
            print("  " + "-" * 40)
            await self._test("驗證 trial booking hourly_rate=0", self._verify_hourly_rate_zero)
            await self._test("更新預約 → completed（觸發獎金）", self._complete_trial_booking)
            await self._test("驗證 trial_completed 獎金紀錄", self._verify_completed_bonus)

            # Phase 2: 錯誤場景（必須在轉正前測試）
            print(f"\n  Phase 2: 錯誤場景驗證")
            print("  " + "-" * 40)
            await self._test("拒絕 regular booking（400）", self._reject_regular)
            await self._test("拒絕 pending booking（400）", self._reject_pending)
            await self._test("拒絕沒上傳 PDF 的合約（400）", self._reject_no_pdf)
            await self._test("拒絕合約不屬於該學生（400）", self._reject_wrong_student)
            await self._test("拒絕為試上學生建 active 合約（400）", self._reject_create_active_for_trial)
            await self._test("拒絕 PUT 把試上學生合約改 active（400）", self._reject_update_to_active_for_trial)

            # Phase 3: 試上轉正 → 差額獎金
            print(f"\n  Phase 3: 試上轉正")
            print("  " + "-" * 40)
            await self._test("轉正學生 1（成功）", self._convert_student_1)
            await self._test("驗證合約狀態 → active", self._verify_contract_active)
            await self._test("驗證 trial_to_formal 差額獎金", self._verify_diff_bonus)
            await self._test("驗證總獎金 = trial_to_formal_bonus", self._verify_total_bonus)
            await self._test("驗證 bookings_view.is_trial_to_formal", self._verify_is_trial_to_formal)
            await self._test("拒絕已轉正 booking（400）", self._reject_already_converted)

            # Phase 4: bonus=0 邊界
            print(f"\n  Phase 4: bonus=0 邊界測試")
            print("  " + "-" * 40)
            await self._test("設定 bonus=0 並轉正學生 2", self._convert_student_2_bonus_zero)
            await self._test("驗證 bonus=0 紀錄存在", self._verify_bonus_zero_record)

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
        # 取得 teacher + active contract
        rows = db_query(
            "SELECT t.id AS teacher_id, tc.id AS tc_id, "
            "tc.trial_to_formal_bonus, tc.trial_completed_bonus "
            "FROM teachers t "
            "JOIN teacher_contracts tc ON tc.teacher_id = t.id "
            "AND tc.contract_status = 'active' AND tc.is_deleted = FALSE "
            "WHERE t.is_deleted = FALSE LIMIT 1"
        )
        if not rows:
            return "No teacher with active contract found"
        self.teacher_id = rows[0]["teacher_id"]
        self.teacher_contract_id = rows[0]["tc_id"]
        self.original_formal_bonus = str(rows[0]["trial_to_formal_bonus"]) if rows[0]["trial_to_formal_bonus"] is not None else "0"
        self.original_completed_bonus = str(rows[0]["trial_completed_bonus"]) if rows[0]["trial_completed_bonus"] is not None else "0"

        # 設定獎金金額
        db_exec(
            f"UPDATE teacher_contracts SET "
            f"trial_completed_bonus = {TRIAL_COMPLETED_BONUS}, "
            f"trial_to_formal_bonus = {TRIAL_TO_FORMAL_BONUS} "
            f"WHERE id = '{self.teacher_contract_id}'"
        )

        # 取得 course
        rows = db_query("SELECT id FROM courses WHERE is_deleted = FALSE LIMIT 1")
        if not rows:
            return "No course found"
        self.course_id = rows[0]["id"]

        # 建立 trial students
        self.student_1_id = db_value(
            f"INSERT INTO students (student_no, name, email, phone, student_type, is_active) "
            f"VALUES ('{TEST_PREFIX}S1', '{TEST_PREFIX}試上生1', '{TEST_PREFIX}s1@example.com', "
            f"'0900000001', 'trial', true) RETURNING id"
        )
        self.student_2_id = db_value(
            f"INSERT INTO students (student_no, name, email, phone, student_type, is_active) "
            f"VALUES ('{TEST_PREFIX}S2', '{TEST_PREFIX}試上生2', '{TEST_PREFIX}s2@example.com', "
            f"'0900000002', 'trial', true) RETURNING id"
        )
        if not self.student_1_id or not self.student_2_id:
            return "Failed to create trial students"

        # 建立 teacher slot
        self.teacher_slot_id = db_value(
            f"INSERT INTO teacher_available_slots "
            f"(teacher_id, teacher_contract_id, slot_date, start_time, end_time, is_available, notes) "
            f"VALUES ('{self.teacher_id}', '{self.teacher_contract_id}', '{self.slot_date}', "
            f"'09:00', '15:00', true, '{TEST_PREFIX}') RETURNING id"
        )

        # 建立 bookings
        def _bk(no, sid, start, end, status, btype):
            return db_value(
                f"INSERT INTO bookings "
                f"(booking_no, student_id, teacher_id, course_id, "
                f"teacher_contract_id, teacher_hourly_rate, "
                f"teacher_slot_id, booking_date, start_time, end_time, "
                f"booking_status, booking_type, notes) "
                f"VALUES ('{no}', '{sid}', '{self.teacher_id}', '{self.course_id}', "
                f"'{self.teacher_contract_id}', 0, "
                f"'{self.teacher_slot_id}', '{self.slot_date}', '{start}', '{end}', "
                f"'{status}', '{btype}', '{TEST_PREFIX}') RETURNING id"
            )

        self.trial_booking_id = _bk(f"{TEST_PREFIX}BK1", self.student_1_id, "09:00", "09:30", "pending", "trial")
        self.regular_booking_id = _bk(f"{TEST_PREFIX}BK2", self.student_1_id, "10:00", "10:30", "completed", "regular")
        self.pending_booking_id = _bk(f"{TEST_PREFIX}BK3", self.student_1_id, "11:00", "11:30", "pending", "trial")
        self.trial_booking_2_id = _bk(f"{TEST_PREFIX}BK4", self.student_2_id, "13:00", "13:30", "completed", "trial")

        if not all([self.trial_booking_id, self.regular_booking_id, self.pending_booking_id, self.trial_booking_2_id]):
            return "Failed to create some bookings"

        # 預建 pending 合約（新流程要求）
        start = date.today().isoformat()
        end = (date.today() + timedelta(days=180)).isoformat()

        def _sc(no, sid, with_pdf=True):
            file_clause = (
                f"'student-contracts/seed/{no}.pdf'" if with_pdf else "NULL"
            )
            return db_value(
                f"INSERT INTO student_contracts "
                f"(contract_no, student_id, contract_status, start_date, end_date, "
                f" total_lessons, remaining_lessons, total_amount, total_leave_allowed, "
                f" contract_file_path, notes) "
                f"VALUES ('{no}', '{sid}', 'pending', '{start}', '{end}', "
                f"10, 10, 10000, 2, {file_clause}, '{TEST_PREFIX}') RETURNING id"
            )

        self.contract_1_id = _sc(f"{TEST_PREFIX}C1", self.student_1_id, with_pdf=True)
        self.contract_2_id = _sc(f"{TEST_PREFIX}C2", self.student_2_id, with_pdf=True)
        self.contract_no_pdf_id = _sc(f"{TEST_PREFIX}CNOPDF", self.student_2_id, with_pdf=False)
        if not all([self.contract_1_id, self.contract_2_id, self.contract_no_pdf_id]):
            return "Failed to create pending contracts"
        return True

    # ── Phase 1: 試上完成 ──

    async def _verify_hourly_rate_zero(self):
        rows = db_query(
            f"SELECT teacher_hourly_rate, booking_type FROM bookings "
            f"WHERE id = '{self.trial_booking_id}' AND is_deleted = FALSE"
        )
        if not rows:
            return "Booking not found"
        if rows[0]["booking_type"] != "trial":
            return f"booking_type={rows[0]['booking_type']}, expected trial"
        if float(rows[0]["teacher_hourly_rate"]) != 0:
            return f"hourly_rate={rows[0]['teacher_hourly_rate']}, expected 0"
        return True

    async def _complete_trial_booking(self):
        resp = await self._put(f"/api/v1/bookings/{self.trial_booking_id}", {"booking_status": "completed"})
        if resp.status_code != 200:
            return f"{resp.status_code} {resp.text[:200]}"
        if resp.json().get("data", {}).get("booking_status") != "completed":
            return "booking_status not completed"
        return True

    async def _verify_completed_bonus(self):
        rows = db_query(
            f"SELECT amount, description FROM teacher_bonus_records "
            f"WHERE related_booking_id = '{self.trial_booking_id}' "
            f"AND bonus_type = 'trial_completed' AND is_deleted = FALSE"
        )
        if not rows:
            return "No trial_completed bonus record"
        amount = float(rows[0]["amount"])
        if amount != TRIAL_COMPLETED_BONUS:
            return f"amount={amount}, expected {TRIAL_COMPLETED_BONUS}"
        return True

    # ── Phase 2: 轉正 ──

    def _convert_payload(self, contract_id, booking_id=None):
        return {
            "student_contract_id": contract_id,
            "teacher_id": self.teacher_id,
            "booking_id": booking_id,
        }

    async def _convert_student_1(self):
        resp = await self._post(
            f"/api/v1/students/{self.student_1_id}/convert-to-formal",
            self._convert_payload(self.contract_1_id, self.trial_booking_id),
        )
        if resp.status_code != 200:
            return f"{resp.status_code} {resp.text[:200]}"
        data = resp.json()
        if data.get("student", {}).get("student_type") != "formal":
            return f"student_type not formal"
        if data.get("bonus_amount") != EXPECTED_DIFF_BONUS:
            return f"bonus_amount={data.get('bonus_amount')}, expected {EXPECTED_DIFF_BONUS}"
        return True

    async def _verify_contract_active(self):
        rows = db_query(
            f"SELECT contract_status FROM student_contracts WHERE id = '{self.contract_1_id}'"
        )
        if not rows:
            return "contract not found"
        if rows[0]["contract_status"] != "active":
            return f"contract_status={rows[0]['contract_status']}, expected active"
        return True

    async def _verify_diff_bonus(self):
        rows = db_query(
            f"SELECT amount FROM teacher_bonus_records "
            f"WHERE related_booking_id = '{self.trial_booking_id}' "
            f"AND bonus_type = 'trial_to_formal' AND is_deleted = FALSE"
        )
        if not rows:
            return "No trial_to_formal bonus record"
        amount = float(rows[0]["amount"])
        if amount != EXPECTED_DIFF_BONUS:
            return f"diff amount={amount}, expected {EXPECTED_DIFF_BONUS}"
        return True

    async def _verify_total_bonus(self):
        rows = db_query(
            f"SELECT SUM(amount) AS total FROM teacher_bonus_records "
            f"WHERE related_booking_id = '{self.trial_booking_id}' "
            f"AND bonus_type IN ('trial_completed', 'trial_to_formal') AND is_deleted = FALSE"
        )
        if not rows:
            return "No bonus records"
        total = float(rows[0]["total"])
        if total != TRIAL_TO_FORMAL_BONUS:
            return f"total={total}, expected {TRIAL_TO_FORMAL_BONUS}"
        return True

    async def _verify_is_trial_to_formal(self):
        rows = db_query(
            f"SELECT is_trial_to_formal FROM bookings_view "
            f"WHERE id = '{self.trial_booking_id}'"
        )
        if not rows:
            return "Booking not in bookings_view"
        if rows[0]["is_trial_to_formal"] is not True:
            return f"is_trial_to_formal={rows[0]['is_trial_to_formal']}"
        return True

    # ── Phase 3: 錯誤場景 ──

    def _err_msg(self, resp) -> str:
        body = resp.json()
        return body.get("detail") or body.get("message") or str(body)

    async def _reject_regular(self):
        resp = await self._post(
            f"/api/v1/students/{self.student_1_id}/convert-to-formal",
            self._convert_payload(self.contract_1_id, self.regular_booking_id),
        )
        if resp.status_code != 400:
            return f"expected 400, got {resp.status_code}: {resp.text[:200]}"
        msg = self._err_msg(resp)
        if "試上" not in msg:
            return f"wrong message: {msg}"
        return True

    async def _reject_pending(self):
        resp = await self._post(
            f"/api/v1/students/{self.student_1_id}/convert-to-formal",
            self._convert_payload(self.contract_1_id, self.pending_booking_id),
        )
        if resp.status_code != 400:
            return f"expected 400, got {resp.status_code}: {resp.text[:200]}"
        msg = self._err_msg(resp)
        if "完成" not in msg and "completed" not in msg.lower():
            return f"wrong message: {msg}"
        return True

    async def _reject_no_pdf(self):
        resp = await self._post(
            f"/api/v1/students/{self.student_2_id}/convert-to-formal",
            self._convert_payload(self.contract_no_pdf_id),
        )
        if resp.status_code != 400:
            return f"expected 400, got {resp.status_code}: {resp.text[:200]}"
        msg = self._err_msg(resp)
        if "PDF" not in msg:
            return f"wrong message: {msg}"
        return True

    async def _reject_wrong_student(self):
        # student_2 拿 student_1 的 contract_1_id
        resp = await self._post(
            f"/api/v1/students/{self.student_2_id}/convert-to-formal",
            self._convert_payload(self.contract_1_id),
        )
        if resp.status_code != 400:
            return f"expected 400, got {resp.status_code}: {resp.text[:200]}"
        msg = self._err_msg(resp)
        if "不屬於" not in msg:
            return f"wrong message: {msg}"
        return True

    async def _reject_create_active_for_trial(self):
        # 直接用 API POST 建 active 合約給 trial 學生 → 應拒
        resp = await self._post("/api/v1/student-contracts", {
            "student_id": self.student_2_id,
            "contract_status": "active",
            "start_date": date.today().isoformat(),
            "end_date": (date.today() + timedelta(days=180)).isoformat(),
            "total_lessons": 10, "remaining_lessons": 10, "total_amount": 10000,
            "notes": TEST_PREFIX,
        })
        if resp.status_code != 400:
            return f"expected 400, got {resp.status_code}: {resp.text[:200]}"
        msg = self._err_msg(resp)
        if "轉正" not in msg:
            return f"wrong message: {msg}"
        return True

    async def _reject_update_to_active_for_trial(self):
        # PUT 把 contract_2_id (pending, trial) 改 active → 應拒
        resp = await self._put(
            f"/api/v1/student-contracts/{self.contract_2_id}",
            {"contract_status": "active"},
        )
        if resp.status_code != 400:
            return f"expected 400, got {resp.status_code}: {resp.text[:200]}"
        msg = self._err_msg(resp)
        if "轉正" not in msg:
            return f"wrong message: {msg}"
        return True

    async def _reject_already_converted(self):
        # student_2 + 已被 student_1 標記轉正的 trial_booking_id
        resp = await self._post(
            f"/api/v1/students/{self.student_2_id}/convert-to-formal",
            self._convert_payload(self.contract_2_id, self.trial_booking_id),
        )
        if resp.status_code != 400:
            return f"expected 400, got {resp.status_code}: {resp.text[:200]}"
        msg = self._err_msg(resp)
        if "已被標記為轉正" not in msg:
            return f"wrong message: {msg}"
        return True

    # ── Phase 4: bonus=0 ──

    async def _convert_student_2_bonus_zero(self):
        # 設定 bonus=0
        db_exec(
            f"UPDATE teacher_contracts SET trial_to_formal_bonus = 0 "
            f"WHERE id = '{self.teacher_contract_id}'"
        )
        resp = await self._post(
            f"/api/v1/students/{self.student_2_id}/convert-to-formal",
            self._convert_payload(self.contract_2_id, self.trial_booking_2_id),
        )
        if resp.status_code != 200:
            return f"{resp.status_code} {resp.text[:200]}"
        data = resp.json()
        if data.get("bonus_recorded") is not True:
            return f"bonus_recorded={data.get('bonus_recorded')}"
        if data.get("bonus_amount") != 0:
            return f"bonus_amount={data.get('bonus_amount')}, expected 0"
        return True

    async def _verify_bonus_zero_record(self):
        rows = db_query(
            f"SELECT amount FROM teacher_bonus_records "
            f"WHERE related_booking_id = '{self.trial_booking_2_id}' "
            f"AND bonus_type = 'trial_to_formal' AND is_deleted = FALSE"
        )
        if not rows:
            return "No bonus=0 record found"
        if float(rows[0]["amount"]) != 0:
            return f"amount={rows[0]['amount']}, expected 0"

        rows2 = db_query(
            f"SELECT is_trial_to_formal FROM bookings_view "
            f"WHERE id = '{self.trial_booking_2_id}'"
        )
        if not rows2 or rows2[0]["is_trial_to_formal"] is not True:
            return "is_trial_to_formal not true for booking 2"
        return True

    # ── Cleanup ──

    async def _cleanup(self):
        sqls = [
            f"DELETE FROM system_alerts WHERE alert_type = 'trial_to_formal_bonus_failed' "
            f"AND metadata->>'student_id' IN (SELECT id::text FROM students WHERE student_no LIKE '{TEST_PREFIX}%')",
            f"DELETE FROM teacher_bonus_records WHERE "
            f"related_student_id IN (SELECT id FROM students WHERE student_no LIKE '{TEST_PREFIX}%') "
            f"OR description LIKE '%{TEST_PREFIX}%'",
            f"DELETE FROM student_contracts WHERE contract_no LIKE '{TEST_PREFIX}%'",
            f"DELETE FROM bookings WHERE notes = '{TEST_PREFIX}'",
            f"DELETE FROM teacher_available_slots WHERE notes = '{TEST_PREFIX}'",
            f"DELETE FROM students WHERE student_no LIKE '{TEST_PREFIX}%'",
        ]
        for sql in sqls:
            db_exec(sql)

        # 恢復 teacher_contract bonus 值
        if self.teacher_contract_id:
            cv = self.original_completed_bonus if self.original_completed_bonus and self.original_completed_bonus != "None" else "0"
            fv = self.original_formal_bonus if self.original_formal_bonus and self.original_formal_bonus != "None" else "0"
            db_exec(
                f"UPDATE teacher_contracts SET "
                f"trial_completed_bonus = {cv}, trial_to_formal_bonus = {fv} "
                f"WHERE id = '{self.teacher_contract_id}'"
            )
        print("    cleaned")


async def main():
    parser = argparse.ArgumentParser(description="E2E Trial-to-Formal Flow Test")
    parser.add_argument("--email", required=True, help="Login email")
    parser.add_argument("--password", required=True, help="Login password")
    parser.add_argument("--cleanup-only", action="store_true")
    args = parser.parse_args()

    tester = TrialToFormalTester()

    if args.cleanup_only:
        await tester._cleanup()
        print("Cleanup done.")
        return

    ok = await tester.run(args.email, args.password)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    asyncio.run(main())

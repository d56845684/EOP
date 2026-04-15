#!/usr/bin/env python3
"""
Live Booking Concurrency Test

驗證預約建立的交易安全性：
1. 建立預約成功
2. 同時段重複預約被拒絕（409 Conflict）
3. 刪除預約後可重新預約同時段

使用方式:
    python tests/live_booking_concurrency_test.py --email eopAdmin@example.com --password yourpassword
"""

import httpx
import asyncio
import subprocess
import json
import argparse
import sys
import os
from datetime import datetime, date, timedelta
from typing import Optional

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8001")
DB_CONTAINER = os.getenv("DB_CONTAINER", "teaching-platform-db")
_TS = datetime.now().strftime("%H%M%S")
TEST_PREFIX = f"CONCUR{_TS}_"


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


class ConcurrencyTester:
    def __init__(self):
        self.url = BACKEND_URL.rstrip("/")
        self.results = []
        self.client = None
        self.slot_date = (date.today() + timedelta(days=14)).isoformat()

        # seeded IDs
        self.course_id = None
        self.student_id = None
        self.teacher_id = None
        self.student_contract_id = None
        self.teacher_contract_id = None
        self.teacher_contract_detail_id = None
        self.student_course_id = None
        self.preference_id = None
        self.slot_id = None
        self.booking_id = None

    async def _post(self, path, json_data=None):
        return await self.client.post(f"{self.url}{path}", json=json_data or {})

    async def _get(self, path, params=None):
        return await self.client.get(f"{self.url}{path}", params=params)

    async def _delete(self, path):
        return await self.client.delete(f"{self.url}{path}")

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

            print(f"\n{'=' * 60}")
            print(f"  Booking Concurrency Test")
            print(f"  Backend: {self.url}")
            print(f"  Slot Date: {self.slot_date}")
            print(f"{'=' * 60}")

            resp = await self._post("/api/v1/auth/login", {"email": email, "password": password})
            if resp.status_code != 200:
                print(f"\n  ✗ Login failed: {resp.status_code}")
                return False
            print(f"\n  ✓ Login")

            # Setup
            print(f"\n  Setup: 建立測試資料")
            print("  " + "-" * 40)
            await self._test("建立課程", self._create_course)
            await self._test("建立學生", self._create_student)
            await self._test("建立教師", self._create_teacher)
            await self._test("建立學生合約", self._create_student_contract)
            await self._test("建立教師合約 + 費率", self._create_teacher_contract)
            await self._test("學生選課", self._create_student_course)
            await self._test("設定教師偏好", self._create_preference)
            await self._test("建立教師時段 (10:00-12:00)", self._create_slot)

            # Tests
            print(f"\n  Phase 1: 併發安全性測試")
            print("  " + "-" * 40)
            await self._test("建立預約（成功）", self._create_booking)
            await self._test("重複預約同時段（應回 409）", self._duplicate_booking)
            await self._test("刪除預約", self._delete_booking)
            await self._test("重新預約同時段（成功）", self._rebook_after_delete)

            # Cleanup
            print(f"\n  Cleanup")
            print("  " + "-" * 40)
            await self._cleanup()

            passed = sum(1 for _, ok, _ in self.results if ok)
            failed = sum(1 for _, ok, _ in self.results if not ok)
            print(f"\n{'=' * 60}")
            print(f"  Results: {passed}/{len(self.results)} passed — {'ALL PASSED' if failed == 0 else f'{failed} FAILED'}")
            if failed:
                for name, ok, msg in self.results:
                    if not ok:
                        print(f"    ✗ {name}: {msg}")
            print(f"{'=' * 60}\n")
            return failed == 0

    # ── Setup ──

    async def _create_course(self):
        resp = await self._post("/api/v1/courses", {
            "course_code": f"{TEST_PREFIX}C01", "course_name": f"{TEST_PREFIX}課程",
            "duration_minutes": 60,
        })
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        self.course_id = resp.json()["data"]["id"]
        return True

    async def _create_student(self):
        resp = await self._post("/api/v1/students", {
            "student_no": f"{TEST_PREFIX}S01", "name": f"{TEST_PREFIX}學生",
            "email": f"{TEST_PREFIX}s@test.local", "student_type": "formal",
        })
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        self.student_id = resp.json()["data"]["id"]
        return True

    async def _create_teacher(self):
        resp = await self._post("/api/v1/teachers", {
            "teacher_no": f"{TEST_PREFIX}T01", "name": f"{TEST_PREFIX}教師",
            "email": f"{TEST_PREFIX}t@test.local", "teacher_level": 1,
        })
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        self.teacher_id = resp.json()["data"]["id"]
        return True

    async def _create_student_contract(self):
        resp = await self._post("/api/v1/student-contracts", {
            "student_id": self.student_id, "contract_status": "active",
            "start_date": date.today().isoformat(),
            "end_date": (date.today() + timedelta(days=365)).isoformat(),
            "total_lessons": 10, "remaining_lessons": 10, "total_amount": 20000,
        })
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        self.student_contract_id = resp.json()["data"]["id"]
        return True

    async def _create_teacher_contract(self):
        resp = await self._post("/api/v1/teacher-contracts", {
            "teacher_id": self.teacher_id, "contract_status": "active",
            "start_date": date.today().isoformat(),
            "end_date": (date.today() + timedelta(days=365)).isoformat(),
            "employment_type": "hourly",
        })
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        self.teacher_contract_id = resp.json()["data"]["id"]
        # 新增課程費率
        resp2 = await self._post(f"/api/v1/teacher-contracts/{self.teacher_contract_id}/details", {
            "detail_type": "course_rate", "course_id": self.course_id,
            "description": f"{TEST_PREFIX} 費率", "amount": 500,
        })
        if resp2.status_code != 200: return f"detail: {resp2.status_code} {resp2.text[:200]}"
        self.teacher_contract_detail_id = resp2.json()["data"]["id"]
        return True

    async def _create_student_course(self):
        resp = await self._post("/api/v1/student-courses", {
            "student_id": self.student_id, "course_id": self.course_id,
        })
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        self.student_course_id = resp.json()["data"]["id"]
        return True

    async def _create_preference(self):
        resp = await self._post("/api/v1/student-teacher-preferences/", {
            "student_id": self.student_id, "primary_teacher_ids": [self.teacher_id],
        })
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        self.preference_id = resp.json()["data"]["id"]
        return True

    async def _create_slot(self):
        resp = await self._post("/api/v1/teacher-slots", {
            "teacher_id": self.teacher_id,
            "teacher_contract_id": self.teacher_contract_id,
            "slot_date": self.slot_date, "start_time": "10:00", "end_time": "12:00",
            "is_available": True,
        })
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        self.slot_id = resp.json()["data"]["id"]
        return True

    # ── Concurrency Tests ──

    def _booking_payload(self):
        return {
            "student_id": self.student_id,
            "teacher_id": self.teacher_id,
            "course_id": self.course_id,
            "student_contract_id": self.student_contract_id,
            "teacher_slot_id": self.slot_id,
            "booking_date": self.slot_date,
            "start_time": "10:00",
            "end_time": "11:00",
            "notes": TEST_PREFIX,
        }

    async def _create_booking(self):
        resp = await self._post("/api/v1/bookings", self._booking_payload())
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        self.booking_id = resp.json()["data"]["id"]
        return True

    async def _duplicate_booking(self):
        resp = await self._post("/api/v1/bookings", self._booking_payload())
        if resp.status_code == 409: return True
        return f"expected 409, got {resp.status_code}: {resp.text[:200]}"

    async def _delete_booking(self):
        resp = await self._delete(f"/api/v1/bookings/{self.booking_id}")
        if resp.status_code not in (200, 204): return f"{resp.status_code} {resp.text[:200]}"
        self.booking_id = None
        return True

    async def _rebook_after_delete(self):
        resp = await self._post("/api/v1/bookings", self._booking_payload())
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        self.booking_id = resp.json()["data"]["id"]
        return True

    # ── Cleanup ──

    async def _cleanup(self):
        for name, path in [
            ("booking", f"/api/v1/bookings/{self.booking_id}" if self.booking_id else None),
            ("slot", f"/api/v1/teacher-slots/{self.slot_id}" if self.slot_id else None),
            ("preference", f"/api/v1/student-teacher-preferences/{self.preference_id}" if self.preference_id else None),
            ("student_course", f"/api/v1/student-courses/{self.student_course_id}" if self.student_course_id else None),
            ("tc_detail", f"/api/v1/teacher-contracts/{self.teacher_contract_id}/details/{self.teacher_contract_detail_id}" if self.teacher_contract_id and self.teacher_contract_detail_id else None),
            ("teacher_contract", f"/api/v1/teacher-contracts/{self.teacher_contract_id}" if self.teacher_contract_id else None),
            ("student_contract", f"/api/v1/student-contracts/{self.student_contract_id}" if self.student_contract_id else None),
            ("teacher", f"/api/v1/teachers/{self.teacher_id}" if self.teacher_id else None),
            ("student", f"/api/v1/students/{self.student_id}" if self.student_id else None),
            ("course", f"/api/v1/courses/{self.course_id}" if self.course_id else None),
        ]:
            if not path: continue
            resp = await self._delete(path)
            s = "OK" if resp.status_code in (200, 204, 404) else f"WARN({resp.status_code})"
            print(f"    {name}: {s}")


async def main():
    parser = argparse.ArgumentParser(description="Booking Concurrency Test")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()
    ok = await ConcurrencyTester().run(args.email, args.password)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    asyncio.run(main())

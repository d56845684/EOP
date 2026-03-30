#!/usr/bin/env python3
"""
Live Booking Concurrency Test

驗證預約建立的交易安全性：
1. 建立預約成功
2. 同時段重複預約被拒絕（409 Conflict）
3. 刪除預約後可重新預約同時段

使用方式:
    python tests/live_booking_concurrency_test.py --email employee@eop-test.com --password TestPassword123!
"""

import httpx
import asyncio
import argparse
import sys
import os
from datetime import datetime, date, timedelta

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8001")
TEST_NOTES = "live_concurrency_test"


async def login(client: httpx.AsyncClient, email: str, password: str) -> bool:
    resp = await client.post(f"{BACKEND_URL}/api/v1/auth/login", json={
        "email": email, "password": password
    })
    return resp.status_code == 200


async def get_test_data(client: httpx.AsyncClient) -> dict:
    """取得測試所需的學生、教師、課程資料"""
    # 取得第一個學生
    resp = await client.get(f"{BACKEND_URL}/api/v1/students", params={"per_page": 1})
    students = resp.json().get("data", [])
    if not students:
        raise RuntimeError("No students found")

    # 取得第一個教師
    resp = await client.get(f"{BACKEND_URL}/api/v1/teachers", params={"per_page": 1})
    teachers = resp.json().get("data", [])
    if not teachers:
        raise RuntimeError("No teachers found")

    # 取得第一個課程
    resp = await client.get(f"{BACKEND_URL}/api/v1/courses", params={"per_page": 1})
    courses = resp.json().get("data", [])
    if not courses:
        raise RuntimeError("No courses found")

    return {
        "student_id": students[0]["id"],
        "teacher_id": teachers[0]["id"],
        "course_id": courses[0]["id"],
        "course_duration": courses[0].get("duration_minutes", 60),
    }


async def create_test_slot(client: httpx.AsyncClient, teacher_id: str, slot_date: str) -> str:
    """建立測試用教師時段"""
    resp = await client.post(f"{BACKEND_URL}/api/v1/teacher-slots", json={
        "teacher_id": teacher_id,
        "slot_date": slot_date,
        "start_time": "10:00",
        "end_time": "12:00",
        "is_available": True,
    })
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Create slot failed: {resp.status_code} {resp.text}")
    return resp.json()["data"]["id"]


async def delete_slot(client: httpx.AsyncClient, slot_id: str):
    await client.delete(f"{BACKEND_URL}/api/v1/teacher-slots/{slot_id}")


async def create_booking(client: httpx.AsyncClient, data: dict, slot_id: str) -> httpx.Response:
    return await client.post(f"{BACKEND_URL}/api/v1/bookings", json={
        "student_id": data["student_id"],
        "teacher_id": data["teacher_id"],
        "course_id": data["course_id"],
        "teacher_slot_id": slot_id,
        "booking_date": data["slot_date"],
        "start_time": "10:00",
        "end_time": "11:00",
        "notes": TEST_NOTES,
    })


async def delete_booking(client: httpx.AsyncClient, booking_id: str):
    await client.delete(f"{BACKEND_URL}/api/v1/bookings/{booking_id}")


async def run_tests(email: str, password: str):
    results = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Login
        ok = await login(client, email, password)
        if not ok:
            print("FAIL: Login failed")
            sys.exit(1)
        print("OK: Logged in")

        # Get test data
        data = await get_test_data(client)
        # Use a future date for the test slot
        test_date = (date.today() + timedelta(days=14)).isoformat()
        data["slot_date"] = test_date
        print(f"OK: Test data ready (student={data['student_id'][:8]}..., date={test_date})")

        slot_id = None
        booking1_id = None

        try:
            # Create test slot
            slot_id = await create_test_slot(client, data["teacher_id"], test_date)
            print(f"OK: Test slot created ({slot_id[:8]}...)")

            # TEST 1: Create booking — should succeed
            resp = await create_booking(client, data, slot_id)
            if resp.status_code == 200:
                booking1_id = resp.json()["data"]["id"]
                results.append(("Create booking", True))
                print(f"PASS: Test 1 — Create booking succeeded ({booking1_id[:8]}...)")
            else:
                results.append(("Create booking", False))
                print(f"FAIL: Test 1 — Create booking failed: {resp.status_code} {resp.text[:200]}")

            # TEST 2: Duplicate booking — should fail with 409
            resp2 = await create_booking(client, data, slot_id)
            if resp2.status_code == 409:
                results.append(("Duplicate booking rejected", True))
                print(f"PASS: Test 2 — Duplicate booking correctly rejected (409)")
            else:
                results.append(("Duplicate booking rejected", False))
                print(f"FAIL: Test 2 — Expected 409, got {resp2.status_code}: {resp2.text[:200]}")

            # TEST 3: Delete booking, then rebook same slot — should succeed
            if booking1_id:
                await delete_booking(client, booking1_id)
                booking1_id = None
                resp3 = await create_booking(client, data, slot_id)
                if resp3.status_code == 200:
                    booking1_id = resp3.json()["data"]["id"]
                    results.append(("Rebook after delete", True))
                    print(f"PASS: Test 3 — Rebook after delete succeeded")
                else:
                    results.append(("Rebook after delete", False))
                    print(f"FAIL: Test 3 — Rebook failed: {resp3.status_code} {resp3.text[:200]}")

        finally:
            # Cleanup
            if booking1_id:
                await delete_booking(client, booking1_id)
                print(f"  Cleaned up booking {booking1_id[:8]}...")
            if slot_id:
                await delete_slot(client, slot_id)
                print(f"  Cleaned up slot {slot_id[:8]}...")

    # Summary
    print("\n" + "=" * 50)
    passed = sum(1 for _, ok in results if ok)
    failed = sum(1 for _, ok in results if not ok)
    print(f"Results: {passed} passed, {failed} failed")
    for name, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'}: {name}")

    return failed == 0


def main():
    parser = argparse.ArgumentParser(description="Live Booking Concurrency Test")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    ok = asyncio.run(run_tests(args.email, args.password))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

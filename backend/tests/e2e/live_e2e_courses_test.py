#!/usr/bin/env python3
"""
End-to-End Courses + Student Enrollment Flow Test

課程 CRUD：建立 → 查詢 → 修改 → 驗證 → 重複建立拒絕
學生選課：建立選課 → 重複拒絕 → 查詢 → 刪除 → 重新選課
刪除課程 → 驗證

使用方式:
    python tests/live_e2e_courses_test.py \
        --email eopAdmin@example.com --password yourpassword
"""

import httpx
import asyncio
import argparse
import sys
import os
from datetime import datetime

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8001")
_TS = datetime.now().strftime("%H%M%S")
TEST_PREFIX = f"E2ECRS{_TS}_"


class CoursesEnrollmentTester:
    def __init__(self):
        self.url = BACKEND_URL.rstrip("/")
        self.results = []
        self.client = None

        self.course_id = None
        self.student_id = None
        self.enrollment_id = None

    async def _post(self, path, json_data=None):
        return await self.client.post(f"{self.url}{path}", json=json_data or {})

    async def _get(self, path, params=None):
        return await self.client.get(f"{self.url}{path}", params=params)

    async def _put(self, path, json_data=None):
        return await self.client.put(f"{self.url}{path}", json=json_data or {})

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
            print(f"  E2E Courses + Enrollment Flow Test")
            print(f"  Backend: {self.url}")
            print(f"{'=' * 60}")

            resp = await self._post("/api/v1/auth/login", {"email": email, "password": password})
            if resp.status_code != 200:
                print(f"\n  ✗ Login failed: {resp.status_code}")
                return False
            print(f"\n  ✓ Login")

            # Phase 1: 課程 CRUD
            print(f"\n  Phase 1: 課程 CRUD")
            print("  " + "-" * 40)
            await self._test("建立課程", self._create_course)
            await self._test("查詢課程列表（搜尋）", self._search_course)
            await self._test("取得單一課程", self._get_course)
            await self._test("修改課程（改名）", self._update_course)
            await self._test("驗證修改結果", self._verify_course_update)
            await self._test("重複建立同 code（應拒絕）", self._reject_duplicate)

            # Prereq: 建立學生
            print(f"\n  Prereq: 建立學生")
            print("  " + "-" * 40)
            await self._test("建立學生", self._create_student)

            # Phase 2: 學生選課
            print(f"\n  Phase 2: 學生選課")
            print("  " + "-" * 40)
            await self._test("新增選課", self._enroll)
            await self._test("重複選課（應拒絕）", self._reject_duplicate_enroll)
            await self._test("查詢學生選課列表", self._list_enrollments)
            await self._test("刪除選課", self._delete_enrollment)
            await self._test("刪除後重新選課（成功）", self._re_enroll)

            # Phase 3: 刪除
            print(f"\n  Phase 3: 刪除")
            print("  " + "-" * 40)
            await self._test("刪除選課", self._delete_enrollment_2)
            await self._test("刪除課程", self._delete_course)
            await self._test("驗證課程已刪除", self._verify_course_deleted)

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

    # ── Course CRUD ──

    async def _create_course(self):
        resp = await self._post("/api/v1/courses", {
            "course_code": f"{TEST_PREFIX}C01",
            "course_name": f"{TEST_PREFIX}英文課",
            "duration_minutes": 60,
        })
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        data = resp.json()["data"]
        self.course_id = data["id"]
        if data.get("course_name") != f"{TEST_PREFIX}英文課": return f"name mismatch"
        if data.get("duration_minutes") != 60: return f"duration={data.get('duration_minutes')}"
        return True

    async def _search_course(self):
        resp = await self._get("/api/v1/courses", {"search": TEST_PREFIX})
        if resp.status_code != 200: return f"{resp.status_code}"
        data = resp.json().get("data", [])
        if not any(d["id"] == self.course_id for d in data): return "搜尋找不到"
        return True

    async def _get_course(self):
        resp = await self._get(f"/api/v1/courses/{self.course_id}")
        if resp.status_code != 200: return f"{resp.status_code}"
        data = resp.json()["data"]
        if data.get("course_code") != f"{TEST_PREFIX}C01": return f"code mismatch"
        return True

    async def _update_course(self):
        resp = await self._put(f"/api/v1/courses/{self.course_id}", {
            "course_name": f"{TEST_PREFIX}英文課_updated",
        })
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        return True

    async def _verify_course_update(self):
        resp = await self._get(f"/api/v1/courses/{self.course_id}")
        if resp.status_code != 200: return f"{resp.status_code}"
        if resp.json()["data"].get("course_name") != f"{TEST_PREFIX}英文課_updated":
            return "name not updated"
        return True

    async def _reject_duplicate(self):
        resp = await self._post("/api/v1/courses", {
            "course_code": f"{TEST_PREFIX}C01",
            "course_name": "duplicate",
            "duration_minutes": 60,
        })
        if resp.status_code == 400: return True
        return f"expected 400, got {resp.status_code}"

    # ── Student ──

    async def _create_student(self):
        resp = await self._post("/api/v1/students", {
            "student_no": f"{TEST_PREFIX}S01", "name": f"{TEST_PREFIX}選課測試學生",
            "eng_name": f"{TEST_PREFIX}eng",
            "email": f"{TEST_PREFIX}s@example.com",
            "phone": "0900000000",
            "student_type": "formal",
        })
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        self.student_id = resp.json()["data"]["id"]
        return True

    # ── Enrollment ──

    async def _enroll(self):
        resp = await self._post("/api/v1/student-courses", {
            "student_id": self.student_id, "course_id": self.course_id,
        })
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        self.enrollment_id = resp.json()["data"]["id"]
        return True

    async def _reject_duplicate_enroll(self):
        resp = await self._post("/api/v1/student-courses", {
            "student_id": self.student_id, "course_id": self.course_id,
        })
        if resp.status_code == 400 or resp.status_code == 409: return True
        return f"expected 400/409, got {resp.status_code}"

    async def _list_enrollments(self):
        resp = await self._get("/api/v1/student-courses", {"student_id": self.student_id})
        if resp.status_code != 200: return f"{resp.status_code}"
        data = resp.json().get("data", [])
        if not any(d.get("id") == self.enrollment_id or d.get("course_id") == self.course_id for d in data):
            return "enrollment not found in list"
        return True

    async def _delete_enrollment(self):
        resp = await self._delete(f"/api/v1/student-courses/{self.enrollment_id}")
        if resp.status_code not in (200, 204): return f"{resp.status_code} {resp.text[:200]}"
        self.enrollment_id = None
        return True

    async def _re_enroll(self):
        resp = await self._post("/api/v1/student-courses", {
            "student_id": self.student_id, "course_id": self.course_id,
        })
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        self.enrollment_id = resp.json()["data"]["id"]
        return True

    async def _delete_enrollment_2(self):
        if not self.enrollment_id: return True
        resp = await self._delete(f"/api/v1/student-courses/{self.enrollment_id}")
        if resp.status_code not in (200, 204): return f"{resp.status_code} {resp.text[:200]}"
        self.enrollment_id = None
        return True

    # ── Delete course ──

    async def _delete_course(self):
        resp = await self._delete(f"/api/v1/courses/{self.course_id}")
        if resp.status_code not in (200, 204): return f"{resp.status_code} {resp.text[:200]}"
        self._deleted_course_id = self.course_id
        self.course_id = None
        return True

    async def _verify_course_deleted(self):
        resp = await self._get(f"/api/v1/courses/{self._deleted_course_id}")
        if resp.status_code == 404: return True
        if resp.status_code == 200:
            if resp.json().get("data", {}).get("is_deleted") is True: return True
        return f"expected 404, got {resp.status_code}"

    # ── Cleanup ──

    async def _cleanup(self):
        for name, path in [
            ("enrollment", f"/api/v1/student-courses/{self.enrollment_id}" if self.enrollment_id else None),
            ("student", f"/api/v1/students/{self.student_id}" if self.student_id else None),
            ("course", f"/api/v1/courses/{self.course_id}" if self.course_id else None),
        ]:
            if not path: continue
            resp = await self._delete(path)
            s = "OK" if resp.status_code in (200, 204, 404) else f"WARN({resp.status_code})"
            print(f"    {name}: {s}")


async def main():
    parser = argparse.ArgumentParser(description="E2E Courses + Enrollment Flow Test")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()
    ok = await CoursesEnrollmentTester().run(args.email, args.password)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    asyncio.run(main())

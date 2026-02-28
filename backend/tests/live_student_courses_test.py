#!/usr/bin/env python3
"""
Student Courses CRUD API 測試腳本

測試學生選課管理功能，包含：
1. 取得下拉選單選項 (Options)
2. 列出選課 (List)
3. 新增選課 (Create)
4. 取得某學生的選課 (By Student)
5. 刪除選課 (Delete / soft-delete)
6. soft-delete 後重新新增

使用方式:
    # 執行完整 CRUD 測試（需要 employee/admin 帳號）
    python tests/live_student_courses_test.py --email employee@example.com --password testpass

    # 自訂後端 URL
    python tests/live_student_courses_test.py --email admin@example.com --password testpass --backend-url http://localhost:8001
"""

import httpx
import asyncio
import argparse
import sys
import os
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8001")


def load_env():
    """載入 .env 檔案"""
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())


load_env()


@dataclass
class TestResult:
    name: str
    passed: bool
    message: str = ""
    duration_ms: float = 0


class StudentCoursesCRUDTester:
    def __init__(self, backend_url: str):
        self.backend_url = backend_url.rstrip("/")
        self.results: list[TestResult] = []
        self.cookies: dict = {}
        self.user_role: str = ""
        self.student_id: Optional[str] = None
        self.course_id: Optional[str] = None
        self.created_enrollment_ids: list[str] = []

    def _record_result(self, name: str, passed: bool, message: str = "", duration_ms: float = 0):
        self.results.append(TestResult(name, passed, message, duration_ms))
        status = "\u2705" if passed else "\u274c"
        duration_str = f" ({duration_ms:.0f}ms)" if duration_ms else ""
        print(f"  {status} {name}{duration_str}")
        if message and not passed:
            print(f"     \u2514\u2500 {message}")

    async def login(self, email: str, password: str) -> bool:
        print("\n" + "=" * 60)
        print("\U0001f510 登入")
        print("=" * 60 + "\n")

        async with httpx.AsyncClient(timeout=30.0) as client:
            start = datetime.now()
            resp = await client.post(
                f"{self.backend_url}/api/v1/auth/login",
                json={"email": email, "password": password}
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code == 200:
                self.cookies = dict(resp.cookies)
                data = resp.json()
                self.user_role = data.get("user", {}).get("role", "student")
                self._record_result(
                    f"登入成功 (角色: {self.user_role})",
                    True,
                    duration_ms=duration
                )
                return True
            else:
                self._record_result(
                    "登入",
                    False,
                    f"狀態碼: {resp.status_code}, 回應: {resp.text}",
                    duration_ms=duration
                )
                return False

    async def fetch_options(self) -> bool:
        print("\n" + "=" * 60)
        print("\U0001f4cb 取得下拉選單選項")
        print("=" * 60 + "\n")

        async with httpx.AsyncClient(timeout=30.0) as client:
            # 學生選項
            start = datetime.now()
            resp = await client.get(
                f"{self.backend_url}/api/v1/student-courses/options/students",
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code == 200:
                students = resp.json().get("data", [])
                if students:
                    self.student_id = students[0].get("id")
                    self._record_result(f"取得學生選項 (共 {len(students)} 筆)", True, duration_ms=duration)
                else:
                    self._record_result("取得學生選項", False, "沒有可用的學生資料")
                    return False
            else:
                self._record_result("取得學生選項", False, f"狀態碼: {resp.status_code}")
                return False

            # 課程選項
            start = datetime.now()
            resp = await client.get(
                f"{self.backend_url}/api/v1/student-courses/options/courses",
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code == 200:
                courses = resp.json().get("data", [])
                if courses:
                    self.course_id = courses[0].get("id")
                    self._record_result(f"取得課程選項 (共 {len(courses)} 筆)", True, duration_ms=duration)
                else:
                    self._record_result("取得課程選項", False, "沒有可用的課程資料")
                    return False
            else:
                self._record_result("取得課程選項", False, f"狀態碼: {resp.status_code}")
                return False

        return True

    async def test_list(self) -> bool:
        print("\n" + "=" * 60)
        print("\U0001f4cb 測試列出學生選課 (List)")
        print("=" * 60 + "\n")

        async with httpx.AsyncClient(timeout=30.0) as client:
            start = datetime.now()
            resp = await client.get(
                f"{self.backend_url}/api/v1/student-courses",
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code == 200:
                data = resp.json()
                total = data.get("total", 0)
                self._record_result(f"列出選課 (共 {total} 筆)", True, duration_ms=duration)
            else:
                self._record_result("列出選課", False, f"狀態碼: {resp.status_code}")
                return False

            # 測試依學生篩選
            if self.student_id:
                start = datetime.now()
                resp = await client.get(
                    f"{self.backend_url}/api/v1/student-courses",
                    params={"student_id": self.student_id},
                    cookies=self.cookies
                )
                duration = (datetime.now() - start).total_seconds() * 1000

                if resp.status_code == 200:
                    self._record_result("依學生篩選", True, duration_ms=duration)
                else:
                    self._record_result("依學生篩選", False, f"狀態碼: {resp.status_code}")

        return True

    async def test_create(self) -> Optional[str]:
        print("\n" + "=" * 60)
        print("\u2795 測試新增學生選課 (Create)")
        print("=" * 60 + "\n")

        if not self.student_id or not self.course_id:
            self._record_result("新增選課", False, "缺少學生或課程 ID")
            return None

        async with httpx.AsyncClient(timeout=30.0) as client:
            start = datetime.now()
            resp = await client.post(
                f"{self.backend_url}/api/v1/student-courses",
                json={
                    "student_id": self.student_id,
                    "course_id": self.course_id
                },
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code == 200:
                data = resp.json()
                enrollment = data.get("data", {})
                enrollment_id = enrollment.get("id")
                self.created_enrollment_ids.append(enrollment_id)
                self._record_result(
                    f"新增選課成功 (ID: {enrollment_id[:8]}...)",
                    True,
                    duration_ms=duration
                )
                print(f"     \u2514\u2500 學生: {enrollment.get('student_name')}")
                print(f"     \u2514\u2500 課程: {enrollment.get('course_code')} - {enrollment.get('course_name')}")
                return enrollment_id
            elif resp.status_code == 400 and "已選修" in resp.text:
                self._record_result("新增選課", True, "此學生已選修此課程（預期行為）", duration_ms=duration)
                return None
            else:
                self._record_result("新增選課", False, f"狀態碼: {resp.status_code}, 回應: {resp.text}", duration_ms=duration)
                return None

    async def test_duplicate_create(self) -> bool:
        print("\n" + "=" * 60)
        print("\U0001f504 測試重複新增")
        print("=" * 60 + "\n")

        async with httpx.AsyncClient(timeout=30.0) as client:
            start = datetime.now()
            resp = await client.post(
                f"{self.backend_url}/api/v1/student-courses",
                json={
                    "student_id": self.student_id,
                    "course_id": self.course_id
                },
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code == 400:
                self._record_result("重複新增返回 400", True, duration_ms=duration)
                return True
            else:
                self._record_result("重複新增檢查", False, f"預期 400，實際 {resp.status_code}", duration_ms=duration)
                return False

    async def test_get_by_student(self) -> bool:
        print("\n" + "=" * 60)
        print("\U0001f50d 測試取得某學生的選課 (By Student)")
        print("=" * 60 + "\n")

        if not self.student_id:
            self._record_result("取得學生選課", False, "缺少學生 ID")
            return False

        async with httpx.AsyncClient(timeout=30.0) as client:
            start = datetime.now()
            resp = await client.get(
                f"{self.backend_url}/api/v1/student-courses/by-student/{self.student_id}",
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code == 200:
                data = resp.json()
                courses = data.get("data", [])
                self._record_result(
                    f"取得學生選課 (共 {len(courses)} 筆)",
                    len(courses) >= 1,
                    duration_ms=duration
                )
                return True
            else:
                self._record_result("取得學生選課", False, f"狀態碼: {resp.status_code}")
                return False

    async def test_delete(self, enrollment_id: str) -> bool:
        print("\n" + "=" * 60)
        print("\U0001f5d1\ufe0f  測試刪除選課 (Delete)")
        print("=" * 60 + "\n")

        async with httpx.AsyncClient(timeout=30.0) as client:
            start = datetime.now()
            resp = await client.delete(
                f"{self.backend_url}/api/v1/student-courses/{enrollment_id}",
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code == 200:
                self._record_result("刪除選課成功", True, duration_ms=duration)
                return True
            else:
                self._record_result("刪除選課", False, f"狀態碼: {resp.status_code}", duration_ms=duration)
                return False

    async def test_re_add_after_delete(self) -> Optional[str]:
        """測試 soft-delete 後重新新增"""
        print("\n" + "=" * 60)
        print("\U0001f504 測試 soft-delete 後重新新增")
        print("=" * 60 + "\n")

        async with httpx.AsyncClient(timeout=30.0) as client:
            start = datetime.now()
            resp = await client.post(
                f"{self.backend_url}/api/v1/student-courses",
                json={
                    "student_id": self.student_id,
                    "course_id": self.course_id
                },
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code == 200:
                enrollment_id = resp.json().get("data", {}).get("id")
                self.created_enrollment_ids.append(enrollment_id)
                self._record_result("soft-delete 後重新新增成功", True, duration_ms=duration)
                return enrollment_id
            else:
                self._record_result(
                    "soft-delete 後重新新增",
                    False,
                    f"狀態碼: {resp.status_code}, 回應: {resp.text}",
                    duration_ms=duration
                )
                return None

    async def cleanup(self):
        if not self.created_enrollment_ids:
            return

        print("\n" + "=" * 60)
        print("\U0001f9f9 清理測試資料")
        print("=" * 60 + "\n")

        async with httpx.AsyncClient(timeout=30.0) as client:
            for eid in self.created_enrollment_ids:
                resp = await client.delete(
                    f"{self.backend_url}/api/v1/student-courses/{eid}",
                    cookies=self.cookies
                )
                if resp.status_code == 200:
                    print(f"  \u2705 已刪除: {eid[:8]}...")
                elif resp.status_code == 404:
                    print(f"  \u23ed\ufe0f  已刪除 (測試中刪除): {eid[:8]}...")
                else:
                    print(f"  \u274c 刪除失敗: {eid[:8]}...")

    def print_summary(self):
        print("\n" + "=" * 60)
        print("\U0001f4ca 測試摘要")
        print("=" * 60 + "\n")

        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        total = len(self.results)

        print(f"  總計: {total} 項測試")
        print(f"  通過: {passed} \u2705")
        print(f"  失敗: {failed} \u274c")
        print(f"  成功率: {passed/total*100:.1f}%" if total > 0 else "  成功率: N/A")
        print()

        if failed > 0:
            print("  失敗的測試:")
            for r in self.results:
                if not r.passed:
                    print(f"    - {r.name}: {r.message}")
            print()

        return failed == 0


async def main():
    parser = argparse.ArgumentParser(
        description="Student Courses CRUD API 測試腳本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--email", required=True, help="登入 Email")
    parser.add_argument("--password", required=True, help="登入密碼")
    parser.add_argument("--backend-url", default=BACKEND_URL, help=f"後端 URL (預設: {BACKEND_URL})")

    args = parser.parse_args()

    tester = StudentCoursesCRUDTester(args.backend_url)

    print("\n" + "\U0001f680" * 20)
    print("\n   Student Courses CRUD API 測試")
    print(f"   後端: {args.backend_url}")
    print("\n" + "\U0001f680" * 20)

    try:
        # 1. 登入
        if not await tester.login(args.email, args.password):
            tester.print_summary()
            sys.exit(1)

        # 2. 取得選項
        if not await tester.fetch_options():
            print("\n\u26a0\ufe0f  無法取得學生或課程選項，請確認資料庫有資料")
            tester.print_summary()
            sys.exit(1)

        # 檢查權限
        if tester.user_role not in ["admin", "employee"]:
            print(f"\n\u26a0\ufe0f  目前角色為 '{tester.user_role}'，無法執行 CRUD 測試")
            tester.print_summary()
            sys.exit(1)

        # 3. 測試列出
        await tester.test_list()

        # 4. 測試新增
        enrollment_id = await tester.test_create()

        if enrollment_id:
            # 5. 測試重複新增
            await tester.test_duplicate_create()

            # 6. 測試取得某學生的選課
            await tester.test_get_by_student()

            # 7. 測試刪除
            await tester.test_delete(enrollment_id)
            tester.created_enrollment_ids = [eid for eid in tester.created_enrollment_ids if eid != enrollment_id]

            # 8. 測試 soft-delete 後重新新增
            new_enrollment_id = await tester.test_re_add_after_delete()

        # 清理
        await tester.cleanup()

        # 摘要
        success = tester.print_summary()
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n\n\u26a0\ufe0f  測試中斷")
        await tester.cleanup()
        sys.exit(1)
    except Exception as e:
        print(f"\n\u274c 測試發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        await tester.cleanup()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

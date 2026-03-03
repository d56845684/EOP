#!/usr/bin/env python3
"""
Live Registration API Test Script

測試註冊 API 的角色專屬欄位功能，包含：
1. 學生註冊（含 birth_date, emergency_contact 等）
2. 教師註冊（含 bio 等）
3. 員工註冊（含 employee_type 等）
4. 欄位驗證（缺少必填欄位、無效角色等）
5. 註冊後驗證實體資料是否正確寫入

使用方式:
    # 執行所有角色測試
    python tests/live_register_test.py

    # 測試特定角色
    python tests/live_register_test.py --roles student teacher

    # 只清理測試資料
    python tests/live_register_test.py --cleanup-only

    # 執行測試但不清理
    python tests/live_register_test.py --no-cleanup
"""

import httpx
import asyncio
import argparse
import sys
import os
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field

# 設定 (使用 127.0.0.1 避免 IPv6 問題)
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8001")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:2f8b5e9731c472a52f3d3068dc97d0d8@127.0.0.1:5432/postgres")

# 測試用戶前綴
TEST_EMAIL_PREFIX = "test_reg_"
TEST_EMAIL_DOMAIN = "@example.com"
TEST_PASSWORD = "TestPassword123!"

# 支援的角色
SUPPORTED_ROLES = ["student", "teacher", "employee"]


@dataclass
class TestResult:
    name: str
    passed: bool
    role: str = ""
    message: str = ""
    duration_ms: float = 0


@dataclass
class TestContext:
    """測試上下文"""
    test_email: str = ""
    test_password: str = TEST_PASSWORD
    test_name: str = "Test User"
    test_role: str = "student"
    user_id: Optional[str] = None
    cookies: dict = field(default_factory=dict)


class LiveRegisterTester:
    def __init__(self, backend_url: str, database_url: str, roles: list[str]):
        self.backend_url = backend_url.rstrip("/")
        self.database_url = database_url
        self.roles = roles
        self.results: list[TestResult] = []
        self.created_user_ids: list[str] = []

        self.client_kwargs = {
            "follow_redirects": True,
            "timeout": httpx.Timeout(30.0, connect=10.0)
        }

    def _generate_email(self, role: str, suffix: str = "") -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        return f"{TEST_EMAIL_PREFIX}{role}{suffix}_{timestamp}{TEST_EMAIL_DOMAIN}"

    # ========== 各角色的註冊測試資料 ==========

    def _student_register_data(self, email: str) -> dict:
        return {
            "email": email,
            "password": TEST_PASSWORD,
            "name": "測試學生",
            "role": "student",
            "phone": "0912345678",
            "address": "台北市大安區測試路100號",
            "birth_date": "2005-06-15",
            "emergency_contact_name": "王大明",
            "emergency_contact_phone": "0987654321",
        }

    def _teacher_register_data(self, email: str) -> dict:
        return {
            "email": email,
            "password": TEST_PASSWORD,
            "name": "測試教師",
            "role": "teacher",
            "phone": "0922333444",
            "address": "台北市信義區教學路200號",
            "bio": "10年英語教學經驗，擅長互動式教學",
        }

    def _employee_register_data(self, email: str) -> dict:
        return {
            "email": email,
            "password": TEST_PASSWORD,
            "name": "測試員工",
            "role": "employee",
            "phone": "0933444555",
            "address": "台北市中山區辦公路300號",
            "employee_type": "intern",
        }

    # ========== 測試執行 ==========

    async def run_all_tests(self) -> bool:
        print(f"\n{'='*60}")
        print(f"🧪 Live Registration Tests (Multi-Role)")
        print(f"{'='*60}")
        print(f"Backend URL: {self.backend_url}")
        print(f"Roles to test: {', '.join(self.roles)}")
        print(f"{'='*60}\n")

        all_passed = True

        # Phase 1: 各角色註冊 + 欄位驗證
        for role in self.roles:
            role_passed = await self._run_role_tests(role)
            if not role_passed:
                all_passed = False

        # Phase 2: 通用驗證測試
        validation_passed = await self._run_validation_tests()
        if not validation_passed:
            all_passed = False

        self._print_final_summary()
        return all_passed

    async def _run_role_tests(self, role: str) -> bool:
        """執行特定角色的註冊 + 驗證測試"""
        print(f"\n{'─'*60}")
        print(f"👤 Testing Role: {role.upper()}")
        print(f"{'─'*60}")

        email = self._generate_email(role)
        print(f"Test Email: {email}\n")

        tests = [
            (f"[{role}] 註冊", lambda: self._test_register(role, email)),
            (f"[{role}] 登入驗證", lambda: self._test_login_after_register(role, email)),
            (f"[{role}] 角色驗證", lambda: self._test_verify_role(role)),
            (f"[{role}] 實體欄位驗證", lambda: self._test_verify_entity_fields(role)),
        ]

        role_results = []
        for name, test_fn in tests:
            result = await self._run_single_test(name, test_fn, role)
            role_results.append(result)
            self.results.append(result)

        passed = sum(1 for r in role_results if r.passed)
        failed = sum(1 for r in role_results if not r.passed)
        print(f"\n📋 Role '{role}': {passed} passed, {failed} failed")
        return failed == 0

    async def _run_validation_tests(self) -> bool:
        """執行通用驗證測試"""
        print(f"\n{'─'*60}")
        print(f"🔒 Validation Tests")
        print(f"{'─'*60}\n")

        tests = [
            ("員工缺少 employee_type", self._test_employee_missing_type),
            ("重複 Email 註冊", self._test_duplicate_email),
            ("無效密碼（太短）", self._test_weak_password),
            ("學生欄位不會寫入教師", self._test_cross_role_field_ignored),
        ]

        validation_results = []
        for name, test_fn in tests:
            result = await self._run_single_test(name, test_fn, "validation")
            validation_results.append(result)
            self.results.append(result)

        passed = sum(1 for r in validation_results if r.passed)
        failed = sum(1 for r in validation_results if not r.passed)
        print(f"\n📋 Validation: {passed} passed, {failed} failed")
        return failed == 0

    async def _run_single_test(self, name: str, test_fn, role: str) -> TestResult:
        print(f"  ▶ {name}...", end=" ", flush=True)
        start = datetime.now()

        try:
            await test_fn()
            duration = (datetime.now() - start).total_seconds() * 1000
            print(f"✅ ({duration:.0f}ms)")
            return TestResult(name, True, role, "OK", duration)
        except AssertionError as e:
            duration = (datetime.now() - start).total_seconds() * 1000
            print(f"❌ {e}")
            return TestResult(name, False, role, str(e), duration)
        except Exception as e:
            duration = (datetime.now() - start).total_seconds() * 1000
            print(f"❌ Error: {e}")
            return TestResult(name, False, role, f"Error: {e}", duration)

    # ========== 測試案例 ==========

    async def _test_register(self, role: str, email: str):
        """測試角色註冊"""
        if role == "student":
            register_data = self._student_register_data(email)
        elif role == "teacher":
            register_data = self._teacher_register_data(email)
        elif role == "employee":
            register_data = self._employee_register_data(email)
        else:
            raise ValueError(f"Unknown role: {role}")

        async with httpx.AsyncClient(**self.client_kwargs) as client:
            resp = await client.post(
                f"{self.backend_url}/api/v1/auth/register",
                json=register_data
            )

            data = resp.json()
            assert resp.status_code == 200, f"HTTP {resp.status_code}: {data}"
            assert data.get("success"), f"Registration failed: {data.get('message')}"

    async def _test_login_after_register(self, role: str, email: str):
        """註冊後登入取得 cookies 和 user_id"""
        async with httpx.AsyncClient(**self.client_kwargs) as client:
            resp = await client.post(
                f"{self.backend_url}/api/v1/auth/login",
                json={"email": email, "password": TEST_PASSWORD}
            )

            assert resp.status_code == 200, f"Login failed: {resp.text}"
            data = resp.json()
            assert data.get("success"), f"Login not successful: {data}"

            # 儲存 cookies 和 user_id 供後續測試使用
            self._current_cookies = dict(resp.cookies)
            self._current_user_id = data["user"]["id"]
            self._current_role = role
            self._current_email = email

            self.created_user_ids.append(self._current_user_id)

    async def _test_verify_role(self, role: str):
        """驗證用戶角色正確"""
        async with httpx.AsyncClient(cookies=self._current_cookies, **self.client_kwargs) as client:
            resp = await client.get(f"{self.backend_url}/api/v1/auth/me")

            assert resp.status_code == 200, f"Get me failed: {resp.text}"
            data = resp.json()
            user_role = data.get("data", {}).get("role")
            assert user_role == role, f"Expected role '{role}', got '{user_role}'"

    async def _test_verify_entity_fields(self, role: str):
        """驗證對應實體表中的額外欄位是否正確寫入（直連 DB）"""
        import asyncpg

        conn = await asyncpg.connect(self.database_url)
        try:
            # 取得 user_profile
            profile = await conn.fetchrow(
                "SELECT student_id, teacher_id, employee_id FROM user_profiles WHERE id = $1",
                self._current_user_id
            )
            assert profile, "user_profiles record not found"

            if role == "student":
                entity_id = profile["student_id"]
                assert entity_id, "student_id is null in user_profiles"

                student = await conn.fetchrow(
                    "SELECT * FROM students WHERE id = $1", entity_id
                )
                assert student, "Student record not found"

                assert student["name"] == "測試學生", f"name mismatch: {student['name']}"
                assert student["phone"] == "0912345678", f"phone mismatch: {student['phone']}"
                assert student["address"] == "台北市大安區測試路100號", f"address mismatch: {student['address']}"
                assert str(student["birth_date"]) == "2005-06-15", f"birth_date mismatch: {student['birth_date']}"
                assert student["emergency_contact_name"] == "王大明", f"emergency_contact_name mismatch: {student['emergency_contact_name']}"
                assert student["emergency_contact_phone"] == "0987654321", f"emergency_contact_phone mismatch: {student['emergency_contact_phone']}"

            elif role == "teacher":
                entity_id = profile["teacher_id"]
                assert entity_id, "teacher_id is null in user_profiles"

                teacher = await conn.fetchrow(
                    "SELECT * FROM teachers WHERE id = $1", entity_id
                )
                assert teacher, "Teacher record not found"

                assert teacher["name"] == "測試教師", f"name mismatch: {teacher['name']}"
                assert teacher["phone"] == "0922333444", f"phone mismatch: {teacher['phone']}"
                assert teacher["address"] == "台北市信義區教學路200號", f"address mismatch: {teacher['address']}"
                assert teacher["bio"] == "10年英語教學經驗，擅長互動式教學", f"bio mismatch: {teacher['bio']}"

            elif role == "employee":
                entity_id = profile["employee_id"]
                assert entity_id, "employee_id is null in user_profiles"

                employee = await conn.fetchrow(
                    "SELECT * FROM employees WHERE id = $1", entity_id
                )
                assert employee, "Employee record not found"

                assert employee["name"] == "測試員工", f"name mismatch: {employee['name']}"
                assert employee["phone"] == "0933444555", f"phone mismatch: {employee['phone']}"
                assert employee["address"] == "台北市中山區辦公路300號", f"address mismatch: {employee['address']}"
                assert employee["employee_type"] == "intern", f"employee_type mismatch: {employee['employee_type']}"
        finally:
            await conn.close()

    async def _test_employee_missing_type(self):
        """員工註冊缺少 employee_type 應回傳 422"""
        async with httpx.AsyncClient(**self.client_kwargs) as client:
            resp = await client.post(
                f"{self.backend_url}/api/v1/auth/register",
                json={
                    "email": self._generate_email("employee", "_noetype"),
                    "password": TEST_PASSWORD,
                    "name": "缺少類型的員工",
                    "role": "employee"
                    # 故意不傳 employee_type
                }
            )
            assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"

    async def _test_duplicate_email(self):
        """重複 Email 註冊應失敗"""
        # 使用第一個已建立的 user 的 email
        if not self.created_user_ids:
            raise Exception("No users created yet, skipping")

        import asyncpg

        # 查詢第一個 user 的 email
        conn = await asyncpg.connect(self.database_url)
        try:
            row = await conn.fetchrow(
                "SELECT email FROM public.users WHERE id = $1",
                self.created_user_ids[0]
            )
            assert row, f"User {self.created_user_ids[0]} not found in DB"
            existing_email = row["email"]
        finally:
            await conn.close()

        async with httpx.AsyncClient(**self.client_kwargs) as client:
            resp = await client.post(
                f"{self.backend_url}/api/v1/auth/register",
                json={
                    "email": existing_email,
                    "password": TEST_PASSWORD,
                    "name": "重複註冊",
                    "role": "student"
                }
            )

            data = resp.json()
            # 可能回 200 + success=false 或其他，只要不是 success=true 就對
            assert not data.get("success") or resp.status_code >= 400, \
                f"Duplicate email should fail, got: {data}"

    async def _test_weak_password(self):
        """太短的密碼應失敗"""
        async with httpx.AsyncClient(**self.client_kwargs) as client:
            resp = await client.post(
                f"{self.backend_url}/api/v1/auth/register",
                json={
                    "email": self._generate_email("student", "_weakpw"),
                    "password": "123",
                    "name": "弱密碼測試",
                    "role": "student"
                }
            )

            data = resp.json()
            if resp.status_code == 200:
                assert not data.get("success"), f"Weak password should fail, got: {data}"
            # 422 or other error codes are also acceptable

    async def _test_cross_role_field_ignored(self):
        """教師角色帶學生欄位（birth_date）應被忽略"""
        email = self._generate_email("teacher", "_crossfield")

        async with httpx.AsyncClient(**self.client_kwargs) as client:
            resp = await client.post(
                f"{self.backend_url}/api/v1/auth/register",
                json={
                    "email": email,
                    "password": TEST_PASSWORD,
                    "name": "跨角色欄位測試",
                    "role": "teacher",
                    "phone": "0955666777",
                    "birth_date": "1990-01-01",  # 學生欄位，教師不應有
                    "emergency_contact_name": "不應出現",  # 學生欄位
                }
            )

            data = resp.json()
            assert resp.status_code == 200 and data.get("success"), f"Register failed: {data}"

            # 登入取得 user_id
            resp = await client.post(
                f"{self.backend_url}/api/v1/auth/login",
                json={"email": email, "password": TEST_PASSWORD}
            )
            assert resp.status_code == 200, f"Login failed: {resp.text}"
            login_data = resp.json()
            user_id = login_data["user"]["id"]
            self.created_user_ids.append(user_id)

        # 查詢 teacher 實體，確認沒有 birth_date（直連 DB）
        import asyncpg

        conn = await asyncpg.connect(self.database_url)
        try:
            profile = await conn.fetchrow(
                "SELECT teacher_id FROM user_profiles WHERE id = $1", user_id
            )
            assert profile, "user_profiles record not found"
            teacher_id = profile["teacher_id"]
            assert teacher_id, "teacher_id is null in user_profiles"

            teacher = await conn.fetchrow(
                "SELECT * FROM teachers WHERE id = $1", teacher_id
            )
            assert teacher, "Teacher record not found"

            # teacher 表沒有 birth_date 欄位，phone 應該正確寫入
            assert teacher["phone"] == "0955666777", f"phone should be set: {teacher['phone']}"
        finally:
            await conn.close()

    # ========== 摘要與清理 ==========

    def _print_final_summary(self):
        print(f"\n{'='*60}")
        print("📊 Final Test Summary")
        print(f"{'='*60}")

        # 按 role 分組
        role_groups = {}
        for r in self.results:
            role_groups.setdefault(r.role, []).append(r)

        for role, role_results in role_groups.items():
            passed = sum(1 for r in role_results if r.passed)
            failed = sum(1 for r in role_results if not r.passed)
            status = "✅" if failed == 0 else "❌"
            label = role.upper() if role != "validation" else "VALIDATION"
            print(f"\n  {status} {label}: {passed} passed, {failed} failed")

            for r in role_results:
                s = "✅" if r.passed else "❌"
                print(f"      {s} {r.name}: {r.message} ({r.duration_ms:.0f}ms)")

        total_passed = sum(1 for r in self.results if r.passed)
        total_failed = sum(1 for r in self.results if not r.passed)
        total_time = sum(r.duration_ms for r in self.results)

        print(f"\n{'='*60}")
        print(f"Total: {total_passed} passed, {total_failed} failed ({total_time:.0f}ms)")
        print(f"{'='*60}\n")

    async def cleanup_test_data(self):
        """清理所有測試資料（直連 PostgreSQL）"""
        try:
            import asyncpg
        except ImportError:
            print("\n⚠️  asyncpg not installed, skipping cleanup.")
            return

        print(f"\n{'='*60}")
        print("🧹 Cleaning up test data...")
        print(f"{'='*60}\n")

        try:
            conn = await asyncpg.connect(self.database_url)
        except Exception as e:
            print(f"  ❌ Failed to connect to database: {e}")
            return

        try:
            test_users = await conn.fetch(
                "SELECT id, email FROM public.users WHERE email LIKE $1",
                f"{TEST_EMAIL_PREFIX}%"
            )

            if not test_users:
                print("  No test users found")
                return

            print(f"  Found {len(test_users)} test user(s)")

            for user in test_users:
                user_id = user["id"]
                email = user["email"]
                print(f"  Deleting {email} ({str(user_id)[:8]}...)...")

                profile = await conn.fetchrow(
                    "SELECT student_id, teacher_id, employee_id FROM user_profiles WHERE id = $1",
                    user_id
                )

                await conn.execute("DELETE FROM public.users WHERE id = $1", user_id)

                if profile:
                    if profile["student_id"]:
                        await conn.execute("DELETE FROM students WHERE id = $1", profile["student_id"])
                    if profile["teacher_id"]:
                        await conn.execute("DELETE FROM teachers WHERE id = $1", profile["teacher_id"])
                    if profile["employee_id"]:
                        await conn.execute("DELETE FROM employees WHERE id = $1", profile["employee_id"])

                print(f"    ✅ Deleted")

        except Exception as e:
            print(f"  ❌ Cleanup error: {e}")
        finally:
            await conn.close()

        print("\n✅ Cleanup completed\n")


async def main():
    parser = argparse.ArgumentParser(
        description="Live Registration API Test Script (Multi-Role)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  # 執行所有角色測試
  python tests/live_register_test.py

  # 只測試學生和教師
  python tests/live_register_test.py --roles student teacher

  # 只清理測試資料
  python tests/live_register_test.py --cleanup-only
        """
    )
    parser.add_argument(
        "--roles",
        nargs="+",
        default=SUPPORTED_ROLES,
        choices=SUPPORTED_ROLES,
        help=f"Roles to test (default: {' '.join(SUPPORTED_ROLES)})"
    )
    parser.add_argument(
        "--cleanup-only",
        action="store_true",
        help="Only cleanup test data without running tests"
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Run tests without cleanup"
    )
    parser.add_argument(
        "--backend-url",
        default=BACKEND_URL,
        help=f"Backend URL (default: {BACKEND_URL})"
    )

    args = parser.parse_args()

    tester = LiveRegisterTester(
        backend_url=args.backend_url,
        database_url=DATABASE_URL,
        roles=args.roles
    )

    if args.cleanup_only:
        await tester.cleanup_test_data()
        return

    success = await tester.run_all_tests()

    if not args.no_cleanup:
        await tester.cleanup_test_data()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
Live Authentication Test Script

測試真實運行中的認證服務，支援多角色測試及清理測試資料。

使用方式:
    # 執行所有角色測試
    python tests/live_auth_test.py

    # 測試特定角色
    python tests/live_auth_test.py --roles student teacher

    # 只清理測試資料
    python tests/live_auth_test.py --cleanup-only

    # 執行測試但不清理
    python tests/live_auth_test.py --no-cleanup
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

# 測試用戶前綴（方便識別和清理）
TEST_EMAIL_PREFIX = "test_auth_"
TEST_EMAIL_DOMAIN = "@example.com"

# 支援的角色列表
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
    """測試上下文，儲存測試過程中的資料"""
    test_email: str = ""
    test_password: str = "TestPassword123!"
    test_name: str = "Test User"
    test_role: str = "student"
    user_id: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    session_id: Optional[str] = None
    cookies: dict = field(default_factory=dict)


@dataclass
class CreatedAccount:
    """記錄創建的帳號資訊"""
    role: str
    email: str
    password: str
    user_id: Optional[str] = None


class LiveAuthTester:
    def __init__(self, backend_url: str, database_url: str, roles: list[str]):
        self.backend_url = backend_url.rstrip("/")
        self.database_url = database_url
        self.roles = roles
        self.results: list[TestResult] = []
        self.created_user_ids: list[str] = []
        self.created_accounts: list[CreatedAccount] = []

        # httpx client config
        self.client_kwargs = {
            "follow_redirects": True,
            "timeout": httpx.Timeout(30.0, connect=10.0)
        }

    def _create_context(self, role: str) -> TestContext:
        """為特定角色建立測試上下文"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        return TestContext(
            test_email=f"{TEST_EMAIL_PREFIX}{role}_{timestamp}{TEST_EMAIL_DOMAIN}",
            test_name=f"Test {role.capitalize()}",
            test_role=role
        )

    async def run_all_tests(self) -> bool:
        """執行所有角色的測試"""
        print(f"\n{'='*60}")
        print(f"🧪 Live Authentication Tests (Multi-Role)")
        print(f"{'='*60}")
        print(f"Backend URL: {self.backend_url}")
        print(f"Roles to test: {', '.join(self.roles)}")
        print(f"{'='*60}\n")

        all_passed = True

        for role in self.roles:
            role_passed = await self._run_role_tests(role)
            if not role_passed:
                all_passed = False

        self._print_final_summary()
        return all_passed

    async def _run_role_tests(self, role: str) -> bool:
        """執行特定角色的所有測試"""
        print(f"\n{'─'*60}")
        print(f"👤 Testing Role: {role.upper()}")
        print(f"{'─'*60}")

        ctx = self._create_context(role)
        print(f"Test Email: {ctx.test_email}\n")

        # 公開註冊已關閉，所有角色透過 DB 建帳 + 驗證 API 被擋
        tests = [
            ("Health Check", self._test_health_check),
            ("Public Register Blocked", self._test_register_blocked),
            ("DB Account Setup", self._test_db_setup),
            ("User Login", self._test_login),
            ("Get Current User", self._test_get_me),
            ("Verify Role", self._test_verify_role),
            ("Get Sessions", self._test_get_sessions),
            ("Token Refresh", self._test_refresh_token),
            ("Logout", self._test_logout),
            ("Access After Logout", self._test_access_after_logout),
        ]

        role_results = []
        for name, test_fn in tests:
            result = await self._run_single_test(name, test_fn, ctx, role)
            role_results.append(result)
            self.results.append(result)

        # 記錄建立的用戶 ID 和帳號資訊
        if ctx.user_id:
            self.created_user_ids.append(ctx.user_id)
            self.created_accounts.append(CreatedAccount(
                role=ctx.test_role,
                email=ctx.test_email,
                password=ctx.test_password,
                user_id=ctx.user_id
            ))

        passed = sum(1 for r in role_results if r.passed)
        failed = sum(1 for r in role_results if not r.passed)
        print(f"\n📋 Role '{role}': {passed} passed, {failed} failed")

        return failed == 0

    async def _run_single_test(self, name: str, test_fn, ctx: TestContext, role: str) -> TestResult:
        """執行單個測試"""
        print(f"  ▶ {name}...", end=" ", flush=True)
        start = datetime.now()

        try:
            await test_fn(ctx)
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

    def _print_final_summary(self):
        """列印最終測試摘要"""
        print(f"\n{'='*60}")
        print("📊 Final Test Summary")
        print(f"{'='*60}")

        # 按角色分組
        for role in self.roles:
            role_results = [r for r in self.results if r.role == role]
            passed = sum(1 for r in role_results if r.passed)
            failed = sum(1 for r in role_results if not r.passed)
            status = "✅" if failed == 0 else "❌"
            print(f"\n  {status} {role.upper()}: {passed} passed, {failed} failed")

            for r in role_results:
                status = "✅" if r.passed else "❌"
                print(f"      {status} {r.name}: {r.message} ({r.duration_ms:.0f}ms)")

        total_passed = sum(1 for r in self.results if r.passed)
        total_failed = sum(1 for r in self.results if not r.passed)
        total_time = sum(r.duration_ms for r in self.results)

        print(f"\n{'='*60}")
        print(f"Total: {total_passed} passed, {total_failed} failed ({total_time:.0f}ms)")
        print(f"{'='*60}\n")

    # ========== 測試案例 ==========

    async def _test_health_check(self, ctx: TestContext):
        """測試健康檢查端點"""
        async with httpx.AsyncClient(**self.client_kwargs) as client:
            resp = await client.get(f"{self.backend_url}/api/v1/health")
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    async def _test_register_blocked(self, ctx: TestContext):
        """驗證公開註冊 API 已關閉（所有角色都應走 invite 流程）"""
        async with httpx.AsyncClient(**self.client_kwargs) as client:
            resp = await client.post(
                f"{self.backend_url}/api/v1/auth/register",
                json={
                    "email": ctx.test_email,
                    "password": ctx.test_password,
                    "name": ctx.test_name,
                    "role": ctx.test_role,
                }
            )
            # endpoint 已移除，應回 404 或 405
            assert resp.status_code in (404, 405, 422), (
                f"Expected register to be disabled, got {resp.status_code}"
            )

    async def _test_db_setup(self, ctx: TestContext):
        """直接透過 DB 建立帳號（模擬 invite 流程 / 管理員操作）"""
        try:
            import asyncpg
            import bcrypt as _bcrypt
            import json
        except ImportError:
            raise AssertionError("asyncpg or bcrypt not installed")

        conn = await asyncpg.connect(self.database_url)
        try:
            # 1. 建立 public.users
            hashed_pw = _bcrypt.hashpw(
                ctx.test_password.encode("utf-8"),
                _bcrypt.gensalt(rounds=10),
            ).decode("utf-8")
            meta = json.dumps({"name": ctx.test_name, "role": ctx.test_role})
            row = await conn.fetchrow(
                """
                INSERT INTO public.users (email, encrypted_password, email_confirmed_at, raw_user_meta_data)
                VALUES ($1, $2, NOW(), $3::jsonb)
                RETURNING id
                """,
                ctx.test_email, hashed_pw, meta,
            )
            assert row, "Failed to insert user"
            user_id = row["id"]

            # 2. 建立角色實體 + user_profiles（編號格式同 trigger）
            uid_prefix = str(user_id).replace("-", "").upper()[:8]

            if ctx.test_role == "student":
                student_no = "S" + uid_prefix
                entity_row = await conn.fetchrow(
                    "INSERT INTO students (student_no, name, email, is_active) VALUES ($1, $2, $3, true) RETURNING id",
                    student_no, ctx.test_name, ctx.test_email,
                )
                assert entity_row, "Failed to insert student"
                await conn.execute(
                    "INSERT INTO user_profiles (id, role, student_id) VALUES ($1, 'student', $2)",
                    user_id, entity_row["id"],
                )

            elif ctx.test_role == "teacher":
                teacher_no = "T" + uid_prefix
                entity_row = await conn.fetchrow(
                    "INSERT INTO teachers (teacher_no, name, email, is_active) VALUES ($1, $2, $3, true) RETURNING id",
                    teacher_no, ctx.test_name, ctx.test_email,
                )
                assert entity_row, "Failed to insert teacher"
                await conn.execute(
                    "INSERT INTO user_profiles (id, role, teacher_id) VALUES ($1, 'teacher', $2)",
                    user_id, entity_row["id"],
                )

            elif ctx.test_role == "employee":
                employee_no = "E" + str(user_id).replace("-", "").upper()[:8]
                entity_row = await conn.fetchrow(
                    """
                    INSERT INTO employees (employee_no, name, email, employee_type, hire_date, is_active)
                    VALUES ($1, $2, $3, 'intern', CURRENT_DATE, true)
                    RETURNING id
                    """,
                    employee_no, ctx.test_name, ctx.test_email,
                )
                assert entity_row, "Failed to insert employee"
                await conn.execute(
                    "INSERT INTO user_profiles (id, role, employee_id, employee_subtype) VALUES ($1, 'employee', $2, 'intern')",
                    user_id, entity_row["id"],
                )

            ctx.user_id = str(user_id)
        finally:
            await conn.close()

    async def _test_login(self, ctx: TestContext):
        """測試用戶登入"""
        async with httpx.AsyncClient(**self.client_kwargs) as client:
            resp = await client.post(
                f"{self.backend_url}/api/v1/auth/login",
                json={
                    "email": ctx.test_email,
                    "password": ctx.test_password
                }
            )

            assert resp.status_code == 200, f"Login failed: {resp.text}"
            data = resp.json()
            assert data.get("success"), f"Login not successful: {data}"

            ctx.cookies = dict(resp.cookies)

            if "tokens" in data:
                ctx.access_token = data["tokens"].get("access_token")
                ctx.refresh_token = data["tokens"].get("refresh_token")

            if "user" in data:
                ctx.user_id = data["user"].get("id")

    async def _test_get_me(self, ctx: TestContext):
        """測試取得當前用戶資訊"""
        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.get(f"{self.backend_url}/api/v1/auth/me")

            assert resp.status_code == 200, f"Get me failed: {resp.text}"
            data = resp.json()
            assert data.get("success"), f"Get me not successful: {data}"
            assert data.get("data", {}).get("email") == ctx.test_email

    async def _test_verify_role(self, ctx: TestContext):
        """驗證用戶角色正確"""
        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.get(f"{self.backend_url}/api/v1/auth/me")

            assert resp.status_code == 200, f"Get me failed: {resp.text}"
            data = resp.json()
            user_role = data.get("data", {}).get("role")
            assert user_role == ctx.test_role, f"Expected role '{ctx.test_role}', got '{user_role}'"

    async def _test_get_sessions(self, ctx: TestContext):
        """測試取得用戶 Sessions"""
        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.get(f"{self.backend_url}/api/v1/auth/sessions")

            assert resp.status_code == 200, f"Get sessions failed: {resp.text}"
            data = resp.json()
            assert data.get("total", 0) >= 1 or len(data.get("sessions", [])) >= 1, "Should have at least 1 session"

    async def _test_refresh_token(self, ctx: TestContext):
        """測試刷新 Token"""
        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.post(f"{self.backend_url}/api/v1/auth/refresh")

            assert resp.status_code == 200, f"Refresh failed: {resp.text}"
            data = resp.json()
            assert data.get("success"), f"Refresh not successful: {data}"

            ctx.cookies.update(dict(resp.cookies))

    async def _test_logout(self, ctx: TestContext):
        """測試登出"""
        async with httpx.AsyncClient(cookies=ctx.cookies, **self.client_kwargs) as client:
            resp = await client.post(
                f"{self.backend_url}/api/v1/auth/logout",
                json={"logout_all_devices": False}
            )

            assert resp.status_code == 200, f"Logout failed: {resp.text}"
            data = resp.json()
            assert data.get("success"), f"Logout not successful: {data}"

    async def _test_access_after_logout(self, ctx: TestContext):
        """測試登出後存取（應該失敗）"""
        async with httpx.AsyncClient(**self.client_kwargs) as client:
            resp = await client.get(f"{self.backend_url}/api/v1/auth/me")
            assert resp.status_code == 401, f"Expected 401 after logout, got {resp.status_code}"

    def print_created_accounts(self):
        """輸出創建的帳號資訊"""
        if not self.created_accounts:
            return

        print(f"\n{'='*60}")
        print("📝 Created Test Accounts (not cleaned up)")
        print(f"{'='*60}\n")

        for acc in self.created_accounts:
            print(f"  [{acc.role.upper()}]")
            print(f"    Email:    {acc.email}")
            print(f"    Password: {acc.password}")
            if acc.user_id:
                print(f"    User ID:  {acc.user_id}")
            print()

        print(f"{'='*60}")
        print("⚠️  These accounts were NOT cleaned up.")
        print("    Run with --cleanup-only to remove them later.")
        print(f"{'='*60}\n")

    # ========== 清理功能 (直連 DB) ==========

    async def cleanup_test_data(self):
        """清理所有測試資料（直連 PostgreSQL）"""
        try:
            import asyncpg
        except ImportError:
            print("\n⚠️  asyncpg not installed, skipping cleanup.")
            print("    Install with: pip install asyncpg")
            print("    Or run: --no-cleanup\n")
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
            # 查找所有測試用戶
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

                # 1. 查詢 user_profiles 取得關聯的 entity ID
                profile = await conn.fetchrow(
                    "SELECT student_id, teacher_id, employee_id FROM user_profiles WHERE id = $1",
                    user_id
                )

                # 2. 刪除 users (CASCADE 自動刪除 user_profiles, line_user_bindings, line_notification_logs)
                await conn.execute("DELETE FROM public.users WHERE id = $1", user_id)

                # 3. 刪除關聯的實體記錄（不在 CASCADE 範圍內）
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
    parser = argparse.ArgumentParser(description="Live Authentication Test Script (Multi-Role)")
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

    tester = LiveAuthTester(
        backend_url=args.backend_url,
        database_url=DATABASE_URL,
        roles=args.roles
    )

    if args.cleanup_only:
        await tester.cleanup_test_data()
        return

    success = await tester.run_all_tests()

    if args.no_cleanup:
        tester.print_created_accounts()
    else:
        await tester.cleanup_test_data()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

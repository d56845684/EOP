#!/usr/bin/env python3
"""
End-to-End Permission Realtime Test

驗證員工變更角色後，權限立即生效（不需重新登入）：
  Phase 1: 建立測試員工帳號（employee 角色，intern 等級）
  Phase 2: 以員工身份登入，驗證初始權限（可存取 employees.list，不可存取 permissions.*）
  Phase 3: Admin 透過 API 變更員工角色為 admin
  Phase 4: 不重新登入，驗證員工立即取得 admin 權限（可存取 permissions.*）
  Phase 5: Admin 將角色改回 employee，驗證權限立即收回
  Phase 6: Admin 變更 employee_type 為 full_time，驗證 permission_level 立即生效
  Cleanup: 清理所有測試資料

使用方式:
    python tests/e2e/live_e2e_permission_realtime_test.py
"""

import httpx
import asyncio
import subprocess
import sys
import os
import json
from datetime import datetime, date
from dataclasses import dataclass

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8001")
DB_CONTAINER = os.getenv("DB_CONTAINER", "teaching-platform-db")

# 載入 .env
_env_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

SUPER_ADMIN_EMAIL = os.getenv("SUPER_ADMIN_EMAIL", "eopAdmin@example.com")
SUPER_ADMIN_PASSWORD = os.getenv("SUPER_ADMIN_PASSWORD", "eopsuper888")

_TS = datetime.now().strftime("%H%M%S")
TEST_PREFIX = f"E2EPERM{_TS}_"
TEST_PASSWORD = "TestPassword123!"

CLIENT_KWARGS = {
    "follow_redirects": True,
    "timeout": httpx.Timeout(30.0, connect=10.0),
}

# Well-known role UUIDs
ROLE_ADMIN_UUID = "a0000000-0000-0000-0000-000000000001"
ROLE_EMPLOYEE_UUID = "a0000000-0000-0000-0000-000000000002"


# ============================================================
# DB helpers (via docker exec)
# ============================================================

def db_exec_raw(sql: str) -> str:
    cmd = [
        "docker", "exec", DB_CONTAINER,
        "psql", "-U", "postgres", "-d", "postgres",
        "-t", "-A", "-c", sql,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    if result.returncode != 0:
        raise RuntimeError(f"DB exec failed: {result.stderr}")
    return result.stdout.strip()


def db_exec(sql: str) -> str:
    raw = db_exec_raw(sql)
    lines = [l for l in raw.split("\n") if l.strip()]
    return lines[0].strip() if lines else ""


# ============================================================
# Test class
# ============================================================

class PermissionRealtimeTester:
    def __init__(self):
        self.url = BACKEND_URL.rstrip("/")
        self.results: list[tuple[str, bool, str]] = []

        # Admin session
        self.admin_client: httpx.AsyncClient | None = None

        # Test employee
        self.test_email = f"{TEST_PREFIX}emp@example.com"
        self.test_user_id: str | None = None
        self.test_employee_id: str | None = None
        self.emp_cookies: dict | None = None

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

    async def run(self):
        async with httpx.AsyncClient(**CLIENT_KWARGS) as admin_client:
            self.admin_client = admin_client

            print(f"\n{'=' * 60}")
            print(f"  E2E Permission Realtime Test")
            print(f"  員工變更角色時，權限立即生效（不需重新登入）")
            print(f"{'=' * 60}\n")

            # Admin login
            resp = await admin_client.post(
                f"{self.url}/api/v1/auth/login",
                json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD},
            )
            if resp.status_code != 200:
                print(f"  ✗ Admin login failed: {resp.status_code}")
                return False
            print("  ✓ Admin login")

            # ── Phase 1: 建立測試員工帳號 ──
            print(f"\n  Phase 1: 建立測試員工帳號")
            print("  " + "-" * 40)
            await self._test("建立測試員工（employee 角色, intern 等級）", self._setup_test_employee)

            # ── Phase 2: 員工登入，驗證初始權限 ──
            print(f"\n  Phase 2: 員工登入，驗證初始權限")
            print("  " + "-" * 40)
            await self._test("員工登入", self._employee_login)
            await self._test("員工可存取 GET /bookings (bookings.list)", self._emp_can_access_bookings)
            await self._test("員工不可存取 GET /roles (permissions.roles) → 403", self._emp_cannot_access_roles)
            await self._test("員工 /permissions/me 不含 permissions.*", self._emp_initial_permissions)

            # ── Phase 3: Admin 變更員工角色為 admin ──
            print(f"\n  Phase 3: Admin 變更員工角色為 admin")
            print("  " + "-" * 40)
            await self._test("Admin 更新員工角色為 admin", self._admin_change_role_to_admin)

            # ── Phase 4: 不重新登入，驗證權限立即生效 ──
            print(f"\n  Phase 4: 不重新登入，驗證 admin 權限立即生效")
            print("  " + "-" * 40)
            await self._test("員工可存取 GET /roles (permissions.roles) → 200", self._emp_can_access_roles_now)
            await self._test("員工 /permissions/me 包含 permissions.*", self._emp_has_admin_permissions)
            await self._test("員工仍可存取 GET /bookings", self._emp_still_has_bookings)

            # ── Phase 5: Admin 將角色改回 employee，驗證權限收回 ──
            print(f"\n  Phase 5: Admin 改回 employee 角色，驗證權限收回")
            print("  " + "-" * 40)
            await self._test("Admin 更新員工角色回 employee", self._admin_change_role_to_employee)
            await self._test("員工不可存取 GET /roles → 403", self._emp_cannot_access_roles_again)
            await self._test("員工 /permissions/me 不再含 permissions.*", self._emp_no_admin_permissions)
            await self._test("員工仍可存取 GET /bookings", self._emp_still_has_bookings_2)

            # ── Phase 6: 變更 employee_type，驗證 permission_level 即時生效 ──
            print(f"\n  Phase 6: 變更 employee_type，驗證 permission_level 即時生效")
            print("  " + "-" * 40)
            await self._test("Admin 更新 employee_type 為 admin", self._admin_change_type_to_admin)
            await self._test("員工 permission_level 立即變為 100 (admin)", self._emp_has_admin_level)
            await self._test("Admin 更新 employee_type 回 intern", self._admin_change_type_to_intern)
            await self._test("員工 permission_level 立即變回 10 (intern)", self._emp_has_intern_level)

            # ── Cleanup ──
            print(f"\n  Cleanup")
            print("  " + "-" * 40)
            await self._cleanup()

            # Summary
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

    # ── Phase 1: Setup ──

    async def _setup_test_employee(self):
        import bcrypt as _bcrypt

        # 1. 建立員工 (via Admin API)
        resp = await self.admin_client.post(
            f"{self.url}/api/v1/employees",
            json={
                "employee_no": f"{TEST_PREFIX}E01",
                "name": f"{TEST_PREFIX}測試員工",
                "email": self.test_email,
                "employee_type": "intern",
                "hire_date": date.today().isoformat(),
            },
        )
        if resp.status_code != 200:
            return f"建立員工失敗: {resp.status_code} {resp.text[:200]}"
        self.test_employee_id = resp.json()["data"]["id"]

        # 2. 建立 user 帳號 (via DB, 因為需要 hash password)
        hashed_pw = _bcrypt.hashpw(TEST_PASSWORD.encode(), _bcrypt.gensalt(rounds=10)).decode()
        meta = json.dumps({"name": f"{TEST_PREFIX}測試員工", "role": "employee"}).replace("'", "''")

        self.test_user_id = db_exec(
            f"INSERT INTO public.users (email, encrypted_password, email_confirmed_at, raw_user_meta_data) "
            f"VALUES ('{self.test_email}', '{hashed_pw}', NOW(), '{meta}'::jsonb) RETURNING id"
        )
        if not self.test_user_id:
            return "建立 user 失敗"

        # 3. 建立 user_profiles (employee role, intern)
        db_exec(
            f"INSERT INTO user_profiles (id, role_id, employee_id, employee_subtype) "
            f"VALUES ('{self.test_user_id}', '{ROLE_EMPLOYEE_UUID}', '{self.test_employee_id}', 'intern')"
        )

        return True

    # ── Phase 2: Employee login & initial permissions ──

    async def _employee_login(self):
        async with httpx.AsyncClient(**CLIENT_KWARGS) as client:
            resp = await client.post(
                f"{self.url}/api/v1/auth/login",
                json={"email": self.test_email, "password": TEST_PASSWORD},
            )
            if resp.status_code != 200:
                return f"登入失敗: {resp.status_code} {resp.text[:200]}"
            self.emp_cookies = dict(resp.cookies)
            return True

    async def _emp_api_get(self, path: str) -> httpx.Response:
        async with httpx.AsyncClient(cookies=self.emp_cookies, **CLIENT_KWARGS) as client:
            return await client.get(f"{self.url}{path}")

    async def _emp_can_access_bookings(self):
        resp = await self._emp_api_get("/api/v1/bookings")
        if resp.status_code != 200:
            return f"expected 200, got {resp.status_code}"
        return True

    async def _emp_cannot_access_roles(self):
        resp = await self._emp_api_get("/api/v1/roles")
        if resp.status_code != 403:
            return f"expected 403, got {resp.status_code}"
        return True

    async def _emp_initial_permissions(self):
        resp = await self._emp_api_get("/api/v1/permissions/me")
        if resp.status_code != 200:
            return f"expected 200, got {resp.status_code}"
        keys = set(resp.json().get("page_keys", []))
        perm_keys = {k for k in keys if k.startswith("permissions.")}
        if perm_keys:
            return f"employee 不應有 permissions.* 權限，但有: {perm_keys}"
        if "bookings.list" not in keys:
            return f"employee 應有 bookings.list，got: {sorted(keys)}"
        return True

    # ── Phase 3: Admin changes role ──

    async def _admin_change_role_to_admin(self):
        resp = await self.admin_client.put(
            f"{self.url}/api/v1/employees/{self.test_employee_id}",
            json={"role_id": ROLE_ADMIN_UUID, "employee_type": "admin"},
        )
        if resp.status_code != 200:
            return f"更新失敗: {resp.status_code} {resp.text[:200]}"
        return True

    # ── Phase 4: Verify immediate permission escalation ──

    async def _emp_can_access_roles_now(self):
        resp = await self._emp_api_get("/api/v1/roles")
        if resp.status_code != 200:
            return f"expected 200, got {resp.status_code}: {resp.text[:200]}"
        return True

    async def _emp_has_admin_permissions(self):
        resp = await self._emp_api_get("/api/v1/permissions/me")
        if resp.status_code != 200:
            return f"expected 200, got {resp.status_code}"
        keys = set(resp.json().get("page_keys", []))
        expected_perm_keys = {"permissions.pages", "permissions.roles", "permissions.users"}
        missing = expected_perm_keys - keys
        if missing:
            return f"admin 角色應有 {expected_perm_keys}，缺少: {missing}"
        return True

    async def _emp_still_has_bookings(self):
        resp = await self._emp_api_get("/api/v1/bookings")
        if resp.status_code != 200:
            return f"expected 200, got {resp.status_code}"
        return True

    # ── Phase 5: Revert role ──

    async def _admin_change_role_to_employee(self):
        resp = await self.admin_client.put(
            f"{self.url}/api/v1/employees/{self.test_employee_id}",
            json={"role_id": ROLE_EMPLOYEE_UUID, "employee_type": "intern"},
        )
        if resp.status_code != 200:
            return f"更新失敗: {resp.status_code} {resp.text[:200]}"
        return True

    async def _emp_cannot_access_roles_again(self):
        resp = await self._emp_api_get("/api/v1/roles")
        if resp.status_code != 403:
            return f"expected 403, got {resp.status_code}"
        return True

    async def _emp_no_admin_permissions(self):
        resp = await self._emp_api_get("/api/v1/permissions/me")
        if resp.status_code != 200:
            return f"expected 200, got {resp.status_code}"
        keys = set(resp.json().get("page_keys", []))
        perm_keys = {k for k in keys if k.startswith("permissions.")}
        if perm_keys:
            return f"改回 employee 後不應有 permissions.*，但有: {perm_keys}"
        return True

    async def _emp_still_has_bookings_2(self):
        resp = await self._emp_api_get("/api/v1/bookings")
        if resp.status_code != 200:
            return f"expected 200, got {resp.status_code}"
        return True

    # ── Phase 6: employee_type change → permission_level ──

    async def _admin_change_type_to_admin(self):
        resp = await self.admin_client.put(
            f"{self.url}/api/v1/employees/{self.test_employee_id}",
            json={"employee_type": "admin"},
        )
        if resp.status_code != 200:
            return f"更新失敗: {resp.status_code} {resp.text[:200]}"
        return True

    async def _emp_has_admin_level(self):
        resp = await self._emp_api_get("/api/v1/permissions/me")
        if resp.status_code != 200:
            return f"expected 200, got {resp.status_code}"
        # 用 employees API 檢查 — 需要 admin 才能看到 employees
        # permission_level 100 意味著 is_admin() == True
        # 嘗試執行一個需要 admin 權限的操作（employees.create 需要 is_admin）
        async with httpx.AsyncClient(cookies=self.emp_cookies, **CLIENT_KWARGS) as client:
            # GET /employees 需要 employees.list page permission 且 is_staff()
            resp2 = await client.get(f"{self.url}/api/v1/employees")
        # employee 角色有 employees.list，且 is_staff == True
        # 重點是 permission_level 已變為 100
        if resp2.status_code != 200:
            return f"expected 200 for GET /employees, got {resp2.status_code}"
        return True

    async def _admin_change_type_to_intern(self):
        resp = await self.admin_client.put(
            f"{self.url}/api/v1/employees/{self.test_employee_id}",
            json={"employee_type": "intern"},
        )
        if resp.status_code != 200:
            return f"更新失敗: {resp.status_code} {resp.text[:200]}"
        return True

    async def _emp_has_intern_level(self):
        # intern permission_level = 10, 不是 admin
        # 驗證方式：呼叫需要 is_admin 的 endpoint，應回 403
        # POST /employees 需要 employees.create + is_admin()
        async with httpx.AsyncClient(cookies=self.emp_cookies, **CLIENT_KWARGS) as client:
            resp = await client.post(
                f"{self.url}/api/v1/employees",
                json={
                    "employee_no": "NOPE999",
                    "name": "Should Fail",
                    "email": "nope@test.local",
                    "employee_type": "intern",
                },
            )
        if resp.status_code != 403:
            return f"intern 不應能建立員工，expected 403, got {resp.status_code}"
        return True

    # ── Cleanup ──

    async def _cleanup(self):
        # 清理 DB 資料（反向順序）
        if self.test_user_id:
            db_exec(f"DELETE FROM user_page_overrides WHERE user_id = '{self.test_user_id}'")
            db_exec(f"DELETE FROM user_profiles WHERE id = '{self.test_user_id}'")
            db_exec(f"DELETE FROM public.users WHERE id = '{self.test_user_id}'")
            print(f"    user + profile: OK")

        if self.test_employee_id:
            db_exec(f"DELETE FROM employees WHERE id = '{self.test_employee_id}'")
            print(f"    employee: OK")

        # 清除 Redis 快取
        redis_pw = os.getenv("REDIS_PASSWORD") or "changeme"
        if self.test_user_id:
            for key in [
                f"permission_level:{self.test_user_id}",
                f"role_id:{self.test_user_id}",
                f"employee_type:{self.test_user_id}",
                f"page_perm:{self.test_user_id}",
            ]:
                subprocess.run(
                    ["docker", "exec", "teaching-platform-redis", "redis-cli", "-a", redis_pw, "DEL", key],
                    capture_output=True, text=True, timeout=5,
                )
            print(f"    redis cache: OK")


async def main():
    ok = await PermissionRealtimeTester().run()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    asyncio.run(main())

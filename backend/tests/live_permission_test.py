#!/usr/bin/env python3
"""
Live API Permission Test Script

驗證 Role-Based API 權限控制（page permission system）是否正確運作。

測試範圍:
  0. Super Admin：應可存取所有 API（含 permissions.* 管理端點），擁有全部 page keys
  1. Employee 測試帳號：應可存取所有非 permissions.* 的 API
  2. Student 測試帳號：只能存取 bookings list/create、courses list、自己的合約等
  3. Teacher 測試帳號：只能存取 bookings、自己的 slots/contracts/bonus
  4. 自訂角色測試：建立只有 bookings.list 的角色 → 只能 GET bookings，POST/PUT/DELETE 回 403
  5. 快取失效：更新 role_pages 後，該角色用戶的權限立即生效

使用方式:
    python3 tests/live_permission_test.py
    python3 tests/live_permission_test.py --no-cleanup
"""

import httpx
import asyncio
import subprocess
import argparse
import json
import sys
import os
from datetime import datetime
from dataclasses import dataclass
from typing import Optional

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8001")
DB_CONTAINER = os.getenv("DB_CONTAINER", "teaching-platform-db")

TEST_PASSWORD = "TestPassword123!"
TEST_EMAIL_PREFIX = "test_perm_"
CUSTOM_ROLE_KEY = "test_limited_role"

# Super Admin（從 .env 讀取）
SUPER_ADMIN_EMAIL = os.getenv("SUPER_ADMIN_EMAIL", "eopAdmin@example.com")
SUPER_ADMIN_PASSWORD = os.getenv("SUPER_ADMIN_PASSWORD", "eopsuper888")

# 動態填入（由 setup 建立）
ACCOUNTS: dict[str, dict] = {}
CREATED_USER_IDS: list[str] = []

CLIENT_KWARGS = {
    "follow_redirects": True,
    "timeout": httpx.Timeout(30.0, connect=10.0),
}


@dataclass
class TestResult:
    name: str
    passed: bool
    message: str = ""


# ============================================================
# DB helper (via docker exec)
# ============================================================

def db_exec_raw(sql: str) -> str:
    """Execute SQL via docker exec psql. Returns raw stdout."""
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
    """Execute SQL via docker exec psql. Returns first non-empty line only."""
    raw = db_exec_raw(sql)
    lines = [l for l in raw.split("\n") if l.strip()]
    return lines[0].strip() if lines else ""


def db_exec_lines(sql: str) -> list[str]:
    """Execute SQL and return all non-empty output lines."""
    raw = db_exec_raw(sql)
    return [l.strip() for l in raw.split("\n") if l.strip()]


# ============================================================
# Helpers
# ============================================================

async def login(email: str, password: str) -> dict:
    """登入並返回 cookies dict"""
    async with httpx.AsyncClient(**CLIENT_KWARGS) as client:
        resp = await client.post(
            f"{BACKEND_URL}/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
        return dict(resp.cookies)


async def api_get(cookies: dict, path: str) -> httpx.Response:
    async with httpx.AsyncClient(cookies=cookies, **CLIENT_KWARGS) as client:
        return await client.get(f"{BACKEND_URL}{path}")


async def api_post(cookies: dict, path: str, body: dict | None = None) -> httpx.Response:
    async with httpx.AsyncClient(cookies=cookies, **CLIENT_KWARGS) as client:
        return await client.post(f"{BACKEND_URL}{path}", json=body or {})


async def api_put(cookies: dict, path: str, body: dict | None = None) -> httpx.Response:
    async with httpx.AsyncClient(cookies=cookies, **CLIENT_KWARGS) as client:
        return await client.put(f"{BACKEND_URL}{path}", json=body or {})


async def api_delete(cookies: dict, path: str, body: dict | None = None) -> httpx.Response:
    async with httpx.AsyncClient(cookies=cookies, **CLIENT_KWARGS) as client:
        if body:
            return await client.request("DELETE", f"{BACKEND_URL}{path}", json=body)
        return await client.delete(f"{BACKEND_URL}{path}")


# ============================================================
# Test runner helper
# ============================================================

def run_test(name: str, results: list[TestResult]):
    """Decorator-style test runner"""
    def decorator(fn):
        async def wrapper(*args, **kwargs):
            print(f"  ▶ {name}...", end=" ", flush=True)
            try:
                await fn(*args, **kwargs)
                print("✅")
                results.append(TestResult(name, True, "OK"))
            except AssertionError as e:
                print(f"❌ {e}")
                results.append(TestResult(name, False, str(e)))
            except Exception as e:
                print(f"❌ Error: {e}")
                results.append(TestResult(name, False, f"Error: {e}"))
        return wrapper
    return decorator


# ============================================================
# 0. Super Admin 測試
# ============================================================

async def test_super_admin(results: list[TestResult]):
    print(f"\n{'─'*60}")
    print("👤 Super Admin Permission Tests")
    print(f"{'─'*60}")

    cookies = await login(SUPER_ADMIN_EMAIL, SUPER_ADMIN_PASSWORD)

    # --- 所有主要 list endpoints 都應 200 ---
    @run_test("SuperAdmin: GET /students (students.list) → 200", results)
    async def t1():
        resp = await api_get(cookies, "/api/v1/students")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
    await t1()

    @run_test("SuperAdmin: GET /teachers (teachers.list) → 200", results)
    async def t2():
        resp = await api_get(cookies, "/api/v1/teachers")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    await t2()

    @run_test("SuperAdmin: GET /courses (courses.list) → 200", results)
    async def t3():
        resp = await api_get(cookies, "/api/v1/courses")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    await t3()

    @run_test("SuperAdmin: GET /bookings (bookings.list) → 200", results)
    async def t4():
        resp = await api_get(cookies, "/api/v1/bookings")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    await t4()

    @run_test("SuperAdmin: GET /users/ (employees.list) → 200", results)
    async def t5():
        resp = await api_get(cookies, "/api/v1/users/")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    await t5()

    @run_test("SuperAdmin: GET /student-contracts (students.contracts) → 200", results)
    async def t6():
        resp = await api_get(cookies, "/api/v1/student-contracts")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    await t6()

    @run_test("SuperAdmin: GET /teacher-contracts (teachers.contracts) → 200", results)
    async def t7():
        resp = await api_get(cookies, "/api/v1/teacher-contracts")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    await t7()

    @run_test("SuperAdmin: GET /teacher-slots (teachers.slots) → 200", results)
    async def t8():
        resp = await api_get(cookies, "/api/v1/teacher-slots")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    await t8()

    @run_test("SuperAdmin: GET /teacher-bonus (teachers.bonus) → 200", results)
    async def t9():
        resp = await api_get(cookies, "/api/v1/teacher-bonus")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    await t9()

    # --- permissions 管理 endpoints 應 200 ---
    @run_test("SuperAdmin: GET /pages (permissions.pages) → 200", results)
    async def t10():
        resp = await api_get(cookies, "/api/v1/pages")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    await t10()

    @run_test("SuperAdmin: GET /roles (permissions.roles) → 200", results)
    async def t11():
        resp = await api_get(cookies, "/api/v1/roles")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    await t11()

    @run_test("SuperAdmin: GET /role-pages?role=admin (permissions.roles) → 200", results)
    async def t12():
        resp = await api_get(cookies, "/api/v1/role-pages?role=admin")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    await t12()

    @run_test("SuperAdmin: GET /user-pages/{user_id} (permissions.users) → 200", results)
    async def t13():
        admin_uid = db_exec("SELECT id FROM public.users WHERE email = 'eopAdmin@example.com'")
        resp = await api_get(cookies, f"/api/v1/user-pages/{admin_uid}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    await t13()

    # --- /permissions/me 應包含所有 page keys ---
    @run_test("SuperAdmin: GET /permissions/me → has ALL page keys (incl. permissions.*)", results)
    async def t14():
        resp = await api_get(cookies, "/api/v1/permissions/me")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        keys = set(data.get("page_keys", []))

        # 驗證包含全部分類
        expected_keys = {
            "students.list", "students.create", "students.edit", "students.delete", "students.contracts",
            "students.courses",
            "teachers.list", "teachers.create", "teachers.edit", "teachers.delete", "teachers.contracts",
            "teachers.slots", "teachers.bonus", "teachers.details",
            "courses.list", "courses.create", "courses.edit", "courses.delete",
            "bookings.list", "bookings.create", "bookings.edit", "bookings.delete",
            "employees.list", "employees.create", "employees.edit", "employees.delete",
            "permissions.pages", "permissions.roles", "permissions.users",
        }
        missing = expected_keys - keys
        assert not missing, f"Super admin missing page keys: {sorted(missing)}"
    await t14()


# ============================================================
# 1. Employee 測試
# ============================================================

async def test_employee(results: list[TestResult]):
    print(f"\n{'─'*60}")
    print("👤 Employee Permission Tests")
    print(f"{'─'*60}")

    cookies = await login(ACCOUNTS["employee"]["email"], ACCOUNTS["employee"]["password"])

    @run_test("Employee: GET /students (students.list) → 200", results)
    async def t1():
        resp = await api_get(cookies, "/api/v1/students")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
    await t1()

    @run_test("Employee: GET /teachers (teachers.list) → 200", results)
    async def t2():
        resp = await api_get(cookies, "/api/v1/teachers")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    await t2()

    @run_test("Employee: GET /courses (courses.list) → 200", results)
    async def t3():
        resp = await api_get(cookies, "/api/v1/courses")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    await t3()

    @run_test("Employee: GET /bookings (bookings.list) → 200", results)
    async def t4():
        resp = await api_get(cookies, "/api/v1/bookings")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    await t4()

    @run_test("Employee: GET /users/ (employees.list) → 200", results)
    async def t5():
        resp = await api_get(cookies, "/api/v1/users/")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    await t5()

    @run_test("Employee: GET /student-contracts (students.contracts) → 200", results)
    async def t6():
        resp = await api_get(cookies, "/api/v1/student-contracts")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    await t6()

    @run_test("Employee: GET /teacher-contracts (teachers.contracts) → 200", results)
    async def t7():
        resp = await api_get(cookies, "/api/v1/teacher-contracts")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    await t7()

    @run_test("Employee: GET /teacher-slots (teachers.slots) → 200", results)
    async def t8():
        resp = await api_get(cookies, "/api/v1/teacher-slots")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    await t8()

    @run_test("Employee: GET /teacher-bonus (teachers.bonus) → 200", results)
    async def t9():
        resp = await api_get(cookies, "/api/v1/teacher-bonus")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    await t9()

    @run_test("Employee: GET /permissions/me → has page keys", results)
    async def t10():
        resp = await api_get(cookies, "/api/v1/permissions/me")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        keys = data.get("page_keys", [])
        assert len(keys) > 0, "Employee should have page keys"
        assert "students.list" in keys, f"Missing students.list, got: {keys}"
        assert "bookings.list" in keys, f"Missing bookings.list, got: {keys}"
    await t10()


# ============================================================
# 2. Student 測試
# ============================================================

async def test_student(results: list[TestResult]):
    print(f"\n{'─'*60}")
    print("👤 Student Permission Tests")
    print(f"{'─'*60}")

    cookies = await login(ACCOUNTS["student"]["email"], ACCOUNTS["student"]["password"])

    @run_test("Student: GET /courses (courses.list) → 200", results)
    async def t1():
        resp = await api_get(cookies, "/api/v1/courses")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    await t1()

    @run_test("Student: GET /bookings (bookings.list) → 200", results)
    async def t2():
        resp = await api_get(cookies, "/api/v1/bookings")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    await t2()

    @run_test("Student: GET /student-contracts (students.contracts) → 200", results)
    async def t3():
        resp = await api_get(cookies, "/api/v1/student-contracts")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    await t3()

    @run_test("Student: GET /teacher-slots (teachers.slots) → 200", results)
    async def t4():
        resp = await api_get(cookies, "/api/v1/teacher-slots")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    await t4()

    # Student 應被擋的 endpoints
    @run_test("Student: GET /students (students.list) → 403", results)
    async def t5():
        resp = await api_get(cookies, "/api/v1/students")
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text[:200]}"
    await t5()

    @run_test("Student: GET /teachers (teachers.list) → 403", results)
    async def t6():
        resp = await api_get(cookies, "/api/v1/teachers")
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
    await t6()

    @run_test("Student: GET /users/ (employees.list) → 403", results)
    async def t7():
        resp = await api_get(cookies, "/api/v1/users/")
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
    await t7()

    @run_test("Student: POST /students (students.create) → 403", results)
    async def t8():
        resp = await api_post(cookies, "/api/v1/students", {
            "student_no": "STEST999", "name": "Test", "email": "nope@test.com"
        })
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
    await t8()

    @run_test("Student: POST /courses (courses.create) → 403", results)
    async def t9():
        resp = await api_post(cookies, "/api/v1/courses", {
            "course_code": "TEST999", "course_name": "No Way"
        })
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
    await t9()

    @run_test("Student: DELETE /bookings/batch (bookings.delete) → 403", results)
    async def t10():
        resp = await api_delete(cookies, "/api/v1/bookings/batch", {
            "teacher_id": "fake", "date_from": "2099-01-01", "date_to": "2099-01-02"
        })
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
    await t10()

    @run_test("Student: GET /teacher-contracts (teachers.contracts) → 403", results)
    async def t11():
        resp = await api_get(cookies, "/api/v1/teacher-contracts")
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
    await t11()

    @run_test("Student: GET /teacher-bonus (teachers.bonus) → 403", results)
    async def t12():
        resp = await api_get(cookies, "/api/v1/teacher-bonus")
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
    await t12()

    @run_test("Student: GET /student-courses (students.courses) → 200", results)
    async def t13():
        resp = await api_get(cookies, "/api/v1/student-courses")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    await t13()

    @run_test("Student: GET /permissions/me → has correct page keys", results)
    async def t14():
        resp = await api_get(cookies, "/api/v1/permissions/me")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        keys = set(data.get("page_keys", []))
        expected = {"bookings.list", "bookings.create", "courses.list", "students.contracts", "teachers.slots", "students.courses"}
        missing = expected - keys
        assert not missing, f"Student missing page keys: {sorted(missing)}, got: {sorted(keys)}"
    await t14()


# ============================================================
# 3. Teacher 測試
# ============================================================

async def test_teacher(results: list[TestResult]):
    print(f"\n{'─'*60}")
    print("👤 Teacher Permission Tests")
    print(f"{'─'*60}")

    cookies = await login(ACCOUNTS["teacher"]["email"], ACCOUNTS["teacher"]["password"])

    @run_test("Teacher: GET /bookings (bookings.list) → 200", results)
    async def t1():
        resp = await api_get(cookies, "/api/v1/bookings")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    await t1()

    @run_test("Teacher: GET /courses (courses.list) → 200", results)
    async def t2():
        resp = await api_get(cookies, "/api/v1/courses")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    await t2()

    @run_test("Teacher: GET /teachers (teachers.list) → 200", results)
    async def t3():
        resp = await api_get(cookies, "/api/v1/teachers")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    await t3()

    @run_test("Teacher: GET /teacher-slots (teachers.slots) → 200", results)
    async def t4():
        resp = await api_get(cookies, "/api/v1/teacher-slots")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    await t4()

    @run_test("Teacher: GET /teacher-contracts (teachers.contracts) → 200", results)
    async def t5():
        resp = await api_get(cookies, "/api/v1/teacher-contracts")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    await t5()

    @run_test("Teacher: GET /teacher-bonus (teachers.bonus) → 200", results)
    async def t6():
        resp = await api_get(cookies, "/api/v1/teacher-bonus")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    await t6()

    # Teacher 應被擋的 endpoints
    @run_test("Teacher: GET /students (students.list) → 403", results)
    async def t7():
        resp = await api_get(cookies, "/api/v1/students")
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
    await t7()

    @run_test("Teacher: GET /users/ (employees.list) → 403", results)
    async def t8():
        resp = await api_get(cookies, "/api/v1/users/")
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
    await t8()

    @run_test("Teacher: POST /students (students.create) → 403", results)
    async def t9():
        resp = await api_post(cookies, "/api/v1/students", {
            "student_no": "STEST999", "name": "Test", "email": "nope@test.com"
        })
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
    await t9()

    @run_test("Teacher: POST /courses (courses.create) → 403", results)
    async def t10():
        resp = await api_post(cookies, "/api/v1/courses", {
            "course_code": "TEST999", "course_name": "No Way"
        })
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
    await t10()

    @run_test("Teacher: DELETE /bookings/batch (bookings.delete) → 403", results)
    async def t11():
        resp = await api_delete(cookies, "/api/v1/bookings/batch", {
            "teacher_id": "fake", "date_from": "2099-01-01", "date_to": "2099-01-02"
        })
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
    await t11()

    @run_test("Teacher: POST /teacher-bonus (teachers.bonus) → needs valid data (not 403, teacher has page key)", results)
    async def t12():
        # Teacher now has teachers.bonus page key (for reading).
        # POST passes permission check but fails on invalid data → 500 (not 403).
        resp = await api_post(cookies, "/api/v1/teacher-bonus", {
            "teacher_id": "fake", "bonus_type": "other", "amount": 100,
            "bonus_date": "2026-01-01",
        })
        assert resp.status_code != 403, f"Teacher should have teachers.bonus page key, got 403"
    await t12()

    @run_test("Teacher: GET /student-contracts (students.contracts) → 403", results)
    async def t13():
        resp = await api_get(cookies, "/api/v1/student-contracts")
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
    await t13()

    @run_test("Teacher: GET /teacher-slots/options/teachers → 200", results)
    async def t14():
        resp = await api_get(cookies, "/api/v1/teacher-slots/options/teachers")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    await t14()

    @run_test("Teacher: GET /permissions/me → has correct page keys", results)
    async def t15():
        resp = await api_get(cookies, "/api/v1/permissions/me")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        keys = set(data.get("page_keys", []))
        expected = {"bookings.list", "bookings.edit", "teachers.list", "teachers.slots",
                    "teachers.contracts", "teachers.bonus", "courses.list", "teachers.details"}
        missing = expected - keys
        assert not missing, f"Teacher missing page keys: {sorted(missing)}, got: {sorted(keys)}"
    await t15()


# ============================================================
# 4. 自訂角色測試 + 5. 快取失效測試
# ============================================================

async def test_custom_role(results: list[TestResult]):
    """建立自訂角色（只有 bookings.list），驗證權限"""
    print(f"\n{'─'*60}")
    print("👤 Custom Role Permission Tests")
    print(f"{'─'*60}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    custom_email = f"test_perm_custom_{timestamp}@example.com"
    custom_user_id = None

    try:
        # 1. 建立自訂角色 (via docker exec)
        db_exec(
            f"INSERT INTO roles (role, name, description, is_system) "
            f"VALUES ('{CUSTOM_ROLE_KEY}', 'Test Limited Role', 'Only bookings.list', false) "
            f"ON CONFLICT (role) DO NOTHING"
        )

        # 2. 找到 bookings.list page ID
        bookings_list_page_id = db_exec(
            "SELECT id FROM pages WHERE key = 'bookings.list' AND is_active = true LIMIT 1"
        )
        assert bookings_list_page_id, "bookings.list page not found in DB"

        # 清除既有 role_pages，重新指派
        db_exec(f"DELETE FROM role_pages WHERE role = '{CUSTOM_ROLE_KEY}'")
        db_exec(
            f"INSERT INTO role_pages (role, page_id) VALUES ('{CUSTOM_ROLE_KEY}', '{bookings_list_page_id}') "
            f"ON CONFLICT DO NOTHING"
        )

        # 3. 建立自訂角色測試用戶 (使用 bcrypt via python, 插入 via docker exec)
        import bcrypt as _bcrypt
        hashed_pw = _bcrypt.hashpw(b"TestPassword123!", _bcrypt.gensalt(rounds=10)).decode()

        # 插入 user
        custom_user_id = db_exec(
            f"INSERT INTO public.users (email, encrypted_password, email_confirmed_at, raw_user_meta_data) "
            f"VALUES ('{custom_email}', '{hashed_pw}', NOW(), "
            f"'{{\"name\": \"Custom Role User\", \"role\": \"{CUSTOM_ROLE_KEY}\"}}'::jsonb) "
            f"RETURNING id"
        )
        assert custom_user_id, f"Failed to create custom user"
        print(f"  Created custom role user: {custom_email} (id: {custom_user_id})")

        uid_prefix = custom_user_id.replace("-", "").upper()[:8]

        # 建立 employee entity
        emp_id = db_exec(
            f"INSERT INTO employees (employee_no, name, email, employee_type, hire_date, is_active) "
            f"VALUES ('E{uid_prefix}', 'Custom Role User', '{custom_email}', 'intern', CURRENT_DATE, true) "
            f"RETURNING id"
        )
        assert emp_id, "Failed to create employee"

        # 建立 user_profiles
        db_exec(
            f"INSERT INTO user_profiles (id, role, employee_id, employee_subtype) "
            f"VALUES ('{custom_user_id}', '{CUSTOM_ROLE_KEY}', '{emp_id}', 'intern')"
        )

        # 4. 登入
        cookies = await login(custom_email, "TestPassword123!")

        @run_test("Custom Role: GET /bookings (bookings.list) → 200", results)
        async def t1():
            resp = await api_get(cookies, "/api/v1/bookings")
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        await t1()

        @run_test("Custom Role: GET /students (students.list) → 403", results)
        async def t2():
            resp = await api_get(cookies, "/api/v1/students")
            assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
        await t2()

        @run_test("Custom Role: GET /courses (courses.list) → 403", results)
        async def t3():
            resp = await api_get(cookies, "/api/v1/courses")
            assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
        await t3()

        @run_test("Custom Role: POST /bookings (bookings.create) → 403", results)
        async def t4():
            resp = await api_post(cookies, "/api/v1/bookings", {})
            assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
        await t4()

        @run_test("Custom Role: DELETE /bookings/batch (bookings.delete) → 403", results)
        async def t5():
            resp = await api_delete(cookies, "/api/v1/bookings/batch", {
                "teacher_id": "fake", "date_from": "2099-01-01", "date_to": "2099-01-02"
            })
            assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
        await t5()

        @run_test("Custom Role: GET /users/ (employees.list) → 403", results)
        async def t6():
            resp = await api_get(cookies, "/api/v1/users/")
            assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
        await t6()

        @run_test("Custom Role: GET /permissions/me → only bookings.list", results)
        async def t7():
            resp = await api_get(cookies, "/api/v1/permissions/me")
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
            data = resp.json()
            keys = data.get("page_keys", [])
            assert "bookings.list" in keys, f"Missing bookings.list, got: {keys}"
            assert len(keys) == 1, f"Should have exactly 1 page key, got {len(keys)}: {keys}"
        await t7()

        # ============================================================
        # 5. 快取失效測試：給自訂角色加 students.list，驗證立即生效
        # ============================================================

        @run_test("Cache Invalidation: add students.list → GET /students → 200", results)
        async def t8():
            # 先確認 GET /students 是 403
            resp = await api_get(cookies, "/api/v1/students")
            assert resp.status_code == 403, f"Pre-check: expected 403, got {resp.status_code}"

            # 直接透過 DB 加入 students.list 到自訂角色
            students_list_page_id = db_exec(
                "SELECT id FROM pages WHERE key = 'students.list' AND is_active = true LIMIT 1"
            )
            assert students_list_page_id, "students.list page not found"

            db_exec(
                f"INSERT INTO role_pages (role, page_id) VALUES ('{CUSTOM_ROLE_KEY}', '{students_list_page_id}') "
                f"ON CONFLICT DO NOTHING"
            )

            # 清除 Redis 快取（模擬 cache invalidation）
            subprocess.run(
                ["docker", "exec", "teaching-platform-redis", "redis-cli", "DEL", f"page_perm:{custom_user_id}"],
                capture_output=True, text=True, timeout=5,
            )

            # 立即驗證自訂角色用戶可以存取 students
            resp3 = await api_get(cookies, "/api/v1/students")
            assert resp3.status_code == 200, f"After cache invalidation: expected 200, got {resp3.status_code}: {resp3.text[:200]}"
        await t8()

    finally:
        # 清理自訂角色相關資料
        if custom_user_id:
            db_exec(f"DELETE FROM user_profiles WHERE id = '{custom_user_id}'")
            db_exec(f"DELETE FROM public.users WHERE id = '{custom_user_id}'")
            db_exec(f"DELETE FROM employees WHERE email = '{custom_email}'")

        db_exec(f"DELETE FROM role_pages WHERE role = '{CUSTOM_ROLE_KEY}'")
        db_exec(f"DELETE FROM roles WHERE role = '{CUSTOM_ROLE_KEY}' AND is_system = false")
        print("  🧹 Custom role test data cleaned up")


# ============================================================
# Setup / Cleanup (via docker exec)
# ============================================================

def setup_test_accounts():
    """建立 student / teacher / employee 測試帳號（via docker exec）"""
    import bcrypt as _bcrypt
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    hashed_pw = _bcrypt.hashpw(TEST_PASSWORD.encode(), _bcrypt.gensalt(rounds=10)).decode()

    for role in ("student", "teacher", "employee"):
        email = f"{TEST_EMAIL_PREFIX}{role}_{timestamp}@example.com"
        meta_json = json.dumps({"name": f"Perm Test {role.capitalize()}", "role": role}).replace("'", "''")

        user_id = db_exec(
            f"INSERT INTO public.users (email, encrypted_password, email_confirmed_at, raw_user_meta_data) "
            f"VALUES ('{email}', '{hashed_pw}', NOW(), '{meta_json}'::jsonb) RETURNING id"
        )
        assert user_id, f"Failed to create {role} user"
        uid_prefix = user_id.replace("-", "").upper()[:8]

        if role == "student":
            entity_id = db_exec(
                f"INSERT INTO students (student_no, name, email, is_active) "
                f"VALUES ('S{uid_prefix}', 'Perm Test Student', '{email}', true) RETURNING id"
            )
            db_exec(
                f"INSERT INTO user_profiles (id, role, student_id) "
                f"VALUES ('{user_id}', 'student', '{entity_id}')"
            )
        elif role == "teacher":
            entity_id = db_exec(
                f"INSERT INTO teachers (teacher_no, name, email, is_active) "
                f"VALUES ('T{uid_prefix}', 'Perm Test Teacher', '{email}', true) RETURNING id"
            )
            db_exec(
                f"INSERT INTO user_profiles (id, role, teacher_id) "
                f"VALUES ('{user_id}', 'teacher', '{entity_id}')"
            )
        elif role == "employee":
            entity_id = db_exec(
                f"INSERT INTO employees (employee_no, name, email, employee_type, hire_date, is_active) "
                f"VALUES ('E{uid_prefix}', 'Perm Test Employee', '{email}', 'intern', CURRENT_DATE, true) RETURNING id"
            )
            db_exec(
                f"INSERT INTO user_profiles (id, role, employee_id, employee_subtype) "
                f"VALUES ('{user_id}', 'employee', '{entity_id}', 'intern')"
            )

        ACCOUNTS[role] = {"email": email, "password": TEST_PASSWORD, "user_id": user_id}
        CREATED_USER_IDS.append(user_id)
        print(f"  Created {role}: {email}")


def cleanup_test_accounts():
    """清理 test_perm_ 開頭的測試帳號"""
    # Find all test users
    user_ids = db_exec_lines(
        f"SELECT id FROM public.users WHERE email LIKE '{TEST_EMAIL_PREFIX}%'"
    )
    if not user_ids:
        print("  No test accounts to clean up")
        return
    for uid in user_ids:
        # Get linked entities
        profile_raw = db_exec(
            f"SELECT student_id, teacher_id, employee_id FROM user_profiles WHERE id = '{uid}'"
        )
        db_exec(f"DELETE FROM user_profiles WHERE id = '{uid}'")
        db_exec(f"DELETE FROM public.users WHERE id = '{uid}'")

        if profile_raw:
            parts = profile_raw.split("|")
            if len(parts) == 3:
                student_id, teacher_id, employee_id = [p.strip() for p in parts]
                if student_id:
                    db_exec(f"DELETE FROM students WHERE id = '{student_id}'")
                if teacher_id:
                    db_exec(f"DELETE FROM teachers WHERE id = '{teacher_id}'")
                if employee_id:
                    db_exec(f"DELETE FROM employees WHERE id = '{employee_id}'")

    print(f"  Cleaned up {len(user_ids)} test user(s)")


# ============================================================
# Main
# ============================================================

async def main():
    parser = argparse.ArgumentParser(description="Live API Permission Test Script")
    parser.add_argument("--no-cleanup", action="store_true", help="Skip cleanup (N/A for this version)")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print("🔐 Live API Permission Tests")
    print(f"{'='*60}")
    print(f"Backend URL: {BACKEND_URL}")
    print(f"DB Container: {DB_CONTAINER}")
    print(f"{'='*60}")

    # Verify DB connectivity
    try:
        ver = db_exec("SELECT version()")
        print(f"DB connected: {ver[:60]}...")
    except Exception as e:
        print(f"❌ Cannot connect to DB container: {e}")
        print("  Make sure Docker is running and DB container is healthy.")
        sys.exit(1)

    # Setup test accounts
    print("\n📦 Setting up test accounts...")
    setup_test_accounts()

    results: list[TestResult] = []

    try:
        # Run all test suites
        await test_super_admin(results)
        await test_employee(results)
        await test_student(results)
        await test_teacher(results)
        await test_custom_role(results)
    finally:
        if not args.no_cleanup:
            print(f"\n🧹 Cleaning up base test accounts...")
            cleanup_test_accounts()
        else:
            print("\n⚠️  Skipping base account cleanup (--no-cleanup)")

    # Summary
    print(f"\n{'='*60}")
    print("📊 Test Summary")
    print(f"{'='*60}")

    passed = [r for r in results if r.passed]
    failed = [r for r in results if not r.passed]

    for r in results:
        status = "✅" if r.passed else "❌"
        print(f"  {status} {r.name}")

    print(f"\n  Total: {len(passed)} passed, {len(failed)} failed")
    print(f"{'='*60}\n")

    if failed:
        print("❌ FAILED tests:")
        for r in failed:
            print(f"  - {r.name}: {r.message}")
        print()

    sys.exit(0 if not failed else 1)


if __name__ == "__main__":
    asyncio.run(main())

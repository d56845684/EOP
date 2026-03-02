#!/usr/bin/env python3
"""
Live Seed Test Data Script

建立測試用的教師、學生（含試上學生）、課程、合約等資料。

使用方式:
    # 建立測試資料（不清理）
    python tests/live_seed_test_data.py

    # 只清理測試資料
    python tests/live_seed_test_data.py --cleanup-only

    # 指定 backend URL
    python tests/live_seed_test_data.py --backend-url http://127.0.0.1:8001
"""

import httpx
import asyncio
import argparse
import sys
import os
from datetime import datetime, date, timedelta
from dataclasses import dataclass, field
from typing import Optional

# 設定
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8001")
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://127.0.0.1:8000")
SERVICE_ROLE_KEY = os.getenv("SERVICE_ROLE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoic2VydmljZV9yb2xlIiwiaXNzIjoic3VwYWJhc2UiLCJpYXQiOjE3NjczMjM3NDcsImV4cCI6MTkyNTAwMzc0N30.h8XFj9oZdc0ZaiczkL83AkQtf6zKDTrdTO3SxtrZVU8")

TEST_EMAIL_PREFIX = "test_seed_"
TEST_EMAIL_DOMAIN = "@example.com"
TEST_PASSWORD = "TestPassword123!"
TEST_NOTES = "live_seed_test_data"


# ── 要建立的測試資料定義 ──

TEACHERS = [
    {
        "name": "王老師",
        "phone": "0911111111",
        "address": "台北市大安區師大路1號",
        "bio": "5年鋼琴教學經驗",
    },
    {
        "name": "李老師",
        "phone": "0922222222",
        "address": "台北市信義區音樂路2號",
        "bio": "10年小提琴教學經驗",
    },
]

STUDENTS_FORMAL = [
    {
        "name": "陳同學",
        "phone": "0933333333",
        "address": "台北市中山區學生路3號",
        "birth_date": "2010-05-15",
        "emergency_contact_name": "陳爸爸",
        "emergency_contact_phone": "0933333300",
    },
    {
        "name": "林同學",
        "phone": "0944444444",
        "address": "台北市松山區讀書路4號",
        "birth_date": "2012-08-20",
        "emergency_contact_name": "林媽媽",
        "emergency_contact_phone": "0944444400",
    },
]

STUDENTS_TRIAL = [
    {
        "name": "試上小明",
        "phone": "0955555555",
        "address": "台北市內湖區試上路5號",
        "birth_date": "2011-03-10",
        "emergency_contact_name": "小明媽媽",
        "emergency_contact_phone": "0955555500",
    },
]

EMPLOYEE = {
    "name": "測試管理員",
    "phone": "0900000000",
    "address": "台北市中正區管理路0號",
    "employee_type": "full_time",
}

COURSES = [
    {"course_code": "PIANO-101", "course_name": "鋼琴初級班", "description": "適合初學者的鋼琴課程", "duration_minutes": 60, "is_active": True},
    {"course_code": "VIOLIN-201", "course_name": "小提琴進階班", "description": "適合有基礎的小提琴課程", "duration_minutes": 60, "is_active": True},
]


@dataclass
class CreatedData:
    """追蹤所有建立的資料"""
    employee_user_id: Optional[str] = None
    employee_cookies: dict = field(default_factory=dict)
    employee_id: Optional[str] = None

    teacher_user_ids: list = field(default_factory=list)
    teacher_entity_ids: list = field(default_factory=list)

    student_user_ids: list = field(default_factory=list)
    student_entity_ids: list = field(default_factory=list)

    trial_student_user_ids: list = field(default_factory=list)
    trial_student_entity_ids: list = field(default_factory=list)

    course_ids: list = field(default_factory=list)
    student_contract_ids: list = field(default_factory=list)
    teacher_contract_ids: list = field(default_factory=list)


class LiveSeedTester:
    def __init__(self, backend_url: str, supabase_url: str, service_role_key: str):
        self.backend_url = backend_url.rstrip("/")
        self.supabase_url = supabase_url.rstrip("/")
        self.service_role_key = service_role_key
        self.data = CreatedData()
        self.all_user_ids: list[str] = []

        self.client_kwargs = {
            "follow_redirects": True,
            "timeout": httpx.Timeout(30.0, connect=10.0),
        }
        self.supa_headers = {
            "Authorization": f"Bearer {self.service_role_key}",
            "apikey": self.service_role_key,
        }

    # ========== 主流程 ==========

    async def seed_all(self) -> bool:
        print(f"\n{'='*60}")
        print(f"🌱 Seeding Test Data")
        print(f"{'='*60}")
        print(f"Backend URL: {self.backend_url}")
        print(f"{'='*60}\n")

        try:
            await self._step("1. 註冊員工帳號（用於後續 CRUD 操作）", self._seed_employee)
            await self._step("2. 註冊教師帳號", self._seed_teachers)
            await self._step("3. 註冊正式學生帳號", self._seed_formal_students)
            await self._step("4. 註冊試上學生帳號", self._seed_trial_students)
            await self._step("5. 建立課程", self._seed_courses)
            await self._step("6. 學生選課", self._seed_student_courses)
            await self._step("7. 建立學生合約（正式學生）", self._seed_student_contracts)
            await self._step("8. 建立教師合約", self._seed_teacher_contracts)

            self._print_summary()
            return True

        except Exception as e:
            print(f"\n❌ Seed failed: {e}")
            return False

    async def _step(self, label: str, fn):
        print(f"\n{'─'*60}")
        print(f"  {label}")
        print(f"{'─'*60}")
        await fn()

    # ========== 註冊帳號 ==========

    async def _register_and_get_entity(self, register_data: dict, role: str) -> tuple[str, str]:
        """註冊帳號，回傳 (user_id, entity_id)"""
        async with httpx.AsyncClient(**self.client_kwargs) as client:
            # 註冊
            resp = await client.post(
                f"{self.backend_url}/api/v1/auth/register",
                json=register_data,
            )
            data = resp.json()
            if resp.status_code != 200 or not data.get("success"):
                raise Exception(f"註冊失敗: {data}")

            # 登入取得 user_id
            resp = await client.post(
                f"{self.backend_url}/api/v1/auth/login",
                json={"email": register_data["email"], "password": TEST_PASSWORD},
            )
            assert resp.status_code == 200, f"Login failed: {resp.text}"
            login_data = resp.json()
            user_id = login_data["user"]["id"]

            # 查詢 entity ID
            resp2 = await client.get(
                f"{self.supabase_url}/rest/v1/user_profiles?id=eq.{user_id}&select=student_id,teacher_id,employee_id",
                headers=self.supa_headers,
            )
            profile = resp2.json()[0]

            entity_key = f"{role}_id" if role != "employee" else "employee_id"
            entity_id = profile.get(entity_key)

            return user_id, entity_id, dict(resp.cookies)

    def _gen_email(self, role: str, index: int) -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{TEST_EMAIL_PREFIX}{role}_{index}_{ts}{TEST_EMAIL_DOMAIN}"

    async def _seed_employee(self):
        email = self._gen_email("employee", 0)
        register_data = {
            "email": email,
            "password": TEST_PASSWORD,
            "name": EMPLOYEE["name"],
            "role": "employee",
            "phone": EMPLOYEE["phone"],
            "address": EMPLOYEE["address"],
            "employee_type": EMPLOYEE["employee_type"],
        }
        user_id, entity_id, cookies = await self._register_and_get_entity(register_data, "employee")
        self.data.employee_user_id = user_id
        self.data.employee_id = entity_id
        self.data.employee_cookies = cookies
        self.all_user_ids.append(user_id)
        print(f"    ✅ {EMPLOYEE['name']} | {email}")
        print(f"       user_id={user_id[:8]}… employee_id={entity_id[:8]}…")

    async def _seed_teachers(self):
        for i, t in enumerate(TEACHERS):
            email = self._gen_email("teacher", i)
            register_data = {
                "email": email,
                "password": TEST_PASSWORD,
                "name": t["name"],
                "role": "teacher",
                "phone": t["phone"],
                "address": t["address"],
                "bio": t["bio"],
            }
            user_id, entity_id, _ = await self._register_and_get_entity(register_data, "teacher")
            self.data.teacher_user_ids.append(user_id)
            self.data.teacher_entity_ids.append(entity_id)
            self.all_user_ids.append(user_id)
            print(f"    ✅ {t['name']} | {email}")
            print(f"       user_id={user_id[:8]}… teacher_id={entity_id[:8]}…")

    async def _seed_formal_students(self):
        for i, s in enumerate(STUDENTS_FORMAL):
            email = self._gen_email("student", i)
            register_data = {
                "email": email,
                "password": TEST_PASSWORD,
                "name": s["name"],
                "role": "student",
                "phone": s["phone"],
                "address": s["address"],
                "birth_date": s["birth_date"],
                "emergency_contact_name": s["emergency_contact_name"],
                "emergency_contact_phone": s["emergency_contact_phone"],
            }
            user_id, entity_id, _ = await self._register_and_get_entity(register_data, "student")
            self.data.student_user_ids.append(user_id)
            self.data.student_entity_ids.append(entity_id)
            self.all_user_ids.append(user_id)
            print(f"    ✅ {s['name']}（正式）| {email}")
            print(f"       user_id={user_id[:8]}… student_id={entity_id[:8]}…")

    async def _seed_trial_students(self):
        for i, s in enumerate(STUDENTS_TRIAL):
            email = self._gen_email("trial", i)
            register_data = {
                "email": email,
                "password": TEST_PASSWORD,
                "name": s["name"],
                "role": "student",
                "phone": s["phone"],
                "address": s["address"],
                "birth_date": s["birth_date"],
                "emergency_contact_name": s["emergency_contact_name"],
                "emergency_contact_phone": s["emergency_contact_phone"],
            }
            user_id, entity_id, _ = await self._register_and_get_entity(register_data, "student")
            self.data.trial_student_user_ids.append(user_id)
            self.data.trial_student_entity_ids.append(entity_id)
            self.all_user_ids.append(user_id)

            # 設定 student_type = 'trial'
            async with httpx.AsyncClient(**self.client_kwargs) as client:
                resp = await client.patch(
                    f"{self.supabase_url}/rest/v1/students?id=eq.{entity_id}",
                    headers={**self.supa_headers, "Content-Type": "application/json", "Prefer": "return=minimal"},
                    json={"student_type": "trial"},
                )
                assert resp.status_code in (200, 204), f"Failed to set trial: {resp.text}"

            print(f"    ✅ {s['name']}（試上）| {email}")
            print(f"       user_id={user_id[:8]}… student_id={entity_id[:8]}… student_type=trial")

    # ========== 建立課程 ==========

    async def _seed_courses(self):
        async with httpx.AsyncClient(cookies=self.data.employee_cookies, **self.client_kwargs) as client:
            for c in COURSES:
                # 先嘗試找已存在的課程（含軟刪除），用 Supabase service role
                async with httpx.AsyncClient(**self.client_kwargs) as supa_client:
                    find_resp = await supa_client.get(
                        f"{self.supabase_url}/rest/v1/courses?course_code=eq.{c['course_code']}&select=id,is_deleted",
                        headers=self.supa_headers,
                    )
                    if find_resp.status_code == 200 and find_resp.json():
                        existing = find_resp.json()[0]
                        course_id = existing["id"]
                        # 如果被軟刪除了，恢復它
                        if existing.get("is_deleted"):
                            await supa_client.patch(
                                f"{self.supabase_url}/rest/v1/courses?id=eq.{course_id}",
                                headers={**self.supa_headers, "Content-Type": "application/json", "Prefer": "return=minimal"},
                                json={"is_deleted": False, "is_active": True},
                            )
                            print(f"    ✅ {c['course_name']}（恢復已有課程）| id={course_id[:8]}…")
                        else:
                            print(f"    ✅ {c['course_name']}（已存在）| id={course_id[:8]}…")
                        self.data.course_ids.append(course_id)
                        continue

                resp = await client.post(
                    f"{self.backend_url}/api/v1/courses",
                    json=c,
                )
                if resp.status_code == 200:
                    course_data = resp.json().get("data", {})
                    course_id = course_data.get("id")
                    if course_id:
                        self.data.course_ids.append(course_id)
                        print(f"    ✅ {c['course_name']} | id={course_id[:8]}…")
                    else:
                        print(f"    ⚠️ {c['course_name']} 回應無 id: {resp.json()}")
                else:
                    print(f"    ❌ {c['course_name']} 建立失敗: {resp.status_code} {resp.text}")

    # ========== 學生選課 ==========

    async def _seed_student_courses(self):
        """為每個學生選修課程"""
        if not self.data.course_ids:
            print("    ⚠️ 無課程，跳過學生選課")
            return

        all_student_ids = self.data.student_entity_ids + self.data.trial_student_entity_ids
        all_student_names = [s["name"] for s in STUDENTS_FORMAL] + [s["name"] for s in STUDENTS_TRIAL]

        async with httpx.AsyncClient(cookies=self.data.employee_cookies, **self.client_kwargs) as client:
            for i, student_id in enumerate(all_student_ids):
                for j, course_id in enumerate(self.data.course_ids):
                    resp = await client.post(
                        f"{self.backend_url}/api/v1/student-courses",
                        json={"student_id": student_id, "course_id": course_id},
                    )
                    if resp.status_code == 200:
                        print(f"    ✅ {all_student_names[i]} → {COURSES[j]['course_name']}")
                    else:
                        print(f"    ❌ {all_student_names[i]} → {COURSES[j]['course_name']}: {resp.status_code} {resp.text}")

    # ========== 建立合約 ==========

    async def _seed_student_contracts(self):
        """為每個正式學生建立合約"""
        if not self.data.course_ids:
            print("    ⚠️ 無課程，跳過建立學生合約")
            return

        course_id = self.data.course_ids[0]
        today = date.today()
        end = today + timedelta(days=180)

        async with httpx.AsyncClient(cookies=self.data.employee_cookies, **self.client_kwargs) as client:
            for i, student_id in enumerate(self.data.student_entity_ids):
                contract_data = {
                    "student_id": student_id,
                    "start_date": today.isoformat(),
                    "end_date": end.isoformat(),
                    "total_lessons": 24,
                    "remaining_lessons": 24,
                    "notes": TEST_NOTES,
                }

                resp = await client.post(
                    f"{self.backend_url}/api/v1/student-contracts",
                    json=contract_data,
                )
                if resp.status_code == 200:
                    sc_data = resp.json().get("data", {})
                    sc_id = sc_data.get("id")
                    sc_no = sc_data.get("contract_no", "?")
                    if sc_id:
                        self.data.student_contract_ids.append(sc_id)
                        print(f"    ✅ 學生合約 {sc_no} → {STUDENTS_FORMAL[i]['name']} | 24堂")

                        # 建立合約明細
                        detail_resp = await client.post(
                            f"{self.backend_url}/api/v1/student-contracts/{sc_id}/details",
                            json={
                                "detail_type": "lesson_price",
                                "course_id": course_id,
                                "description": "每堂課費用",
                                "amount": 800,
                            },
                        )
                        if detail_resp.status_code == 200:
                            print(f"       └─ 明細: lesson_price 800元/{COURSES[0]['course_name']}")
                        else:
                            print(f"       └─ ⚠️ 明細建立失敗: {detail_resp.status_code} {detail_resp.text}")
                    else:
                        print(f"    ⚠️ 學生合約回應無 id: {resp.json()}")
                else:
                    print(f"    ❌ 學生合約建立失敗: {resp.status_code} {resp.text}")

    async def _seed_teacher_contracts(self):
        """為每個教師建立合約"""
        today = date.today()
        end = today + timedelta(days=365)

        async with httpx.AsyncClient(cookies=self.data.employee_cookies, **self.client_kwargs) as client:
            for i, teacher_id in enumerate(self.data.teacher_entity_ids):
                contract_data = {
                    "teacher_id": teacher_id,
                    "start_date": today.isoformat(),
                    "end_date": end.isoformat(),
                    "employment_type": "hourly",
                    "notes": TEST_NOTES,
                }

                resp = await client.post(
                    f"{self.backend_url}/api/v1/teacher-contracts",
                    json=contract_data,
                )
                if resp.status_code == 200:
                    tc_data = resp.json().get("data", {})
                    tc_id = tc_data.get("id")
                    tc_no = tc_data.get("contract_no", "?")
                    if tc_id:
                        self.data.teacher_contract_ids.append(tc_id)
                        print(f"    ✅ 教師合約 {tc_no} → {TEACHERS[i]['name']}")

                        # 為每個課程建立時薪明細
                        for j, course_id in enumerate(self.data.course_ids):
                            rate = 500 + (i * 100) + (j * 50)
                            detail_resp = await client.post(
                                f"{self.backend_url}/api/v1/teacher-contracts/{tc_id}/details",
                                json={
                                    "detail_type": "course_rate",
                                    "course_id": course_id,
                                    "description": f"{COURSES[j]['course_name']}時薪",
                                    "amount": rate,
                                },
                            )
                            if detail_resp.status_code == 200:
                                print(f"       └─ 明細: {COURSES[j]['course_name']} {rate}元/hr")
                            else:
                                print(f"       └─ ⚠️ 明細建立失敗: {detail_resp.status_code} {detail_resp.text}")
                    else:
                        print(f"    ⚠️ 教師合約回應無 id: {resp.json()}")
                else:
                    print(f"    ❌ 教師合約建立失敗: {resp.status_code} {resp.text}")

    # ========== 摘要 ==========

    def _print_summary(self):
        print(f"\n{'='*60}")
        print("📊 Seed Summary")
        print(f"{'='*60}\n")

        print(f"  👨‍💼 員工: 1")
        print(f"  👨‍🏫 教師: {len(self.data.teacher_entity_ids)}")
        print(f"  👨‍🎓 正式學生: {len(self.data.student_entity_ids)}")
        print(f"  🆕 試上學生: {len(self.data.trial_student_entity_ids)}")
        print(f"  📚 課程: {len(self.data.course_ids)}")
        print(f"  📝 學生合約: {len(self.data.student_contract_ids)}")
        print(f"  📝 教師合約: {len(self.data.teacher_contract_ids)}")

        print(f"\n{'─'*60}")
        print("  📋 測試帳號密碼統一: TestPassword123!")
        print(f"{'─'*60}")

        print(f"\n  ⚠️  清理指令:")
        print(f"  python tests/live_seed_test_data.py --cleanup-only")
        print(f"\n{'='*60}\n")

    # ========== 清理 ==========

    async def cleanup(self):
        print(f"\n{'='*60}")
        print("🧹 Cleaning up seed test data...")
        print(f"{'='*60}\n")

        async with httpx.AsyncClient(**self.client_kwargs) as client:
            # 搜尋所有 test_seed_ 前綴的用戶
            resp = await client.get(
                f"{self.supabase_url}/auth/v1/admin/users",
                headers=self.supa_headers,
                params={"per_page": 1000},
            )

            if resp.status_code != 200:
                print(f"  ❌ Failed to list users: {resp.status_code}")
                return

            users = resp.json().get("users", [])
            test_users = [u for u in users if u.get("email", "").startswith(TEST_EMAIL_PREFIX)]

            if not test_users:
                print("  No seed test users found")
            else:
                print(f"  Found {len(test_users)} seed test user(s)")

            for user in test_users:
                await self._delete_user(client, user["id"])

            # 清理課程（透過 notes 欄位不容易做，用 service role 搜尋名稱）
            for course_name in [c["course_name"] for c in COURSES]:
                resp = await client.get(
                    f"{self.supabase_url}/rest/v1/courses?course_name=eq.{course_name}&select=id",
                    headers=self.supa_headers,
                )
                if resp.status_code == 200:
                    for c in resp.json():
                        del_resp = await client.patch(
                            f"{self.supabase_url}/rest/v1/courses?id=eq.{c['id']}",
                            headers={**self.supa_headers, "Content-Type": "application/json", "Prefer": "return=minimal"},
                            json={"is_deleted": True},
                        )
                        status = "✅" if del_resp.status_code in (200, 204) else "❌"
                        print(f"    {status} Soft-deleted course: {course_name}")

        print("\n✅ Cleanup completed\n")

    async def _delete_user(self, client: httpx.AsyncClient, user_id: str):
        """刪除用戶及其關聯資料"""
        print(f"  Deleting user {user_id[:8]}...")

        headers_rw = {
            **self.supa_headers,
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }

        # 查詢 entity IDs
        resp = await client.get(
            f"{self.supabase_url}/rest/v1/user_profiles?id=eq.{user_id}&select=student_id,teacher_id,employee_id",
            headers=self.supa_headers,
        )
        entity_ids = {}
        if resp.status_code == 200 and resp.json():
            entity_ids = resp.json()[0]

        # 清理 student 關聯（合約明細 → 合約 → bookings）
        student_id = entity_ids.get("student_id")
        if student_id:
            # student_contract_details → student_contracts
            sc_resp = await client.get(
                f"{self.supabase_url}/rest/v1/student_contracts?student_id=eq.{student_id}&select=id",
                headers=self.supa_headers,
            )
            if sc_resp.status_code == 200:
                for sc in sc_resp.json():
                    await client.delete(
                        f"{self.supabase_url}/rest/v1/student_contract_details?student_contract_id=eq.{sc['id']}",
                        headers=headers_rw,
                    )
                    await client.delete(
                        f"{self.supabase_url}/rest/v1/student_contract_teachers?student_contract_id=eq.{sc['id']}",
                        headers=headers_rw,
                    )
                    await client.delete(
                        f"{self.supabase_url}/rest/v1/student_contract_leave_records?student_contract_id=eq.{sc['id']}",
                        headers=headers_rw,
                    )
                    # bookings referencing this contract
                    await client.delete(
                        f"{self.supabase_url}/rest/v1/bookings?student_contract_id=eq.{sc['id']}",
                        headers=headers_rw,
                    )
                await client.delete(
                    f"{self.supabase_url}/rest/v1/student_contracts?student_id=eq.{student_id}",
                    headers=headers_rw,
                )
            # bookings by student_id (trial students without contract)
            await client.delete(
                f"{self.supabase_url}/rest/v1/bookings?student_id=eq.{student_id}",
                headers=headers_rw,
            )

        # 清理 teacher 關聯
        teacher_id = entity_ids.get("teacher_id")
        if teacher_id:
            tc_resp = await client.get(
                f"{self.supabase_url}/rest/v1/teacher_contracts?teacher_id=eq.{teacher_id}&select=id",
                headers=self.supa_headers,
            )
            if tc_resp.status_code == 200:
                for tc in tc_resp.json():
                    await client.delete(
                        f"{self.supabase_url}/rest/v1/teacher_contract_details?teacher_contract_id=eq.{tc['id']}",
                        headers=headers_rw,
                    )
                    await client.delete(
                        f"{self.supabase_url}/rest/v1/teacher_available_slots?teacher_contract_id=eq.{tc['id']}",
                        headers=headers_rw,
                    )
                await client.delete(
                    f"{self.supabase_url}/rest/v1/teacher_contracts?teacher_id=eq.{teacher_id}",
                    headers=headers_rw,
                )
            await client.delete(
                f"{self.supabase_url}/rest/v1/teacher_available_slots?teacher_id=eq.{teacher_id}",
                headers=headers_rw,
            )

        # 刪除 line_user_bindings, user_profiles, entity, auth user
        await client.delete(
            f"{self.supabase_url}/rest/v1/line_user_bindings?user_id=eq.{user_id}",
            headers=headers_rw,
        )
        await client.delete(
            f"{self.supabase_url}/rest/v1/user_profiles?id=eq.{user_id}",
            headers=headers_rw,
        )
        if student_id:
            await client.delete(f"{self.supabase_url}/rest/v1/students?id=eq.{student_id}", headers=headers_rw)
        if teacher_id:
            await client.delete(f"{self.supabase_url}/rest/v1/teachers?id=eq.{teacher_id}", headers=headers_rw)
        if entity_ids.get("employee_id"):
            await client.delete(f"{self.supabase_url}/rest/v1/employees?id=eq.{entity_ids['employee_id']}", headers=headers_rw)

        resp = await client.delete(
            f"{self.supabase_url}/auth/v1/admin/users/{user_id}",
            headers=self.supa_headers,
        )
        status = "✅" if resp.status_code in (200, 204) else "❌"
        print(f"    {status} User {user_id[:8]}… deleted")


async def main():
    parser = argparse.ArgumentParser(description="Seed test data for teachers and students")
    parser.add_argument("--cleanup-only", action="store_true", help="Only cleanup test data")
    parser.add_argument("--backend-url", default=BACKEND_URL, help=f"Backend URL (default: {BACKEND_URL})")

    args = parser.parse_args()

    seeder = LiveSeedTester(
        backend_url=args.backend_url,
        supabase_url=SUPABASE_URL,
        service_role_key=SERVICE_ROLE_KEY,
    )

    if args.cleanup_only:
        await seeder.cleanup()
        return

    success = await seeder.seed_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

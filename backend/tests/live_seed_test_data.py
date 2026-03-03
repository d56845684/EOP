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
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:2f8b5e9731c472a52f3d3068dc97d0d8@127.0.0.1:5432/postgres")

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
    def __init__(self, backend_url: str, database_url: str):
        self.backend_url = backend_url.rstrip("/")
        self.database_url = database_url
        self.data = CreatedData()
        self.all_user_ids: list[str] = []

        self.client_kwargs = {
            "follow_redirects": True,
            "timeout": httpx.Timeout(30.0, connect=10.0),
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

    async def _register_and_get_entity(self, register_data: dict, role: str) -> tuple[str, str, dict]:
        """註冊帳號，回傳 (user_id, entity_id, cookies)"""
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

            # Query entity ID via asyncpg
            import asyncpg
            conn = await asyncpg.connect(self.database_url)
            try:
                profile = await conn.fetchrow(
                    "SELECT student_id, teacher_id, employee_id FROM user_profiles WHERE id = $1::uuid",
                    user_id
                )
                entity_key = f"{role}_id" if role != "employee" else "employee_id"
                entity_id = str(profile[entity_key]) if profile and profile[entity_key] else None
            finally:
                await conn.close()

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

            # 設定 student_type = 'trial' via asyncpg
            import asyncpg
            conn = await asyncpg.connect(self.database_url)
            try:
                await conn.execute(
                    "UPDATE students SET student_type = $1 WHERE id = $2::uuid",
                    "trial", entity_id
                )
            finally:
                await conn.close()

            print(f"    ✅ {s['name']}（試上）| {email}")
            print(f"       user_id={user_id[:8]}… student_id={entity_id[:8]}… student_type=trial")

    # ========== 建立課程 ==========

    async def _seed_courses(self):
        async with httpx.AsyncClient(cookies=self.data.employee_cookies, **self.client_kwargs) as client:
            for c in COURSES:
                # 先嘗試找已存在的課程（含軟刪除），用 asyncpg 直連 DB
                import asyncpg
                conn = await asyncpg.connect(self.database_url)
                try:
                    existing = await conn.fetchrow(
                        "SELECT id, is_deleted FROM courses WHERE course_code = $1",
                        c['course_code']
                    )
                    if existing:
                        course_id = str(existing["id"])
                        if existing["is_deleted"]:
                            await conn.execute(
                                "UPDATE courses SET is_deleted = false, is_active = true WHERE id = $1",
                                existing["id"]
                            )
                            print(f"    ✅ {c['course_name']}（恢復已有課程）| id={course_id[:8]}…")
                        else:
                            print(f"    ✅ {c['course_name']}（已存在）| id={course_id[:8]}…")
                        self.data.course_ids.append(course_id)
                        continue
                finally:
                    await conn.close()

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

        try:
            import asyncpg
        except ImportError:
            print("⚠️  asyncpg not installed, skipping cleanup.")
            return

        try:
            conn = await asyncpg.connect(self.database_url)
        except Exception as e:
            print(f"  ❌ Failed to connect to database: {e}")
            return

        try:
            # Find all test_seed_ users
            test_users = await conn.fetch(
                "SELECT id, email FROM public.users WHERE email LIKE $1",
                f"{TEST_EMAIL_PREFIX}%"
            )

            if not test_users:
                print("  No seed test users found")
            else:
                print(f"  Found {len(test_users)} seed test user(s)")
                for user in test_users:
                    await self._delete_user_db(conn, user["id"], user["email"])

            # Soft-delete test courses
            for course_name in [c["course_name"] for c in COURSES]:
                result = await conn.execute(
                    "UPDATE courses SET is_deleted = true WHERE course_name = $1 AND is_deleted = false",
                    course_name
                )
                if "UPDATE" in result and result != "UPDATE 0":
                    print(f"    ✅ Soft-deleted course: {course_name}")

        except Exception as e:
            print(f"  ❌ Cleanup error: {e}")
        finally:
            await conn.close()

        print("\n✅ Cleanup completed\n")

    async def _delete_user_db(self, conn, user_id, email=""):
        """刪除用戶及其關聯資料（透過 asyncpg 直連 DB）"""
        print(f"  Deleting user {str(user_id)[:8]}... ({email})")

        # Get entity IDs from profile
        profile = await conn.fetchrow(
            "SELECT student_id, teacher_id, employee_id FROM user_profiles WHERE id = $1",
            user_id
        )

        student_id = profile["student_id"] if profile else None
        teacher_id = profile["teacher_id"] if profile else None
        employee_id = profile["employee_id"] if profile else None

        # Clean up student-related data
        if student_id:
            # Delete student contract details, teachers, leave records via contracts
            contracts = await conn.fetch(
                "SELECT id FROM student_contracts WHERE student_id = $1", student_id
            )
            for sc in contracts:
                await conn.execute("DELETE FROM student_contract_details WHERE student_contract_id = $1", sc["id"])
                await conn.execute("DELETE FROM student_contract_teachers WHERE student_contract_id = $1", sc["id"])
                await conn.execute("DELETE FROM student_contract_leave_records WHERE student_contract_id = $1", sc["id"])
                await conn.execute("DELETE FROM bookings WHERE student_contract_id = $1", sc["id"])
            await conn.execute("DELETE FROM student_contracts WHERE student_id = $1", student_id)
            await conn.execute("DELETE FROM bookings WHERE student_id = $1", student_id)

        # Clean up teacher-related data
        if teacher_id:
            contracts = await conn.fetch(
                "SELECT id FROM teacher_contracts WHERE teacher_id = $1", teacher_id
            )
            for tc in contracts:
                await conn.execute("DELETE FROM teacher_contract_details WHERE teacher_contract_id = $1", tc["id"])
                await conn.execute("DELETE FROM teacher_available_slots WHERE teacher_contract_id = $1", tc["id"])
            await conn.execute("DELETE FROM teacher_contracts WHERE teacher_id = $1", teacher_id)
            await conn.execute("DELETE FROM teacher_available_slots WHERE teacher_id = $1", teacher_id)

        # Delete user (CASCADE handles user_profiles, line_user_bindings)
        await conn.execute("DELETE FROM public.users WHERE id = $1", user_id)

        # Delete entity records (not in CASCADE)
        if student_id:
            await conn.execute("DELETE FROM students WHERE id = $1", student_id)
        if teacher_id:
            await conn.execute("DELETE FROM teachers WHERE id = $1", teacher_id)
        if employee_id:
            await conn.execute("DELETE FROM employees WHERE id = $1", employee_id)

        print(f"    ✅ User {str(user_id)[:8]}… deleted")


async def main():
    parser = argparse.ArgumentParser(description="Seed test data for teachers and students")
    parser.add_argument("--cleanup-only", action="store_true", help="Only cleanup test data")
    parser.add_argument("--backend-url", default=BACKEND_URL, help=f"Backend URL (default: {BACKEND_URL})")

    args = parser.parse_args()

    seeder = LiveSeedTester(
        backend_url=args.backend_url,
        database_url=DATABASE_URL,
    )

    if args.cleanup_only:
        await seeder.cleanup()
        return

    success = await seeder.seed_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

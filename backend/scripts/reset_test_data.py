"""
reset_test_data.py
==================
Hard-delete 所有測試資料（只保留 eopAdmin），重建乾淨的 teacher/student/employee 帳號。

執行方式：
    docker compose exec backend python scripts/reset_test_data.py
"""

import asyncio
import os
import uuid
from datetime import date, timedelta

import asyncpg
from passlib.hash import bcrypt as passlib_bcrypt

# ── 常數 ──────────────────────────────────────────────────────
EOP_ADMIN_USER_ID = "07c9f502-1bc0-4fe2-8974-9a75c81aa073"
EOP_ADMIN_EMPLOYEE_ID = "416f8d81-dab5-42e6-9458-bbf70425a329"

PASSWORD = "TestPassword123!"

# 固定 role UUID（與 migration 028 一致）
ROLE_IDS = {
    "admin": uuid.UUID("a0000000-0000-0000-0000-000000000001"),
    "employee": uuid.UUID("a0000000-0000-0000-0000-000000000002"),
    "teacher": uuid.UUID("a0000000-0000-0000-0000-000000000003"),
    "student": uuid.UUID("a0000000-0000-0000-0000-000000000004"),
}

NEW_ACCOUNTS = [
    {
        "role": "employee",
        "email": "employee@eop-test.com",
        "name": "Test Employee",
        "entity_no": "E001",
    },
    {
        "role": "teacher",
        "email": "teacher@eop-test.com",
        "name": "Test Teacher",
        "entity_no": "T001",
    },
    {
        "role": "student",
        "email": "student@eop-test.com",
        "name": "Test Student",
        "entity_no": "S001",
    },
]

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@db:5432/postgres",
)


# ── Step 1: Hard-delete ───────────────────────────────────────
async def hard_delete(conn: asyncpg.Connection) -> None:
    """刪除所有資料（eopAdmin 除外），按 FK 順序。"""
    print("\n=== Step 1: Hard-delete all data (except eopAdmin) ===")

    # Deletion order respects FK constraints.
    # bookings <-> substitute_details is circular, break it first.
    # bookings references teacher_available_slots, so slots must be deleted AFTER bookings.

    await conn.execute("UPDATE bookings SET substitute_detail_id = NULL")
    print("  [OK] Cleared bookings.substitute_detail_id")

    # Ordered deletion list: (table, where_clause or None)
    # Phase 1: tables referencing bookings / contracts
    # Phase 2: bookings itself
    # Phase 3: tables bookings referenced (slots, contract details)
    # Phase 4: contracts, courses, zoom
    # Phase 5: user-related (filtered)
    # Phase 6: profiles, entities, users
    delete_steps: list[tuple[str, str | None]] = [
        # ── Phase 1: leaf tables ──
        ("booking_details", None),
        ("zoom_meeting_logs", None),
        ("leave_records", None),
        ("substitute_details", None),
        ("teacher_bonus_records", None),
        ("student_teacher_preferences", None),
        ("student_contract_leave_records", None),
        ("student_contract_details", None),
        ("student_details", None),
        ("teacher_details", None),
        ("course_details", None),
        # ── Phase 2: bookings ──
        ("bookings", None),
        # ── Phase 3: tables that bookings referenced ──
        ("teacher_available_slots", None),
        ("teacher_contract_details", None),
        ("student_courses", None),
        # ── Phase 4: contracts, courses, zoom ──
        ("student_contracts", None),
        ("teacher_contracts", None),
        ("teacher_zoom_accounts", None),
        ("zoom_accounts", None),
        ("courses", None),
        # ── Phase 5: user-related ──
        ("line_notification_logs", f"user_id != '{EOP_ADMIN_USER_ID}'"),
        ("line_user_bindings", f"user_id != '{EOP_ADMIN_USER_ID}'"),
        ("user_page_overrides", f"user_id != '{EOP_ADMIN_USER_ID}'"),
        # ── Phase 6: profiles & entities ──
        ("user_profiles", f"id != '{EOP_ADMIN_USER_ID}'"),
        ("teachers", None),
        ("students", None),
        ("employees", f"id != '{EOP_ADMIN_EMPLOYEE_ID}'"),
        ("public.users", f"id != '{EOP_ADMIN_USER_ID}'"),
    ]

    for tbl, where in delete_steps:
        try:
            sql = f"DELETE FROM {tbl}"
            if where:
                sql += f" WHERE {where}"
            count = await conn.execute(sql)
            print(f"  [OK] {tbl}: {count}")
        except asyncpg.exceptions.UndefinedTableError:
            print(f"  [SKIP] {tbl}: table does not exist")

    print("  ✓ Hard-delete complete")


# ── Step 2: Rebuild test data ─────────────────────────────────
async def rebuild_test_data(conn: asyncpg.Connection) -> dict:
    """建立乾淨的 teacher / student / employee 帳號及基本資料。"""
    print("\n=== Step 2: Rebuild test data ===")

    hashed_pw = passlib_bcrypt.using(rounds=10).hash(PASSWORD)
    print(f"  Password hash generated (bcrypt, 10 rounds)")

    created = {}  # role -> {user_id, entity_id}

    for acct in NEW_ACCOUNTS:
        user_id = uuid.uuid4()
        entity_id = uuid.uuid4()
        role = acct["role"]
        email = acct["email"]
        name = acct["name"]
        entity_no = acct["entity_no"]

        # 1. Insert into public.users
        await conn.execute(
            """
            INSERT INTO public.users (id, email, encrypted_password, email_confirmed_at, raw_user_meta_data)
            VALUES ($1, $2, $3, NOW(), $4)
            """,
            user_id,
            email,
            hashed_pw,
            f'{{"name": "{name}", "role": "{role}"}}',
        )

        # 2. Create entity manually (so we control entity_no)
        role_id = ROLE_IDS[role]

        if role == "employee":
            await conn.execute(
                """
                INSERT INTO employees (id, employee_no, name, email, employee_type, hire_date, is_active)
                VALUES ($1, $2, $3, $4, 'full_time', CURRENT_DATE, TRUE)
                """,
                entity_id, entity_no, name, email,
            )
            await conn.execute(
                """
                INSERT INTO user_profiles (id, role_id, employee_id, employee_subtype, is_active)
                VALUES ($1, $2, $3, 'full_time', TRUE)
                """,
                user_id, role_id, entity_id,
            )
        elif role == "teacher":
            await conn.execute(
                """
                INSERT INTO teachers (id, teacher_no, name, email, is_active)
                VALUES ($1, $2, $3, $4, TRUE)
                """,
                entity_id, entity_no, name, email,
            )
            await conn.execute(
                """
                INSERT INTO user_profiles (id, role_id, teacher_id, is_active)
                VALUES ($1, $2, $3, TRUE)
                """,
                user_id, role_id, entity_id,
            )
        elif role == "student":
            await conn.execute(
                """
                INSERT INTO students (id, student_no, name, email, is_active)
                VALUES ($1, $2, $3, $4, TRUE)
                """,
                entity_id, entity_no, name, email,
            )
            await conn.execute(
                """
                INSERT INTO user_profiles (id, role_id, student_id, is_active)
                VALUES ($1, $2, $3, TRUE)
                """,
                user_id, role_id, entity_id,
            )

        created[role] = {"user_id": user_id, "entity_id": entity_id}
        print(f"  [OK] {role}: {email}  (user={user_id}, entity={entity_id})")

    # ── 額外測試資料 ──

    # Course: C001 一般課程
    course_id = uuid.uuid4()
    await conn.execute(
        """
        INSERT INTO courses (id, course_code, course_name, duration_minutes, is_active,
                             created_by, updated_by)
        VALUES ($1, 'C001', '一般課程', 50, TRUE, $2, $2)
        """,
        course_id,
        created["employee"]["entity_id"],
    )
    print(f"  [OK] course: C001 一般課程 ({course_id})")

    # Teacher contract (active)
    tc_id = uuid.uuid4()
    today = date.today()
    await conn.execute(
        """
        INSERT INTO teacher_contracts (id, contract_no, teacher_id, contract_status,
                                       start_date, end_date, employment_type,
                                       created_by, updated_by)
        VALUES ($1, 'TC-001', $2, 'active', $3, $4, 'hourly', $5, $5)
        """,
        tc_id,
        created["teacher"]["entity_id"],
        today,
        today + timedelta(days=365),
        created["employee"]["entity_id"],
    )
    # Teacher contract detail: course_rate for C001
    await conn.execute(
        """
        INSERT INTO teacher_contract_details (id, teacher_contract_id, detail_type,
                                              course_id, amount,
                                              created_by, updated_by)
        VALUES ($1, $2, 'course_rate', $3, 500, $4, $4)
        """,
        uuid.uuid4(),
        tc_id,
        course_id,
        created["employee"]["entity_id"],
    )
    print(f"  [OK] teacher_contract: TC-001 ({tc_id})")

    # Student contract (active, 10 lessons)
    # Note: course_id was removed from student_contracts in migration 005
    sc_id = uuid.uuid4()
    await conn.execute(
        """
        INSERT INTO student_contracts (id, contract_no, student_id,
                                       contract_status, start_date, end_date,
                                       total_lessons, remaining_lessons,
                                       created_by, updated_by)
        VALUES ($1, 'SC-001', $2, 'active', $3, $4, 10, 10, $5, $5)
        """,
        sc_id,
        created["student"]["entity_id"],
        today,
        today + timedelta(days=180),
        created["employee"]["entity_id"],
    )
    print(f"  [OK] student_contract: SC-001 ({sc_id})")

    # Student course
    await conn.execute(
        """
        INSERT INTO student_courses (id, student_id, course_id,
                                     created_by, updated_by)
        VALUES ($1, $2, $3, $4, $4)
        """,
        uuid.uuid4(),
        created["student"]["entity_id"],
        course_id,
        created["employee"]["entity_id"],
    )
    print(f"  [OK] student_course: S001 → C001")

    print("  ✓ Test data rebuild complete")
    return created


# ── Step 3: Flush Redis ───────────────────────────────────────
async def flush_redis() -> None:
    """清除 Redis 快取。"""
    print("\n=== Step 3: Flush Redis cache ===")
    try:
        import redis.asyncio as aioredis

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        redis_pw = os.getenv("REDIS_PASSWORD", None)
        r = aioredis.from_url(redis_url, password=redis_pw, decode_responses=True)
        await r.flushdb()
        await r.aclose()
        print("  [OK] Redis flushdb complete")
    except Exception as e:
        print(f"  [WARN] Redis flush failed (non-fatal): {e}")


# ── Main ──────────────────────────────────────────────────────
async def main() -> None:
    print("=" * 60)
    print("  EOP Test Data Reset Script")
    print("=" * 60)
    print(f"  Keeping: eopAdmin ({EOP_ADMIN_USER_ID})")
    print(f"  DB: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else DATABASE_URL}")

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        async with conn.transaction():
            await hard_delete(conn)
            created = await rebuild_test_data(conn)

        await flush_redis()

        # Summary
        print("\n" + "=" * 60)
        print("  DONE — New test accounts:")
        print("=" * 60)
        for acct in NEW_ACCOUNTS:
            role = acct["role"]
            info = created[role]
            print(f"  [{role.upper()}]")
            print(f"    Email:     {acct['email']}")
            print(f"    Password:  {PASSWORD}")
            print(f"    User ID:   {info['user_id']}")
            print(f"    Entity ID: {info['entity_id']}")
            print()
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

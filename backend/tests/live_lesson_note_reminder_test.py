#!/usr/bin/env python3
"""
Live test: lesson_note_reminder_service.scan_and_notify

直接在 backend container 內跑（需要 app 模組環境）。

設計：
  1. Setup — 直接 SQL 插入 3 筆測試 booking：
        13h 前結束（12-24h 窗口）
        16h 前結束（12-24h 窗口）
        26h 前結束（>=24h 窗口）
     都是 booking_status='confirmed' 且沒對應 lesson_notes。
  2. Run 1 — 呼叫 scan_and_notify()，預期：
        - 13h / 16h booking 觸發老師通知（count=1, last_teacher_notified_at set）
        - 26h booking 觸發 admin 通知 + 老師通知（hours_since>=24 也走 admin 路徑）
        - LINE 真實送出可能失敗（沒 binding），但 state 仍應寫入 reminders
  3. Run 2 — 立即重跑：
        - 老師通知都在 3h window 內 → 不再 increment
        - admin_notified_at 已設 → 不再重發 admin
  4. Setup B — 把某筆 reminder.last_teacher_notified_at 倒退 3.5h，重跑 → 應再次 increment
  5. Setup C — 為某筆 booking 補上 lesson_notes，重跑 → 透過 upload_lesson_note 沒走，
     直接 INSERT 不會自動寫 resolved_at；改測：cron 主查詢應自動跳過（LEFT JOIN ln IS NULL）
  6. Cleanup — 刪除所有測試 booking + reminders。

執行：
    docker exec teaching-platform-backend python tests/live_lesson_note_reminder_test.py
"""
import asyncio
import logging
import sys
import uuid
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# 讓 backend container 內的 app 模組可被找到（PYTHONPATH 已預設指向 /app）
from app.config import settings
from app.services.supabase_service import supabase_service
from app.services.lesson_note_reminder_service import lesson_note_reminder_service


TEST_TAG = f"lnr_test_{int(datetime.now().timestamp())}"
PASS = "✅"
FAIL = "❌"
INFO = "ℹ️ "


def log(msg: str) -> None:
    print(f"  {msg}")


def expect(cond: bool, label: str) -> bool:
    icon = PASS if cond else FAIL
    print(f"  {icon} {label}")
    return cond


async def fetch_seed_entities() -> dict | None:
    """從 DB 找一組可用的 teacher / student / course / teacher_contract / teacher_slot / user。"""
    row = await supabase_service.pool.fetchrow(
        """
        SELECT t.id AS teacher_id, s.id AS student_id, c.id AS course_id,
               tc.id AS teacher_contract_id, tas.id AS teacher_slot_id,
               (SELECT id FROM users LIMIT 1) AS any_user_id
        FROM teachers t, students s, courses c, teacher_contracts tc,
             teacher_available_slots tas
        WHERE t.is_deleted = FALSE AND s.is_deleted = FALSE AND c.is_deleted = FALSE
          AND tc.is_deleted = FALSE AND tc.teacher_id = t.id AND tas.teacher_id = t.id
        LIMIT 1
        """
    )
    if not row:
        return None
    return dict(row)


async def create_test_booking(seed: dict, hours_ago_end: float, label: str) -> str:
    """建立一筆 booking_status='confirmed' 的測試 booking，end_time 設定在 hours_ago_end 小時前。"""
    now = datetime.now()
    end_dt = now - timedelta(hours=hours_ago_end)
    start_dt = end_dt - timedelta(hours=1)
    booking_date = end_dt.date()

    # 對齊 30 分鐘邊界
    def _align(t):
        return t.replace(microsecond=0, second=0, minute=0 if t.minute < 30 else 30)

    start_time = _align(start_dt.time())
    end_time = _align(end_dt.time())

    bid = str(uuid.uuid4())
    booking_no = f"TST{label}{uuid.uuid4().hex[:8]}"[:50]

    await supabase_service.pool.execute(
        """
        INSERT INTO bookings (
            id, booking_no, student_id, teacher_id, course_id,
            teacher_contract_id, teacher_slot_id, teacher_hourly_rate,
            booking_status, booking_date, start_time, end_time, notes
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, 0, 'confirmed', $8, $9, $10, $11)
        """,
        bid, booking_no,
        seed["student_id"], seed["teacher_id"], seed["course_id"],
        seed["teacher_contract_id"], seed["teacher_slot_id"],
        booking_date, start_time, end_time, TEST_TAG,
    )
    log(f"{INFO}Created {label}: bid={bid[:8]}..., end={booking_date} {end_time} ({hours_ago_end:.0f}h ago)")
    return bid


async def get_reminder(booking_id: str) -> dict | None:
    row = await supabase_service.pool.fetchrow(
        "SELECT * FROM lesson_note_reminders WHERE booking_id = $1", booking_id
    )
    return dict(row) if row else None


async def print_reminders_state(booking_ids: list[tuple[str, str]]) -> None:
    for bid, label in booking_ids:
        r = await get_reminder(bid)
        if not r:
            log(f"{label}: <no row>")
        else:
            log(
                f"{label}: t_count={r['teacher_notified_count']} "
                f"t_last={r['last_teacher_notified_at']!s:.30s} "
                f"admin_at={r['admin_notified_at']!s:.30s} "
                f"resolved_at={r['resolved_at']}"
            )


async def cleanup(booking_ids: list[tuple[str, str]]) -> None:
    for bid, _ in booking_ids:
        await supabase_service.pool.execute(
            "DELETE FROM lesson_note_reminders WHERE booking_id = $1", bid
        )
        await supabase_service.pool.execute(
            "DELETE FROM lesson_notes WHERE booking_id = $1", bid
        )
        await supabase_service.pool.execute(
            "DELETE FROM bookings WHERE id = $1", bid
        )


async def main() -> int:
    print("==========================================")
    print("lesson_note_reminder_service live test")
    print(f"Test tag: {TEST_TAG}")
    print("==========================================\n")

    await supabase_service.connect(settings.DATABASE_URL)

    seed = await fetch_seed_entities()
    if not seed:
        print(f"{FAIL} 找不到 seed 資料（teacher/student/course/teacher_contract/teacher_slot），跳過測試")
        return 1
    log(f"{INFO}Seed: teacher={str(seed['teacher_id'])[:8]}.., student={str(seed['student_id'])[:8]}..")

    print("\n[Setup]")
    bid_13h = await create_test_booking(seed, 13, "h13")
    bid_16h = await create_test_booking(seed, 16, "h16")
    bid_26h = await create_test_booking(seed, 26, "h26")
    booking_ids = [(bid_13h, "13h"), (bid_16h, "16h"), (bid_26h, "26h")]

    all_passed = True
    try:
        print("\n[Run 1] scan_and_notify()")
        result1 = await lesson_note_reminder_service.scan_and_notify()
        log(f"{INFO}Result: {result1}")

        print("\n[State after Run 1]")
        await print_reminders_state(booking_ids)

        r13 = await get_reminder(bid_13h)
        r16 = await get_reminder(bid_16h)
        r26 = await get_reminder(bid_26h)

        all_passed &= expect(
            r13 is not None and r13["teacher_notified_count"] == 1,
            "13h booking: 老師通知計數=1",
        )
        all_passed &= expect(
            r13 is not None and r13["last_teacher_notified_at"] is not None,
            "13h booking: last_teacher_notified_at 已設",
        )
        all_passed &= expect(
            r13 is not None and r13["admin_notified_at"] is None,
            "13h booking: admin_notified_at 仍空（<24h）",
        )

        all_passed &= expect(
            r16 is not None and r16["teacher_notified_count"] == 1,
            "16h booking: 老師通知計數=1",
        )

        all_passed &= expect(
            r26 is not None and r26["admin_notified_at"] is not None,
            "26h booking: admin_notified_at 已設（>=24h）",
        )
        # 26h booking 因為 hours_since>=24, 不會進老師通知 branch
        all_passed &= expect(
            r26 is not None and (r26["teacher_notified_count"] or 0) == 0,
            "26h booking: 老師通知計數=0（>=24h 已轉 admin 通知）",
        )

        print("\n[Run 2] 立即重跑（測試 3h 節流）")
        result2 = await lesson_note_reminder_service.scan_and_notify()
        log(f"{INFO}Result: {result2}")

        print("\n[State after Run 2]")
        await print_reminders_state(booking_ids)

        r13_b = await get_reminder(bid_13h)
        r26_b = await get_reminder(bid_26h)

        all_passed &= expect(
            r13_b is not None and r13_b["teacher_notified_count"] == 1,
            "13h booking: 計數沒變（3h 節流生效）",
        )
        all_passed &= expect(
            r26_b is not None and r26_b["admin_notified_at"] == r26["admin_notified_at"],
            "26h booking: admin_notified_at 沒變（已通知過）",
        )

        print("\n[Setup B] 把 13h booking 的 last_teacher_notified_at 倒退 4h，重跑")
        await supabase_service.pool.execute(
            """
            UPDATE lesson_note_reminders
               SET last_teacher_notified_at = NOW() - INTERVAL '4 hours'
             WHERE booking_id = $1
            """,
            bid_13h,
        )
        result3 = await lesson_note_reminder_service.scan_and_notify()
        log(f"{INFO}Result: {result3}")
        r13_c = await get_reminder(bid_13h)
        all_passed &= expect(
            r13_c is not None and r13_c["teacher_notified_count"] == 2,
            "13h booking: 倒退 4h 後計數=2（節流通過）",
        )

        print("\n[Setup C] 為 16h booking 插入 lesson_notes，cron 應跳過")
        await supabase_service.pool.execute(
            """
            INSERT INTO lesson_notes (booking_id, google_doc_url, uploaded_by, status)
            VALUES ($1, 'https://docs.google.com/document/d/TEST', $2, 'pending_confirmation')
            """,
            bid_16h, seed["any_user_id"],
        )
        prev_16h = await get_reminder(bid_16h)
        result4 = await lesson_note_reminder_service.scan_and_notify()
        log(f"{INFO}Result: {result4}")
        r16_b = await get_reminder(bid_16h)
        all_passed &= expect(
            r16_b is not None and r16_b["teacher_notified_count"]
                == (prev_16h["teacher_notified_count"] if prev_16h else 0),
            "16h booking: 有 lesson_notes 後 cron 不再通知",
        )

        print("\n[Cancel test] 把 13h booking 設 cancelled，重跑應自動排除")
        await supabase_service.pool.execute(
            "UPDATE bookings SET booking_status = 'cancelled' WHERE id = $1", bid_13h
        )
        prev_13h = r13_c
        await lesson_note_reminder_service.scan_and_notify()
        r13_d = await get_reminder(bid_13h)
        all_passed &= expect(
            r13_d is not None and r13_d["teacher_notified_count"]
                == (prev_13h["teacher_notified_count"] if prev_13h else 0),
            "13h booking: cancelled 後不再增加通知計數",
        )
    finally:
        # uploaded_by FK 限制：lesson_notes 引用 users.id，但我們塞了 teacher_id 進去
        # 可能導致 cleanup 出錯，但因為 ON DELETE CASCADE，刪 bookings 會連帶清掉
        print("\n[Cleanup]")
        try:
            await cleanup(booking_ids)
            log(f"{PASS}清理 {len(booking_ids)} 筆測試資料")
        except Exception as e:
            log(f"{FAIL}清理失敗: {e}")
            all_passed = False

    print("\n==========================================")
    print(f"{'PASS' if all_passed else 'FAIL'}")
    print("==========================================")
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

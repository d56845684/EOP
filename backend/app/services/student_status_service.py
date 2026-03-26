"""
學生狀態自動同步服務

根據合約狀態決定學生狀態：
  trial     → 試上（student_type='trial'，無合約）
  active    → 上課中（有 active 合約）
  suspended → 暫停（有 suspended 合約，無 active）
  extended  → 展延（有 active addendum，原合約已過期但展延中）
  terminated→ 解約（最近合約被 terminated）
  completed → 已結業（所有合約都 expired/completed，無 active/suspended/pending）
"""

import logging
from datetime import date
from app.services.supabase_service import supabase_service

logger = logging.getLogger(__name__)


async def sync_student_status(student_id: str):
    """根據該學生所有合約的狀態，自動更新 students.student_status"""
    try:
        import uuid as _uuid
        sid = _uuid.UUID(student_id) if isinstance(student_id, str) else student_id

        # 查學生基本資料
        student = await supabase_service.pool.fetchrow(
            "SELECT student_type, student_status FROM students WHERE id = $1 AND is_deleted = FALSE",
            sid,
        )
        if not student:
            return

        # 試上學生不做合約狀態同步
        if student["student_type"] == "trial":
            if student["student_status"] != "trial":
                await supabase_service.pool.execute(
                    "UPDATE students SET student_status = 'trial' WHERE id = $1", sid
                )
            return

        # 查所有合約狀態
        contracts = await supabase_service.pool.fetch(
            """SELECT contract_status, end_date
               FROM student_contracts
               WHERE student_id = $1 AND is_deleted = FALSE""",
            sid,
        )

        if not contracts:
            # 正式學生但無合約 → completed
            new_status = "completed"
        else:
            statuses = [c["contract_status"] for c in contracts]

            if "active" in statuses:
                # 檢查是否有展延（active 合約的 end_date 已過但有 active addendum）
                has_extension = False
                for c in contracts:
                    if c["contract_status"] == "active" and c["end_date"]:
                        end = c["end_date"] if isinstance(c["end_date"], date) else date.fromisoformat(str(c["end_date"]))
                        if end < date.today():
                            has_extension = True
                            break
                new_status = "extended" if has_extension else "active"
            elif "suspended" in statuses:
                new_status = "suspended"
            elif "terminated" in statuses and "pending" not in statuses:
                new_status = "terminated"
            elif "pending" in statuses:
                new_status = "pending"  # 有待生效合約 → 待開課
            else:
                # 全部 expired
                new_status = "completed"

        if student["student_status"] != new_status:
            await supabase_service.pool.execute(
                "UPDATE students SET student_status = $1 WHERE id = $2",
                new_status, sid,
            )
            logger.info(f"Student {student_id}: 狀態同步 {student['student_status']} → {new_status}")

    except Exception as e:
        logger.warning(f"Student {student_id}: 狀態同步失敗: {e}")

"""
學生教師偏好服務 — 偏好白名單計算與等級驗證
"""
import uuid as _uuid
from fastapi import HTTPException
from app.services.supabase_service import supabase_service


class PreferenceService:
    """學生教師偏好相關的核心業務邏輯"""

    async def get_student_allowed_teachers(self, student_id: str) -> tuple[set[str], bool]:
        """取得學生所有偏好設定的教師聯集（已優化：單次 SQL 取代三層巢狀迴圈）

        等級向下兼容：選 level 2 → 可選 level 1 和 2 的教師（teacher_level <= 偏好值）

        情境 1: primary_teacher_id 有值 → 直接加入該教師
        情境 2: course_id=NULL + min_teacher_level → 全域等級過濾（向下兼容）
        情境 3: course_id=X  + min_teacher_level → 指定課程等級過濾（向下兼容）

        Returns:
            (allowed_set, has_preferences)
        """
        pool = supabase_service.pool
        sid = _uuid.UUID(student_id) if isinstance(student_id, str) else student_id

        all_prefs = await pool.fetch(
            """SELECT id, min_teacher_level, primary_teacher_id, course_id
               FROM student_teacher_preferences
               WHERE student_id = $1 AND is_deleted = FALSE""",
            sid,
        )

        if not all_prefs:
            return set(), False

        allowed: set[str] = set()

        # 分類偏好
        primary_ids = []
        global_min_levels = []
        course_prefs = []  # [(min_level, course_id)]

        for pref in all_prefs:
            primary = pref["primary_teacher_id"]
            min_level = pref["min_teacher_level"] or 1
            pref_course_id = pref["course_id"]

            if primary:
                primary_ids.append(primary)
            elif pref_course_id:
                course_prefs.append((min_level, pref_course_id))
            else:
                global_min_levels.append(min_level)

        # 情境 1: 指定教師 → 直接加入
        for pid in primary_ids:
            allowed.add(str(pid))

        # 情境 2: 全域等級過濾 → 一次查詢（向下兼容：等級 <= 偏好值）
        if global_min_levels:
            max_level_val = max(global_min_levels)  # 取最寬鬆的等級（向下兼容取最高）
            rows = await pool.fetch(
                """SELECT id FROM teachers
                   WHERE is_deleted = FALSE AND is_active = TRUE AND teacher_level <= $1""",
                max_level_val,
            )
            for r in rows:
                allowed.add(str(r["id"]))

        # 情境 3: 指定課程 + 等級 → 單一 SQL 搞定（取代三層巢狀）
        if course_prefs:
            for min_level, cid in course_prefs:
                rows = await pool.fetch(
                    """SELECT DISTINCT t.id
                       FROM teachers t
                       JOIN teacher_contracts tc ON tc.teacher_id = t.id
                           AND tc.is_deleted = FALSE AND tc.contract_status = 'active'
                       JOIN teacher_contract_details tcd ON tcd.teacher_contract_id = tc.id
                           AND tcd.course_id = $1 AND tcd.detail_type = 'course_rate'
                           AND tcd.is_deleted = FALSE
                       WHERE t.is_deleted = FALSE AND t.is_active = TRUE AND t.teacher_level <= $2""",
                    cid, min_level,
                )
                for r in rows:
                    allowed.add(str(r["id"]))

        return allowed, True

    async def validate_teacher_level_for_course(
        self, student_id: str, teacher_id: str, course_id: str, teacher_level: int
    ) -> None:
        """驗證教師等級是否符合學生偏好（主要教師不受等級限制）

        Raises:
            HTTPException 400 if teacher level exceeds preference
        """
        pref_list = await supabase_service.table_select(
            table="student_teacher_preferences",
            select="id,primary_teacher_id,min_teacher_level",
            filters={
                "student_id": student_id,
                "course_id": f"eq.{course_id}",
                "is_deleted": "eq.false"
            },
        )
        pref = pref_list[0] if pref_list else None
        if pref:
            is_primary = pref.get("primary_teacher_id") == teacher_id
            if not is_primary:
                max_level = pref.get("min_teacher_level", 1)
                if teacher_level > max_level:
                    raise HTTPException(
                        status_code=400,
                        detail=f"教師等級 ({teacher_level}) 超過學生偏好的最高等級 ({max_level})"
                    )


preference_service = PreferenceService()

import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException

from app.services.preference_service import PreferenceService


@pytest.fixture
def service():
    return PreferenceService()


@pytest.fixture
def student_id():
    return str(uuid.uuid4())


def _record(**kwargs):
    """建立模擬的 asyncpg Record（dict-like）"""
    return kwargs


@pytest.mark.asyncio
class TestGetStudentAllowedTeachers:
    """get_student_allowed_teachers 測試"""

    async def test_no_preferences_returns_empty(self, service, student_id):
        """無偏好設定 → 空集合, False"""
        mock_pool = MagicMock()
        mock_pool.fetch = AsyncMock(return_value=[])

        with patch("app.services.preference_service.supabase_service") as mock_svc:
            mock_svc.pool = mock_pool
            result, has_prefs = await service.get_student_allowed_teachers(student_id)

        assert result == set()
        assert has_prefs is False

    async def test_scenario1_primary_teacher(self, service, student_id):
        """情境 1: primary_teacher_id 指定教師 → 直接加入白名單"""
        teacher_id = str(uuid.uuid4())
        prefs = [_record(
            id=uuid.uuid4(),
            min_teacher_level=None,
            primary_teacher_id=uuid.UUID(teacher_id),
            course_id=None,
        )]

        mock_pool = MagicMock()
        mock_pool.fetch = AsyncMock(return_value=prefs)

        with patch("app.services.preference_service.supabase_service") as mock_svc:
            mock_svc.pool = mock_pool
            result, has_prefs = await service.get_student_allowed_teachers(student_id)

        assert teacher_id in result
        assert has_prefs is True

    async def test_scenario2_global_level_filter(self, service, student_id):
        """情境 2: 全域等級過濾 → 查詢 teacher_level <= N 的教師"""
        t1 = str(uuid.uuid4())
        t2 = str(uuid.uuid4())

        prefs = [_record(
            id=uuid.uuid4(),
            min_teacher_level=2,
            primary_teacher_id=None,
            course_id=None,
        )]
        level_teachers = [_record(id=uuid.UUID(t1)), _record(id=uuid.UUID(t2))]

        mock_pool = MagicMock()
        mock_pool.fetch = AsyncMock(side_effect=[prefs, level_teachers])

        with patch("app.services.preference_service.supabase_service") as mock_svc:
            mock_svc.pool = mock_pool
            result, has_prefs = await service.get_student_allowed_teachers(student_id)

        assert t1 in result
        assert t2 in result
        assert has_prefs is True
        # 驗證第二次 SQL 用了 max level
        call_args = mock_pool.fetch.call_args_list[1]
        assert call_args[0][1] == 2  # max_level_val

    async def test_scenario3_course_level_filter(self, service, student_id):
        """情境 3: 指定課程 + 等級過濾"""
        course_id = uuid.uuid4()
        t1 = str(uuid.uuid4())

        prefs = [_record(
            id=uuid.uuid4(),
            min_teacher_level=3,
            primary_teacher_id=None,
            course_id=course_id,
        )]
        course_teachers = [_record(id=uuid.UUID(t1))]

        mock_pool = MagicMock()
        mock_pool.fetch = AsyncMock(side_effect=[prefs, course_teachers])

        with patch("app.services.preference_service.supabase_service") as mock_svc:
            mock_svc.pool = mock_pool
            result, has_prefs = await service.get_student_allowed_teachers(student_id)

        assert t1 in result
        assert has_prefs is True
        # 驗證 SQL 參數: course_id 和 min_level
        call_args = mock_pool.fetch.call_args_list[1]
        assert call_args[0][1] == course_id
        assert call_args[0][2] == 3

    async def test_mixed_scenarios_union(self, service, student_id):
        """三種情境混合 → 結果取聯集"""
        primary_tid = str(uuid.uuid4())
        level_tid = str(uuid.uuid4())
        course_tid = str(uuid.uuid4())
        course_id = uuid.uuid4()

        prefs = [
            _record(id=uuid.uuid4(), min_teacher_level=None,
                    primary_teacher_id=uuid.UUID(primary_tid), course_id=None),
            _record(id=uuid.uuid4(), min_teacher_level=2,
                    primary_teacher_id=None, course_id=None),
            _record(id=uuid.uuid4(), min_teacher_level=1,
                    primary_teacher_id=None, course_id=course_id),
        ]
        level_teachers = [_record(id=uuid.UUID(level_tid))]
        course_teachers = [_record(id=uuid.UUID(course_tid))]

        mock_pool = MagicMock()
        mock_pool.fetch = AsyncMock(side_effect=[prefs, level_teachers, course_teachers])

        with patch("app.services.preference_service.supabase_service") as mock_svc:
            mock_svc.pool = mock_pool
            result, has_prefs = await service.get_student_allowed_teachers(student_id)

        assert primary_tid in result
        assert level_tid in result
        assert course_tid in result
        assert len(result) == 3
        assert has_prefs is True


@pytest.mark.asyncio
class TestValidateTeacherLevelForCourse:
    """validate_teacher_level_for_course 測試"""

    async def test_no_preference_passes(self, service, student_id):
        """無偏好設定 → 不阻擋"""
        with patch("app.services.preference_service.supabase_service") as mock_svc:
            mock_svc.table_select = AsyncMock(return_value=[])
            # 不應拋出例外
            await service.validate_teacher_level_for_course(
                student_id=student_id,
                teacher_id=str(uuid.uuid4()),
                course_id=str(uuid.uuid4()),
                teacher_level=5,
            )

    async def test_primary_teacher_bypasses_level_check(self, service, student_id):
        """主要教師 → 不受等級限制"""
        teacher_id = str(uuid.uuid4())

        with patch("app.services.preference_service.supabase_service") as mock_svc:
            mock_svc.table_select = AsyncMock(return_value=[{
                "id": str(uuid.uuid4()),
                "primary_teacher_id": teacher_id,
                "min_teacher_level": 1,
            }])
            # teacher_level=99 但是主要教師，不應阻擋
            await service.validate_teacher_level_for_course(
                student_id=student_id,
                teacher_id=teacher_id,
                course_id=str(uuid.uuid4()),
                teacher_level=99,
            )

    async def test_non_primary_within_level_passes(self, service, student_id):
        """非主要教師，等級在範圍內 → 通過"""
        with patch("app.services.preference_service.supabase_service") as mock_svc:
            mock_svc.table_select = AsyncMock(return_value=[{
                "id": str(uuid.uuid4()),
                "primary_teacher_id": str(uuid.uuid4()),  # 不同教師
                "min_teacher_level": 3,
            }])
            await service.validate_teacher_level_for_course(
                student_id=student_id,
                teacher_id=str(uuid.uuid4()),  # 不同的教師
                course_id=str(uuid.uuid4()),
                teacher_level=2,  # <= 3, 通過
            )

    async def test_non_primary_exceeds_level_raises(self, service, student_id):
        """非主要教師，等級超過 → 拋出 400"""
        with patch("app.services.preference_service.supabase_service") as mock_svc:
            mock_svc.table_select = AsyncMock(return_value=[{
                "id": str(uuid.uuid4()),
                "primary_teacher_id": str(uuid.uuid4()),
                "min_teacher_level": 2,
            }])
            with pytest.raises(HTTPException) as exc_info:
                await service.validate_teacher_level_for_course(
                    student_id=student_id,
                    teacher_id=str(uuid.uuid4()),
                    course_id=str(uuid.uuid4()),
                    teacher_level=5,  # > 2, 應阻擋
                )
            assert exc_info.value.status_code == 400
            assert "超過學生偏好的最高等級" in exc_info.value.detail

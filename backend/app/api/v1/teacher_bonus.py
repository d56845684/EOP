from fastapi import APIRouter, Depends, Query, HTTPException
from app.services.supabase_service import supabase_service
from app.core.dependencies import get_current_user, CurrentUser, require_staff, get_user_employee_id
from app.schemas.teacher_bonus import (
    TeacherBonusCreate, TeacherBonusUpdate,
    TeacherBonusResponse, TeacherBonusListResponse,
)
from app.schemas.response import BaseResponse, DataResponse
from typing import Optional
from datetime import datetime, date
import math

router = APIRouter(prefix="/teacher-bonus", tags=["教師獎金管理"])

BONUS_SELECT = "id,teacher_id,bonus_type,amount,bonus_date,description,related_student_id,related_booking_id,notes,created_at,created_by,updated_at"


async def enrich_bonus(record: dict) -> dict:
    """加入 teacher_name, student_name"""
    # teacher_name
    try:
        teachers = await supabase_service.table_select(
            table="teachers", select="name",
            filters={"id": record["teacher_id"]},
            use_service_key=True
        )
        if teachers:
            record["teacher_name"] = teachers[0].get("name")
    except Exception:
        pass
    # student_name
    if record.get("related_student_id"):
        try:
            students = await supabase_service.table_select(
                table="students", select="name",
                filters={"id": record["related_student_id"]},
                use_service_key=True
            )
            if students:
                record["student_name"] = students[0].get("name")
        except Exception:
            pass
    return record


@router.get("", response_model=TeacherBonusListResponse)
async def list_teacher_bonus(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    teacher_id: Optional[str] = Query(None, description="教師 ID"),
    bonus_type: Optional[str] = Query(None, description="獎金類型"),
    date_from: Optional[str] = Query(None, description="起始日期 (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="結束日期 (YYYY-MM-DD)"),
    current_user: CurrentUser = Depends(get_current_user)
):
    """取得教師獎金列表（老師只看自己、員工看全部）"""
    try:
        filters: dict = {"is_deleted": "eq.false"}

        # 老師只能看自己的
        is_staff = current_user.role in ("admin", "employee")
        if not is_staff:
            # 查出 teacher_id
            profiles = await supabase_service.table_select(
                table="user_profiles", select="teacher_id",
                filters={"id": current_user.user_id},
                use_service_key=True
            )
            if profiles and profiles[0].get("teacher_id"):
                filters["teacher_id"] = f"eq.{profiles[0]['teacher_id']}"
            else:
                return TeacherBonusListResponse()

        if teacher_id:
            filters["teacher_id"] = f"eq.{teacher_id}"
        if bonus_type:
            filters["bonus_type"] = f"eq.{bonus_type}"
        if date_from:
            filters["bonus_date"] = f"gte.{date_from}"
        if date_to:
            # 若已有 bonus_date filter (gte)，需用不同 key
            if "bonus_date" in filters:
                filters["bonus_date"] = filters["bonus_date"]  # keep gte
                # postgrest 不支援同 key 兩個 filter，改用 and 策略
                # 改用 range filter 方式
                filters.pop("bonus_date")
                filters["bonus_date"] = f"gte.{date_from}"
                # 額外加一個 lte filter — 使用 postgrest 的 and syntax 不適用這裡
                # 用 select 後 python filter 代替
            else:
                filters["bonus_date"] = f"lte.{date_to}"

        # 取 total
        all_records = await supabase_service.table_select(
            table="teacher_bonus_records", select="id",
            filters=filters, use_service_key=True
        )

        # 若有 date_to 且同時有 date_from，在 python 端過濾
        if date_from and date_to:
            # 重新查帶完整 filter
            filters_count = {"is_deleted": "eq.false"}
            if teacher_id:
                filters_count["teacher_id"] = f"eq.{teacher_id}"
            if bonus_type:
                filters_count["bonus_type"] = f"eq.{bonus_type}"
            if not is_staff and profiles and profiles[0].get("teacher_id"):
                filters_count["teacher_id"] = f"eq.{profiles[0]['teacher_id']}"
            filters_count["bonus_date"] = f"gte.{date_from}"
            all_gte = await supabase_service.table_select(
                table="teacher_bonus_records", select="id,bonus_date",
                filters=filters_count, use_service_key=True
            )
            all_records = [r for r in all_gte if r.get("bonus_date", "") <= date_to]
            filters = filters_count

        total = len(all_records)
        total_pages = math.ceil(total / per_page) if total > 0 else 1
        offset = (page - 1) * per_page

        records = await supabase_service.table_select_with_pagination(
            table="teacher_bonus_records", select=BONUS_SELECT,
            filters=filters, order_by="bonus_date.desc,created_at.desc",
            limit=per_page, offset=offset, use_service_key=True
        )

        # python-side date_to filter
        if date_from and date_to:
            records = [r for r in records if r.get("bonus_date", "") <= date_to]

        # enrich
        enriched = []
        for r in records:
            enriched.append(TeacherBonusResponse(**(await enrich_bonus(r))))

        return TeacherBonusListResponse(
            data=enriched,
            total=total, page=page, per_page=per_page, total_pages=total_pages
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得教師獎金列表失敗: {str(e)}")


@router.get("/{bonus_id}", response_model=DataResponse[TeacherBonusResponse])
async def get_teacher_bonus(
    bonus_id: str,
    current_user: CurrentUser = Depends(get_current_user)
):
    """取得單筆教師獎金"""
    try:
        result = await supabase_service.table_select(
            table="teacher_bonus_records", select=BONUS_SELECT,
            filters={"id": bonus_id, "is_deleted": "eq.false"},
            use_service_key=True
        )
        if not result:
            raise HTTPException(status_code=404, detail="獎金紀錄不存在")
        enriched = await enrich_bonus(result[0])
        return DataResponse(data=TeacherBonusResponse(**enriched))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得教師獎金失敗: {str(e)}")


@router.post("", response_model=DataResponse[TeacherBonusResponse])
async def create_teacher_bonus(
    data: TeacherBonusCreate,
    current_user: CurrentUser = Depends(require_staff)
):
    """新增教師獎金紀錄（僅限員工）"""
    try:
        # 驗證教師存在
        teachers = await supabase_service.table_select(
            table="teachers", select="id",
            filters={"id": data.teacher_id, "is_deleted": "eq.false"},
            use_service_key=True
        )
        if not teachers:
            raise HTTPException(status_code=404, detail="教師不存在")

        bonus_data: dict = {
            "teacher_id": data.teacher_id,
            "bonus_type": data.bonus_type.value,
            "amount": data.amount,
            "bonus_date": (data.bonus_date or date.today()).isoformat(),
        }
        if data.description is not None:
            bonus_data["description"] = data.description
        if data.related_student_id is not None:
            bonus_data["related_student_id"] = data.related_student_id
        if data.related_booking_id is not None:
            bonus_data["related_booking_id"] = data.related_booking_id
        if data.notes is not None:
            bonus_data["notes"] = data.notes

        employee_id = await get_user_employee_id(current_user.user_id)
        if employee_id:
            bonus_data["created_by"] = employee_id

        result = await supabase_service.table_insert(
            table="teacher_bonus_records", data=bonus_data, use_service_key=True
        )
        if not result:
            raise HTTPException(status_code=500, detail="新增教師獎金失敗")

        enriched = await enrich_bonus(result)
        return DataResponse(message="教師獎金新增成功", data=TeacherBonusResponse(**enriched))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"新增教師獎金失敗: {str(e)}")


@router.put("/{bonus_id}", response_model=DataResponse[TeacherBonusResponse])
async def update_teacher_bonus(
    bonus_id: str,
    data: TeacherBonusUpdate,
    current_user: CurrentUser = Depends(require_staff)
):
    """更新教師獎金紀錄（僅限員工）"""
    try:
        existing = await supabase_service.table_select(
            table="teacher_bonus_records", select="id",
            filters={"id": bonus_id, "is_deleted": "eq.false"},
            use_service_key=True
        )
        if not existing:
            raise HTTPException(status_code=404, detail="獎金紀錄不存在")

        update_data: dict = {}
        if data.bonus_type is not None:
            update_data["bonus_type"] = data.bonus_type.value
        if data.amount is not None:
            update_data["amount"] = data.amount
        if data.bonus_date is not None:
            update_data["bonus_date"] = data.bonus_date.isoformat()
        if data.description is not None:
            update_data["description"] = data.description
        if data.related_student_id is not None:
            update_data["related_student_id"] = data.related_student_id
        if data.related_booking_id is not None:
            update_data["related_booking_id"] = data.related_booking_id
        if data.notes is not None:
            update_data["notes"] = data.notes

        if not update_data:
            raise HTTPException(status_code=400, detail="沒有要更新的資料")

        employee_id = await get_user_employee_id(current_user.user_id)
        if employee_id:
            update_data["updated_by"] = employee_id

        result = await supabase_service.table_update(
            table="teacher_bonus_records", data=update_data,
            filters={"id": bonus_id}, use_service_key=True
        )
        if not result:
            raise HTTPException(status_code=500, detail="更新教師獎金失敗")

        enriched = await enrich_bonus(result)
        return DataResponse(message="教師獎金更新成功", data=TeacherBonusResponse(**enriched))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新教師獎金失敗: {str(e)}")


@router.delete("/{bonus_id}", response_model=BaseResponse)
async def delete_teacher_bonus(
    bonus_id: str,
    current_user: CurrentUser = Depends(require_staff)
):
    """軟刪除教師獎金紀錄（僅限員工）"""
    try:
        existing = await supabase_service.table_select(
            table="teacher_bonus_records", select="id",
            filters={"id": bonus_id, "is_deleted": "eq.false"},
            use_service_key=True
        )
        if not existing:
            raise HTTPException(status_code=404, detail="獎金紀錄不存在")

        employee_id = await get_user_employee_id(current_user.user_id)
        delete_data: dict = {
            "is_deleted": True,
            "deleted_at": datetime.utcnow().isoformat(),
        }
        if employee_id:
            delete_data["deleted_by"] = employee_id

        result = await supabase_service.table_update(
            table="teacher_bonus_records", data=delete_data,
            filters={"id": bonus_id}, use_service_key=True
        )
        if not result:
            raise HTTPException(status_code=500, detail="刪除教師獎金失敗")

        return BaseResponse(message="教師獎金刪除成功")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刪除教師獎金失敗: {str(e)}")


# ========== Options ==========

@router.get("/options/teachers")
async def get_teacher_options(
    current_user: CurrentUser = Depends(get_current_user)
):
    """取得教師下拉選項"""
    try:
        teachers = await supabase_service.table_select(
            table="teachers", select="id,teacher_no,name",
            filters={"is_deleted": "eq.false", "is_active": "eq.true"},
            use_service_key=True
        )
        return {"data": teachers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得教師選項失敗: {str(e)}")

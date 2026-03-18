from fastapi import APIRouter, Depends, Query, HTTPException
from app.services.supabase_service import supabase_service
from app.core.dependencies import get_current_user, CurrentUser, require_page_permission, get_user_employee_id
from app.schemas.substitute_detail import (
    SubstituteDetailCreate, SubstituteDetailResponse, SubstituteDetailListResponse
)
from app.schemas.response import BaseResponse, DataResponse
from typing import Optional
from datetime import datetime
import math
import logging

router = APIRouter(prefix="/substitute-details", tags=["代課管理"])
logger = logging.getLogger(__name__)


async def enrich_substitute_detail(record: dict) -> dict:
    """為代課紀錄添加關聯名稱"""
    # 代課教師名稱
    if record.get("substitute_teacher_id"):
        teacher = await supabase_service.table_select(
            table="teachers", select="name",
            filters={"id": record["substitute_teacher_id"]},
        )
        record["substitute_teacher_name"] = teacher[0]["name"] if teacher else None
    else:
        record["substitute_teacher_name"] = None

    # 預約編號 + 原教師名稱
    if record.get("booking_id"):
        booking = await supabase_service.table_select(
            table="bookings", select="booking_no,teacher_id",
            filters={"id": record["booking_id"]},
        )
        if booking:
            record["booking_no"] = booking[0].get("booking_no")
            # 原教師名稱
            if booking[0].get("teacher_id"):
                orig_teacher = await supabase_service.table_select(
                    table="teachers", select="name",
                    filters={"id": booking[0]["teacher_id"]},
                )
                record["original_teacher_name"] = orig_teacher[0]["name"] if orig_teacher else None
            else:
                record["original_teacher_name"] = None
        else:
            record["booking_no"] = None
            record["original_teacher_name"] = None
    else:
        record["booking_no"] = None
        record["original_teacher_name"] = None

    return record


@router.post("", response_model=DataResponse[SubstituteDetailResponse])
async def create_substitute_detail(
    data: SubstituteDetailCreate,
    current_user: CurrentUser = Depends(require_page_permission("bookings.edit"))
):
    """指派代課（僅限員工）"""
    try:
        if not current_user.is_staff():
            raise HTTPException(status_code=403, detail="僅限員工指派代課")

        # 驗證預約存在且為 confirmed
        booking = await supabase_service.table_select(
            table="bookings",
            select="id,booking_status,teacher_id,booking_date,start_time,end_time,course_id,substitute_detail_id",
            filters={"id": data.booking_id, "is_deleted": "eq.false"},
        )
        if not booking:
            raise HTTPException(status_code=404, detail="預約不存在")
        if booking[0].get("booking_status") != "confirmed":
            raise HTTPException(status_code=400, detail="只有已確認的預約可以指派代課")
        if booking[0].get("substitute_detail_id"):
            raise HTTPException(status_code=400, detail="此預約已有代課紀錄")

        # 不能指派原教師自己
        if data.substitute_teacher_id == booking[0].get("teacher_id"):
            raise HTTPException(status_code=400, detail="不能指派原教師自己為代課教師")

        # 驗證代課教師存在
        sub_teacher = await supabase_service.table_select(
            table="teachers", select="id,name",
            filters={"id": data.substitute_teacher_id, "is_deleted": "eq.false", "is_active": "eq.true"},
        )
        if not sub_teacher:
            raise HTTPException(status_code=400, detail="代課教師不存在或未啟用")

        # 驗證代課教師在該日有涵蓋時段的 slot
        booking_date = booking[0].get("booking_date")
        booking_start = booking[0].get("start_time", "")[:5]
        booking_end = booking[0].get("end_time", "")[:5]
        course_id = booking[0].get("course_id")

        slots = await supabase_service.table_select(
            table="teacher_available_slots",
            select="id,start_time,end_time",
            filters={
                "teacher_id": data.substitute_teacher_id,
                "slot_date": f"eq.{booking_date}",
                "is_deleted": "eq.false",
                "is_available": "eq.true",
            },
        )
        has_covering_slot = any(
            s.get("start_time", "")[:5] <= booking_start
            and s.get("end_time", "")[:5] >= booking_end
            for s in slots
        )
        if not has_covering_slot:
            raise HTTPException(status_code=400, detail="代課教師在該時段沒有可用的預約時段")

        # 驗證代課教師合約存在且有效
        sub_contract = await supabase_service.table_select(
            table="teacher_contracts", select="id",
            filters={"id": data.substitute_contract_id, "is_deleted": "eq.false", "contract_status": "eq.active"},
        )
        if not sub_contract:
            raise HTTPException(status_code=400, detail="代課教師合約不存在或非有效狀態")

        # 驗證代課教師合約有該課程的 course_rate
        if course_id:
            course_rate = await supabase_service.table_select(
                table="teacher_contract_details",
                select="id",
                filters={
                    "teacher_contract_id": data.substitute_contract_id,
                    "course_id": course_id,
                    "detail_type": "eq.course_rate",
                    "is_deleted": "eq.false",
                },
            )
            if not course_rate:
                raise HTTPException(status_code=400, detail="代課教師合約未包含此課程")

        # 檢查代課教師同日同時段是否有其他預約（時間衝突）

        # 查代課教師當天所有有效預約
        teacher_bookings = await supabase_service.table_select(
            table="bookings",
            select="id,start_time,end_time,booking_status",
            filters={
                "teacher_id": f"eq.{data.substitute_teacher_id}",
                "booking_date": f"eq.{booking_date}",
                "is_deleted": "eq.false",
            },
        )
        for tb in teacher_bookings:
            if tb.get("booking_status") in ("cancelled",):
                continue
            tb_start = tb.get("start_time", "")[:5]
            tb_end = tb.get("end_time", "")[:5]
            if booking_start < tb_end and booking_end > tb_start:
                raise HTTPException(
                    status_code=409,
                    detail=f"代課教師在 {booking_date} {tb_start}-{tb_end} 已有預約，時間衝突"
                )

        # 也檢查代課教師作為代課者的其他預約是否衝突
        existing_subs = await supabase_service.table_select(
            table="substitute_details",
            select="id,booking_id",
            filters={
                "substitute_teacher_id": f"eq.{data.substitute_teacher_id}",
                "is_deleted": "eq.false",
            },
        )
        for sub in existing_subs:
            sub_booking = await supabase_service.table_select(
                table="bookings",
                select="id,booking_date,start_time,end_time,booking_status",
                filters={"id": sub["booking_id"], "is_deleted": "eq.false"},
            )
            if sub_booking:
                sb = sub_booking[0]
                if sb.get("booking_status") in ("cancelled",):
                    continue
                if sb.get("booking_date") != booking_date:
                    continue
                sb_start = sb.get("start_time", "")[:5]
                sb_end = sb.get("end_time", "")[:5]
                if booking_start < sb_end and booking_end > sb_start:
                    raise HTTPException(
                        status_code=409,
                        detail=f"代課教師在 {booking_date} {sb_start}-{sb_end} 已有代課安排，時間衝突"
                    )

        # 從代課教師合約取得 course_rate
        course_id = booking[0].get("course_id")
        substitute_hourly_rate = 0
        if course_id:
            rate = await supabase_service.table_select(
                table="teacher_contract_details",
                select="amount",
                filters={
                    "teacher_contract_id": data.substitute_contract_id,
                    "course_id": course_id,
                    "detail_type": "eq.course_rate",
                    "is_deleted": "eq.false",
                },
            )
            if rate:
                substitute_hourly_rate = rate[0].get("amount", 0)

        employee_id = await get_user_employee_id(current_user.user_id)

        sub_data = {
            "booking_id": data.booking_id,
            "substitute_teacher_id": data.substitute_teacher_id,
            "substitute_contract_id": data.substitute_contract_id,
            "substitute_hourly_rate": substitute_hourly_rate,
            "reason": data.reason,
            "approved_by": employee_id,
            "approved_at": datetime.utcnow().isoformat(),
        }
        if employee_id:
            sub_data["created_by"] = employee_id

        result = await supabase_service.table_insert(
            table="substitute_details", data=sub_data,
        )

        if not result:
            raise HTTPException(status_code=500, detail="建立代課紀錄失敗")

        # 更新 booking 的 substitute_detail_id
        await supabase_service.table_update(
            table="bookings",
            data={"substitute_detail_id": result["id"]},
            filters={"id": data.booking_id},
        )

        enriched = await enrich_substitute_detail(result)
        return DataResponse(message="代課指派成功", data=SubstituteDetailResponse(**enriched))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"指派代課失敗: {str(e)}")


@router.get("", response_model=SubstituteDetailListResponse)
async def list_substitute_details(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: CurrentUser = Depends(require_page_permission("bookings.list"))
):
    """取得代課紀錄列表"""
    try:
        filters = {"is_deleted": "eq.false"}

        all_records = await supabase_service.table_select(
            table="substitute_details", select="id", filters=filters,
        )
        total = len(all_records)
        total_pages = math.ceil(total / per_page) if total > 0 else 1
        offset = (page - 1) * per_page

        records = await supabase_service.table_select_with_pagination(
            table="substitute_details",
            select="id,booking_id,substitute_teacher_id,substitute_contract_id,substitute_hourly_rate,reason,approved_by,approved_at,created_at,updated_at",
            filters=filters,
            order_by="created_at.desc",
            limit=per_page,
            offset=offset,
        )

        enriched = []
        for record in records:
            enriched.append(await enrich_substitute_detail(record))

        return SubstituteDetailListResponse(
            data=[SubstituteDetailResponse(**r) for r in enriched],
            total=total, page=page, per_page=per_page, total_pages=total_pages,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得代課紀錄失敗: {str(e)}")


@router.get("/{sub_id}", response_model=DataResponse[SubstituteDetailResponse])
async def get_substitute_detail(
    sub_id: str,
    current_user: CurrentUser = Depends(require_page_permission("bookings.list"))
):
    """取得單筆代課紀錄"""
    try:
        result = await supabase_service.table_select(
            table="substitute_details",
            select="id,booking_id,substitute_teacher_id,substitute_contract_id,substitute_hourly_rate,reason,approved_by,approved_at,created_at,updated_at",
            filters={"id": sub_id, "is_deleted": "eq.false"},
        )
        if not result:
            raise HTTPException(status_code=404, detail="代課紀錄不存在")

        enriched = await enrich_substitute_detail(result[0])
        return DataResponse(data=SubstituteDetailResponse(**enriched))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得代課紀錄失敗: {str(e)}")


@router.delete("/{sub_id}", response_model=BaseResponse)
async def delete_substitute_detail(
    sub_id: str,
    current_user: CurrentUser = Depends(require_page_permission("bookings.edit"))
):
    """取消代課（僅限員工）— 清除 booking.substitute_detail_id"""
    try:
        if not current_user.is_staff():
            raise HTTPException(status_code=403, detail="僅限員工取消代課")

        record = await supabase_service.table_select(
            table="substitute_details",
            select="id,booking_id",
            filters={"id": sub_id, "is_deleted": "eq.false"},
        )
        if not record:
            raise HTTPException(status_code=404, detail="代課紀錄不存在")

        employee_id = await get_user_employee_id(current_user.user_id)

        # 軟刪除代課紀錄
        delete_data = {
            "is_deleted": True,
            "deleted_at": datetime.utcnow().isoformat(),
        }
        if employee_id:
            delete_data["deleted_by"] = employee_id

        await supabase_service.table_update(
            table="substitute_details",
            data=delete_data,
            filters={"id": sub_id},
        )

        # 清除 booking 的 substitute_detail_id + 狀態改回 pending
        booking_id = record[0].get("booking_id")
        if booking_id:
            await supabase_service.table_update(
                table="bookings",
                data={"substitute_detail_id": None, "booking_status": "pending"},
                filters={"id": booking_id},
            )

        return BaseResponse(message="代課已取消，預約狀態已改為待確認")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取消代課失敗: {str(e)}")

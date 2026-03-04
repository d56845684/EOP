from fastapi import APIRouter, Depends, Query, HTTPException
from app.services.supabase_service import supabase_service
from app.core.dependencies import get_current_user, CurrentUser, require_staff, get_user_employee_id
from app.schemas.teacher_slot import (
    TeacherSlotCreate, TeacherSlotBatchCreate, TeacherSlotBatchDelete, TeacherSlotBatchUpdate,
    TeacherSlotBatchDeleteByIds, TeacherSlotBatchUpdateByIds,
    TeacherSlotUpdate, TeacherSlotResponse, TeacherSlotListResponse
)
from app.schemas.response import BaseResponse, DataResponse
from typing import Optional
from datetime import date, datetime, timedelta
import math

router = APIRouter(prefix="/teacher-slots", tags=["教師時段管理"])


async def slot_has_active_bookings(slot_id: str) -> bool:
    """動態查詢該 slot 是否有有效的 booking（非取消、非已刪除）"""
    bookings = await supabase_service.table_select(
        table="bookings",
        select="id",
        filters={
            "teacher_slot_id": f"eq.{slot_id}",
            "is_deleted": "eq.false",
        },
    )
    # 過濾掉已取消的
    active = [b for b in bookings if b.get("booking_status") != "cancelled"]
    return len(active) > 0


async def enrich_slot_with_relations(slot: dict) -> dict:
    """為時段資料添加關聯名稱"""
    # 取得教師名稱
    if slot.get("teacher_id"):
        teacher = await supabase_service.table_select(
            table="teachers",
            select="name,teacher_no",
            filters={"id": slot["teacher_id"]},
        )
        if teacher:
            slot["teacher_name"] = teacher[0]["name"]
            slot["teacher_no"] = teacher[0]["teacher_no"]

    # 取得教師合約編號
    if slot.get("teacher_contract_id"):
        contract = await supabase_service.table_select(
            table="teacher_contracts",
            select="contract_no",
            filters={"id": slot["teacher_contract_id"]},
        )
        slot["teacher_contract_no"] = contract[0]["contract_no"] if contract else None

    return slot


async def get_user_teacher_id(user_id: str) -> Optional[str]:
    """取得用戶關聯的教師 ID"""
    profile = await supabase_service.table_select(
        table="user_profiles",
        select="teacher_id",
        filters={"id": user_id},
    )
    if profile and profile[0].get("teacher_id"):
        return profile[0]["teacher_id"]
    return None



@router.get("", response_model=TeacherSlotListResponse)
async def list_teacher_slots(
    page: int = Query(1, ge=1, description="頁碼"),
    per_page: int = Query(20, ge=1, le=100, description="每頁數量"),
    teacher_id: Optional[str] = Query(None, description="篩選教師"),
    date_from: Optional[date] = Query(None, description="開始日期"),
    date_to: Optional[date] = Query(None, description="結束日期"),
    is_available: Optional[bool] = Query(None, description="篩選可用狀態"),
    current_user: CurrentUser = Depends(get_current_user)
):
    """取得教師時段列表"""
    try:
        # 建立基本查詢
        filters = {"is_deleted": "eq.false"}

        # 根據角色過濾
        user_role = current_user.role

        if user_role == "teacher":
            # 教師只能看自己的時段
            user_teacher_id = await get_user_teacher_id(current_user.user_id)
            if user_teacher_id:
                filters["teacher_id"] = f"eq.{user_teacher_id}"
            else:
                # 教師沒有關聯的 teacher_id，返回空列表
                return TeacherSlotListResponse(data=[], total=0, page=page, per_page=per_page, total_pages=0)
        elif user_role == "student":
            # 學生只能看可用的時段（不再用 is_booked 過濾）
            filters["is_available"] = "eq.true"
        # staff (admin/employee) 可看所有時段

        # 套用篩選條件
        if teacher_id:
            filters["teacher_id"] = f"eq.{teacher_id}"

        if date_from:
            filters["slot_date"] = f"gte.{date_from.isoformat()}"

        if is_available is not None:
            filters["is_available"] = f"eq.{str(is_available).lower()}"

        # 取得總數
        all_slots = await supabase_service.table_select(
            table="teacher_available_slots",
            select="id",
            filters=filters,
        )

        # 如果有結束日期，在結果中篩選
        if date_to:
            all_slots_filtered = []
            for s in all_slots:
                # 需要取得完整資料來過濾
                pass
            # 簡化處理：先取得所有資料再過濾

        total = len(all_slots)

        # 計算分頁
        total_pages = math.ceil(total / per_page) if total > 0 else 1
        offset = (page - 1) * per_page

        # 取得分頁資料
        slots = await supabase_service.table_select_with_pagination(
            table="teacher_available_slots",
            select="id,teacher_id,teacher_contract_id,slot_date,start_time,end_time,is_available,is_booked,notes,created_at,updated_at",
            filters=filters,
            order_by="slot_date.asc,start_time.asc",
            limit=per_page,
            offset=offset,
        )

        # 如果有結束日期，在結果中篩選
        if date_to:
            slots = [s for s in slots if s.get("slot_date") <= date_to.isoformat()]

        # 為每筆時段添加關聯名稱
        enriched_slots = []
        for slot in slots:
            enriched = await enrich_slot_with_relations(slot)
            enriched_slots.append(enriched)

        return TeacherSlotListResponse(
            data=[TeacherSlotResponse(**s) for s in enriched_slots],
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得教師時段列表失敗: {str(e)}")


@router.get("/options/teachers", tags=["教師時段管理"])
async def get_teacher_options(
    current_user: CurrentUser = Depends(require_staff)
):
    """取得教師下拉選單（僅限員工）"""
    try:
        teachers = await supabase_service.table_select(
            table="teachers",
            select="id,teacher_no,name,teacher_level",
            filters={"is_deleted": "eq.false", "is_active": "eq.true"},
        )
        return {"data": teachers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/my-contracts", tags=["教師時段管理"])
async def get_my_contracts(
    current_user: CurrentUser = Depends(get_current_user)
):
    """取得當前教師的合約（教師用）"""
    try:
        user_teacher_id = await get_user_teacher_id(current_user.user_id)

        if not user_teacher_id:
            return {"data": []}

        contracts = await supabase_service.table_select(
            table="teacher_contracts",
            select="id,contract_no",
            filters={
                "teacher_id": user_teacher_id,
                "is_deleted": "eq.false",
                "contract_status": "eq.active"
            },
        )
        return {"data": contracts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{slot_id}", response_model=DataResponse[TeacherSlotResponse])
async def get_teacher_slot(
    slot_id: str,
    current_user: CurrentUser = Depends(get_current_user)
):
    """取得單一教師時段"""
    try:
        result = await supabase_service.table_select(
            table="teacher_available_slots",
            select="id,teacher_id,teacher_contract_id,slot_date,start_time,end_time,is_available,is_booked,notes,created_at,updated_at",
            filters={"id": slot_id, "is_deleted": "eq.false"},
        )

        if not result:
            raise HTTPException(status_code=404, detail="教師時段不存在")

        slot = result[0]

        # 權限檢查
        user_role = current_user.role
        if user_role == "teacher":
            user_teacher_id = await get_user_teacher_id(current_user.user_id)
            if slot["teacher_id"] != user_teacher_id:
                raise HTTPException(status_code=403, detail="無權查看此時段")
        elif user_role == "student":
            # 學生只能查看可用的時段（不再檢查 is_booked）
            if not slot["is_available"]:
                raise HTTPException(status_code=403, detail="此時段不可查看")

        enriched = await enrich_slot_with_relations(slot)
        return DataResponse(data=TeacherSlotResponse(**enriched))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得教師時段失敗: {str(e)}")


@router.post("", response_model=DataResponse[TeacherSlotResponse])
async def create_teacher_slot(
    data: TeacherSlotCreate,
    current_user: CurrentUser = Depends(get_current_user)
):
    """建立教師時段（教師自己或員工）"""
    try:
        user_role = current_user.role

        # 權限檢查
        if user_role == "teacher":
            user_teacher_id = await get_user_teacher_id(current_user.user_id)
            if data.teacher_id != user_teacher_id:
                raise HTTPException(status_code=403, detail="教師只能建立自己的時段")
        elif user_role not in ["admin", "employee"]:
            raise HTTPException(status_code=403, detail="無權建立教師時段")

        # 驗證教師存在
        teacher = await supabase_service.table_select(
            table="teachers",
            select="id,name",
            filters={"id": data.teacher_id, "is_deleted": "eq.false"},
        )
        if not teacher:
            raise HTTPException(status_code=400, detail="教師不存在")

        # 驗證教師合約存在（如果有提供）
        if data.teacher_contract_id:
            contract = await supabase_service.table_select(
                table="teacher_contracts",
                select="id",
                filters={"id": data.teacher_contract_id, "is_deleted": "eq.false"},
            )
            if not contract:
                raise HTTPException(status_code=400, detail="教師合約不存在")

        # 取得操作者的 employee_id
        employee_id = await get_user_employee_id(current_user.user_id)

        # 建立時段（不再設定 is_booked）
        slot_data = {
            "teacher_id": data.teacher_id,
            "teacher_contract_id": data.teacher_contract_id,
            "slot_date": data.slot_date.isoformat(),
            "start_time": data.start_time.isoformat(),
            "end_time": data.end_time.isoformat(),
            "is_available": data.is_available,
            "notes": data.notes,
        }
        if employee_id:
            slot_data["created_by"] = employee_id

        result = await supabase_service.table_insert(
            table="teacher_available_slots",
            data=slot_data,
        )

        if not result:
            raise HTTPException(status_code=500, detail="建立教師時段失敗")

        # 添加關聯名稱
        enriched = await enrich_slot_with_relations(result)

        return DataResponse(
            message="教師時段建立成功",
            data=TeacherSlotResponse(**enriched)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"建立教師時段失敗: {str(e)}")


@router.post("/batch", response_model=BaseResponse)
async def create_teacher_slots_batch(
    data: TeacherSlotBatchCreate,
    current_user: CurrentUser = Depends(get_current_user)
):
    """批次建立教師時段（週期性）"""
    try:
        user_role = current_user.role

        # 權限檢查
        if user_role == "teacher":
            user_teacher_id = await get_user_teacher_id(current_user.user_id)
            if data.teacher_id != user_teacher_id:
                raise HTTPException(status_code=403, detail="教師只能建立自己的時段")
        elif user_role not in ["admin", "employee"]:
            raise HTTPException(status_code=403, detail="無權建立教師時段")

        # 驗證教師存在
        teacher = await supabase_service.table_select(
            table="teachers",
            select="id,name",
            filters={"id": data.teacher_id, "is_deleted": "eq.false"},
        )
        if not teacher:
            raise HTTPException(status_code=400, detail="教師不存在")

        # 驗證教師合約存在（如果有提供）
        if data.teacher_contract_id:
            contract = await supabase_service.table_select(
                table="teacher_contracts",
                select="id",
                filters={"id": data.teacher_contract_id, "is_deleted": "eq.false"},
            )
            if not contract:
                raise HTTPException(status_code=400, detail="教師合約不存在")

        # 取得操作者的 employee_id
        employee_id = await get_user_employee_id(current_user.user_id)

        # 計算所有日期
        slots_to_create = []
        current_date = data.start_date
        while current_date <= data.end_date:
            # weekday(): 0=Monday, 6=Sunday
            if current_date.weekday() in data.weekdays:
                slot_item = {
                    "teacher_id": data.teacher_id,
                    "teacher_contract_id": data.teacher_contract_id,
                    "slot_date": current_date.isoformat(),
                    "start_time": data.start_time.isoformat(),
                    "end_time": data.end_time.isoformat(),
                    "is_available": True,
                    "notes": data.notes,
                }
                if employee_id:
                    slot_item["created_by"] = employee_id
                slots_to_create.append(slot_item)
            current_date += timedelta(days=1)

        if not slots_to_create:
            raise HTTPException(status_code=400, detail="選定的日期範圍內沒有符合的星期")

        # 批次插入
        created_count = 0
        for slot_data in slots_to_create:
            result = await supabase_service.table_insert(
                table="teacher_available_slots",
                data=slot_data,
            )
            if result:
                created_count += 1

        return BaseResponse(message=f"成功建立 {created_count} 個教師時段")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批次建立教師時段失敗: {str(e)}")


@router.delete("/batch", response_model=BaseResponse)
async def delete_teacher_slots_batch(
    data: TeacherSlotBatchDelete,
    current_user: CurrentUser = Depends(get_current_user)
):
    """批次刪除教師時段（僅刪除無有效預約的時段）"""
    try:
        user_role = current_user.role

        # 權限檢查
        if user_role == "teacher":
            user_teacher_id = await get_user_teacher_id(current_user.user_id)
            if data.teacher_id != user_teacher_id:
                raise HTTPException(status_code=403, detail="教師只能刪除自己的時段")
        elif user_role not in ["admin", "employee"]:
            raise HTTPException(status_code=403, detail="無權刪除教師時段")

        # 查詢符合條件的時段（不再用 is_booked 過濾）
        filters = {
            "teacher_id": f"eq.{data.teacher_id}",
            "is_deleted": "eq.false",
        }

        # 取得所有符合日期範圍的時段
        all_slots = await supabase_service.table_select(
            table="teacher_available_slots",
            select="id,slot_date,start_time,end_time",
            filters=filters,
        )

        # 在 Python 中進行更精細的過濾
        slots_to_delete = []
        skipped_booked = 0
        for slot in all_slots:
            slot_date_str = slot.get("slot_date", "")
            slot_date_obj = date.fromisoformat(slot_date_str) if slot_date_str else None

            if not slot_date_obj:
                continue

            # 檢查日期範圍
            if slot_date_obj < data.start_date or slot_date_obj > data.end_date:
                continue

            # 檢查星期幾
            if data.weekdays is not None and slot_date_obj.weekday() not in data.weekdays:
                continue

            # 檢查時間範圍
            if data.start_time is not None:
                slot_start = slot.get("start_time", "")
                if slot_start and slot_start[:5] != data.start_time.isoformat()[:5]:
                    continue

            if data.end_time is not None:
                slot_end = slot.get("end_time", "")
                if slot_end and slot_end[:5] != data.end_time.isoformat()[:5]:
                    continue

            # 動態檢查是否有有效預約
            if await slot_has_active_bookings(slot["id"]):
                skipped_booked += 1
                continue

            slots_to_delete.append(slot["id"])

        if not slots_to_delete:
            msg = "沒有符合條件的時段可刪除"
            if skipped_booked:
                msg += f"（{skipped_booked} 個有預約的時段已跳過）"
            return BaseResponse(message=msg)

        # 取得操作者的 employee_id
        employee_id = await get_user_employee_id(current_user.user_id)

        # 批次軟刪除
        deleted_count = 0
        delete_time = datetime.utcnow().isoformat()
        delete_data = {
            "is_deleted": True,
            "deleted_at": delete_time,
        }
        if employee_id:
            delete_data["deleted_by"] = employee_id

        for slot_id in slots_to_delete:
            result = await supabase_service.table_update(
                table="teacher_available_slots",
                data=delete_data,
                filters={"id": slot_id},
            )
            if result:
                deleted_count += 1

        message = f"成功刪除 {deleted_count} 個教師時段"
        if skipped_booked:
            message += f"，跳過 {skipped_booked} 個有預約的時段"

        return BaseResponse(message=message)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批次刪除教師時段失敗: {str(e)}")


@router.put("/batch", response_model=BaseResponse)
async def update_teacher_slots_batch(
    data: TeacherSlotBatchUpdate,
    current_user: CurrentUser = Depends(get_current_user)
):
    """批次更新教師時段（有預約的時段不可修改時間）"""
    try:
        user_role = current_user.role

        # 權限檢查
        if user_role == "teacher":
            user_teacher_id = await get_user_teacher_id(current_user.user_id)
            if data.teacher_id != user_teacher_id:
                raise HTTPException(status_code=403, detail="教師只能更新自己的時段")
        elif user_role not in ["admin", "employee"]:
            raise HTTPException(status_code=403, detail="無權更新教師時段")

        # 檢查是否有要更新的內容
        update_fields = {}
        if data.new_start_time is not None:
            update_fields["start_time"] = data.new_start_time.isoformat()
        if data.new_end_time is not None:
            update_fields["end_time"] = data.new_end_time.isoformat()
        if data.is_available is not None:
            update_fields["is_available"] = data.is_available
        if data.notes is not None:
            update_fields["notes"] = data.notes

        if not update_fields:
            raise HTTPException(status_code=400, detail="沒有指定要更新的內容")

        updating_time = data.new_start_time is not None or data.new_end_time is not None

        # 查詢符合條件的時段
        filters = {
            "teacher_id": f"eq.{data.teacher_id}",
            "is_deleted": "eq.false",
        }

        # 取得所有符合日期範圍的時段
        all_slots = await supabase_service.table_select(
            table="teacher_available_slots",
            select="id,slot_date,start_time,end_time",
            filters=filters,
        )

        # 在 Python 中進行更精細的過濾
        slots_to_update = []
        skipped_booked = 0
        for slot in all_slots:
            slot_date_str = slot.get("slot_date", "")
            slot_date_obj = date.fromisoformat(slot_date_str) if slot_date_str else None

            if not slot_date_obj:
                continue

            # 檢查日期範圍
            if slot_date_obj < data.start_date or slot_date_obj > data.end_date:
                continue

            # 檢查星期幾
            if data.weekdays is not None and slot_date_obj.weekday() not in data.weekdays:
                continue

            # 檢查時間範圍
            if data.filter_start_time is not None:
                slot_start = slot.get("start_time", "")
                if slot_start and slot_start[:5] != data.filter_start_time.isoformat()[:5]:
                    continue

            if data.filter_end_time is not None:
                slot_end = slot.get("end_time", "")
                if slot_end and slot_end[:5] != data.filter_end_time.isoformat()[:5]:
                    continue

            # 如果要更新時間，動態檢查是否有有效預約
            if updating_time and await slot_has_active_bookings(slot["id"]):
                skipped_booked += 1
                continue

            slots_to_update.append(slot["id"])

        if not slots_to_update:
            msg = "沒有符合條件的時段可更新"
            if skipped_booked:
                msg += f"（{skipped_booked} 個有預約的時段已跳過）"
            return BaseResponse(message=msg)

        # 批次更新
        updated_count = 0
        for slot_id in slots_to_update:
            result = await supabase_service.table_update(
                table="teacher_available_slots",
                data=update_fields,
                filters={"id": slot_id},
            )
            if result:
                updated_count += 1

        message = f"成功更新 {updated_count} 個教師時段"
        if skipped_booked:
            message += f"，跳過 {skipped_booked} 個有預約的時段"

        return BaseResponse(message=message)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批次更新教師時段失敗: {str(e)}")


@router.post("/batch-by-ids/delete", response_model=BaseResponse)
async def delete_teacher_slots_by_ids(
    data: TeacherSlotBatchDeleteByIds,
    current_user: CurrentUser = Depends(get_current_user)
):
    """根據 ID 批次刪除教師時段（僅刪除無有效預約的時段）"""
    try:
        user_role = current_user.role

        if not data.slot_ids:
            raise HTTPException(status_code=400, detail="請選擇要刪除的時段")

        # 取得操作者的 employee_id
        employee_id = await get_user_employee_id(current_user.user_id)

        # 查詢所有選中的時段
        deleted_count = 0
        skipped_count = 0
        delete_time = datetime.utcnow().isoformat()

        for slot_id in data.slot_ids:
            # 檢查時段是否存在
            existing = await supabase_service.table_select(
                table="teacher_available_slots",
                select="id,teacher_id",
                filters={"id": slot_id, "is_deleted": "eq.false"},
            )

            if not existing:
                continue

            slot = existing[0]

            # 權限檢查
            if user_role == "teacher":
                user_teacher_id = await get_user_teacher_id(current_user.user_id)
                if slot["teacher_id"] != user_teacher_id:
                    skipped_count += 1
                    continue
            elif user_role not in ["admin", "employee"]:
                skipped_count += 1
                continue

            # 動態檢查是否有有效預約
            if await slot_has_active_bookings(slot_id):
                skipped_count += 1
                continue

            # 軟刪除
            delete_data = {
                "is_deleted": True,
                "deleted_at": delete_time,
            }
            if employee_id:
                delete_data["deleted_by"] = employee_id

            result = await supabase_service.table_update(
                table="teacher_available_slots",
                data=delete_data,
                filters={"id": slot_id},
            )
            if result:
                deleted_count += 1

        message = f"成功刪除 {deleted_count} 個時段"
        if skipped_count > 0:
            message += f"，跳過 {skipped_count} 個（有預約或無權限）"

        return BaseResponse(message=message)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批次刪除教師時段失敗: {str(e)}")


@router.post("/batch-by-ids/update", response_model=BaseResponse)
async def update_teacher_slots_by_ids(
    data: TeacherSlotBatchUpdateByIds,
    current_user: CurrentUser = Depends(get_current_user)
):
    """根據 ID 批次更新教師時段"""
    try:
        user_role = current_user.role

        if not data.slot_ids:
            raise HTTPException(status_code=400, detail="請選擇要更新的時段")

        # 檢查是否有要更新的內容
        update_fields = {}
        if data.new_start_time is not None:
            update_fields["start_time"] = data.new_start_time.isoformat()
        if data.new_end_time is not None:
            update_fields["end_time"] = data.new_end_time.isoformat()
        if data.is_available is not None:
            update_fields["is_available"] = data.is_available
        if data.notes is not None:
            update_fields["notes"] = data.notes

        if not update_fields:
            raise HTTPException(status_code=400, detail="請指定要更新的內容")

        updating_time = data.new_start_time is not None or data.new_end_time is not None

        updated_count = 0
        skipped_count = 0

        for slot_id in data.slot_ids:
            # 檢查時段是否存在
            existing = await supabase_service.table_select(
                table="teacher_available_slots",
                select="id,teacher_id",
                filters={"id": slot_id, "is_deleted": "eq.false"},
            )

            if not existing:
                continue

            slot = existing[0]

            # 權限檢查
            if user_role == "teacher":
                user_teacher_id = await get_user_teacher_id(current_user.user_id)
                if slot["teacher_id"] != user_teacher_id:
                    skipped_count += 1
                    continue
            elif user_role not in ["admin", "employee"]:
                skipped_count += 1
                continue

            # 如果要更新時間，動態檢查是否有有效預約
            if updating_time and await slot_has_active_bookings(slot_id):
                skipped_count += 1
                continue

            # 更新
            result = await supabase_service.table_update(
                table="teacher_available_slots",
                data=update_fields,
                filters={"id": slot_id},
            )
            if result:
                updated_count += 1

        message = f"成功更新 {updated_count} 個時段"
        if skipped_count > 0:
            message += f"，跳過 {skipped_count} 個（有預約或無權限）"

        return BaseResponse(message=message)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批次更新教師時段失敗: {str(e)}")


@router.put("/{slot_id}", response_model=DataResponse[TeacherSlotResponse])
async def update_teacher_slot(
    slot_id: str,
    data: TeacherSlotUpdate,
    current_user: CurrentUser = Depends(get_current_user)
):
    """更新教師時段（教師自己或員工）"""
    try:
        # 檢查時段是否存在
        existing = await supabase_service.table_select(
            table="teacher_available_slots",
            select="id,teacher_id",
            filters={"id": slot_id, "is_deleted": "eq.false"},
        )

        if not existing:
            raise HTTPException(status_code=404, detail="教師時段不存在")

        slot = existing[0]

        # 權限檢查
        user_role = current_user.role
        if user_role == "teacher":
            user_teacher_id = await get_user_teacher_id(current_user.user_id)
            if slot["teacher_id"] != user_teacher_id:
                raise HTTPException(status_code=403, detail="教師只能更新自己的時段")
        elif user_role not in ["admin", "employee"]:
            raise HTTPException(status_code=403, detail="無權更新教師時段")

        # 有有效預約的時段不能修改日期/時間
        if data.slot_date is not None or data.start_time is not None or data.end_time is not None:
            if await slot_has_active_bookings(slot_id):
                raise HTTPException(status_code=400, detail="有預約的時段無法修改日期或時間")

        # 更新時段
        update_data = {k: v for k, v in data.model_dump().items() if v is not None}

        # 轉換日期時間格式
        if "slot_date" in update_data:
            update_data["slot_date"] = update_data["slot_date"].isoformat()
        if "start_time" in update_data:
            update_data["start_time"] = update_data["start_time"].isoformat()
        if "end_time" in update_data:
            update_data["end_time"] = update_data["end_time"].isoformat()

        if not update_data:
            raise HTTPException(status_code=400, detail="沒有要更新的資料")

        result = await supabase_service.table_update(
            table="teacher_available_slots",
            data=update_data,
            filters={"id": slot_id},
        )

        if not result:
            raise HTTPException(status_code=500, detail="更新教師時段失敗")

        # 添加關聯名稱
        enriched = await enrich_slot_with_relations(result)

        return DataResponse(
            message="教師時段更新成功",
            data=TeacherSlotResponse(**enriched)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新教師時段失敗: {str(e)}")


@router.delete("/{slot_id}", response_model=BaseResponse)
async def delete_teacher_slot(
    slot_id: str,
    current_user: CurrentUser = Depends(get_current_user)
):
    """刪除教師時段（軟刪除，無有效預約才可刪除）"""
    try:
        # 檢查時段是否存在
        existing = await supabase_service.table_select(
            table="teacher_available_slots",
            select="id,teacher_id",
            filters={"id": slot_id, "is_deleted": "eq.false"},
        )

        if not existing:
            raise HTTPException(status_code=404, detail="教師時段不存在")

        slot = existing[0]

        # 權限檢查
        user_role = current_user.role
        if user_role == "teacher":
            user_teacher_id = await get_user_teacher_id(current_user.user_id)
            if slot["teacher_id"] != user_teacher_id:
                raise HTTPException(status_code=403, detail="教師只能刪除自己的時段")
        elif user_role not in ["admin", "employee"]:
            raise HTTPException(status_code=403, detail="無權刪除教師時段")

        # 動態檢查是否有有效預約
        if await slot_has_active_bookings(slot_id):
            raise HTTPException(status_code=400, detail="有預約的時段無法刪除")

        # 取得操作者的 employee_id
        employee_id = await get_user_employee_id(current_user.user_id)

        # 軟刪除
        delete_data = {
            "is_deleted": True,
            "deleted_at": datetime.utcnow().isoformat(),
        }
        if employee_id:
            delete_data["deleted_by"] = employee_id

        result = await supabase_service.table_update(
            table="teacher_available_slots",
            data=delete_data,
            filters={"id": slot_id},
        )

        if not result:
            raise HTTPException(status_code=500, detail="刪除教師時段失敗")

        return BaseResponse(message="教師時段刪除成功")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刪除教師時段失敗: {str(e)}")

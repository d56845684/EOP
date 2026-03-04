from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from app.services.supabase_service import supabase_service
from app.services.storage_service import storage_service
from app.config import settings
from app.core.dependencies import get_current_user, CurrentUser, require_staff, get_user_employee_id
from app.schemas.student_contract import (
    StudentContractCreate, StudentContractUpdate, StudentContractResponse,
    StudentContractListResponse, ContractStatus,
    StudentContractDetailCreate, StudentContractDetailUpdate, StudentContractDetailResponse,
    StudentContractLeaveRecordCreate, StudentContractLeaveRecordResponse
)
from app.schemas.response import BaseResponse, DataResponse
from typing import Optional
from datetime import datetime
import math
import uuid
import re

router = APIRouter(prefix="/student-contracts", tags=["學生合約管理"])

CONTRACT_SELECT = "id,contract_no,student_id,contract_status,start_date,end_date,total_lessons,remaining_lessons,total_amount,total_leave_allowed,used_leave_count,is_recurring,notes,created_at,updated_at,contract_file_path,contract_file_name,contract_file_uploaded_at"


async def get_user_student_id(user_id: str) -> Optional[str]:
    """根據 user_id 取得對應的 student_id"""
    result = await supabase_service.table_select(
        table="user_profiles",
        select="student_id",
        filters={"id": user_id},
    )
    if result and result[0].get("student_id"):
        return result[0]["student_id"]
    return None


async def generate_contract_no() -> str:
    """生成合約編號: SC{YYYYMMDD}{序號}"""
    today = datetime.utcnow().strftime("%Y%m%d")
    prefix = f"SC{today}"

    # 查詢今天已有多少合約
    result = await supabase_service.table_select(
        table="student_contracts",
        select="contract_no",
        filters={"contract_no": f"like.{prefix}%"},
    )

    if not result:
        return f"{prefix}001"

    # 找出最大序號
    max_seq = 0
    for item in result:
        contract_no = item.get("contract_no", "")
        if contract_no.startswith(prefix):
            try:
                seq = int(contract_no[len(prefix):])
                max_seq = max(max_seq, seq)
            except ValueError:
                pass

    return f"{prefix}{str(max_seq + 1).zfill(3)}"


async def check_student_active_conflict(student_id: str, exclude_contract_id: str = None):
    """檢查該學生是否已有生效中合約，回傳衝突合約或 None"""
    result = await supabase_service.table_select(
        table="student_contracts",
        select="id,contract_no",
        filters={
            "student_id": f"eq.{student_id}",
            "contract_status": "eq.active",
            "is_deleted": "eq.false"
        },
    )
    for contract in result:
        if exclude_contract_id and contract["id"] == exclude_contract_id:
            continue
        return contract
    return None


async def enrich_contract_with_relations(contract: dict) -> dict:
    """為合約資料添加關聯名稱、明細、教師和請假紀錄"""
    # 取得學生名稱
    if contract.get("student_id"):
        student = await supabase_service.table_select(
            table="students",
            select="name",
            filters={"id": contract["student_id"]},
        )
        contract["student_name"] = student[0]["name"] if student else None

    # 取得合約明細
    details = await supabase_service.table_select(
        table="student_contract_details",
        select="id,student_contract_id,detail_type,course_id,description,amount,notes,created_at,updated_at",
        filters={
            "student_contract_id": f"eq.{contract['id']}",
            "is_deleted": "eq.false"
        },
    )

    # 為 lesson_price 明細加上 course_name
    enriched_details = []
    for detail in details:
        if detail.get("course_id"):
            course = await supabase_service.table_select(
                table="courses",
                select="course_name",
                filters={"id": detail["course_id"]},
            )
            detail["course_name"] = course[0]["course_name"] if course else None
        enriched_details.append(detail)

    contract["details"] = enriched_details

    # 取得請假紀錄
    leave_records = await supabase_service.table_select(
        table="student_contract_leave_records",
        select="id,student_contract_id,leave_date,reason,created_at",
        filters={
            "student_contract_id": f"eq.{contract['id']}",
            "is_deleted": "eq.false"
        },
    )
    contract["leave_records"] = leave_records

    return contract


# ========== Options ==========

@router.get("/options/students", tags=["學生合約管理"])
async def get_student_options(
    current_user: CurrentUser = Depends(get_current_user)
):
    """取得學生下拉選單"""
    try:
        students = await supabase_service.table_select(
            table="students",
            select="id,student_no,name",
            filters={"is_deleted": "eq.false", "is_active": "eq.true"},
        )
        return {"data": students}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/options/courses", tags=["學生合約管理"])
async def get_course_options(
    student_id: Optional[str] = Query(None, description="若提供，只回傳該學生已選修的課程"),
    current_user: CurrentUser = Depends(get_current_user)
):
    """取得課程下拉選單（供明細 form 使用）

    若提供 student_id，只回傳該學生在 student_courses 中的課程。
    若未提供，回傳全部課程（保持向後相容）。
    """
    try:
        if student_id:
            # 取得該學生已選的課程 ID
            enrollments = await supabase_service.table_select(
                table="student_courses",
                select="course_id",
                filters={
                    "student_id": f"eq.{student_id}",
                    "is_deleted": "eq.false"
                },
            )
            if not enrollments:
                return {"data": []}

            course_ids = [e["course_id"] for e in enrollments]

            # 取得這些課程的詳細資訊
            courses = []
            for cid in course_ids:
                course = await supabase_service.table_select(
                    table="courses",
                    select="id,course_code,course_name",
                    filters={"id": cid, "is_deleted": "eq.false", "is_active": "eq.true"},
                )
                if course:
                    courses.append(course[0])

            return {"data": courses}
        else:
            courses = await supabase_service.table_select(
                table="courses",
                select="id,course_code,course_name",
                filters={"is_deleted": "eq.false", "is_active": "eq.true"},
            )
            return {"data": courses}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/options/teachers", tags=["學生合約管理"])
async def get_teacher_options(
    current_user: CurrentUser = Depends(get_current_user)
):
    """取得教師下拉選單"""
    try:
        teachers = await supabase_service.table_select(
            table="teachers",
            select="id,teacher_no,name",
            filters={"is_deleted": "eq.false", "is_active": "eq.true"},
        )
        return {"data": teachers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== Contract CRUD ==========

@router.get("", response_model=StudentContractListResponse)
async def list_student_contracts(
    page: int = Query(1, ge=1, description="頁碼"),
    per_page: int = Query(20, ge=1, le=100, description="每頁數量"),
    search: Optional[str] = Query(None, description="搜尋合約編號"),
    contract_status: Optional[ContractStatus] = Query(None, description="篩選合約狀態"),
    student_id: Optional[str] = Query(None, description="篩選學生"),
    current_user: CurrentUser = Depends(get_current_user)
):
    """取得學生合約列表

    權限控制:
    - 學生: 僅能看到自己的合約
    - 教師: 無法查看學生合約
    - 員工/管理員: 可查看所有合約
    """
    try:
        # 建立基本查詢
        filters = {"is_deleted": "eq.false"}

        # 角色權限過濾 (RLS 邏輯在後端實現)
        if current_user.is_student():
            # 學生只能看自己的合約
            user_student_id = await get_user_student_id(current_user.user_id)
            if not user_student_id:
                # 沒有對應的 student_id，返回空列表
                return StudentContractListResponse(
                    data=[],
                    total=0,
                    page=page,
                    per_page=per_page,
                    total_pages=1
                )
            filters["student_id"] = f"eq.{user_student_id}"
        elif current_user.is_teacher():
            # 教師無法查看學生合約，返回空列表
            return StudentContractListResponse(
                data=[],
                total=0,
                page=page,
                per_page=per_page,
                total_pages=1
            )
        # 員工/管理員不需要額外過濾

        if contract_status:
            filters["contract_status"] = f"eq.{contract_status.value}"

        # 學生角色時忽略 student_id 參數（已強制過濾）
        if student_id and not current_user.is_student():
            filters["student_id"] = f"eq.{student_id}"

        # 取得總數
        all_contracts = await supabase_service.table_select(
            table="student_contracts",
            select="id",
            filters=filters,
        )
        total = len(all_contracts)

        # 計算分頁
        total_pages = math.ceil(total / per_page) if total > 0 else 1
        offset = (page - 1) * per_page

        # 取得分頁資料
        contracts = await supabase_service.table_select_with_pagination(
            table="student_contracts",
            select=CONTRACT_SELECT,
            filters=filters,
            order_by="created_at.desc",
            limit=per_page,
            offset=offset,
        )

        # 如果有搜尋關鍵字，在結果中篩選
        if search:
            search_lower = search.lower()
            contracts = [
                c for c in contracts
                if search_lower in c.get("contract_no", "").lower()
            ]

        # 為每筆合約添加關聯名稱
        enriched_contracts = []
        for contract in contracts:
            enriched = await enrich_contract_with_relations(contract)
            enriched_contracts.append(enriched)

        return StudentContractListResponse(
            data=[StudentContractResponse(**c) for c in enriched_contracts],
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得學生合約列表失敗: {str(e)}")


@router.get("/{contract_id}", response_model=DataResponse[StudentContractResponse])
async def get_student_contract(
    contract_id: str,
    current_user: CurrentUser = Depends(get_current_user)
):
    """取得單一學生合約

    權限控制:
    - 學生: 僅能查看自己的合約
    - 教師: 無法查看學生合約
    - 員工/管理員: 可查看所有合約
    """
    try:
        # 教師無權查看學生合約
        if current_user.is_teacher():
            raise HTTPException(status_code=403, detail="教師無權查看學生合約")

        result = await supabase_service.table_select(
            table="student_contracts",
            select=CONTRACT_SELECT,
            filters={"id": contract_id, "is_deleted": "eq.false"},
        )

        if not result:
            raise HTTPException(status_code=404, detail="學生合約不存在")

        contract = result[0]

        # 學生只能查看自己的合約
        if current_user.is_student():
            user_student_id = await get_user_student_id(current_user.user_id)
            if contract.get("student_id") != user_student_id:
                raise HTTPException(status_code=403, detail="無權查看此合約")

        contract = await enrich_contract_with_relations(contract)
        return DataResponse(data=StudentContractResponse(**contract))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得學生合約失敗: {str(e)}")


@router.post("", response_model=DataResponse[StudentContractResponse])
async def create_student_contract(
    data: StudentContractCreate,
    current_user: CurrentUser = Depends(require_staff)
):
    """建立學生合約（僅限員工）"""
    try:
        # 驗證學生存在
        student = await supabase_service.table_select(
            table="students",
            select="id,name",
            filters={"id": data.student_id, "is_deleted": "eq.false"},
        )
        if not student:
            raise HTTPException(status_code=400, detail="學生不存在")

        # 檢查 active 合約唯一性
        if data.contract_status == ContractStatus.active:
            conflict = await check_student_active_conflict(data.student_id)
            if conflict:
                raise HTTPException(
                    status_code=400,
                    detail=f"該學生已有生效中的合約 (合約編號: {conflict['contract_no']}, ID: {conflict['id']})"
                )

        # 生成合約編號
        contract_no = await generate_contract_no()

        # 計算 total_leave_allowed
        total_leave_allowed = data.total_leave_allowed if data.total_leave_allowed is not None else data.total_lessons * 2

        # 建立合約
        contract_data = {
            "contract_no": contract_no,
            "student_id": data.student_id,
            "contract_status": data.contract_status.value,
            "start_date": data.start_date.isoformat(),
            "end_date": data.end_date.isoformat(),
            "total_lessons": data.total_lessons,
            "remaining_lessons": data.remaining_lessons,
            "total_amount": data.total_amount,
            "total_leave_allowed": total_leave_allowed,
            "used_leave_count": 0,
            "notes": data.notes,
        }

        employee_id = await get_user_employee_id(current_user.user_id)
        if employee_id:
            contract_data["created_by"] = employee_id

        result = await supabase_service.table_insert(
            table="student_contracts",
            data=contract_data,
        )

        if not result:
            raise HTTPException(status_code=500, detail="建立學生合約失敗")

        # 添加關聯名稱
        enriched = await enrich_contract_with_relations(result)

        return DataResponse(
            message="學生合約建立成功",
            data=StudentContractResponse(**enriched)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"建立學生合約失敗: {str(e)}")


@router.put("/{contract_id}", response_model=DataResponse[StudentContractResponse])
async def update_student_contract(
    contract_id: str,
    data: StudentContractUpdate,
    current_user: CurrentUser = Depends(require_staff)
):
    """更新學生合約（僅限員工）"""
    try:
        # 檢查合約是否存在
        existing = await supabase_service.table_select(
            table="student_contracts",
            select="id,student_id",
            filters={"id": contract_id, "is_deleted": "eq.false"},
        )

        if not existing:
            raise HTTPException(status_code=404, detail="學生合約不存在")

        # 檢查 active 合約唯一性
        if data.contract_status == ContractStatus.active:
            check_student_id = data.student_id or existing[0].get("student_id")
            if check_student_id:
                conflict = await check_student_active_conflict(check_student_id, exclude_contract_id=contract_id)
                if conflict:
                    raise HTTPException(
                        status_code=400,
                        detail=f"該學生已有生效中的合約 (合約編號: {conflict['contract_no']}, ID: {conflict['id']})"
                    )

        # 如果有更新學生 ID，驗證學生存在
        if data.student_id:
            student = await supabase_service.table_select(
                table="students",
                select="id",
                filters={"id": data.student_id, "is_deleted": "eq.false"},
            )
            if not student:
                raise HTTPException(status_code=400, detail="學生不存在")

        # 更新合約
        update_data = {}
        for key, value in data.model_dump().items():
            if value is not None:
                if key == "contract_status":
                    update_data[key] = value.value
                elif key in ["start_date", "end_date"]:
                    update_data[key] = value.isoformat()
                else:
                    update_data[key] = value

        if not update_data:
            raise HTTPException(status_code=400, detail="沒有要更新的資料")

        result = await supabase_service.table_update(
            table="student_contracts",
            data=update_data,
            filters={"id": contract_id},
        )

        if not result:
            raise HTTPException(status_code=500, detail="更新學生合約失敗")

        # 添加關聯名稱
        enriched = await enrich_contract_with_relations(result)

        return DataResponse(
            message="學生合約更新成功",
            data=StudentContractResponse(**enriched)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新學生合約失敗: {str(e)}")


@router.delete("/{contract_id}", response_model=BaseResponse)
async def delete_student_contract(
    contract_id: str,
    current_user: CurrentUser = Depends(require_staff)
):
    """刪除學生合約（軟刪除，僅限員工）— 連帶刪除明細、教師綁定和請假紀錄"""
    try:
        # 檢查合約是否存在
        existing = await supabase_service.table_select(
            table="student_contracts",
            select="id",
            filters={"id": contract_id, "is_deleted": "eq.false"},
        )

        if not existing:
            raise HTTPException(status_code=404, detail="學生合約不存在")

        employee_id = await get_user_employee_id(current_user.user_id)
        now = datetime.utcnow().isoformat()

        # 軟刪除相關明細
        details = await supabase_service.table_select(
            table="student_contract_details",
            select="id",
            filters={
                "student_contract_id": f"eq.{contract_id}",
                "is_deleted": "eq.false"
            },
        )
        for detail in details:
            detail_update = {
                "is_deleted": True,
                "deleted_at": now
            }
            if employee_id:
                detail_update["deleted_by"] = employee_id
            await supabase_service.table_update(
                table="student_contract_details",
                data=detail_update,
                filters={"id": detail["id"]},
            )

        # 軟刪除相關請假紀錄
        leave_records = await supabase_service.table_select(
            table="student_contract_leave_records",
            select="id",
            filters={
                "student_contract_id": f"eq.{contract_id}",
                "is_deleted": "eq.false"
            },
        )
        for record in leave_records:
            record_update = {
                "is_deleted": True,
                "deleted_at": now
            }
            if employee_id:
                record_update["deleted_by"] = employee_id
            await supabase_service.table_update(
                table="student_contract_leave_records",
                data=record_update,
                filters={"id": record["id"]},
            )

        # 軟刪除合約
        delete_data = {
            "is_deleted": True,
            "deleted_at": now
        }
        if employee_id:
            delete_data["deleted_by"] = employee_id

        result = await supabase_service.table_update(
            table="student_contracts",
            data=delete_data,
            filters={"id": contract_id},
        )

        if not result:
            raise HTTPException(status_code=500, detail="刪除學生合約失敗")

        return BaseResponse(message="學生合約刪除成功")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刪除學生合約失敗: {str(e)}")


# ========== Contract Details CRUD ==========

@router.get("/{contract_id}/details")
async def list_contract_details(
    contract_id: str,
    current_user: CurrentUser = Depends(get_current_user)
):
    """取得合約明細列表"""
    try:
        # 教師無權
        if current_user.is_teacher():
            raise HTTPException(status_code=403, detail="教師無權查看學生合約明細")

        # 確認合約存在
        contract = await supabase_service.table_select(
            table="student_contracts",
            select="id,student_id",
            filters={"id": contract_id, "is_deleted": "eq.false"},
        )
        if not contract:
            raise HTTPException(status_code=404, detail="學生合約不存在")

        # 學生只能看自己的合約明細
        if current_user.is_student():
            user_student_id = await get_user_student_id(current_user.user_id)
            if contract[0].get("student_id") != user_student_id:
                raise HTTPException(status_code=403, detail="無權查看此合約明細")

        details = await supabase_service.table_select(
            table="student_contract_details",
            select="id,student_contract_id,detail_type,course_id,description,amount,notes,created_at,updated_at",
            filters={
                "student_contract_id": f"eq.{contract_id}",
                "is_deleted": "eq.false"
            },
        )

        # enrich course_name
        enriched = []
        for d in details:
            if d.get("course_id"):
                course = await supabase_service.table_select(
                    table="courses",
                    select="course_name",
                    filters={"id": d["course_id"]},
                )
                d["course_name"] = course[0]["course_name"] if course else None
            enriched.append(d)

        return {"data": [StudentContractDetailResponse(**d) for d in enriched]}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得合約明細失敗: {str(e)}")


@router.post("/{contract_id}/details")
async def create_contract_detail(
    contract_id: str,
    data: StudentContractDetailCreate,
    current_user: CurrentUser = Depends(require_staff)
):
    """新增合約明細（僅限員工）"""
    try:
        # 確認合約存在
        contract = await supabase_service.table_select(
            table="student_contracts",
            select="id,student_id",
            filters={"id": contract_id, "is_deleted": "eq.false"},
        )
        if not contract:
            raise HTTPException(status_code=404, detail="學生合約不存在")

        # 若為 lesson_price，驗證課程存在
        if data.course_id:
            course = await supabase_service.table_select(
                table="courses",
                select="id,course_name",
                filters={"id": data.course_id, "is_deleted": "eq.false"},
            )
            if not course:
                raise HTTPException(status_code=400, detail="課程不存在")

            # 驗證課程在學生的 student_courses 中
            student_id = contract[0].get("student_id")
            if student_id:
                enrollment = await supabase_service.table_select(
                    table="student_courses",
                    select="id",
                    filters={
                        "student_id": f"eq.{student_id}",
                        "course_id": f"eq.{data.course_id}",
                        "is_deleted": "eq.false"
                    },
                )
                if not enrollment:
                    raise HTTPException(status_code=400, detail="此學生尚未選修此課程，請先在「學生選課」中新增")

        detail_data = {
            "student_contract_id": contract_id,
            "detail_type": data.detail_type.value,
            "course_id": data.course_id,
            "description": data.description,
            "amount": data.amount,
            "notes": data.notes,
        }

        employee_id = await get_user_employee_id(current_user.user_id)
        if employee_id:
            detail_data["created_by"] = employee_id

        result = await supabase_service.table_insert(
            table="student_contract_details",
            data=detail_data,
        )

        if not result:
            raise HTTPException(status_code=500, detail="新增合約明細失敗")

        # 補償堂數連動 remaining_lessons
        if data.detail_type.value == "compensation":
            contract_data = await supabase_service.table_select(
                table="student_contracts",
                select="remaining_lessons",
                filters={"id": contract_id},
            )
            if contract_data:
                new_remaining = contract_data[0]["remaining_lessons"] + int(data.amount)
                await supabase_service.table_update(
                    table="student_contracts",
                    data={"remaining_lessons": new_remaining},
                    filters={"id": contract_id},
                )

        # enrich course_name
        if result.get("course_id"):
            course = await supabase_service.table_select(
                table="courses",
                select="course_name",
                filters={"id": result["course_id"]},
            )
            result["course_name"] = course[0]["course_name"] if course else None

        return DataResponse(
            message="合約明細新增成功",
            data=StudentContractDetailResponse(**result)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"新增合約明細失敗: {str(e)}")


@router.put("/{contract_id}/details/{detail_id}")
async def update_contract_detail(
    contract_id: str,
    detail_id: str,
    data: StudentContractDetailUpdate,
    current_user: CurrentUser = Depends(require_staff)
):
    """更新合約明細（僅限員工，不可改 detail_type 和 course_id）"""
    try:
        # 確認明細存在且屬於此合約
        existing = await supabase_service.table_select(
            table="student_contract_details",
            select="id,student_contract_id,detail_type,amount",
            filters={
                "id": detail_id,
                "student_contract_id": f"eq.{contract_id}",
                "is_deleted": "eq.false"
            },
        )
        if not existing:
            raise HTTPException(status_code=404, detail="合約明細不存在")

        update_data = {}
        for key, value in data.model_dump().items():
            if value is not None:
                update_data[key] = value

        if not update_data:
            raise HTTPException(status_code=400, detail="沒有要更新的資料")

        employee_id = await get_user_employee_id(current_user.user_id)
        if employee_id:
            update_data["updated_by"] = employee_id

        result = await supabase_service.table_update(
            table="student_contract_details",
            data=update_data,
            filters={"id": detail_id},
        )

        if not result:
            raise HTTPException(status_code=500, detail="更新合約明細失敗")

        # 補償堂數連動 remaining_lessons
        if existing[0].get("detail_type") == "compensation" and data.amount is not None:
            old_amount = int(existing[0]["amount"])
            new_amount = int(data.amount)
            diff = new_amount - old_amount
            if diff != 0:
                contract_data = await supabase_service.table_select(
                    table="student_contracts",
                    select="remaining_lessons",
                    filters={"id": contract_id},
                )
                if contract_data:
                    new_remaining = contract_data[0]["remaining_lessons"] + diff
                    await supabase_service.table_update(
                        table="student_contracts",
                        data={"remaining_lessons": new_remaining},
                        filters={"id": contract_id},
                    )

        # enrich course_name
        if result.get("course_id"):
            course = await supabase_service.table_select(
                table="courses",
                select="course_name",
                filters={"id": result["course_id"]},
            )
            result["course_name"] = course[0]["course_name"] if course else None

        return DataResponse(
            message="合約明細更新成功",
            data=StudentContractDetailResponse(**result)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新合約明細失敗: {str(e)}")


@router.delete("/{contract_id}/details/{detail_id}", response_model=BaseResponse)
async def delete_contract_detail(
    contract_id: str,
    detail_id: str,
    current_user: CurrentUser = Depends(require_staff)
):
    """刪除合約明細（軟刪除，僅限員工）"""
    try:
        # 確認明細存在且屬於此合約
        existing = await supabase_service.table_select(
            table="student_contract_details",
            select="id,student_contract_id,detail_type,amount",
            filters={
                "id": detail_id,
                "student_contract_id": f"eq.{contract_id}",
                "is_deleted": "eq.false"
            },
        )
        if not existing:
            raise HTTPException(status_code=404, detail="合約明細不存在")

        delete_data = {
            "is_deleted": True,
            "deleted_at": datetime.utcnow().isoformat()
        }

        employee_id = await get_user_employee_id(current_user.user_id)
        if employee_id:
            delete_data["deleted_by"] = employee_id

        result = await supabase_service.table_update(
            table="student_contract_details",
            data=delete_data,
            filters={"id": detail_id},
        )

        if not result:
            raise HTTPException(status_code=500, detail="刪除合約明細失敗")

        # 補償堂數連動 remaining_lessons
        if existing[0].get("detail_type") == "compensation":
            compensation_amount = int(existing[0]["amount"])
            contract_data = await supabase_service.table_select(
                table="student_contracts",
                select="remaining_lessons",
                filters={"id": contract_id},
            )
            if contract_data:
                new_remaining = contract_data[0]["remaining_lessons"] - compensation_amount
                await supabase_service.table_update(
                    table="student_contracts",
                    data={"remaining_lessons": max(0, new_remaining)},
                    filters={"id": contract_id},
                )

        return BaseResponse(message="合約明細刪除成功")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刪除合約明細失敗: {str(e)}")


# ========== Leave Records CRUD ==========

@router.get("/{contract_id}/leave-records")
async def list_leave_records(
    contract_id: str,
    current_user: CurrentUser = Depends(get_current_user)
):
    """取得合約請假紀錄"""
    try:
        if current_user.is_teacher():
            raise HTTPException(status_code=403, detail="教師無權查看學生合約請假紀錄")

        # 確認合約存在
        contract = await supabase_service.table_select(
            table="student_contracts",
            select="id,student_id",
            filters={"id": contract_id, "is_deleted": "eq.false"},
        )
        if not contract:
            raise HTTPException(status_code=404, detail="學生合約不存在")

        # 學生只能看自己的
        if current_user.is_student():
            user_student_id = await get_user_student_id(current_user.user_id)
            if contract[0].get("student_id") != user_student_id:
                raise HTTPException(status_code=403, detail="無權查看此合約請假紀錄")

        records = await supabase_service.table_select(
            table="student_contract_leave_records",
            select="id,student_contract_id,leave_date,reason,created_at",
            filters={
                "student_contract_id": f"eq.{contract_id}",
                "is_deleted": "eq.false"
            },
        )

        return {"data": [StudentContractLeaveRecordResponse(**r) for r in records]}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得請假紀錄失敗: {str(e)}")


@router.post("/{contract_id}/leave-records")
async def create_leave_record(
    contract_id: str,
    data: StudentContractLeaveRecordCreate,
    current_user: CurrentUser = Depends(require_staff)
):
    """新增請假紀錄（僅限員工），同時 used_leave_count +1"""
    try:
        # 確認合約存在
        contract = await supabase_service.table_select(
            table="student_contracts",
            select="id,used_leave_count,total_leave_allowed",
            filters={"id": contract_id, "is_deleted": "eq.false"},
        )
        if not contract:
            raise HTTPException(status_code=404, detail="學生合約不存在")

        current_used = contract[0].get("used_leave_count", 0)
        total_allowed = contract[0].get("total_leave_allowed", 0)

        if current_used >= total_allowed:
            raise HTTPException(status_code=400, detail=f"已達請假上限 ({total_allowed} 次)")

        record_data = {
            "student_contract_id": contract_id,
            "leave_date": data.leave_date.isoformat(),
            "reason": data.reason,
        }

        employee_id = await get_user_employee_id(current_user.user_id)
        if employee_id:
            record_data["created_by"] = employee_id

        result = await supabase_service.table_insert(
            table="student_contract_leave_records",
            data=record_data,
        )

        if not result:
            raise HTTPException(status_code=500, detail="新增請假紀錄失敗")

        # 更新 used_leave_count +1
        await supabase_service.table_update(
            table="student_contracts",
            data={"used_leave_count": current_used + 1},
            filters={"id": contract_id},
        )

        return DataResponse(
            message="請假紀錄新增成功",
            data=StudentContractLeaveRecordResponse(**result)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"新增請假紀錄失敗: {str(e)}")


@router.delete("/{contract_id}/leave-records/{record_id}", response_model=BaseResponse)
async def delete_leave_record(
    contract_id: str,
    record_id: str,
    current_user: CurrentUser = Depends(require_staff)
):
    """刪除請假紀錄（軟刪除，僅限員工），同時 used_leave_count -1"""
    try:
        # 確認紀錄存在且屬於此合約
        existing = await supabase_service.table_select(
            table="student_contract_leave_records",
            select="id,student_contract_id",
            filters={
                "id": record_id,
                "student_contract_id": f"eq.{contract_id}",
                "is_deleted": "eq.false"
            },
        )
        if not existing:
            raise HTTPException(status_code=404, detail="請假紀錄不存在")

        delete_data = {
            "is_deleted": True,
            "deleted_at": datetime.utcnow().isoformat()
        }

        employee_id = await get_user_employee_id(current_user.user_id)
        if employee_id:
            delete_data["deleted_by"] = employee_id

        result = await supabase_service.table_update(
            table="student_contract_leave_records",
            data=delete_data,
            filters={"id": record_id},
        )

        if not result:
            raise HTTPException(status_code=500, detail="刪除請假紀錄失敗")

        # 更新 used_leave_count -1
        contract = await supabase_service.table_select(
            table="student_contracts",
            select="id,used_leave_count",
            filters={"id": contract_id, "is_deleted": "eq.false"},
        )
        if contract:
            current_used = contract[0].get("used_leave_count", 0)
            new_used = max(0, current_used - 1)
            await supabase_service.table_update(
                table="student_contracts",
                data={"used_leave_count": new_used},
                filters={"id": contract_id},
            )

        return BaseResponse(message="請假紀錄刪除成功")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刪除請假紀錄失敗: {str(e)}")


# ========== File Upload/Download (unchanged) ==========

class ConfirmUploadRequest(BaseModel):
    """確認上傳請求"""
    storage_path: str
    file_name: str


@router.post("/{contract_id}/upload-url")
async def get_student_contract_upload_url(
    contract_id: str,
    current_user: CurrentUser = Depends(require_staff)
):
    """取得學生合約檔案的 signed upload URL（僅限員工）

    前端收到後直接 PUT 檔案到該 URL，上傳完成後呼叫 confirm-upload。
    """
    try:
        # 檢查合約是否存在
        existing = await supabase_service.table_select(
            table="student_contracts",
            select="id",
            filters={"id": contract_id, "is_deleted": "eq.false"},
        )
        if not existing:
            raise HTTPException(status_code=404, detail="學生合約不存在")

        # 確保 bucket 存在
        await storage_service.ensure_bucket_exists(settings.AWS_S3_BUCKET)

        # 產生安全檔名
        safe_filename = f"{uuid.uuid4().hex}.pdf"
        storage_path = f"student-contracts/{contract_id}/{safe_filename}"

        # 產生 S3 presigned upload URL
        signed = await storage_service.create_signed_upload_url(
            bucket=settings.AWS_S3_BUCKET,
            path=storage_path,
        )
        if not signed:
            raise HTTPException(status_code=500, detail="產生上傳連結失敗")

        return {
            "upload_url": signed["upload_url"],
            "storage_path": storage_path,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"產生上傳連結失敗: {str(e)}")


@router.post("/{contract_id}/confirm-upload", response_model=DataResponse[StudentContractResponse])
async def confirm_student_contract_upload(
    contract_id: str,
    body: ConfirmUploadRequest,
    current_user: CurrentUser = Depends(require_staff)
):
    """確認學生合約檔案上傳完成（僅限員工）

    前端直接上傳 S3 成功後呼叫此 API，更新 DB 並將狀態改為 active。
    """
    try:
        # 檢查合約是否存在
        existing = await supabase_service.table_select(
            table="student_contracts",
            select="id,student_id",
            filters={"id": contract_id, "is_deleted": "eq.false"},
        )
        if not existing:
            raise HTTPException(status_code=404, detail="學生合約不存在")

        # 檢查 active 合約唯一性（上傳確認會自動設為 active）
        check_student_id = existing[0].get("student_id")
        if check_student_id:
            conflict = await check_student_active_conflict(check_student_id, exclude_contract_id=contract_id)
            if conflict:
                raise HTTPException(
                    status_code=400,
                    detail=f"該學生已有生效中的合約 (合約編號: {conflict['contract_no']}, ID: {conflict['id']})"
                )

        # 驗證 storage_path 格式
        if not re.match(r'^student-contracts/[a-f0-9\-]+/[a-f0-9]+\.pdf$', body.storage_path):
            raise HTTPException(status_code=400, detail="無效的檔案路徑格式")

        # 確認檔案已上傳至 S3
        file_exists = await storage_service.verify_file_exists(
            bucket=settings.AWS_S3_BUCKET,
            path=body.storage_path,
        )
        if not file_exists:
            raise HTTPException(status_code=400, detail="檔案尚未上傳至 S3，請重新上傳")

        # 取得員工 ID
        employee_id = await get_user_employee_id(current_user.user_id)

        # 更新 DB：檔案資訊 + 狀態改為 active
        update_data = {
            "contract_file_path": body.storage_path,
            "contract_file_name": body.file_name,
            "contract_file_uploaded_at": datetime.utcnow().isoformat(),
            "contract_status": "active",
        }
        if employee_id:
            update_data["contract_file_uploaded_by"] = employee_id

        result = await supabase_service.table_update(
            table="student_contracts",
            data=update_data,
            filters={"id": contract_id},
        )

        if not result:
            raise HTTPException(status_code=500, detail="更新合約資訊失敗")

        enriched = await enrich_contract_with_relations(result)
        return DataResponse(
            message="合約檔案上傳成功，狀態已更新為生效中",
            data=StudentContractResponse(**enriched)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"確認上傳失敗: {str(e)}")


@router.get("/{contract_id}/download-url")
async def get_student_contract_download_url(
    contract_id: str,
    current_user: CurrentUser = Depends(get_current_user)
):
    """取得學生合約檔案的 signed download URL

    權限控制:
    - 學生: 僅能下載自己的合約
    - 教師: 無法下載學生合約
    - 員工/管理員: 可下載所有合約
    """
    try:
        # 教師無權下載學生合約
        if current_user.is_teacher():
            raise HTTPException(status_code=403, detail="教師無權下載學生合約")

        # 查詢合約
        result = await supabase_service.table_select(
            table="student_contracts",
            select="id,student_id,contract_file_path,contract_file_name",
            filters={"id": contract_id, "is_deleted": "eq.false"},
        )

        if not result:
            raise HTTPException(status_code=404, detail="學生合約不存在")

        contract = result[0]

        # 學生只能下載自己的合約
        if current_user.is_student():
            user_student_id = await get_user_student_id(current_user.user_id)
            if contract.get("student_id") != user_student_id:
                raise HTTPException(status_code=403, detail="無權下載此合約")

        # 檢查是否有檔案
        file_path = contract.get("contract_file_path")
        if not file_path:
            raise HTTPException(status_code=404, detail="此合約尚未上傳檔案")

        # 產生 signed download URL
        signed_url = await storage_service.create_signed_download_url(
            bucket=settings.AWS_S3_BUCKET,
            path=file_path,
            expires_in=3600,
        )
        if not signed_url:
            raise HTTPException(status_code=500, detail="產生下載連結失敗")

        return {
            "download_url": signed_url,
            "file_name": contract.get("contract_file_name", "contract.pdf"),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得下載連結失敗: {str(e)}")

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from app.services.supabase_service import supabase_service
from app.services.storage_service import storage_service
from app.services.contract_pdf_service import generate_teacher_contract_pdf, generate_addendum_pdf
from app.config import settings
from app.core.dependencies import get_current_user, CurrentUser, require_staff, require_page_permission, get_user_employee_id
from app.schemas.teacher_contract import (
    TeacherContractCreate, TeacherContractUpdate, TeacherContractResponse,
    TeacherContractListResponse, ContractStatus, EmploymentType,
    TeacherContractDetailCreate, TeacherContractDetailUpdate, TeacherContractDetailResponse,
    TeacherWorkScheduleCreate, TeacherWorkScheduleBatchSet, TeacherWorkScheduleResponse
)
from app.schemas.contract_addendum import (
    ContractAddendumCreate, ContractAddendumUpdate,
    ContractAddendumResponse, ContractAddendumListResponse,
)
from app.schemas.response import BaseResponse, DataResponse
from typing import Optional
from datetime import datetime
import math
import uuid
import re

router = APIRouter(prefix="/teacher-contracts", tags=["教師合約管理"])


async def generate_contract_no() -> str:
    """生成合約編號: TC{YYYYMMDD}{序號}"""
    today = datetime.utcnow().strftime("%Y%m%d")
    prefix = f"TC{today}"

    # 查詢今天已有多少合約
    result = await supabase_service.table_select(
        table="teacher_contracts",
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


async def check_teacher_active_conflict(teacher_id: str, exclude_contract_id: str = None):
    """檢查該教師是否已有生效中合約，回傳衝突合約或 None"""
    result = await supabase_service.table_select(
        table="teacher_contracts",
        select="id,contract_no",
        filters={
            "teacher_id": f"eq.{teacher_id}",
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
    """為合約資料添加關聯名稱和明細"""
    # 取得教師名稱
    if contract.get("teacher_id"):
        teacher = await supabase_service.table_select(
            table="teachers",
            select="name",
            filters={"id": contract["teacher_id"]},
        )
        contract["teacher_name"] = teacher[0]["name"] if teacher else None

    # 取得合約明細
    details = await supabase_service.table_select(
        table="teacher_contract_details",
        select="id,teacher_contract_id,detail_type,course_id,description,amount,notes,created_at,updated_at",
        filters={
            "teacher_contract_id": f"eq.{contract['id']}",
            "is_deleted": "eq.false"
        },
    )

    # 為 course_rate 明細加上 course_name
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
    # 僅正職合約計算 total_amount（底薪+津貼加總），時薪合約不計算
    if contract.get("employment_type") == "full_time":
        contract["total_amount"] = sum(d["amount"] for d in enriched_details)
    else:
        contract["total_amount"] = None

    # 取得工作時段
    work_schedules = await supabase_service.table_select(
        table="teacher_work_schedules",
        select="id,teacher_contract_id,weekday,start_time,end_time,notes,created_at,updated_at",
        filters={
            "teacher_contract_id": f"eq.{contract['id']}",
            "is_deleted": "eq.false"
        },
    )
    contract["work_schedules"] = work_schedules

    # 取得附約列表
    addendums = await supabase_service.table_select(
        table="contract_addendums",
        select="id,addendum_no,contract_type,parent_contract_id,original_end_date,new_end_date,addendum_status,file_path,file_name,file_uploaded_at,notes,created_at,updated_at",
        filters={
            "contract_type": "eq.teacher",
            "parent_contract_id": f"eq.{contract['id']}",
            "is_deleted": "eq.false",
        },
    )
    for a in addendums:
        a["parent_contract_no"] = contract.get("contract_no")
        a["person_name"] = contract.get("teacher_name")
    contract["addendums"] = addendums

    return contract


CONTRACT_SELECT = "id,contract_no,teacher_id,contract_status,start_date,end_date,employment_type,trial_completed_bonus,trial_to_formal_bonus,work_start_time,work_end_time,notes,created_at,updated_at,contract_file_path,contract_file_name,contract_file_uploaded_at"


@router.get("/options/teachers", tags=["教師合約管理"])
async def get_teacher_options(
    current_user: CurrentUser = Depends(require_page_permission("teachers.contracts"))
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


@router.get("/options/courses", tags=["教師合約管理"])
async def get_course_options(
    current_user: CurrentUser = Depends(require_page_permission("teachers.contracts"))
):
    """取得課程下拉選單"""
    try:
        courses = await supabase_service.table_select(
            table="courses",
            select="id,course_code,course_name",
            filters={"is_deleted": "eq.false", "is_active": "eq.true"},
        )
        return {"data": courses}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=TeacherContractListResponse)
async def list_teacher_contracts(
    page: int = Query(1, ge=1, description="頁碼"),
    per_page: int = Query(20, ge=1, le=100, description="每頁數量"),
    search: Optional[str] = Query(None, description="搜尋合約編號"),
    contract_status: Optional[ContractStatus] = Query(None, description="篩選合約狀態"),
    employment_type: Optional[EmploymentType] = Query(None, description="篩選僱用類型"),
    teacher_id: Optional[str] = Query(None, description="篩選教師"),
    current_user: CurrentUser = Depends(require_page_permission("teachers.contracts"))
):
    """取得教師合約列表

    權限控制:
    - 教師: 僅能看到自己的合約
    - 學生: 無法查看教師合約
    - 員工/管理員: 可查看所有合約
    """
    try:
        # 建立基本查詢
        filters = {"is_deleted": "eq.false"}

        # 角色權限過濾 (RLS 邏輯在後端實現)
        if current_user.is_teacher():
            # 教師只能看自己的合約
            user_teacher_id = current_user.teacher_id
            if not user_teacher_id:
                # 沒有對應的 teacher_id，返回空列表
                return TeacherContractListResponse(
                    data=[],
                    total=0,
                    page=page,
                    per_page=per_page,
                    total_pages=1
                )
            filters["teacher_id"] = f"eq.{user_teacher_id}"
        elif current_user.is_student():
            # 學生無法查看教師合約，返回空列表
            return TeacherContractListResponse(
                data=[],
                total=0,
                page=page,
                per_page=per_page,
                total_pages=1
            )
        # 員工/管理員不需要額外過濾

        if contract_status:
            filters["contract_status"] = f"eq.{contract_status.value}"

        if employment_type:
            filters["employment_type"] = f"eq.{employment_type.value}"

        # 教師角色時忽略 teacher_id 參數（已強制過濾）
        if teacher_id and not current_user.is_teacher():
            filters["teacher_id"] = f"eq.{teacher_id}"

        # 取得總數
        all_contracts = await supabase_service.table_select(
            table="teacher_contracts",
            select="id",
            filters=filters,
        )
        total = len(all_contracts)

        # 計算分頁
        total_pages = math.ceil(total / per_page) if total > 0 else 1
        offset = (page - 1) * per_page

        # 取得分頁資料
        contracts = await supabase_service.table_select_with_pagination(
            table="teacher_contracts",
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

        return TeacherContractListResponse(
            data=[TeacherContractResponse(**c) for c in enriched_contracts],
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得教師合約列表失敗: {str(e)}")


@router.get("/{contract_id}", response_model=DataResponse[TeacherContractResponse])
async def get_teacher_contract(
    contract_id: str,
    current_user: CurrentUser = Depends(require_page_permission("teachers.contracts"))
):
    """取得單一教師合約

    權限控制:
    - 教師: 僅能查看自己的合約
    - 學生: 無法查看教師合約
    - 員工/管理員: 可查看所有合約
    """
    try:
        # 學生無權查看教師合約
        if current_user.is_student():
            raise HTTPException(status_code=403, detail="學生無權查看教師合約")

        result = await supabase_service.table_select(
            table="teacher_contracts",
            select=CONTRACT_SELECT,
            filters={"id": contract_id, "is_deleted": "eq.false"},
        )

        if not result:
            raise HTTPException(status_code=404, detail="教師合約不存在")

        contract = result[0]

        # 教師只能查看自己的合約
        if current_user.is_teacher():
            user_teacher_id = current_user.teacher_id
            if contract.get("teacher_id") != user_teacher_id:
                raise HTTPException(status_code=403, detail="無權查看此合約")

        contract = await enrich_contract_with_relations(contract)
        return DataResponse(data=TeacherContractResponse(**contract))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得教師合約失敗: {str(e)}")


@router.post("", response_model=DataResponse[TeacherContractResponse])
async def create_teacher_contract(
    data: TeacherContractCreate,
    current_user: CurrentUser = Depends(require_page_permission("teachers.contracts"))
):
    """建立教師合約（僅限員工）"""
    try:
        # 驗證教師存在
        teacher = await supabase_service.table_select(
            table="teachers",
            select="id,name",
            filters={"id": data.teacher_id, "is_deleted": "eq.false"},
        )
        if not teacher:
            raise HTTPException(status_code=400, detail="教師不存在")

        # 檢查 active 合約唯一性
        if data.contract_status == ContractStatus.active:
            conflict = await check_teacher_active_conflict(data.teacher_id)
            if conflict:
                raise HTTPException(
                    status_code=400,
                    detail=f"該教師已有生效中的合約 (合約編號: {conflict['contract_no']}, ID: {conflict['id']})"
                )

        # 生成合約編號
        contract_no = await generate_contract_no()

        # 建立合約
        contract_data = {
            "contract_no": contract_no,
            "teacher_id": data.teacher_id,
            "contract_status": data.contract_status.value,
            "start_date": data.start_date.isoformat(),
            "end_date": data.end_date.isoformat(),
            "employment_type": data.employment_type.value,
            "trial_completed_bonus": data.trial_completed_bonus,
            "trial_to_formal_bonus": data.trial_to_formal_bonus,
            "work_start_time": data.work_start_time.isoformat() if data.work_start_time else None,
            "work_end_time": data.work_end_time.isoformat() if data.work_end_time else None,
            "notes": data.notes,
        }

        employee_id = await get_user_employee_id(current_user.user_id)
        if employee_id:
            contract_data["created_by"] = employee_id

        result = await supabase_service.table_insert(
            table="teacher_contracts",
            data=contract_data,
        )

        if not result:
            raise HTTPException(status_code=500, detail="建立教師合約失敗")

        # 添加關聯名稱
        enriched = await enrich_contract_with_relations(result)

        return DataResponse(
            message="教師合約建立成功",
            data=TeacherContractResponse(**enriched)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"建立教師合約失敗: {str(e)}")


@router.put("/{contract_id}", response_model=DataResponse[TeacherContractResponse])
async def update_teacher_contract(
    contract_id: str,
    data: TeacherContractUpdate,
    current_user: CurrentUser = Depends(require_page_permission("teachers.contracts"))
):
    """更新教師合約（僅限員工）"""
    try:
        # 檢查合約是否存在
        existing = await supabase_service.table_select(
            table="teacher_contracts",
            select="id,teacher_id",
            filters={"id": contract_id, "is_deleted": "eq.false"},
        )

        if not existing:
            raise HTTPException(status_code=404, detail="教師合約不存在")

        # 檢查 active 合約唯一性
        if data.contract_status == ContractStatus.active:
            check_teacher_id = data.teacher_id or existing[0].get("teacher_id")
            if check_teacher_id:
                conflict = await check_teacher_active_conflict(check_teacher_id, exclude_contract_id=contract_id)
                if conflict:
                    raise HTTPException(
                        status_code=400,
                        detail=f"該教師已有生效中的合約 (合約編號: {conflict['contract_no']}, ID: {conflict['id']})"
                    )

        # 如果有更新教師 ID，驗證教師存在
        if data.teacher_id:
            teacher = await supabase_service.table_select(
                table="teachers",
                select="id",
                filters={"id": data.teacher_id, "is_deleted": "eq.false"},
            )
            if not teacher:
                raise HTTPException(status_code=400, detail="教師不存在")

        # 更新合約
        update_data = {}
        for key, value in data.model_dump().items():
            if value is not None:
                if key == "contract_status":
                    update_data[key] = value.value
                elif key == "employment_type":
                    update_data[key] = value.value
                elif key in ["start_date", "end_date"]:
                    update_data[key] = value.isoformat()
                elif key in ["work_start_time", "work_end_time"]:
                    update_data[key] = value.isoformat()
                else:
                    update_data[key] = value

        if not update_data:
            raise HTTPException(status_code=400, detail="沒有要更新的資料")

        result = await supabase_service.table_update(
            table="teacher_contracts",
            data=update_data,
            filters={"id": contract_id},
        )

        if not result:
            raise HTTPException(status_code=500, detail="更新教師合約失敗")

        # 添加關聯名稱
        enriched = await enrich_contract_with_relations(result)

        return DataResponse(
            message="教師合約更新成功",
            data=TeacherContractResponse(**enriched)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新教師合約失敗: {str(e)}")


@router.delete("/{contract_id}", response_model=BaseResponse)
async def delete_teacher_contract(
    contract_id: str,
    current_user: CurrentUser = Depends(require_page_permission("teachers.contracts"))
):
    """刪除教師合約（軟刪除，僅限員工）— 連帶刪除明細"""
    try:
        # 檢查合約是否存在
        existing = await supabase_service.table_select(
            table="teacher_contracts",
            select="id",
            filters={"id": contract_id, "is_deleted": "eq.false"},
        )

        if not existing:
            raise HTTPException(status_code=404, detail="教師合約不存在")

        employee_id = await get_user_employee_id(current_user.user_id)
        now = datetime.utcnow().isoformat()

        # 軟刪除相關工作時段
        work_schedules = await supabase_service.table_select(
            table="teacher_work_schedules",
            select="id",
            filters={
                "teacher_contract_id": f"eq.{contract_id}",
                "is_deleted": "eq.false"
            },
        )
        for ws in work_schedules:
            ws_update = {
                "is_deleted": True,
                "deleted_at": now
            }
            if employee_id:
                ws_update["deleted_by"] = employee_id
            await supabase_service.table_update(
                table="teacher_work_schedules",
                data=ws_update,
                filters={"id": ws["id"]},
            )

        # 軟刪除相關明細
        details = await supabase_service.table_select(
            table="teacher_contract_details",
            select="id",
            filters={
                "teacher_contract_id": f"eq.{contract_id}",
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
                table="teacher_contract_details",
                data=detail_update,
                filters={"id": detail["id"]},
            )

        # 軟刪除合約
        delete_data = {
            "is_deleted": True,
            "deleted_at": now
        }
        if employee_id:
            delete_data["deleted_by"] = employee_id

        result = await supabase_service.table_update(
            table="teacher_contracts",
            data=delete_data,
            filters={"id": contract_id},
        )

        if not result:
            raise HTTPException(status_code=500, detail="刪除教師合約失敗")

        return BaseResponse(message="教師合約刪除成功")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刪除教師合約失敗: {str(e)}")


# ========== Contract Details CRUD ==========

@router.get("/{contract_id}/details")
async def list_contract_details(
    contract_id: str,
    current_user: CurrentUser = Depends(require_page_permission("teachers.contracts"))
):
    """取得合約明細列表"""
    try:
        # 學生無權
        if current_user.is_student():
            raise HTTPException(status_code=403, detail="學生無權查看教師合約明細")

        # 確認合約存在
        contract = await supabase_service.table_select(
            table="teacher_contracts",
            select="id,teacher_id",
            filters={"id": contract_id, "is_deleted": "eq.false"},
        )
        if not contract:
            raise HTTPException(status_code=404, detail="教師合約不存在")

        # 教師只能看自己的合約明細
        if current_user.is_teacher():
            user_teacher_id = current_user.teacher_id
            if contract[0].get("teacher_id") != user_teacher_id:
                raise HTTPException(status_code=403, detail="無權查看此合約明細")

        details = await supabase_service.table_select(
            table="teacher_contract_details",
            select="id,teacher_contract_id,detail_type,course_id,description,amount,notes,created_at,updated_at",
            filters={
                "teacher_contract_id": f"eq.{contract_id}",
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

        return {"data": [TeacherContractDetailResponse(**d) for d in enriched]}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得合約明細失敗: {str(e)}")


@router.post("/{contract_id}/details")
async def create_contract_detail(
    contract_id: str,
    data: TeacherContractDetailCreate,
    current_user: CurrentUser = Depends(require_page_permission("teachers.contracts"))
):
    """新增合約明細（僅限員工）"""
    try:
        # 確認合約存在
        contract = await supabase_service.table_select(
            table="teacher_contracts",
            select="id",
            filters={"id": contract_id, "is_deleted": "eq.false"},
        )
        if not contract:
            raise HTTPException(status_code=404, detail="教師合約不存在")

        # 若為 course_rate，驗證課程存在
        if data.course_id:
            course = await supabase_service.table_select(
                table="courses",
                select="id,course_name",
                filters={"id": data.course_id, "is_deleted": "eq.false"},
            )
            if not course:
                raise HTTPException(status_code=400, detail="課程不存在")

        detail_data = {
            "teacher_contract_id": contract_id,
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
            table="teacher_contract_details",
            data=detail_data,
        )

        if not result:
            raise HTTPException(status_code=500, detail="新增合約明細失敗")

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
            data=TeacherContractDetailResponse(**result)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"新增合約明細失敗: {str(e)}")


@router.put("/{contract_id}/details/{detail_id}")
async def update_contract_detail(
    contract_id: str,
    detail_id: str,
    data: TeacherContractDetailUpdate,
    current_user: CurrentUser = Depends(require_page_permission("teachers.contracts"))
):
    """更新合約明細（僅限員工，不可改 detail_type 和 course_id）"""
    try:
        # 確認明細存在且屬於此合約
        existing = await supabase_service.table_select(
            table="teacher_contract_details",
            select="id,teacher_contract_id",
            filters={
                "id": detail_id,
                "teacher_contract_id": f"eq.{contract_id}",
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
            table="teacher_contract_details",
            data=update_data,
            filters={"id": detail_id},
        )

        if not result:
            raise HTTPException(status_code=500, detail="更新合約明細失敗")

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
            data=TeacherContractDetailResponse(**result)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新合約明細失敗: {str(e)}")


@router.delete("/{contract_id}/details/{detail_id}", response_model=BaseResponse)
async def delete_contract_detail(
    contract_id: str,
    detail_id: str,
    current_user: CurrentUser = Depends(require_page_permission("teachers.contracts"))
):
    """刪除合約明細（軟刪除，僅限員工）"""
    try:
        # 確認明細存在且屬於此合約
        existing = await supabase_service.table_select(
            table="teacher_contract_details",
            select="id,teacher_contract_id",
            filters={
                "id": detail_id,
                "teacher_contract_id": f"eq.{contract_id}",
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
            table="teacher_contract_details",
            data=delete_data,
            filters={"id": detail_id},
        )

        if not result:
            raise HTTPException(status_code=500, detail="刪除合約明細失敗")

        return BaseResponse(message="合約明細刪除成功")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刪除合約明細失敗: {str(e)}")


# ========== Work Schedules CRUD ==========

@router.get("/{contract_id}/work-schedules")
async def list_work_schedules(
    contract_id: str,
    current_user: CurrentUser = Depends(require_page_permission("teachers.contracts"))
):
    """取得合約工作時段列表"""
    try:
        if current_user.is_student():
            raise HTTPException(status_code=403, detail="學生無權查看教師合約工作時段")

        contract = await supabase_service.table_select(
            table="teacher_contracts",
            select="id,teacher_id",
            filters={"id": contract_id, "is_deleted": "eq.false"},
        )
        if not contract:
            raise HTTPException(status_code=404, detail="教師合約不存在")

        if current_user.is_teacher():
            if contract[0].get("teacher_id") != current_user.teacher_id:
                raise HTTPException(status_code=403, detail="無權查看此合約工作時段")

        schedules = await supabase_service.table_select(
            table="teacher_work_schedules",
            select="id,teacher_contract_id,weekday,start_time,end_time,notes,created_at,updated_at",
            filters={
                "teacher_contract_id": f"eq.{contract_id}",
                "is_deleted": "eq.false"
            },
        )

        return {"data": [TeacherWorkScheduleResponse(**s) for s in schedules]}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得工作時段失敗: {str(e)}")


@router.put("/{contract_id}/work-schedules")
async def set_work_schedules(
    contract_id: str,
    data: TeacherWorkScheduleBatchSet,
    current_user: CurrentUser = Depends(require_page_permission("teachers.contracts"))
):
    """全量替換合約工作時段（soft delete 舊的 + insert 新的）"""
    try:
        contract = await supabase_service.table_select(
            table="teacher_contracts",
            select="id",
            filters={"id": contract_id, "is_deleted": "eq.false"},
        )
        if not contract:
            raise HTTPException(status_code=404, detail="教師合約不存在")

        # 檢查同 weekday 時段重疊
        by_weekday: dict[int, list[TeacherWorkScheduleCreate]] = {}
        for s in data.schedules:
            by_weekday.setdefault(s.weekday, []).append(s)

        for weekday, slots in by_weekday.items():
            sorted_slots = sorted(slots, key=lambda x: x.start_time)
            for i in range(len(sorted_slots) - 1):
                if sorted_slots[i].end_time > sorted_slots[i + 1].start_time:
                    weekday_names = ['週一', '週二', '週三', '週四', '週五', '週六', '週日']
                    raise HTTPException(
                        status_code=400,
                        detail=f"{weekday_names[weekday]}的工作時段有重疊"
                    )

        employee_id = await get_user_employee_id(current_user.user_id)
        now = datetime.utcnow().isoformat()

        # Soft delete 舊的
        old_schedules = await supabase_service.table_select(
            table="teacher_work_schedules",
            select="id",
            filters={
                "teacher_contract_id": f"eq.{contract_id}",
                "is_deleted": "eq.false"
            },
        )
        for old in old_schedules:
            delete_data = {"is_deleted": True, "deleted_at": now}
            if employee_id:
                delete_data["deleted_by"] = employee_id
            await supabase_service.table_update(
                table="teacher_work_schedules",
                data=delete_data,
                filters={"id": old["id"]},
            )

        # Insert 新的
        inserted = []
        for s in data.schedules:
            schedule_data = {
                "teacher_contract_id": contract_id,
                "weekday": s.weekday,
                "start_time": s.start_time.isoformat(),
                "end_time": s.end_time.isoformat(),
                "notes": s.notes,
            }
            if employee_id:
                schedule_data["created_by"] = employee_id

            result = await supabase_service.table_insert(
                table="teacher_work_schedules",
                data=schedule_data,
            )
            if result:
                inserted.append(result)

        return {
            "message": "工作時段更新成功",
            "data": [TeacherWorkScheduleResponse(**s) for s in inserted]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新工作時段失敗: {str(e)}")


@router.delete("/{contract_id}/work-schedules", response_model=BaseResponse)
async def clear_work_schedules(
    contract_id: str,
    current_user: CurrentUser = Depends(require_page_permission("teachers.contracts"))
):
    """清除合約所有工作時段（soft delete）"""
    try:
        contract = await supabase_service.table_select(
            table="teacher_contracts",
            select="id",
            filters={"id": contract_id, "is_deleted": "eq.false"},
        )
        if not contract:
            raise HTTPException(status_code=404, detail="教師合約不存在")

        employee_id = await get_user_employee_id(current_user.user_id)
        now = datetime.utcnow().isoformat()

        old_schedules = await supabase_service.table_select(
            table="teacher_work_schedules",
            select="id",
            filters={
                "teacher_contract_id": f"eq.{contract_id}",
                "is_deleted": "eq.false"
            },
        )
        for old in old_schedules:
            delete_data = {"is_deleted": True, "deleted_at": now}
            if employee_id:
                delete_data["deleted_by"] = employee_id
            await supabase_service.table_update(
                table="teacher_work_schedules",
                data=delete_data,
                filters={"id": old["id"]},
            )

        return BaseResponse(message="工作時段已清除")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清除工作時段失敗: {str(e)}")


# ========== PDF Generation ==========

@router.get("/{contract_id}/generate-pdf")
async def generate_teacher_pdf(
    contract_id: str,
    current_user: CurrentUser = Depends(require_page_permission("teachers.contracts"))
):
    """產生教師合約 PDF（僅限員工）"""
    try:
        result = await generate_teacher_contract_pdf(contract_id)
        if not result:
            raise HTTPException(status_code=404, detail="教師合約不存在")

        pdf_bytes, contract_no = result
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{contract_no}.pdf"'
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"產生合約 PDF 失敗: {str(e)}")


# ========== File Upload/Download (unchanged) ==========

class ConfirmUploadRequest(BaseModel):
    """確認上傳請求"""
    storage_path: str
    file_name: str


@router.post("/{contract_id}/upload-url")
async def get_teacher_contract_upload_url(
    contract_id: str,
    current_user: CurrentUser = Depends(require_page_permission("teachers.contracts"))
):
    """取得教師合約檔案的 signed upload URL（僅限員工）

    前端收到後直接 PUT 檔案到該 URL，上傳完成後呼叫 confirm-upload。
    """
    try:
        existing = await supabase_service.table_select(
            table="teacher_contracts",
            select="id",
            filters={"id": contract_id, "is_deleted": "eq.false"},
        )
        if not existing:
            raise HTTPException(status_code=404, detail="教師合約不存在")

        await storage_service.ensure_bucket_exists(settings.AWS_S3_BUCKET)

        safe_filename = f"{uuid.uuid4().hex}.pdf"
        storage_path = f"teacher-contracts/{contract_id}/{safe_filename}"

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


@router.post("/{contract_id}/confirm-upload", response_model=DataResponse[TeacherContractResponse])
async def confirm_teacher_contract_upload(
    contract_id: str,
    body: ConfirmUploadRequest,
    current_user: CurrentUser = Depends(require_page_permission("teachers.contracts"))
):
    """確認教師合約檔案上傳完成（僅限員工）

    前端直接上傳 S3 成功後呼叫此 API，更新 DB 並將狀態改為 active。
    """
    try:
        existing = await supabase_service.table_select(
            table="teacher_contracts",
            select="id,teacher_id",
            filters={"id": contract_id, "is_deleted": "eq.false"},
        )
        if not existing:
            raise HTTPException(status_code=404, detail="教師合約不存在")

        # 檢查 active 合約唯一性（上傳確認會自動設為 active）
        check_teacher_id = existing[0].get("teacher_id")
        if check_teacher_id:
            conflict = await check_teacher_active_conflict(check_teacher_id, exclude_contract_id=contract_id)
            if conflict:
                raise HTTPException(
                    status_code=400,
                    detail=f"該教師已有生效中的合約 (合約編號: {conflict['contract_no']}, ID: {conflict['id']})"
                )

        # 驗證 storage_path 格式
        if not re.match(r'^teacher-contracts/[a-f0-9\-]+/[a-f0-9]+\.pdf$', body.storage_path):
            raise HTTPException(status_code=400, detail="無效的檔案路徑格式")

        # 確認檔案已上傳至 S3
        file_exists = await storage_service.verify_file_exists(
            bucket=settings.AWS_S3_BUCKET,
            path=body.storage_path,
        )
        if not file_exists:
            raise HTTPException(status_code=400, detail="檔案尚未上傳至 S3，請重新上傳")

        employee_id = await get_user_employee_id(current_user.user_id)

        update_data = {
            "contract_file_path": body.storage_path,
            "contract_file_name": body.file_name,
            "contract_file_uploaded_at": datetime.utcnow().isoformat(),
            "contract_status": "active",
        }
        if employee_id:
            update_data["contract_file_uploaded_by"] = employee_id

        result = await supabase_service.table_update(
            table="teacher_contracts",
            data=update_data,
            filters={"id": contract_id},
        )

        if not result:
            raise HTTPException(status_code=500, detail="更新合約資訊失敗")

        enriched = await enrich_contract_with_relations(result)
        return DataResponse(
            message="合約檔案上傳成功，狀態已更新為生效中",
            data=TeacherContractResponse(**enriched)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"確認上傳失敗: {str(e)}")


@router.get("/{contract_id}/download-url")
async def get_teacher_contract_download_url(
    contract_id: str,
    current_user: CurrentUser = Depends(require_page_permission("teachers.contracts"))
):
    """取得教師合約檔案的 signed download URL

    權限控制:
    - 教師: 僅能下載自己的合約
    - 學生: 無法下載教師合約
    - 員工/管理員: 可下載所有合約
    """
    try:
        if current_user.is_student():
            raise HTTPException(status_code=403, detail="學生無權下載教師合約")

        result = await supabase_service.table_select(
            table="teacher_contracts",
            select="id,teacher_id,contract_file_path,contract_file_name",
            filters={"id": contract_id, "is_deleted": "eq.false"},
        )

        if not result:
            raise HTTPException(status_code=404, detail="教師合約不存在")

        contract = result[0]

        if current_user.is_teacher():
            user_teacher_id = current_user.teacher_id
            if contract.get("teacher_id") != user_teacher_id:
                raise HTTPException(status_code=403, detail="無權下載此合約")

        file_path = contract.get("contract_file_path")
        if not file_path:
            raise HTTPException(status_code=404, detail="此合約尚未上傳檔案")

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


# ========== Contract Addendums (附約) ==========

ADDENDUM_SELECT = "id,addendum_no,contract_type,parent_contract_id,original_end_date,new_end_date,addendum_status,file_path,file_name,file_uploaded_at,notes,created_at,updated_at"


async def _enrich_teacher_addendum(addendum: dict, contract: dict = None) -> dict:
    """為附約添加 parent_contract_no 和 person_name"""
    if not contract:
        result = await supabase_service.table_select(
            table="teacher_contracts",
            select="contract_no,teacher_id",
            filters={"id": addendum["parent_contract_id"], "is_deleted": "eq.false"},
        )
        contract = result[0] if result else {}

    addendum["parent_contract_no"] = contract.get("contract_no")
    if contract.get("teacher_id"):
        teacher = await supabase_service.table_select(
            table="teachers", select="name",
            filters={"id": contract["teacher_id"]},
        )
        addendum["person_name"] = teacher[0]["name"] if teacher else None
    return addendum


async def _generate_teacher_addendum_no(parent_contract_no: str, parent_contract_id: str) -> str:
    """生成附約編號: {母約編號}-A{序號}（序號計入已刪除的）"""
    result = await supabase_service.table_select(
        table="contract_addendums",
        select="addendum_no",
        filters={
            "parent_contract_id": f"eq.{parent_contract_id}",
        },
    )
    max_seq = 0
    prefix = f"{parent_contract_no}-A"
    for item in result:
        no = item.get("addendum_no", "")
        if no.startswith(prefix):
            try:
                seq = int(no[len(prefix):])
                max_seq = max(max_seq, seq)
            except ValueError:
                pass
    return f"{prefix}{max_seq + 1}"


@router.get("/{contract_id}/addendums", response_model=ContractAddendumListResponse)
async def list_teacher_addendums(
    contract_id: str,
    current_user: CurrentUser = Depends(require_page_permission("teachers.contracts"))
):
    """取得教師合約附約列表"""
    try:
        contract = await supabase_service.table_select(
            table="teacher_contracts",
            select="id,contract_no,teacher_id",
            filters={"id": contract_id, "is_deleted": "eq.false"},
        )
        if not contract:
            raise HTTPException(status_code=404, detail="教師合約不存在")

        addendums = await supabase_service.table_select(
            table="contract_addendums",
            select=ADDENDUM_SELECT,
            filters={
                "contract_type": "eq.teacher",
                "parent_contract_id": f"eq.{contract_id}",
                "is_deleted": "eq.false",
            },
        )

        enriched = []
        for a in addendums:
            a = await _enrich_teacher_addendum(a, contract[0])
            enriched.append(ContractAddendumResponse(**a))

        return ContractAddendumListResponse(data=enriched)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得附約列表失敗: {str(e)}")


@router.post("/{contract_id}/addendums", response_model=DataResponse[ContractAddendumResponse])
async def create_teacher_addendum(
    contract_id: str,
    data: ContractAddendumCreate,
    current_user: CurrentUser = Depends(require_page_permission("teachers.contracts"))
):
    """建立教師合約附約（僅限員工）"""
    try:
        contract = await supabase_service.table_select(
            table="teacher_contracts",
            select="id,contract_no,teacher_id,contract_status,end_date",
            filters={"id": contract_id, "is_deleted": "eq.false"},
        )
        if not contract:
            raise HTTPException(status_code=404, detail="教師合約不存在")

        parent = contract[0]
        if parent["contract_status"] != "active":
            raise HTTPException(status_code=400, detail="只有生效中的合約才能建立附約")

        if data.new_end_date.isoformat() <= parent["end_date"]:
            raise HTTPException(status_code=400, detail="新結束日期必須大於母約當前結束日期")

        addendum_no = await _generate_teacher_addendum_no(parent["contract_no"], contract_id)

        addendum_data = {
            "addendum_no": addendum_no,
            "contract_type": "teacher",
            "parent_contract_id": contract_id,
            "original_end_date": parent["end_date"],
            "new_end_date": data.new_end_date.isoformat(),
            "addendum_status": "pending",
            "notes": data.notes,
        }

        employee_id = await get_user_employee_id(current_user.user_id)
        if employee_id:
            addendum_data["created_by"] = employee_id

        result = await supabase_service.table_insert(
            table="contract_addendums",
            data=addendum_data,
        )
        if not result:
            raise HTTPException(status_code=500, detail="建立附約失敗")

        result = await _enrich_teacher_addendum(result, parent)
        return DataResponse(message="附約建立成功", data=ContractAddendumResponse(**result))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"建立附約失敗: {str(e)}")


@router.get("/{contract_id}/addendums/{addendum_id}", response_model=DataResponse[ContractAddendumResponse])
async def get_teacher_addendum(
    contract_id: str,
    addendum_id: str,
    current_user: CurrentUser = Depends(require_page_permission("teachers.contracts"))
):
    """取得單一教師合約附約"""
    try:
        result = await supabase_service.table_select(
            table="contract_addendums",
            select=ADDENDUM_SELECT,
            filters={
                "id": addendum_id,
                "parent_contract_id": f"eq.{contract_id}",
                "contract_type": "eq.teacher",
                "is_deleted": "eq.false",
            },
        )
        if not result:
            raise HTTPException(status_code=404, detail="附約不存在")

        enriched = await _enrich_teacher_addendum(result[0])
        return DataResponse(data=ContractAddendumResponse(**enriched))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得附約失敗: {str(e)}")


@router.put("/{contract_id}/addendums/{addendum_id}", response_model=DataResponse[ContractAddendumResponse])
async def update_teacher_addendum(
    contract_id: str,
    addendum_id: str,
    data: ContractAddendumUpdate,
    current_user: CurrentUser = Depends(require_page_permission("teachers.contracts"))
):
    """更新教師合約附約（僅限員工，pending 狀態才可修改）"""
    try:
        existing = await supabase_service.table_select(
            table="contract_addendums",
            select="id,addendum_status,original_end_date,parent_contract_id",
            filters={
                "id": addendum_id,
                "parent_contract_id": f"eq.{contract_id}",
                "contract_type": "eq.teacher",
                "is_deleted": "eq.false",
            },
        )
        if not existing:
            raise HTTPException(status_code=404, detail="附約不存在")

        if existing[0]["addendum_status"] != "pending":
            raise HTTPException(status_code=400, detail="只有待生效狀態的附約才可修改")

        update_data = {}
        if data.new_end_date is not None:
            original = existing[0]["original_end_date"]
            if data.new_end_date.isoformat() <= original:
                raise HTTPException(status_code=400, detail="新結束日期必須大於原結束日期")
            update_data["new_end_date"] = data.new_end_date.isoformat()
        if data.notes is not None:
            update_data["notes"] = data.notes

        if not update_data:
            raise HTTPException(status_code=400, detail="沒有要更新的資料")

        employee_id = await get_user_employee_id(current_user.user_id)
        if employee_id:
            update_data["updated_by"] = employee_id

        result = await supabase_service.table_update(
            table="contract_addendums",
            data=update_data,
            filters={"id": addendum_id},
        )
        if not result:
            raise HTTPException(status_code=500, detail="更新附約失敗")

        enriched = await _enrich_teacher_addendum(result)
        return DataResponse(message="附約更新成功", data=ContractAddendumResponse(**enriched))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新附約失敗: {str(e)}")


@router.delete("/{contract_id}/addendums/{addendum_id}", response_model=BaseResponse)
async def delete_teacher_addendum(
    contract_id: str,
    addendum_id: str,
    current_user: CurrentUser = Depends(require_page_permission("teachers.contracts"))
):
    """刪除教師合約附約（軟刪除，僅限員工）"""
    try:
        existing = await supabase_service.table_select(
            table="contract_addendums",
            select="id",
            filters={
                "id": addendum_id,
                "parent_contract_id": f"eq.{contract_id}",
                "contract_type": "eq.teacher",
                "is_deleted": "eq.false",
            },
        )
        if not existing:
            raise HTTPException(status_code=404, detail="附約不存在")

        employee_id = await get_user_employee_id(current_user.user_id)
        delete_data = {
            "is_deleted": True,
            "deleted_at": datetime.utcnow().isoformat(),
        }
        if employee_id:
            delete_data["deleted_by"] = employee_id

        result = await supabase_service.table_update(
            table="contract_addendums",
            data=delete_data,
            filters={"id": addendum_id},
        )
        if not result:
            raise HTTPException(status_code=500, detail="刪除附約失敗")

        return BaseResponse(message="附約刪除成功")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刪除附約失敗: {str(e)}")


@router.get("/{contract_id}/addendums/{addendum_id}/generate-pdf")
async def generate_teacher_addendum_pdf(
    contract_id: str,
    addendum_id: str,
    current_user: CurrentUser = Depends(require_page_permission("teachers.contracts"))
):
    """產生教師合約附約 PDF"""
    try:
        existing = await supabase_service.table_select(
            table="contract_addendums",
            select="id",
            filters={
                "id": addendum_id,
                "parent_contract_id": f"eq.{contract_id}",
                "contract_type": "eq.teacher",
                "is_deleted": "eq.false",
            },
        )
        if not existing:
            raise HTTPException(status_code=404, detail="附約不存在")

        result = await generate_addendum_pdf(addendum_id)
        if not result:
            raise HTTPException(status_code=404, detail="產生附約 PDF 失敗")

        pdf_bytes, addendum_no = result
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{addendum_no}.pdf"'
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"產生附約 PDF 失敗: {str(e)}")


class AddendumConfirmUploadRequest(BaseModel):
    """附約確認上傳請求"""
    storage_path: str
    file_name: str


@router.post("/{contract_id}/addendums/{addendum_id}/upload-url")
async def get_teacher_addendum_upload_url(
    contract_id: str,
    addendum_id: str,
    current_user: CurrentUser = Depends(require_page_permission("teachers.contracts"))
):
    """取得教師合約附約的 S3 上傳 URL"""
    try:
        existing = await supabase_service.table_select(
            table="contract_addendums",
            select="id",
            filters={
                "id": addendum_id,
                "parent_contract_id": f"eq.{contract_id}",
                "contract_type": "eq.teacher",
                "is_deleted": "eq.false",
            },
        )
        if not existing:
            raise HTTPException(status_code=404, detail="附約不存在")

        await storage_service.ensure_bucket_exists(settings.AWS_S3_BUCKET)

        safe_filename = f"{uuid.uuid4().hex}.pdf"
        storage_path = f"contract-addendums/{addendum_id}/{safe_filename}"

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


@router.post("/{contract_id}/addendums/{addendum_id}/confirm-upload", response_model=DataResponse[ContractAddendumResponse])
async def confirm_teacher_addendum_upload(
    contract_id: str,
    addendum_id: str,
    body: AddendumConfirmUploadRequest,
    current_user: CurrentUser = Depends(require_page_permission("teachers.contracts"))
):
    """確認教師合約附約上傳完成 → active + 更新母約 end_date"""
    try:
        existing = await supabase_service.table_select(
            table="contract_addendums",
            select="id,new_end_date",
            filters={
                "id": addendum_id,
                "parent_contract_id": f"eq.{contract_id}",
                "contract_type": "eq.teacher",
                "is_deleted": "eq.false",
            },
        )
        if not existing:
            raise HTTPException(status_code=404, detail="附約不存在")

        if not re.match(r'^contract-addendums/[a-f0-9\-]+/[a-f0-9]+\.pdf$', body.storage_path):
            raise HTTPException(status_code=400, detail="無效的檔案路徑格式")

        file_exists = await storage_service.verify_file_exists(
            bucket=settings.AWS_S3_BUCKET,
            path=body.storage_path,
        )
        if not file_exists:
            raise HTTPException(status_code=400, detail="檔案尚未上傳至 S3，請重新上傳")

        # 再次驗證母約仍為 active
        parent = await supabase_service.table_select(
            table="teacher_contracts",
            select="id,contract_status",
            filters={"id": contract_id, "is_deleted": "eq.false"},
        )
        if not parent or parent[0]["contract_status"] != "active":
            raise HTTPException(status_code=400, detail="母約狀態不是生效中，無法確認附約")

        employee_id = await get_user_employee_id(current_user.user_id)

        update_data = {
            "file_path": body.storage_path,
            "file_name": body.file_name,
            "file_uploaded_at": datetime.utcnow().isoformat(),
            "addendum_status": "active",
        }
        if employee_id:
            update_data["updated_by"] = employee_id

        result = await supabase_service.table_update(
            table="contract_addendums",
            data=update_data,
            filters={"id": addendum_id},
        )
        if not result:
            raise HTTPException(status_code=500, detail="更新附約失敗")

        # 更新母約 end_date
        new_end_date = existing[0]["new_end_date"]
        await supabase_service.table_update(
            table="teacher_contracts",
            data={"end_date": new_end_date},
            filters={"id": contract_id},
        )

        enriched = await _enrich_teacher_addendum(result)
        return DataResponse(
            message="附約上傳成功，母約結束日期已更新",
            data=ContractAddendumResponse(**enriched)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"確認上傳失敗: {str(e)}")


@router.get("/{contract_id}/addendums/{addendum_id}/download-url")
async def get_teacher_addendum_download_url(
    contract_id: str,
    addendum_id: str,
    current_user: CurrentUser = Depends(require_page_permission("teachers.contracts"))
):
    """取得教師合約附約的下載 URL"""
    try:
        result = await supabase_service.table_select(
            table="contract_addendums",
            select="id,file_path,file_name",
            filters={
                "id": addendum_id,
                "parent_contract_id": f"eq.{contract_id}",
                "contract_type": "eq.teacher",
                "is_deleted": "eq.false",
            },
        )
        if not result:
            raise HTTPException(status_code=404, detail="附約不存在")

        file_path = result[0].get("file_path")
        if not file_path:
            raise HTTPException(status_code=404, detail="此附約尚未上傳檔案")

        signed_url = await storage_service.create_signed_download_url(
            bucket=settings.AWS_S3_BUCKET,
            path=file_path,
            expires_in=3600,
        )
        if not signed_url:
            raise HTTPException(status_code=500, detail="產生下載連結失敗")

        return {
            "download_url": signed_url,
            "file_name": result[0].get("file_name", "addendum.pdf"),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得下載連結失敗: {str(e)}")

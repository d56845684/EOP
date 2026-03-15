from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from app.services.supabase_service import supabase_service
from app.services.storage_service import storage_service
from app.config import settings
from app.core.dependencies import get_current_user, CurrentUser, require_staff, require_page_permission, get_user_employee_id
from app.schemas.teacher_contract import (
    TeacherContractCreate, TeacherContractUpdate, TeacherContractResponse,
    TeacherContractListResponse, ContractStatus, EmploymentType,
    TeacherContractDetailCreate, TeacherContractDetailUpdate, TeacherContractDetailResponse
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

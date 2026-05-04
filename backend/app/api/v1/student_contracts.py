from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

# 合約上傳允許的格式
CONTRACT_ALLOWED_TYPES = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "doc": "application/msword",
}
CONTRACT_ALLOWED_EXT_REGEX = r"\.(pdf|docx|doc)"
from app.services.supabase_service import supabase_service
from app.services.storage_service import storage_service
from app.services.contract_pdf_service import generate_student_contract_pdf, generate_addendum_pdf, generate_student_contract_docx
from app.config import settings
from app.core.dependencies import get_current_user, CurrentUser, require_staff, require_page_permission, get_user_employee_id
from app.schemas.student_contract import (
    StudentContractCreate, StudentContractUpdate, StudentContractResponse,
    StudentContractListResponse, ContractStatus,
    StudentContractDetailCreate, StudentContractDetailUpdate, StudentContractDetailResponse,
    StudentContractLeaveRecordCreate, StudentContractLeaveRecordResponse
)
from app.schemas.contract_addendum import (
    ContractAddendumCreate, ContractAddendumUpdate,
    ContractAddendumResponse, ContractAddendumListResponse,
)
from app.schemas.response import BaseResponse, DataResponse, UploadUrlResponse, DownloadUrlResponse, StudentOption, CourseOption, TeacherOption
from typing import Optional, List
from datetime import datetime
import math
import uuid
import re

router = APIRouter(prefix="/student-contracts", tags=["學生合約管理"])

CONTRACT_SELECT = "id,contract_no,student_id,contract_status,start_date,end_date,total_lessons,remaining_lessons,total_amount,total_leave_allowed,used_leave_count,used_emergency_leave_count,is_recurring,notes,created_at,updated_at,contract_file_path,contract_file_name,contract_file_uploaded_at"


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
    # 取得學生名稱 + 電話 + 身分證字號
    if contract.get("student_id"):
        student = await supabase_service.table_select(
            table="students",
            select="name,phone,id_number",
            filters={"id": contract["student_id"]},
        )
        if student:
            contract["student_name"] = student[0]["name"]
            contract["student_phone"] = student[0].get("phone")
            contract["student_id_number"] = student[0].get("id_number")
        else:
            contract["student_name"] = None
            contract["student_phone"] = None
            contract["student_id_number"] = None

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

    # 計算緊急請假額度（堂數 = total_lessons + 補償堂數）
    total_lessons = contract.get("total_lessons", 0) or 0
    compensation_total = sum(
        int(d.get("amount", 0) or 0)
        for d in enriched_details
        if d.get("detail_type") == "compensation"
    )
    effective_lessons = total_lessons + compensation_total
    contract["emergency_leave_quota"] = math.ceil(effective_lessons * 0.2) if effective_lessons else 0
    used_em = contract.get("used_emergency_leave_count", 0) or 0
    contract["remaining_emergency_leave_count"] = max(0, contract["emergency_leave_quota"] - used_em)

    # 取得附約列表
    addendums = await supabase_service.table_select(
        table="contract_addendums",
        select="id,addendum_no,contract_type,parent_contract_id,original_end_date,new_end_date,addendum_status,file_path,file_name,file_uploaded_at,notes,created_at,updated_at",
        filters={
            "contract_type": "eq.student",
            "parent_contract_id": f"eq.{contract['id']}",
            "is_deleted": "eq.false",
        },
    )
    for a in addendums:
        a["parent_contract_no"] = contract.get("contract_no")
        a["person_name"] = contract.get("student_name")
    contract["addendums"] = addendums

    return contract


# ========== Options ==========

@router.get("/options/students", tags=["學生合約管理"], response_model=DataResponse[List[StudentOption]])
async def get_student_options(
    current_user: CurrentUser = Depends(require_page_permission("students.contracts"))
):
    """取得學生下拉選單"""
    try:
        students = await supabase_service.table_select(
            table="students",
            select="id,student_no,name",
            filters={"is_deleted": "eq.false", "is_active": "eq.true"},
        )
        return {"success": True, "message": "操作成功", "data": students}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/options/courses", tags=["學生合約管理"], response_model=DataResponse[List[CourseOption]])
async def get_course_options(
    student_id: Optional[str] = Query(None, description="若提供，只回傳該學生已選修的課程"),
    current_user: CurrentUser = Depends(require_page_permission("students.contracts"))
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
                return {"success": True, "message": "操作成功", "data": []}

            course_ids = [e["course_id"] for e in enrollments]

            # 批次查詢（取代逐一查詢）
            pool = supabase_service.pool
            import uuid as _uuid
            uid_list = [_uuid.UUID(cid) if isinstance(cid, str) else cid for cid in course_ids]
            rows = await pool.fetch(
                """SELECT id, course_code, course_name FROM courses
                   WHERE id = ANY($1) AND is_deleted = FALSE AND is_active = TRUE""",
                uid_list,
            )
            courses = [{"id": str(r["id"]), "course_code": r["course_code"], "course_name": r["course_name"]} for r in rows]

            return {"success": True, "message": "操作成功", "data": courses}
        else:
            courses = await supabase_service.table_select(
                table="courses",
                select="id,course_code,course_name",
                filters={"is_deleted": "eq.false", "is_active": "eq.true"},
            )
            return {"success": True, "message": "操作成功", "data": courses}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/options/teachers", tags=["學生合約管理"], response_model=DataResponse[List[TeacherOption]])
async def get_teacher_options(
    current_user: CurrentUser = Depends(require_page_permission("students.contracts"))
):
    """取得教師下拉選單"""
    try:
        teachers = await supabase_service.table_select(
            table="teachers",
            select="id,teacher_no,name",
            filters={"is_deleted": "eq.false", "is_active": "eq.true"},
        )
        return {"success": True, "message": "操作成功", "data": teachers}
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
    current_user: CurrentUser = Depends(require_page_permission("students.contracts"))
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
            user_student_id = current_user.student_id
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
        total = await supabase_service.table_count(table="student_contracts", filters=filters)

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

        # 為合約批次加載關聯資料（取代 N+1 enrich 迴圈）
        if not contracts:
            return StudentContractListResponse(data=[], total=total, page=page, per_page=per_page, total_pages=total_pages)

        contract_ids = [c["id"] for c in contracts]
        student_ids = list({c["student_id"] for c in contracts if c.get("student_id")})
        pool = supabase_service.pool

        import asyncio as _aio
        async def _empty(): return []

        # 批次查詢：學生名稱、明細(含課程名)、請假、附約 — 並行
        students_task = pool.fetch(
            "SELECT id, name, phone, id_number FROM students WHERE id = ANY($1)",
            student_ids,
        ) if student_ids else _empty()

        details_task = pool.fetch(
            """SELECT d.id, d.student_contract_id, d.detail_type, d.course_id,
                      d.description, d.amount, d.notes, d.created_at, d.updated_at,
                      c.course_name
               FROM student_contract_details d
               LEFT JOIN courses c ON c.id = d.course_id
               WHERE d.student_contract_id = ANY($1) AND d.is_deleted = FALSE""",
            contract_ids,
        )

        leaves_task = pool.fetch(
            """SELECT id, student_contract_id, leave_date, reason, created_at
               FROM student_contract_leave_records
               WHERE student_contract_id = ANY($1) AND is_deleted = FALSE""",
            contract_ids,
        )

        addendums_task = pool.fetch(
            """SELECT id, addendum_no, contract_type, parent_contract_id,
                      original_end_date, new_end_date, addendum_status,
                      file_path, file_name, file_uploaded_at, notes, created_at, updated_at
               FROM contract_addendums
               WHERE contract_type = 'student' AND parent_contract_id = ANY($1)
                 AND is_deleted = FALSE""",
            contract_ids,
        )

        student_rows, detail_rows, leave_rows, addendum_rows = await _aio.gather(
            students_task, details_task, leaves_task, addendums_task
        )

        # asyncpg Record → dict，UUID → str
        import uuid as _uuid
        def _to_dict(row):
            d = dict(row)
            for k, v in d.items():
                if isinstance(v, _uuid.UUID):
                    d[k] = str(v)
            return d

        # 建立 lookup maps
        student_map = {str(r["id"]): r for r in student_rows}
        detail_map: dict[str, list] = {}
        for d in detail_rows:
            key = str(d["student_contract_id"])
            detail_map.setdefault(key, []).append(_to_dict(d))
        leave_map: dict[str, list] = {}
        for l in leave_rows:
            key = str(l["student_contract_id"])
            leave_map.setdefault(key, []).append(_to_dict(l))
        addendum_map: dict[str, list] = {}
        for a in addendum_rows:
            key = str(a["parent_contract_id"])
            addendum_map.setdefault(key, []).append(_to_dict(a))

        # 組裝
        enriched_contracts = []
        for contract in contracts:
            cid = contract["id"]
            sid = contract.get("student_id")
            student = student_map.get(str(sid)) if sid else None
            contract["student_name"] = student["name"] if student else None
            contract["student_phone"] = student.get("phone") if student else None
            contract["student_id_number"] = student.get("id_number") if student else None
            contract["details"] = detail_map.get(str(cid), [])
            contract["leave_records"] = leave_map.get(str(cid), [])
            total_lessons = contract.get("total_lessons", 0) or 0
            compensation_total = sum(
                int(d.get("amount", 0) or 0)
                for d in contract["details"]
                if d.get("detail_type") == "compensation"
            )
            effective_lessons = total_lessons + compensation_total
            contract["emergency_leave_quota"] = math.ceil(effective_lessons * 0.2) if effective_lessons else 0
            used_em = contract.get("used_emergency_leave_count", 0) or 0
            contract["remaining_emergency_leave_count"] = max(0, contract["emergency_leave_quota"] - used_em)
            addendums = addendum_map.get(str(cid), [])
            for a in addendums:
                a["parent_contract_no"] = contract.get("contract_no")
                a["person_name"] = contract.get("student_name")
            contract["addendums"] = addendums
            enriched_contracts.append(contract)

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
    current_user: CurrentUser = Depends(require_page_permission("students.contracts"))
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
            user_student_id = current_user.student_id
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
    current_user: CurrentUser = Depends(require_page_permission("students.contracts"))
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
        total_leave_allowed = data.total_leave_allowed if data.total_leave_allowed is not None else math.ceil(data.total_lessons * 0.2)

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

        # 同步學生狀態
        from app.services.student_status_service import sync_student_status
        if contract_data.get("student_id"):
            await sync_student_status(str(contract_data["student_id"]))

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
    current_user: CurrentUser = Depends(require_page_permission("students.contracts"))
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

        # 合約狀態變更 → 同步學生狀態
        if data.contract_status:
            from app.services.student_status_service import sync_student_status
            student_id = data.student_id or existing[0].get("student_id")
            if student_id:
                await sync_student_status(str(student_id))

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
    current_user: CurrentUser = Depends(require_page_permission("students.contracts"))
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

        # 同步學生狀態
        from app.services.student_status_service import sync_student_status
        student_id = existing[0].get("student_id")
        if student_id:
            await sync_student_status(str(student_id))

        return BaseResponse(message="學生合約刪除成功")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刪除學生合約失敗: {str(e)}")


# ========== Contract Details CRUD ==========

@router.get("/{contract_id}/details", response_model=DataResponse[List[StudentContractDetailResponse]])
async def list_contract_details(
    contract_id: str,
    current_user: CurrentUser = Depends(require_page_permission("students.contracts"))
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
            user_student_id = current_user.student_id
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

        return {"success": True, "message": "操作成功", "data": [StudentContractDetailResponse(**d) for d in enriched]}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得合約明細失敗: {str(e)}")


@router.post("/{contract_id}/details", response_model=DataResponse[StudentContractDetailResponse])
async def create_contract_detail(
    contract_id: str,
    data: StudentContractDetailCreate,
    current_user: CurrentUser = Depends(require_page_permission("students.contracts"))
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


@router.put("/{contract_id}/details/{detail_id}", response_model=DataResponse[StudentContractDetailResponse])
async def update_contract_detail(
    contract_id: str,
    detail_id: str,
    data: StudentContractDetailUpdate,
    current_user: CurrentUser = Depends(require_page_permission("students.contracts"))
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
    current_user: CurrentUser = Depends(require_page_permission("students.contracts"))
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

@router.get("/{contract_id}/leave-records", response_model=DataResponse[List[StudentContractLeaveRecordResponse]])
async def list_leave_records(
    contract_id: str,
    current_user: CurrentUser = Depends(require_page_permission("students.contracts"))
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
            user_student_id = current_user.student_id
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

        return {"success": True, "message": "操作成功", "data": [StudentContractLeaveRecordResponse(**r) for r in records]}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得請假紀錄失敗: {str(e)}")


@router.post("/{contract_id}/leave-records", response_model=DataResponse[StudentContractLeaveRecordResponse])
async def create_leave_record(
    contract_id: str,
    data: StudentContractLeaveRecordCreate,
    current_user: CurrentUser = Depends(require_page_permission("students.contracts"))
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
    current_user: CurrentUser = Depends(require_page_permission("students.contracts"))
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


# ========== PDF Generation ==========

@router.get("/{contract_id}/generate-pdf", deprecated=True)
async def generate_student_pdf(
    contract_id: str,
    current_user: CurrentUser = Depends(require_page_permission("students.contracts"))
):
    """[Deprecated] 產生學生合約 PDF — 請改用 generate-docx"""
    try:
        result = await generate_student_contract_pdf(contract_id)
        if not result:
            raise HTTPException(status_code=404, detail="學生合約不存在")

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


@router.get("/{contract_id}/generate-docx")
async def generate_student_docx(
    contract_id: str,
    current_user: CurrentUser = Depends(require_page_permission("students.contracts"))
):
    """產生學生合約 DOCX（基於 2026 新 EOP 課程合約範本）"""
    try:
        result = await generate_student_contract_docx(contract_id)
        if not result:
            raise HTTPException(status_code=404, detail="學生合約不存在")

        docx_bytes, filename = result
        from urllib.parse import quote
        encoded_filename = quote(filename)
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"產生合約 DOCX 失敗: {str(e)}")


# ========== File Upload/Download (unchanged) ==========

class ConfirmUploadRequest(BaseModel):
    """確認上傳請求"""
    storage_path: str
    file_name: str


@router.post("/{contract_id}/upload-url", response_model=UploadUrlResponse)
async def get_student_contract_upload_url(
    contract_id: str,
    file_ext: str = Query("pdf", description="檔案格式 (pdf/docx/doc)"),
    current_user: CurrentUser = Depends(require_page_permission("students.contracts"))
):
    """取得學生合約檔案的 signed upload URL（僅限員工，支援 pdf/docx/doc）"""
    try:
        ext = file_ext.lower().replace(".", "")
        if ext not in CONTRACT_ALLOWED_TYPES:
            raise HTTPException(status_code=400, detail=f"不支援的檔案格式: {ext}（允許 pdf/docx/doc）")

        existing = await supabase_service.table_select(
            table="student_contracts",
            select="id",
            filters={"id": contract_id, "is_deleted": "eq.false"},
        )
        if not existing:
            raise HTTPException(status_code=404, detail="學生合約不存在")

        await storage_service.ensure_bucket_exists(settings.AWS_S3_BUCKET)

        safe_filename = f"{uuid.uuid4().hex}.{ext}"
        storage_path = f"student-contracts/{contract_id}/{safe_filename}"

        signed = await storage_service.create_signed_upload_url(
            bucket=settings.AWS_S3_BUCKET,
            path=storage_path,
            content_type=CONTRACT_ALLOWED_TYPES[ext],
        )
        if not signed:
            raise HTTPException(status_code=500, detail="產生上傳連結失敗")

        return {
            "upload_url": signed["upload_url"],
            "storage_path": storage_path,
            "content_type": CONTRACT_ALLOWED_TYPES[ext],
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"產生上傳連結失敗: {str(e)}")


@router.post("/{contract_id}/confirm-upload", response_model=DataResponse[StudentContractResponse])
async def confirm_student_contract_upload(
    contract_id: str,
    body: ConfirmUploadRequest,
    current_user: CurrentUser = Depends(require_page_permission("students.contracts"))
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
        if not re.match(r'^student-contracts/[a-f0-9\-]+/[a-f0-9]+\.(pdf|docx|doc)$', body.storage_path):
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


@router.get("/{contract_id}/download-url", response_model=DownloadUrlResponse)
async def get_student_contract_download_url(
    contract_id: str,
    current_user: CurrentUser = Depends(require_page_permission("students.contracts"))
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
            user_student_id = current_user.student_id
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


# ========== Contract Addendums (附約) ==========

ADDENDUM_SELECT = "id,addendum_no,contract_type,parent_contract_id,original_end_date,new_end_date,addendum_status,file_path,file_name,file_uploaded_at,notes,created_at,updated_at"


async def _enrich_student_addendum(addendum: dict, contract: dict = None) -> dict:
    """為附約添加 parent_contract_no 和 person_name"""
    if not contract:
        result = await supabase_service.table_select(
            table="student_contracts",
            select="contract_no,student_id",
            filters={"id": addendum["parent_contract_id"], "is_deleted": "eq.false"},
        )
        contract = result[0] if result else {}

    addendum["parent_contract_no"] = contract.get("contract_no")
    if contract.get("student_id"):
        student = await supabase_service.table_select(
            table="students", select="name",
            filters={"id": contract["student_id"]},
        )
        addendum["person_name"] = student[0]["name"] if student else None
    return addendum


async def _generate_addendum_no(parent_contract_no: str, parent_contract_id: str) -> str:
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
async def list_student_addendums(
    contract_id: str,
    current_user: CurrentUser = Depends(require_page_permission("students.contracts"))
):
    """取得學生合約附約列表"""
    try:
        contract = await supabase_service.table_select(
            table="student_contracts",
            select="id,contract_no,student_id",
            filters={"id": contract_id, "is_deleted": "eq.false"},
        )
        if not contract:
            raise HTTPException(status_code=404, detail="學生合約不存在")

        addendums = await supabase_service.table_select(
            table="contract_addendums",
            select=ADDENDUM_SELECT,
            filters={
                "contract_type": "eq.student",
                "parent_contract_id": f"eq.{contract_id}",
                "is_deleted": "eq.false",
            },
        )

        enriched = []
        for a in addendums:
            a = await _enrich_student_addendum(a, contract[0])
            enriched.append(ContractAddendumResponse(**a))

        return ContractAddendumListResponse(data=enriched)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得附約列表失敗: {str(e)}")


@router.post("/{contract_id}/addendums", response_model=DataResponse[ContractAddendumResponse])
async def create_student_addendum(
    contract_id: str,
    data: ContractAddendumCreate,
    current_user: CurrentUser = Depends(require_page_permission("students.contracts"))
):
    """建立學生合約附約（僅限員工）"""
    try:
        contract = await supabase_service.table_select(
            table="student_contracts",
            select="id,contract_no,student_id,contract_status,end_date",
            filters={"id": contract_id, "is_deleted": "eq.false"},
        )
        if not contract:
            raise HTTPException(status_code=404, detail="學生合約不存在")

        parent = contract[0]
        if parent["contract_status"] != "active":
            raise HTTPException(status_code=400, detail="只有生效中的合約才能建立附約")

        if data.new_end_date.isoformat() <= parent["end_date"]:
            raise HTTPException(status_code=400, detail="新結束日期必須大於母約當前結束日期")

        addendum_no = await _generate_addendum_no(parent["contract_no"], contract_id)

        addendum_data = {
            "addendum_no": addendum_no,
            "contract_type": "student",
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

        result = await _enrich_student_addendum(result, parent)
        return DataResponse(message="附約建立成功", data=ContractAddendumResponse(**result))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"建立附約失敗: {str(e)}")


@router.get("/{contract_id}/addendums/{addendum_id}", response_model=DataResponse[ContractAddendumResponse])
async def get_student_addendum(
    contract_id: str,
    addendum_id: str,
    current_user: CurrentUser = Depends(require_page_permission("students.contracts"))
):
    """取得單一學生合約附約"""
    try:
        result = await supabase_service.table_select(
            table="contract_addendums",
            select=ADDENDUM_SELECT,
            filters={
                "id": addendum_id,
                "parent_contract_id": f"eq.{contract_id}",
                "contract_type": "eq.student",
                "is_deleted": "eq.false",
            },
        )
        if not result:
            raise HTTPException(status_code=404, detail="附約不存在")

        enriched = await _enrich_student_addendum(result[0])
        return DataResponse(data=ContractAddendumResponse(**enriched))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得附約失敗: {str(e)}")


@router.put("/{contract_id}/addendums/{addendum_id}", response_model=DataResponse[ContractAddendumResponse])
async def update_student_addendum(
    contract_id: str,
    addendum_id: str,
    data: ContractAddendumUpdate,
    current_user: CurrentUser = Depends(require_page_permission("students.contracts"))
):
    """更新學生合約附約（僅限員工，pending 狀態才可修改）"""
    try:
        existing = await supabase_service.table_select(
            table="contract_addendums",
            select="id,addendum_status,original_end_date,parent_contract_id",
            filters={
                "id": addendum_id,
                "parent_contract_id": f"eq.{contract_id}",
                "contract_type": "eq.student",
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

        enriched = await _enrich_student_addendum(result)
        return DataResponse(message="附約更新成功", data=ContractAddendumResponse(**enriched))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新附約失敗: {str(e)}")


@router.delete("/{contract_id}/addendums/{addendum_id}", response_model=BaseResponse)
async def delete_student_addendum(
    contract_id: str,
    addendum_id: str,
    current_user: CurrentUser = Depends(require_page_permission("students.contracts"))
):
    """刪除學生合約附約（軟刪除，僅限員工）"""
    try:
        existing = await supabase_service.table_select(
            table="contract_addendums",
            select="id",
            filters={
                "id": addendum_id,
                "parent_contract_id": f"eq.{contract_id}",
                "contract_type": "eq.student",
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
async def generate_student_addendum_pdf(
    contract_id: str,
    addendum_id: str,
    current_user: CurrentUser = Depends(require_page_permission("students.contracts"))
):
    """產生學生合約附約 PDF"""
    try:
        # 確認附約存在且屬於此合約
        existing = await supabase_service.table_select(
            table="contract_addendums",
            select="id",
            filters={
                "id": addendum_id,
                "parent_contract_id": f"eq.{contract_id}",
                "contract_type": "eq.student",
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


@router.post("/{contract_id}/addendums/{addendum_id}/upload-url", response_model=UploadUrlResponse)
async def get_student_addendum_upload_url(
    contract_id: str,
    addendum_id: str,
    current_user: CurrentUser = Depends(require_page_permission("students.contracts"))
):
    """取得學生合約附約的 S3 上傳 URL"""
    try:
        existing = await supabase_service.table_select(
            table="contract_addendums",
            select="id",
            filters={
                "id": addendum_id,
                "parent_contract_id": f"eq.{contract_id}",
                "contract_type": "eq.student",
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
            "content_type": "application/pdf",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"產生上傳連結失敗: {str(e)}")


@router.post("/{contract_id}/addendums/{addendum_id}/confirm-upload", response_model=DataResponse[ContractAddendumResponse])
async def confirm_student_addendum_upload(
    contract_id: str,
    addendum_id: str,
    body: AddendumConfirmUploadRequest,
    current_user: CurrentUser = Depends(require_page_permission("students.contracts"))
):
    """確認學生合約附約上傳完成 → active + 更新母約 end_date"""
    try:
        existing = await supabase_service.table_select(
            table="contract_addendums",
            select="id,new_end_date",
            filters={
                "id": addendum_id,
                "parent_contract_id": f"eq.{contract_id}",
                "contract_type": "eq.student",
                "is_deleted": "eq.false",
            },
        )
        if not existing:
            raise HTTPException(status_code=404, detail="附約不存在")

        # 驗證 storage_path 格式
        if not re.match(r'^contract-addendums/[a-f0-9\-]+/[a-f0-9]+\.(pdf|docx|doc)$', body.storage_path):
            raise HTTPException(status_code=400, detail="無效的檔案路徑格式")

        # 確認檔案已上傳
        file_exists = await storage_service.verify_file_exists(
            bucket=settings.AWS_S3_BUCKET,
            path=body.storage_path,
        )
        if not file_exists:
            raise HTTPException(status_code=400, detail="檔案尚未上傳至 S3，請重新上傳")

        # 再次驗證母約仍為 active
        parent = await supabase_service.table_select(
            table="student_contracts",
            select="id,contract_status",
            filters={"id": contract_id, "is_deleted": "eq.false"},
        )
        if not parent or parent[0]["contract_status"] != "active":
            raise HTTPException(status_code=400, detail="母約狀態不是生效中，無法確認附約")

        employee_id = await get_user_employee_id(current_user.user_id)

        # 更新附約
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
            table="student_contracts",
            data={"end_date": new_end_date},
            filters={"id": contract_id},
        )

        enriched = await _enrich_student_addendum(result)
        return DataResponse(
            message="附約上傳成功，母約結束日期已更新",
            data=ContractAddendumResponse(**enriched)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"確認上傳失敗: {str(e)}")


@router.get("/{contract_id}/addendums/{addendum_id}/download-url", response_model=DownloadUrlResponse)
async def get_student_addendum_download_url(
    contract_id: str,
    addendum_id: str,
    current_user: CurrentUser = Depends(require_page_permission("students.contracts"))
):
    """取得學生合約附約的下載 URL"""
    try:
        result = await supabase_service.table_select(
            table="contract_addendums",
            select="id,file_path,file_name",
            filters={
                "id": addendum_id,
                "parent_contract_id": f"eq.{contract_id}",
                "contract_type": "eq.student",
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

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from app.services.supabase_service import supabase_service
from app.services.storage_service import storage_service
from app.config import settings
from app.core.dependencies import get_current_user, CurrentUser, require_staff, require_teacher, get_user_employee_id
from app.schemas.teacher import TeacherCreate, TeacherUpdate, TeacherResponse, TeacherListResponse
from app.schemas.response import BaseResponse, DataResponse
from typing import Optional
from datetime import datetime
import math
import uuid

router = APIRouter(prefix="/teachers", tags=["教師管理"])

TEACHER_SELECT = "id,teacher_no,name,email,phone,address,bio,teacher_level,is_active,email_verified_at,created_at,updated_at"


@router.get("", response_model=TeacherListResponse)
async def list_teachers(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="搜尋（編號/姓名/email）"),
    is_active: Optional[bool] = Query(None),
    current_user: CurrentUser = Depends(get_current_user)
):
    """取得教師列表"""
    try:
        filters = {"is_deleted": "eq.false"}
        if is_active is not None:
            filters["is_active"] = f"eq.{str(is_active).lower()}"

        all_teachers = await supabase_service.table_select(
            table="teachers", select="id", filters=filters
        )
        total = len(all_teachers)
        total_pages = math.ceil(total / per_page) if total > 0 else 1
        offset = (page - 1) * per_page

        teachers = await supabase_service.table_select_with_pagination(
            table="teachers", select=TEACHER_SELECT, filters=filters,
            order_by="created_at.desc", limit=per_page, offset=offset
        )

        if search:
            s = search.lower()
            teachers = [
                t for t in teachers
                if s in t.get("teacher_no", "").lower()
                or s in t.get("name", "").lower()
                or s in t.get("email", "").lower()
            ]

        return TeacherListResponse(
            data=[TeacherResponse(**t) for t in teachers],
            total=total, page=page, per_page=per_page, total_pages=total_pages
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得教師列表失敗: {str(e)}")


# ========== 教師自我更新（必須在 /{teacher_id} 之前定義）==========

class TeacherSelfUpdate(BaseModel):
    """教師自行更新的欄位"""
    bio: Optional[str] = Field(None, description="簡介")
    phone: Optional[str] = Field(None, max_length=20, description="電話")
    address: Optional[str] = Field(None, description="地址")


@router.put("/me", response_model=DataResponse[TeacherResponse])
async def update_teacher_self(
    data: TeacherSelfUpdate,
    current_user: CurrentUser = Depends(require_teacher)
):
    """教師更新自己的資料（bio/phone/address）"""
    try:
        # 從 user_profiles 取得 teacher_id
        profiles = await supabase_service.table_select(
            table="user_profiles",
            select="teacher_id",
            filters={"id": current_user.user_id},
        )
        if not profiles or not profiles[0].get("teacher_id"):
            raise HTTPException(status_code=403, detail="找不到對應的教師資料")

        teacher_id = profiles[0]["teacher_id"]

        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        if not update_data:
            raise HTTPException(status_code=400, detail="沒有要更新的資料")

        result = await supabase_service.table_update(
            table="teachers", data=update_data,
            filters={"id": teacher_id, "is_deleted": "eq.false"},
        )
        if not result:
            raise HTTPException(status_code=500, detail="更新教師資料失敗")

        return DataResponse(message="教師資料更新成功", data=TeacherResponse(**result))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新教師資料失敗: {str(e)}")


@router.get("/{teacher_id}", response_model=DataResponse[TeacherResponse])
async def get_teacher(
    teacher_id: str,
    current_user: CurrentUser = Depends(get_current_user)
):
    """取得單一教師"""
    try:
        result = await supabase_service.table_select(
            table="teachers", select=TEACHER_SELECT,
            filters={"id": teacher_id, "is_deleted": "eq.false"}
        )
        if not result:
            raise HTTPException(status_code=404, detail="教師不存在")
        return DataResponse(data=TeacherResponse(**result[0]))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得教師失敗: {str(e)}")


@router.post("", response_model=DataResponse[TeacherResponse])
async def create_teacher(
    data: TeacherCreate,
    current_user: CurrentUser = Depends(require_staff)
):
    """建立教師（僅限員工）"""
    try:
        existing = await supabase_service.table_select(
            table="teachers", select="id",
            filters={"teacher_no": data.teacher_no, "is_deleted": "eq.false"}
        )
        if existing:
            raise HTTPException(status_code=400, detail="教師編號已存在")

        existing_email = await supabase_service.table_select(
            table="teachers", select="id",
            filters={"email": data.email, "is_deleted": "eq.false"}
        )
        if existing_email:
            raise HTTPException(status_code=400, detail="Email 已存在")

        teacher_data = data.model_dump()
        employee_id = await get_user_employee_id(current_user.user_id)
        if employee_id:
            teacher_data["created_by"] = employee_id

        result = await supabase_service.table_insert(
            table="teachers", data=teacher_data
        )
        if not result:
            raise HTTPException(status_code=500, detail="建立教師失敗")

        return DataResponse(message="教師建立成功", data=TeacherResponse(**result))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"建立教師失敗: {str(e)}")


@router.put("/{teacher_id}", response_model=DataResponse[TeacherResponse])
async def update_teacher(
    teacher_id: str,
    data: TeacherUpdate,
    current_user: CurrentUser = Depends(require_staff)
):
    """更新教師（僅限員工）"""
    try:
        existing = await supabase_service.table_select(
            table="teachers", select="id,teacher_no,email",
            filters={"id": teacher_id, "is_deleted": "eq.false"}
        )
        if not existing:
            raise HTTPException(status_code=404, detail="教師不存在")

        if data.email and data.email != existing[0]["email"]:
            dup = await supabase_service.table_select(
                table="teachers", select="id",
                filters={"email": data.email, "is_deleted": "eq.false"}
            )
            if dup:
                raise HTTPException(status_code=400, detail="Email 已存在")

        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        if not update_data:
            raise HTTPException(status_code=400, detail="沒有要更新的資料")

        result = await supabase_service.table_update(
            table="teachers", data=update_data, filters={"id": teacher_id}
        )
        if not result:
            raise HTTPException(status_code=500, detail="更新教師失敗")

        return DataResponse(message="教師更新成功", data=TeacherResponse(**result))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新教師失敗: {str(e)}")


@router.delete("/{teacher_id}", response_model=BaseResponse)
async def delete_teacher(
    teacher_id: str,
    current_user: CurrentUser = Depends(require_staff)
):
    """刪除教師（軟刪除，僅限員工）"""
    try:
        existing = await supabase_service.table_select(
            table="teachers", select="id",
            filters={"id": teacher_id, "is_deleted": "eq.false"}
        )
        if not existing:
            raise HTTPException(status_code=404, detail="教師不存在")

        result = await supabase_service.table_update(
            table="teachers",
            data={"is_deleted": True, "deleted_at": datetime.utcnow().isoformat()},
            filters={"id": teacher_id}
        )
        if not result:
            raise HTTPException(status_code=500, detail="刪除教師失敗")

        return BaseResponse(message="教師刪除成功")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刪除教師失敗: {str(e)}")


# ========== 教師頭像上傳 ==========

class AvatarConfirmRequest(BaseModel):
    """確認頭像上傳請求"""
    storage_path: str
    file_name: str


@router.post("/{teacher_id}/avatar/upload-url")
async def get_teacher_avatar_upload_url(
    teacher_id: str,
    current_user: CurrentUser = Depends(require_staff)
):
    """取得教師頭像的 signed upload URL（僅限員工）"""
    try:
        existing = await supabase_service.table_select(
            table="teachers", select="id",
            filters={"id": teacher_id, "is_deleted": "eq.false"},
        )
        if not existing:
            raise HTTPException(status_code=404, detail="教師不存在")

        await storage_service.ensure_bucket_exists(settings.AWS_S3_BUCKET)

        safe_filename = f"{uuid.uuid4().hex}.jpg"
        storage_path = f"teachers/{teacher_id}/avatar/{safe_filename}"

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


@router.post("/{teacher_id}/avatar/confirm-upload", response_model=DataResponse[TeacherResponse])
async def confirm_teacher_avatar_upload(
    teacher_id: str,
    body: AvatarConfirmRequest,
    current_user: CurrentUser = Depends(require_staff)
):
    """確認教師頭像上傳完成（僅限員工）"""
    try:
        existing = await supabase_service.table_select(
            table="teachers", select="id",
            filters={"id": teacher_id, "is_deleted": "eq.false"},
        )
        if not existing:
            raise HTTPException(status_code=404, detail="教師不存在")

        # 驗證 S3 檔案存在
        file_exists = await storage_service.verify_file_exists(
            bucket=settings.AWS_S3_BUCKET,
            path=body.storage_path
        )
        if not file_exists:
            raise HTTPException(status_code=400, detail="檔案尚未上傳至 S3")

        # 產生 avatar_url（使用 S3 path）
        result = await supabase_service.table_update(
            table="teachers",
            data={"avatar_url": body.storage_path},
            filters={"id": teacher_id},
        )
        if not result:
            raise HTTPException(status_code=500, detail="更新頭像失敗")

        return DataResponse(message="頭像上傳成功", data=TeacherResponse(**result))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"確認頭像上傳失敗: {str(e)}")

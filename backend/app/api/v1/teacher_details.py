from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from app.services.supabase_service import supabase_service
from app.services.storage_service import storage_service
from app.config import settings
from app.core.dependencies import get_current_user, CurrentUser, require_staff, require_page_permission, get_user_employee_id
from app.schemas.teacher_detail import (
    TeacherDetailCreate, TeacherDetailUpdate,
    TeacherDetailResponse, TeacherDetailListResponse,
)
from app.schemas.response import BaseResponse, DataResponse
from datetime import datetime
import uuid

router = APIRouter(prefix="/teacher-details", tags=["教師明細管理"])

DETAIL_SELECT = "id,teacher_id,detail_type,content,issue_date,expiry_date,file_path,file_name,created_at,updated_at"


@router.get("", response_model=TeacherDetailListResponse)
async def list_teacher_details(
    teacher_id: str = Query(..., description="教師 ID"),
    current_user: CurrentUser = Depends(require_page_permission("teachers.details"))
):
    """取得教師明細列表"""
    try:
        # Ownership check: 教師只能查自己的明細
        if current_user.is_teacher():
            user_teacher_id = current_user.teacher_id
            if teacher_id != user_teacher_id:
                raise HTTPException(status_code=403, detail="無權查看其他教師的明細")

        details = await supabase_service.table_select(
            table="teacher_details",
            select=DETAIL_SELECT,
            filters={"teacher_id": teacher_id, "is_deleted": "eq.false"},
        )
        return TeacherDetailListResponse(
            data=[TeacherDetailResponse(**d) for d in details]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得教師明細失敗: {str(e)}")


@router.post("", response_model=DataResponse[TeacherDetailResponse])
async def create_teacher_detail(
    data: TeacherDetailCreate,
    current_user: CurrentUser = Depends(require_page_permission("teachers.edit"))
):
    """新增教師明細（僅限員工）"""
    try:
        # 驗證教師存在
        teachers = await supabase_service.table_select(
            table="teachers", select="id",
            filters={"id": data.teacher_id, "is_deleted": "eq.false"},
        )
        if not teachers:
            raise HTTPException(status_code=404, detail="教師不存在")

        detail_data = {}
        detail_data["teacher_id"] = data.teacher_id
        detail_data["detail_type"] = data.detail_type.value
        if data.content is not None:
            detail_data["content"] = data.content
        if data.issue_date is not None:
            detail_data["issue_date"] = data.issue_date.isoformat()
        if data.expiry_date is not None:
            detail_data["expiry_date"] = data.expiry_date.isoformat()

        employee_id = await get_user_employee_id(current_user.user_id)
        if employee_id:
            detail_data["created_by"] = employee_id

        result = await supabase_service.table_insert(
            table="teacher_details", data=detail_data
        )
        if not result:
            raise HTTPException(status_code=500, detail="新增教師明細失敗")

        return DataResponse(message="教師明細新增成功", data=TeacherDetailResponse(**result))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"新增教師明細失敗: {str(e)}")


@router.put("/{detail_id}", response_model=DataResponse[TeacherDetailResponse])
async def update_teacher_detail(
    detail_id: str,
    data: TeacherDetailUpdate,
    current_user: CurrentUser = Depends(require_page_permission("teachers.edit"))
):
    """更新教師明細（僅限員工）"""
    try:
        existing = await supabase_service.table_select(
            table="teacher_details", select="id",
            filters={"id": detail_id, "is_deleted": "eq.false"},
        )
        if not existing:
            raise HTTPException(status_code=404, detail="教師明細不存在")

        update_data = {}
        if data.content is not None:
            update_data["content"] = data.content
        if data.issue_date is not None:
            update_data["issue_date"] = data.issue_date.isoformat()
        if data.expiry_date is not None:
            update_data["expiry_date"] = data.expiry_date.isoformat()

        if not update_data:
            raise HTTPException(status_code=400, detail="沒有要更新的資料")

        employee_id = await get_user_employee_id(current_user.user_id)
        if employee_id:
            update_data["updated_by"] = employee_id

        result = await supabase_service.table_update(
            table="teacher_details", data=update_data,
            filters={"id": detail_id}
        )
        if not result:
            raise HTTPException(status_code=500, detail="更新教師明細失敗")

        return DataResponse(message="教師明細更新成功", data=TeacherDetailResponse(**result))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新教師明細失敗: {str(e)}")


@router.delete("/{detail_id}", response_model=BaseResponse)
async def delete_teacher_detail(
    detail_id: str,
    current_user: CurrentUser = Depends(require_page_permission("teachers.edit"))
):
    """軟刪除教師明細（僅限員工）"""
    try:
        existing = await supabase_service.table_select(
            table="teacher_details", select="id",
            filters={"id": detail_id, "is_deleted": "eq.false"},
        )
        if not existing:
            raise HTTPException(status_code=404, detail="教師明細不存在")

        employee_id = await get_user_employee_id(current_user.user_id)
        delete_data = {
            "is_deleted": True,
            "deleted_at": datetime.utcnow().isoformat(),
        }
        if employee_id:
            delete_data["deleted_by"] = employee_id

        result = await supabase_service.table_update(
            table="teacher_details", data=delete_data,
            filters={"id": detail_id}
        )
        if not result:
            raise HTTPException(status_code=500, detail="刪除教師明細失敗")

        return BaseResponse(message="教師明細刪除成功")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刪除教師明細失敗: {str(e)}")


# ========== File Upload / Download ==========

class ConfirmUploadRequest(BaseModel):
    """確認上傳請求"""
    storage_path: str
    file_name: str


@router.post("/{detail_id}/upload-url")
async def get_teacher_detail_upload_url(
    detail_id: str,
    current_user: CurrentUser = Depends(require_page_permission("teachers.edit"))
):
    """取得教師明細檔案的 signed upload URL（僅限員工）

    前端收到後直接 PUT 檔案到該 URL，上傳完成後呼叫 confirm-upload。
    """
    try:
        existing = await supabase_service.table_select(
            table="teacher_details",
            select="id,teacher_id,detail_type",
            filters={"id": detail_id, "is_deleted": "eq.false"},
        )
        if not existing:
            raise HTTPException(status_code=404, detail="教師明細不存在")

        detail = existing[0]
        teacher_id = detail["teacher_id"]
        detail_type = detail["detail_type"]

        await storage_service.ensure_bucket_exists(settings.AWS_S3_BUCKET)

        safe_filename = f"{uuid.uuid4().hex}.pdf"
        storage_path = f"teachers/{teacher_id}/{detail_type}/{safe_filename}"

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


@router.post("/{detail_id}/confirm-upload", response_model=DataResponse[TeacherDetailResponse])
async def confirm_teacher_detail_upload(
    detail_id: str,
    body: ConfirmUploadRequest,
    current_user: CurrentUser = Depends(require_page_permission("teachers.edit"))
):
    """確認教師明細檔案上傳完成（僅限員工）"""
    try:
        existing = await supabase_service.table_select(
            table="teacher_details", select="id",
            filters={"id": detail_id, "is_deleted": "eq.false"},
        )
        if not existing:
            raise HTTPException(status_code=404, detail="教師明細不存在")

        # 驗證 S3 檔案存在
        file_exists = await storage_service.verify_file_exists(
            bucket=settings.AWS_S3_BUCKET,
            path=body.storage_path
        )
        if not file_exists:
            raise HTTPException(status_code=400, detail="檔案尚未上傳至 S3")

        update_data = {
            "file_path": body.storage_path,
            "file_name": body.file_name,
            "file_uploaded_at": datetime.utcnow().isoformat(),
        }

        result = await supabase_service.table_update(
            table="teacher_details", data=update_data,
            filters={"id": detail_id}
        )
        if not result:
            raise HTTPException(status_code=500, detail="更新檔案資訊失敗")

        return DataResponse(
            message="檔案上傳確認成功",
            data=TeacherDetailResponse(**result)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"確認上傳失敗: {str(e)}")


@router.get("/{detail_id}/download-url")
async def get_teacher_detail_download_url(
    detail_id: str,
    current_user: CurrentUser = Depends(require_page_permission("teachers.details"))
):
    """取得教師明細檔案的 signed download URL"""
    try:
        result = await supabase_service.table_select(
            table="teacher_details",
            select="id,teacher_id,file_path,file_name",
            filters={"id": detail_id, "is_deleted": "eq.false"},
        )
        if not result:
            raise HTTPException(status_code=404, detail="教師明細不存在")

        detail = result[0]

        # Ownership check: 教師只能下載自己的文件
        if current_user.is_teacher():
            user_teacher_id = current_user.teacher_id
            if detail.get("teacher_id") != user_teacher_id:
                raise HTTPException(status_code=403, detail="無權下載此文件")

        if not detail.get("file_path"):
            raise HTTPException(status_code=404, detail="此明細尚無上傳檔案")

        download_url = await storage_service.create_signed_download_url(
            bucket=settings.AWS_S3_BUCKET,
            path=detail["file_path"]
        )
        if not download_url:
            raise HTTPException(status_code=500, detail="產生下載連結失敗")

        return {
            "download_url": download_url,
            "file_name": detail.get("file_name"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"產生下載連結失敗: {str(e)}")

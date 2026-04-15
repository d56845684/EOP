from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.supabase_service import supabase_service
from app.core.dependencies import get_current_user, CurrentUser
from app.schemas.response import DataResponse

router = APIRouter(prefix="/notifications", tags=["通知管理"])


class NotificationPreferences(BaseModel):
    email_enabled: bool = True
    booking_confirmed: bool = True
    booking_cancelled: bool = True
    contract_activated: bool = True
    contract_converted: bool = True
    contract_terminated: bool = True


@router.get("/preferences", response_model=DataResponse[NotificationPreferences])
async def get_notification_preferences(
    current_user: CurrentUser = Depends(get_current_user),
):
    """取得我的通知偏好"""
    result = await supabase_service.table_select(
        table="notification_preferences",
        select="email_enabled,booking_confirmed,booking_cancelled,contract_activated,contract_converted,contract_terminated",
        filters={"user_id": current_user.user_id},
    )
    if result:
        return DataResponse(data=NotificationPreferences(**result[0]))
    # 無紀錄 → 回傳預設值
    return DataResponse(data=NotificationPreferences())


@router.put("/preferences", response_model=DataResponse[NotificationPreferences])
async def update_notification_preferences(
    data: NotificationPreferences,
    current_user: CurrentUser = Depends(get_current_user),
):
    """更新我的通知偏好"""
    existing = await supabase_service.table_select(
        table="notification_preferences",
        select="id",
        filters={"user_id": current_user.user_id},
    )

    prefs = data.model_dump()
    if existing:
        await supabase_service.table_update(
            table="notification_preferences",
            data=prefs,
            filters={"user_id": current_user.user_id},
        )
    else:
        prefs["user_id"] = current_user.user_id
        await supabase_service.table_insert(
            table="notification_preferences",
            data=prefs,
        )

    return DataResponse(message="通知偏好已更新", data=data)

from fastapi import APIRouter, Depends, Query, HTTPException
from app.services.supabase_service import supabase_service
from app.core.dependencies import CurrentUser, require_staff, require_page_permission
from app.schemas.response import BaseResponse
from typing import Optional
import math
import uuid

router = APIRouter(prefix="/alerts", tags=["系統告警"])

ALERT_SELECT = "id,alert_type,severity,title,message,metadata,is_read,read_by,read_at,created_at"


@router.get("")
async def list_alerts(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    is_read: Optional[bool] = Query(None, description="篩選已讀/未讀"),
    severity: Optional[str] = Query(None, description="篩選嚴重度 (info/warning/error)"),
    current_user: CurrentUser = Depends(require_page_permission("dashboard.alerts")),
):
    """列出系統告警（僅限員工/管理員）"""
    try:
        pool = supabase_service.pool

        conditions = []
        params = []
        idx = 0

        if is_read is not None:
            idx += 1
            conditions.append(f"is_read = ${idx}")
            params.append(is_read)

        if severity:
            idx += 1
            conditions.append(f"severity = ${idx}")
            params.append(severity)

        where_sql = ""
        if conditions:
            where_sql = "WHERE " + " AND ".join(conditions)

        count_row = await pool.fetchrow(
            f"SELECT COUNT(*) FROM system_alerts {where_sql}", *params
        )
        total = count_row[0] if count_row else 0
        total_pages = math.ceil(total / per_page) if total > 0 else 1

        idx += 1
        params.append(per_page)
        limit_idx = idx
        idx += 1
        params.append((page - 1) * per_page)
        offset_idx = idx

        rows = await pool.fetch(
            f"SELECT {ALERT_SELECT} FROM system_alerts {where_sql} "
            f"ORDER BY created_at DESC LIMIT ${limit_idx} OFFSET ${offset_idx}",
            *params,
        )

        data = []
        for r in rows:
            d = dict(r)
            for k, v in d.items():
                if isinstance(v, uuid.UUID):
                    d[k] = str(v)
            data.append(d)

        # 未讀數量
        unread_row = await pool.fetchrow(
            "SELECT COUNT(*) FROM system_alerts WHERE is_read = FALSE"
        )
        unread_count = unread_row[0] if unread_row else 0

        return {
            "success": True,
            "data": data,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "unread_count": unread_count,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得告警列表失敗: {e}")


@router.put("/{alert_id}/read", response_model=BaseResponse)
async def mark_alert_read(
    alert_id: str,
    current_user: CurrentUser = Depends(require_page_permission("dashboard.alerts")),
):
    """標記單一告警為已讀"""
    try:
        result = await supabase_service.table_update(
            table="system_alerts",
            data={
                "is_read": True,
                "read_by": current_user.user_id,
                "read_at": "now()",
            },
            filters={"id": alert_id},
        )
        if not result:
            raise HTTPException(status_code=404, detail="告警不存在")
        return BaseResponse(message="已標記為已讀")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"標記失敗: {e}")


@router.put("/read-all", response_model=BaseResponse)
async def mark_all_read(
    current_user: CurrentUser = Depends(require_page_permission("dashboard.alerts")),
):
    """全部標記為已讀"""
    try:
        await supabase_service.pool.execute(
            "UPDATE system_alerts SET is_read = TRUE, read_by = $1, read_at = now() "
            "WHERE is_read = FALSE",
            uuid.UUID(current_user.user_id),
        )
        return BaseResponse(message="已全部標記為已讀")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"標記失敗: {e}")


@router.get("/unread-count")
async def get_unread_count(
    current_user: CurrentUser = Depends(require_page_permission("dashboard.alerts")),
):
    """取得未讀告警數量（供 navbar badge 用）"""
    try:
        row = await supabase_service.pool.fetchrow(
            "SELECT COUNT(*) FROM system_alerts WHERE is_read = FALSE"
        )
        return {"success": True, "count": row[0] if row else 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得未讀數量失敗: {e}")

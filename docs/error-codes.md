# API 錯誤碼對照表

所有 API 錯誤回傳格式：

```json
{
  "success": false,
  "message": "中文錯誤訊息（給使用者看）",
  "detail": "中文錯誤訊息",
  "error_code": "AUTH_ERROR"
}
```

`error_code` 為英文 UPPER_SNAKE_CASE，供前端程式化處理。

定義檔：`backend/app/core/error_codes.py`

---

## 401 — 認證失敗

| error_code | 說明 | 觸發情境 |
|------------|------|----------|
| `AUTH_ERROR` | 通用認證錯誤 | 未提供 token、認證流程異常 |
| `AUTH_TOKEN_EXPIRED` | Token 已過期 | JWT access token 超過有效期 |
| `AUTH_TOKEN_INVALID` | 無效的 Token | Token 格式錯誤、簽名不符、已被列入黑名單 |
| `AUTH_SESSION_EXPIRED` | Session 已過期 | Redis session 不存在或已銷毀 |
| `AUTH_IDLE_TIMEOUT` | 閒置超時自動登出 | 使用者閒置超過設定時間（預設 10 分鐘） |
| `AUTH_SESSION_REPLACED` | 帳號在其他裝置登入 | 同帳號不可重複登入，舊 session 被銷毀 |
| `AUTH_LOGIN_FAILED` | 登入失敗 | 帳號或密碼錯誤 |
| `AUTH_API_KEY_INVALID` | API Key 無效 | Service Account 的 API Key 驗證失敗 |

## 403 — 權限不足

| error_code | 說明 | 觸發情境 |
|------------|------|----------|
| `FORBIDDEN` | 通用權限不足 | 權限等級不夠 |
| `FORBIDDEN_ROLE` | 角色限制 | 「僅限管理員操作」等角色檢查 |
| `FORBIDDEN_OWNER` | 非資源擁有者 | 學生/教師嘗試操作他人資源 |
| `FORBIDDEN_PROTECTED` | 受保護帳號 | 操作被標記為 is_protected 的帳號 |
| `FORBIDDEN_PAGE` | 缺少頁面權限 | 角色未被授權存取該頁面功能 |

## 404 — 資源不存在

| error_code | 說明 | 觸發情境 |
|------------|------|----------|
| `NOT_FOUND` | 資源不存在 | ID 不存在或已被軟刪除 |

## 400 — 請求錯誤

| error_code | 說明 | 觸發情境 |
|------------|------|----------|
| `VALIDATION_ERROR` | 通用驗證錯誤 | 欄位格式不符、業務邏輯錯誤 |
| `DUPLICATE_ENTRY` | 資料已存在 | Email 重複、編號重複等唯一性衝突 |
| `NO_UPDATE_DATA` | 無更新內容 | PUT 請求未提供任何要更新的欄位 |
| `INVALID_STATE` | 狀態不允許操作 | 如「只有待確認狀態的預約才可刪除」 |
| `INVALID_FILE` | 檔案錯誤 | 檔案格式不支援、上傳失敗 |
| `QUOTA_EXCEEDED` | 額度超限 | 如請假額度用完、合約堂數不足 |
| `WRONG_PASSWORD` | 密碼錯誤 | 變更密碼時當前密碼不正確 |

## 409 — 資源衝突

| error_code | 說明 | 觸發情境 |
|------------|------|----------|
| `CONFLICT` | 資源衝突 | 預約時間重疊、並發操作衝突 |

## 422 — 請求格式錯誤

由 FastAPI/Pydantic 自動回傳，不走 error_code 系統。

```json
{
  "detail": [{
    "type": "value_error",
    "loc": ["body", "email"],
    "msg": "value is not a valid email address: An email address must have an @-sign.",
    "input": "not-an-email"
  }]
}
```

常見觸發：EmailStr 格式驗證、必填欄位缺失、數值範圍不符。

## 429 — 請求頻率過高

| error_code | 說明 | 觸發情境 |
|------------|------|----------|
| `RATE_LIMITED` | 請求頻率過高 | Rate limiting middleware 攔截 |

## 500 — 伺服器錯誤

| error_code | 說明 | 觸發情境 |
|------------|------|----------|
| `INTERNAL_ERROR` | 伺服器內部錯誤 | 未預期的例外（detail 不暴露內部細節） |

## 503 — 服務不可用

| error_code | 說明 | 觸發情境 |
|------------|------|----------|
| `SERVICE_UNAVAILABLE` | 服務不可用 | 資料庫/Redis 連線失敗等 |

---

## 前端處理參考

前端 `fetchWithAuth` 會解析 `error_code` 來決定行為：

| error_code | 前端行為 |
|------------|----------|
| `AUTH_IDLE_TIMEOUT` | 導向 `/login?reason=idle` |
| `AUTH_SESSION_REPLACED` | 導向 `/login?reason=replaced` |
| `AUTH_SESSION_EXPIRED` / `AUTH_TOKEN_EXPIRED` | 嘗試 refresh，失敗則導向 `/login?reason=expired` |
| 其他 401 | 嘗試 refresh，失敗則登出 |
| 422 | 解析 `detail[0].msg` 顯示驗證錯誤 |
| 其他 | 顯示 `message` 或 `detail` 給使用者 |

# Playwright E2E 測試規劃

## 環境

| 項目 | 值 |
|------|---|
| Frontend URL | `http://localhost:4173/demo` |
| Backend API | `http://localhost:8001` |
| basePath | `/demo` |
| 啟動方式 | `docker compose up -d`（frontend-demo + backend + db + redis） |

## 測試帳號

| 角色 | Email | Password | 可存取頁面 |
|------|-------|----------|-----------|
| Admin | `eopAdmin@example.com` | (from .env) | 全部 |
| Employee | `employee@eop-test.com` | `TestPassword123!` | 全部（除 permissions.*） |
| Teacher | `teacher@eop-test.com` | `TestPassword123!` | bookings, courses, teacher-slots/contracts/bonus, profile |
| Student | `student@eop-test.com` | `TestPassword123!` | bookings, courses, student-contracts, profile |

## 安裝

```bash
cd frontend-dennis
npm install -D @playwright/test
npx playwright install chromium  # 只裝 Chromium 就夠
```

`package.json` 新增 script：
```json
{
  "scripts": {
    "test:e2e": "playwright test",
    "test:e2e:ui": "playwright test --ui"
  }
}
```

## 目錄結構

```
frontend-dennis/
├── e2e/
│   ├── PLAN.md              ← 本文件
│   ├── helpers/
│   │   └── auth.ts          ← 共用登入 helper（存 storageState）
│   ├── auth.spec.ts         ← 認證流程測試
│   ├── navigation.spec.ts   ← 側邊欄導航 + 權限測試
│   ├── students.spec.ts     ← 學生 CRUD 測試
│   ├── teachers.spec.ts     ← 教師 CRUD 測試
│   ├── courses.spec.ts      ← 課程 CRUD 測試
│   ├── bookings.spec.ts     ← 預約流程測試
│   ├── contracts.spec.ts    ← 合約管理測試
│   ├── employees.spec.ts    ← 員工管理 + 角色變更測試
│   └── permissions.spec.ts  ← 權限即時生效測試
├── playwright.config.ts
└── .auth/                   ← storageState 暫存（gitignore）
```

## playwright.config.ts 重點

```typescript
export default defineConfig({
  testDir: './e2e',
  baseURL: 'http://localhost:4173/demo',
  timeout: 30_000,
  retries: 1,
  use: {
    locale: 'zh-TW',
    screenshot: 'only-on-failure',
    trace: 'on-first-retry',
  },
  projects: [
    // 先跑 setup 把各角色的 session 存下來
    { name: 'setup', testMatch: /global-setup\.ts/ },
    // 實際測試用存好的 session
    { name: 'admin', use: { storageState: '.auth/admin.json' }, dependencies: ['setup'] },
    { name: 'employee', use: { storageState: '.auth/employee.json' }, dependencies: ['setup'] },
    { name: 'teacher', use: { storageState: '.auth/teacher.json' }, dependencies: ['setup'] },
    { name: 'student', use: { storageState: '.auth/student.json' }, dependencies: ['setup'] },
  ],
})
```

## 共用登入 Helper

```typescript
// e2e/helpers/auth.ts
async function loginAndSave(page, email, password, savePath) {
  await page.goto('/login')
  await page.fill('input[type="email"]', email)
  await page.fill('input[type="password"]', password)
  await page.click('button[type="submit"]')
  await page.waitForURL('**/profile')
  await page.context().storageState({ path: savePath })
}
```

登入一次就好，後續所有測試直接載入 `storageState`，不用每次重新登入。

---

## 測試案例

### 1. auth.spec.ts — 認證流程

| # | 測試案例 | 步驟 | 驗證 |
|---|---------|------|------|
| 1.1 | 正常登入 | 填寫 email + password → 送出 | 導向 /profile，顯示使用者名稱 |
| 1.2 | 錯誤密碼 | 填寫錯誤密碼 → 送出 | 顯示錯誤訊息，停留在 /login |
| 1.3 | 空欄位送出 | 不填寫直接送出 | 表單驗證阻擋，不送 request |
| 1.4 | 登出 | 點擊側邊欄登出按鈕 | 導向 /login |
| 1.5 | 未登入存取受保護頁面 | 直接訪問 /students | 導向 /login |

### 2. navigation.spec.ts — 側邊欄導航 + 權限

以不同角色登入，驗證側邊欄顯示的項目是否正確。

| # | 角色 | 驗證 |
|---|------|------|
| 2.1 | Admin | 側邊欄包含：學生、教師、課程、預約、員工、帳號管理、角色權限 |
| 2.2 | Employee | 側邊欄包含：學生、教師、課程、預約、員工；**不含**帳號管理、角色權限 |
| 2.3 | Teacher | 側邊欄包含：預約、課程、教師時段、教師合約；**不含**學生管理、員工管理 |
| 2.4 | Student | 側邊欄包含：預約、課程、學生合約；**不含**教師管理、員工管理 |
| 2.5 | 各角色 | 點擊側邊欄每個項目 → 頁面正確載入（無白屏、無 500 錯誤） |

### 3. students.spec.ts — 學生 CRUD（Admin 角色）

| # | 測試案例 | 步驟 | 驗證 |
|---|---------|------|------|
| 3.1 | 建立學生 | 點擊「新增」→ 填寫表單 → 送出 | 列表出現新學生 |
| 3.2 | 搜尋學生 | 在搜尋框輸入學生名稱 | 列表只顯示符合的結果 |
| 3.3 | 編輯學生 | 點擊編輯 → 修改姓名 → 儲存 | 列表顯示新名稱 |
| 3.4 | 停用學生 | 點擊停用 → 確認 | 學生狀態變為停用 |
| 3.5 | 刪除學生 | 點擊刪除 → 確認 | 列表不再顯示該學生 |

### 4. teachers.spec.ts — 教師 CRUD（Admin 角色）

同 students，另加：

| # | 測試案例 | 步驟 | 驗證 |
|---|---------|------|------|
| 4.6 | 教師總覽 | 進入教師總覽頁面 | 顯示合約數、預約數等統計 |
| 4.7 | 教師詳情 | 點擊教師 → 進入詳情 | 顯示合約、預約、獎金區段 |

### 5. courses.spec.ts — 課程 CRUD（Admin 角色）

| # | 測試案例 | 步驟 | 驗證 |
|---|---------|------|------|
| 5.1 | 建立課程 | 填寫課程代碼 + 名稱 + 時長 → 送出 | 列表出現新課程 |
| 5.2 | 修改課程 | 編輯課程名稱 → 儲存 | 列表顯示新名稱 |
| 5.3 | 重複代碼 | 建立相同課程代碼 | 顯示錯誤「已存在」 |
| 5.4 | 刪除課程 | 刪除 → 確認 | 列表不再顯示 |

### 6. bookings.spec.ts — 預約流程（Admin 角色）

| # | 測試案例 | 步驟 | 驗證 |
|---|---------|------|------|
| 6.1 | 建立預約 | 選擇學生 → 教師 → 課程 → 時段 → 送出 | 預約出現在列表 |
| 6.2 | 確認預約 | 將預約狀態改為 confirmed | 狀態標籤變更 |
| 6.3 | 取消預約 | 取消預約 | 狀態變為 cancelled |
| 6.4 | 重複預約 | 建立相同時段預約 | 顯示衝突錯誤 |

### 7. contracts.spec.ts — 合約管理（Admin 角色）

| # | 測試案例 | 步驟 | 驗證 |
|---|---------|------|------|
| 7.1 | 建立學生合約 | 選擇學生 → 填寫堂數/金額 → 送出 | 合約出現在列表 |
| 7.2 | 新增合約明細 | 進入合約 → 新增課程費率明細 | 明細列表顯示 |
| 7.3 | 建立教師合約 | 選擇教師 → 填寫合約資訊 → 送出 | 合約出現在列表 |
| 7.4 | 修改合約 | 編輯合約狀態 → 儲存 | 狀態更新 |

### 8. employees.spec.ts — 員工管理（Admin 角色）

| # | 測試案例 | 步驟 | 驗證 |
|---|---------|------|------|
| 8.1 | 建立員工 | 填寫員工資料 → 送出 | 列表出現新員工 |
| 8.2 | 變更角色 | 編輯員工 → 選擇不同角色 → 儲存 | 角色欄位更新 |
| 8.3 | 刪除員工 | 刪除 → 確認 | 列表不再顯示 |

### 9. permissions.spec.ts — 權限即時生效（Admin 角色）

這是最重要的測試，驗證後端的權限即時生效機制在前端也正確反映：

| # | 測試案例 | 步驟 | 驗證 |
|---|---------|------|------|
| 9.1 | 角色變更即時生效 | Admin 建立 employee (intern) → 用該 employee 登入 → Admin 將其改為 admin 角色 → employee **不重新登入** → 重新整理頁面 | 側邊欄出現「帳號管理」「角色權限」 |
| 9.2 | 權限收回即時生效 | 接續 9.1 → Admin 將角色改回 employee → employee 重新整理 | 側邊欄不再顯示「帳號管理」「角色權限」 |
| 9.3 | 頁面存取被拒 | Student 角色直接存取 /students | 顯示權限不足或導向其他頁面 |

---

## 執行方式

```bash
# 前置：確保 Docker stack 運行中
docker compose up -d

# 跑全部測試
cd frontend-dennis
npx playwright test

# 跑特定測試
npx playwright test e2e/auth.spec.ts

# 用 UI 模式除錯
npx playwright test --ui

# 只跑某個角色的測試
npx playwright test --project=admin

# 看報告
npx playwright show-report
```

## 優先順序

| 優先級 | 測試檔案 | 理由 |
|--------|---------|------|
| P0 | auth.spec.ts | 登入是所有流程的基礎 |
| P0 | navigation.spec.ts | 驗證權限系統在前端正確反映 |
| P1 | permissions.spec.ts | 驗證角色變更即時生效（核心功能） |
| P1 | students.spec.ts | 最常用的 CRUD 流程 |
| P1 | bookings.spec.ts | 最複雜的業務流程 |
| P2 | courses.spec.ts | 基礎 CRUD |
| P2 | teachers.spec.ts | CRUD + 總覽 |
| P2 | contracts.spec.ts | 合約管理 |
| P3 | employees.spec.ts | 員工管理 |

## 注意事項

1. **測試資料隔離**：每個 spec 檔案建立自己的測試資料，測試結束後清除（`afterAll`）
2. **避免互相依賴**：各 spec 可獨立執行，不依賴其他測試的資料
3. **等待策略**：用 `waitForResponse` 或 `waitForSelector` 取代固定 `sleep`
4. **失敗截圖**：失敗時自動截圖存到 `test-results/`，方便除錯
5. **CI 整合**：未來可加入 GitHub Actions，在 PR 時自動跑 E2E 測試

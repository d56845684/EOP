# EOP 教學管理平台 — 完整操作流程

## 總覽

```mermaid
flowchart LR
    A[建立帳號] --> B[合約設定]
    B --> C[課前準備]
    C --> D[預約上課]
    D --> E[課後處理]

    style A fill:#e3f2fd
    style B fill:#fff3e0
    style C fill:#f3e5f5
    style D fill:#e8f5e9
    style E fill:#fce4ec
```

---

## 一、建立帳號（員工操作）

> 所有帳號都必須由員工邀請，無法自行註冊。

```mermaid
flowchart TD
    subgraph 員工操作
        E1[建立學生/教師資料] --> E2[填寫姓名、email、電話等]
        E2 --> E3[系統產生邀請連結]
    end

    subgraph 被邀請者操作
        E3 --> U1[收到邀請連結]
        U1 --> U2[設定密碼，完成註冊]
        U2 --> U3[首次登入]
        U3 --> U4[強制修改密碼]
        U4 --> U5[帳號啟用完成 ✓]
    end
```

### 角色說明

| 角色 | 說明 | 權限 |
|------|------|------|
| **學生 Student** | 試上生或正式生 | 查看自己的預約、合約 |
| **教師 Teacher** | 授課老師 | 查看/確認自己的預約、管理時段 |
| **員工 Employee** | 後台管理人員 | 完整 CRUD 操作 |
| **管理員 Admin** | 系統管理員 | 所有權限 + 角色管理 |

---

## 二、合約設定（員工操作）

```mermaid
flowchart TD
    subgraph TC["教師合約"]
        TC1[建立教師合約] --> TC2[設定合約期間]
        TC2 --> TC3["設定聘僱類型（時薪制/月薪制）"]
        TC3 --> TC4[設定各課程費率]
        TC4 --> TC5[設定試上轉正獎金金額]
    end

    subgraph SC["學生合約（正式生）"]
        SC1[建立學生合約] --> SC2[設定合約期間]
        SC2 --> SC3["設定總堂數 & 總金額"]
        SC3 --> SC4["系統自動計算<br/>剩餘堂數 = 總堂數<br/>請假上限 = 總堂數 × 2"]
    end
```

> **試上生不需要合約**，可直接預約試上課程。

---

## 三、課前準備（員工操作）

```mermaid
flowchart TD
    subgraph 學生端設定
        S1[學生選課<br/>student_courses] --> S2[設定教師偏好<br/>student_teacher_preferences]
        S2 --> S3{偏好模式}
        S3 -->|指定老師| S3A[設定 primary_teacher_id]
        S3 -->|教師等級| S3B[設定 min_teacher_level<br/>+ 可選課程篩選]
    end

    subgraph 教師端設定
        T1[教師開放時段<br/>teacher_available_slots]
        T1 --> T2[選擇日期]
        T2 --> T3[設定起迄時間<br/>必須為 30 分鐘的倍數]
        T3 --> T4[時段建立完成 ✓]
    end

    S3A --> READY[可以開始預約 ✓]
    S3B --> READY
    T4 --> READY
```

### 教師時段說明

- 時段以 **30 分鐘** 為最小區塊
- 例：開放 09:00–12:00 = 6 個 30 分鐘區塊
- 同一時段可容納多筆不重疊的預約
- 所有區塊被預約後，時段標記為 `is_booked = true`

---

## 四、預約上課

### 4-1. 預約建立流程

```mermaid
flowchart TD
    B1[選擇學生] --> B2{學生類型?}

    B2 -->|試上生 trial| B3T[不需要合約<br/>不需要選課]
    B2 -->|正式生 formal| B3F[檢查合約剩餘堂數<br/>檢查是否有選該課程]

    B3T --> B4
    B3F --> B4[選擇教師]

    B4 --> B5{教師是否在<br/>學生偏好名單中?}
    B5 -->|否| B5X[❌ 拒絕]
    B5 -->|是| B6[選擇課程]

    B6 --> B7{教師合約有<br/>該課程費率?}
    B7 -->|否| B7X[❌ 拒絕]
    B7 -->|是| B8[選擇日期 & 時段]

    B8 --> B9{時段有空檔?<br/>且不重疊?}
    B9 -->|否| B9X[❌ 拒絕]
    B9 -->|是| B10[計算使用堂數<br/>= 預約時長 ÷ 課程時長]

    B10 --> B11{正式生?}
    B11 -->|否| B12[建立預約 ✓<br/>booking_type = trial]
    B11 -->|是| B13{剩餘堂數足夠?}
    B13 -->|否| B13X[❌ 拒絕]
    B13 -->|是| B14[建立預約 ✓<br/>booking_type = regular<br/>扣除合約堂數]
```

### 4-2. 預約狀態流轉

```mermaid
stateDiagram-v2
    [*] --> pending: 建立預約

    pending --> confirmed: 教師確認
    pending --> cancelled: 取消預約

    confirmed --> completed: 員工標記完成
    confirmed --> cancelled: 取消預約（員工直接取消 or 請假核准）

    completed --> [*]: 結束（堂數不退）

    cancelled --> [*]: 結束（堂數退回合約）

    note right of pending: 員工/學生可建立
    note right of confirmed: 觸發 Zoom 會議建立
    note left of cancelled: 自動退回剩餘堂數<br/>釋放教師時段<br/>取消 Zoom 會議
```

### 4-3. 預約操作權限

| 操作 | 學生 | 教師 | 員工 |
|------|------|------|------|
| 建立預約 | ✅ 只能幫自己 | ❌ | ✅ 可幫任何學生 |
| 確認預約 | ❌ | ✅ 只能確認自己的 | ✅ |
| 標記完成 | ❌ | ❌ | ✅ |
| 取消預約 | ❌ | ❌ | ✅ |
| 刪除預約 | ❌ | ❌ | ✅（僅 pending/cancelled）|
| 縮短時間 | ❌ | ❌ | ✅（只能縮短，不能延長）|
| 申請請假 | ✅ 只能幫自己 | ✅ 只能幫自己 | ✅ |
| 審核請假 | ❌ | ❌ | ✅ |
| 指派代課 | ❌ | ❌ | ✅ |
| 取消代課 | ❌ | ❌ | ✅ |

### 4-4. 批次預約

```mermaid
flowchart LR
    BA1[選擇日期範圍<br/>最多 3 個月] --> BA2[選擇星期幾<br/>例: 每週二、四]
    BA2 --> BA3[系統自動匹配<br/>教師可用時段]
    BA3 --> BA4[一次建立多筆預約<br/>自動扣除合約堂數]
```

### 4-5. 取消預約副作用

當預約狀態變更為 `cancelled` 時，系統自動執行以下操作：

1. **堂數歸還** — 將 `lessons_used` 加回學生合約的 `remaining_lessons`
2. **時段釋放** — 重新計算教師時段的 `is_booked` 狀態
3. **Zoom 取消** — 非同步取消該預約的 Zoom 會議

> 此邏輯由 `cancel_booking_side_effects` 共用函式處理，適用於：直接取消、請假核准取消、批次取消、刪除預約。

---

## 五、請假流程

### 5-1. 請假申請

```mermaid
flowchart TD
    L1{發起者?}
    L1 -->|學生| L2S[學生對已確認預約<br/>提交請假申請]
    L1 -->|教師| L2T[教師對已確認預約<br/>提交請假申請]
    L1 -->|員工| L2E[員工代為提交請假]

    L2S --> L3[建立 leave_record<br/>leave_status = pending<br/>initiator_type = student/teacher]
    L2T --> L3
    L2E --> L3

    L3 --> L4[等待員工審核]
```

### 5-2. 請假審核（員工操作）

```mermaid
flowchart TD
    R1{審核決定?}

    R1 -->|駁回| R2[leave_status → rejected<br/>填寫駁回原因<br/>預約維持 confirmed]

    R1 -->|核准 — 學生請假| R3[leave_status → approved<br/>booking → cancelled<br/>觸發取消副作用]
    R3 --> R3A[寫入 student_contract_leave_records<br/>used_leave_count + 1]

    R1 -->|核准 — 教師請假<br/>已指派代課| R4[leave_status → approved<br/>booking 維持 confirmed<br/>由代課教師授課]

    R1 -->|核准 — 教師請假<br/>未指派代課| R5[leave_status → approved<br/>booking → cancelled<br/>觸發取消副作用]
```

### 5-3. 請假狀態

| 狀態 | 說明 |
|------|------|
| `pending` | 等待審核 |
| `approved` | 已核准 |
| `rejected` | 已駁回（含駁回原因） |
| `cancelled` | 已撤回（發起者或員工可撤回 pending 狀態的申請） |

---

## 六、代課流程

### 6-1. 指派代課（員工操作）

```mermaid
flowchart TD
    S1[選擇已確認的預約] --> S2{預約已有代課?}
    S2 -->|是| S2X[❌ 拒絕]
    S2 -->|否| S3[選擇代課教師]

    S3 --> S4{驗證}
    S4 --> V1[不能指派原教師自己]
    S4 --> V2[代課教師必須在<br/>學生偏好白名單內]
    S4 --> V3[代課教師合約有效]
    S4 --> V4[代課教師同日<br/>同時段無衝突]

    V1 & V2 & V3 & V4 --> S5[建立 substitute_detail<br/>記錄代課時薪<br/>booking.substitute_detail_id 指向該紀錄]

    S5 --> S6[預約維持 confirmed<br/>原教師不變<br/>代課資訊在 substitute_details]
```

### 6-2. 取消代課（員工操作）

```mermaid
flowchart LR
    C1[員工取消代課] --> C2[軟刪除 substitute_detail]
    C2 --> C3[清除 booking.substitute_detail_id]
    C3 --> C4[booking 狀態改為 pending]
```

### 6-3. 教師請假 + 代課的完整流程

```mermaid
flowchart TD
    T1[教師對已確認預約請假] --> T2[建立 leave_record<br/>initiator_type = teacher]
    T2 --> T3[員工審核]
    T3 --> T4{處理方式?}

    T4 -->|指派代課後核准| T5[建立 substitute_detail<br/>→ 核准 leave_record<br/>→ 預約維持 confirmed]

    T4 -->|直接核准取消| T6[核准 leave_record<br/>→ 預約取消<br/>→ 觸發取消副作用]

    T4 -->|駁回| T7[leave_record rejected<br/>預約維持 confirmed]
```

---

## 七、課後處理

### 7-1. 試上完成獎金

當員工將試上預約 (`booking_type = trial`) 標記為 `completed` 時，系統自動：
- 從教師合約取得 `trial_completed_bonus` 金額
- 寫入 `teacher_bonus_records`（金額可以為 0）

### 7-2. 試上轉正

```mermaid
flowchart TD
    C1{學生完成試上課?} -->|是| C2[員工發起轉正]

    C2 --> C3[選擇試上預約<br/>必須 booking_type = trial<br/>必須 status = completed<br/>必須尚未轉正]

    C3 --> C4[填寫合約資訊<br/>合約編號、堂數、金額、期間]

    C4 --> C5{指定老師?}
    C5 -->|是| C6[查詢教師合約的<br/>trial_to_formal_bonus]
    C5 -->|否| C8

    C6 --> C7[寫入獎金紀錄<br/>teacher_bonus_records<br/>金額可以為 0]
    C7 --> C8[學生類型 trial → formal<br/>建立學生合約<br/>標記預約 is_trial_to_formal = true]

    C8 --> C9[轉正完成 ✓]
```

### 7-3. 教師獎金

| 獎金類型 | 說明 | 觸發時機 |
|---------|------|---------|
| `trial_completed` | 試上完成獎金 | 試上預約標記完成時自動記錄 |
| `trial_to_formal` | 試上轉正獎金 | 試上生轉正時自動記錄 |
| 其他自訂類型 | 績效獎金等 | 員工手動建立 |

### 7-4. 正班 / 加班堂數計算

針對**月薪制（full_time）**教師的預約，系統依課程時長拆分正班與加班堂數：

- 以課程的 `duration_minutes` 為一堂
- 從預約開始時間逐堂判斷：
  - 該堂完全落在教師合約的 `[work_start_time, work_end_time]` 內 → **正班**
  - 否則 → **加班**

```
教師合約工時: 09:00 ~ 18:00
課程時長: 60 分鐘
預約時段: 17:00 ~ 19:00（共 2 堂）

第 1 堂 17:00-18:00 → 落在工時內 → 正班
第 2 堂 18:00-19:00 → 超出工時   → 加班

結果: regular_lessons = 1, overtime_lessons = 1
```

---

## 八、Zoom 整合

- 預約狀態變為 `confirmed` 時 → 非同步自動建立 Zoom 會議
- 預約狀態變為 `cancelled` 時 → 非同步自動取消 Zoom 會議
- 支援 OAuth 授權綁定 Zoom 帳號
- 可透過 `ZOOM_ENABLED` 環境變數開關

---

## 完整生命週期

```mermaid
flowchart TD
    subgraph 1. 帳號建立
        A1[員工建立學生/教師資料]
        A2[發送邀請連結]
        A3[設定密碼、啟用帳號]
    end

    subgraph 2. 合約與設定
        B1[建立教師合約 + 課程費率]
        B2[建立學生合約（正式生）]
        B3[學生選課]
        B4[設定教師偏好]
        B5[教師開放時段]
    end

    subgraph 3. 預約與上課
        C1[建立預約]
        C2[教師確認]
        C3[上課]
        C4[員工標記完成]
    end

    subgraph 4. 課中異動
        E1[學生/教師請假]
        E2[員工審核請假]
        E3[指派代課教師]
        E4[員工直接取消預約]
    end

    subgraph 5. 後續處理
        D1{試上生?}
        D2[試上轉正 + 建合約]
        D3[記錄教師獎金]
        D4[繼續預約下一堂課]
    end

    A1 --> A2 --> A3
    A3 --> B1 & B2 & B3 & B4 & B5
    B1 & B2 & B3 & B4 & B5 --> C1
    C1 --> C2 --> C3 --> C4
    C2 --> E1
    E1 --> E2
    E2 -->|教師請假| E3
    E2 -->|核准取消| E4
    C4 --> D1
    D1 -->|是| D2 --> D3 --> D4
    D1 -->|否| D4
    D4 --> C1
```

---

## 附錄：30 分鐘區塊系統

```
教師時段: 09:00 ~ 12:00（共 6 個區塊）

 09:00  09:30  10:00  10:30  11:00  11:30  12:00
   |------|------|------|------|------|------|
   | 預約A (09:00-10:00)  |      | 預約B       |
   |=======|=======|      |      |=======|======|
   | block1| block2|block3|block4| block5|block6|
   |  佔用  |  佔用  | 空閒  | 空閒  |  佔用  | 佔用 |

→ is_booked = false（還有空閒區塊）
→ 新預約可選 10:00-11:00
```

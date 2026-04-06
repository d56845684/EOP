# EOP 教學管理平台 — 財務報表 SQL 查詢

## 資料來源總覽

### 收入端（學生）

| 表 | 欄位 | 說明 |
|----|------|------|
| `student_contracts` | `total_amount` | 合約總金額 |
| `student_contracts` | `total_lessons` | 合約總堂數 |
| `student_contract_details` | `detail_type='lesson_price'`, `course_id`, `amount` | 每門課的單堂價格 |
| `bookings` | `lessons_used` | 每筆預約消耗堂數 |

### 支出端（教師）

| 表 | 欄位 | 說明 |
|----|------|------|
| `bookings` | `teacher_hourly_rate` | 建立預約時快照的課程費率 |
| `bookings` | `overtime_pay` | 建立預約時計算的加班費（僅正職） |
| `teacher_contract_details` | `base_salary` | 正職底薪（月固定） |
| `teacher_contract_details` | `allowance` | 正職津貼（月固定） |
| `teacher_contract_details` | `overtime_rate` | 正職加班費率（每堂） |
| `teacher_bonus_records` | `amount`, `bonus_date` | 各類獎金 |

### 共用篩選條件

所有查詢都遵循以下慣例：

```sql
-- 排除已刪除
WHERE is_deleted = FALSE
-- 只計算已確認/已完成的預約
AND booking_status IN ('confirmed', 'completed')
-- 排除試上（不收費）
AND booking_type != 'trial'
```

---

## 一、每月教師薪資總表

> 整合教學費 + 加班費 + 底薪 + 津貼 + 獎金，一張表看完。

```sql
WITH monthly_teaching AS (
    -- 教學費 + 加班費（從 bookings 直接聚合）
    SELECT
        b.teacher_id,
        DATE_TRUNC('month', b.booking_date) AS month,
        SUM(b.teacher_hourly_rate * b.lessons_used) AS teaching_pay,
        SUM(COALESCE(b.overtime_pay, 0))             AS overtime_pay,
        SUM(b.lessons_used)                           AS total_lessons,
        COUNT(*)                                      AS booking_count
    FROM bookings b
    WHERE b.is_deleted = FALSE
      AND b.booking_status IN ('confirmed', 'completed')
      AND b.booking_type != 'trial'
    GROUP BY b.teacher_id, DATE_TRUNC('month', b.booking_date)
),
monthly_bonus AS (
    -- 獎金
    SELECT
        teacher_id,
        DATE_TRUNC('month', bonus_date) AS month,
        SUM(amount) AS total_bonus,
        COUNT(*)    AS bonus_count
    FROM teacher_bonus_records
    WHERE is_deleted = FALSE
    GROUP BY teacher_id, DATE_TRUNC('month', bonus_date)
),
fixed_salary AS (
    -- 正職底薪 + 津貼（月固定，取 active 合約）
    SELECT
        tc.teacher_id,
        SUM(CASE WHEN tcd.detail_type = 'base_salary' THEN tcd.amount ELSE 0 END) AS base_salary,
        SUM(CASE WHEN tcd.detail_type = 'allowance'   THEN tcd.amount ELSE 0 END) AS allowance
    FROM teacher_contracts tc
    JOIN teacher_contract_details tcd ON tcd.teacher_contract_id = tc.id
        AND tcd.is_deleted = FALSE
        AND tcd.detail_type IN ('base_salary', 'allowance')
    WHERE tc.is_deleted = FALSE
      AND tc.contract_status = 'active'
      AND tc.employment_type = 'full_time'
    GROUP BY tc.teacher_id
)
SELECT
    t.name                                    AS 教師姓名,
    TO_CHAR(mt.month, 'YYYY-MM')              AS 月份,
    mt.booking_count                           AS 上課次數,
    mt.total_lessons                           AS 上課堂數,
    mt.teaching_pay                            AS 教學費,
    mt.overtime_pay                            AS 加班費,
    COALESCE(fs.base_salary, 0)                AS 底薪,
    COALESCE(fs.allowance, 0)                  AS 津貼,
    COALESCE(bn.total_bonus, 0)                AS 獎金,
    -- 總薪資
    mt.teaching_pay
        + mt.overtime_pay
        + COALESCE(fs.base_salary, 0)
        + COALESCE(fs.allowance, 0)
        + COALESCE(bn.total_bonus, 0)          AS 總薪資
FROM monthly_teaching mt
JOIN teachers t ON t.id = mt.teacher_id
LEFT JOIN fixed_salary fs ON fs.teacher_id = mt.teacher_id
LEFT JOIN monthly_bonus bn ON bn.teacher_id = mt.teacher_id AND bn.month = mt.month
ORDER BY mt.month DESC, t.name;
```

---

## 二、時薪教師月薪資

> 時薪教師的薪資 = 教學費 + 獎金（無底薪/津貼/加班費）。

```sql
SELECT
    t.name                                      AS 教師姓名,
    TO_CHAR(DATE_TRUNC('month', b.booking_date), 'YYYY-MM') AS 月份,
    COUNT(*)                                     AS 上課次數,
    SUM(b.lessons_used)                          AS 上課堂數,
    SUM(b.teacher_hourly_rate * b.lessons_used)  AS 教學費,
    COALESCE(bn.total_bonus, 0)                  AS 獎金,
    SUM(b.teacher_hourly_rate * b.lessons_used)
        + COALESCE(bn.total_bonus, 0)            AS 總薪資
FROM bookings b
JOIN teachers t ON t.id = b.teacher_id
JOIN teacher_contracts tc ON tc.id = b.teacher_contract_id
    AND tc.employment_type = 'hourly'
LEFT JOIN (
    SELECT teacher_id, DATE_TRUNC('month', bonus_date) AS month, SUM(amount) AS total_bonus
    FROM teacher_bonus_records WHERE is_deleted = FALSE
    GROUP BY teacher_id, DATE_TRUNC('month', bonus_date)
) bn ON bn.teacher_id = b.teacher_id
    AND bn.month = DATE_TRUNC('month', b.booking_date)
WHERE b.is_deleted = FALSE
  AND b.booking_status IN ('confirmed', 'completed')
  AND b.booking_type != 'trial'
GROUP BY t.name, DATE_TRUNC('month', b.booking_date), bn.total_bonus
ORDER BY 月份 DESC, t.name;
```

---

## 三、正職教師月薪資明細

> 正職教師的薪資 = 底薪 + 津貼 + 教學費 + 加班費 + 獎金。

```sql
SELECT
    t.name                                      AS 教師姓名,
    TO_CHAR(DATE_TRUNC('month', b.booking_date), 'YYYY-MM') AS 月份,
    COUNT(*)                                     AS 上課次數,
    SUM(b.lessons_used)                          AS 上課堂數,
    -- 固定薪資（每月固定）
    COALESCE(fs.base_salary, 0)                  AS 底薪,
    COALESCE(fs.allowance, 0)                    AS 津貼,
    -- 浮動薪資
    SUM(b.teacher_hourly_rate * b.lessons_used)  AS 教學費,
    SUM(COALESCE(b.overtime_pay, 0))             AS 加班費,
    COALESCE(bn.total_bonus, 0)                  AS 獎金,
    -- 總計
    COALESCE(fs.base_salary, 0)
        + COALESCE(fs.allowance, 0)
        + SUM(b.teacher_hourly_rate * b.lessons_used)
        + SUM(COALESCE(b.overtime_pay, 0))
        + COALESCE(bn.total_bonus, 0)            AS 總薪資
FROM bookings b
JOIN teachers t ON t.id = b.teacher_id
JOIN teacher_contracts tc ON tc.id = b.teacher_contract_id
    AND tc.employment_type = 'full_time'
LEFT JOIN (
    SELECT tc2.teacher_id,
           SUM(CASE WHEN tcd.detail_type = 'base_salary' THEN tcd.amount ELSE 0 END) AS base_salary,
           SUM(CASE WHEN tcd.detail_type = 'allowance'   THEN tcd.amount ELSE 0 END) AS allowance
    FROM teacher_contracts tc2
    JOIN teacher_contract_details tcd ON tcd.teacher_contract_id = tc2.id
        AND tcd.is_deleted = FALSE AND tcd.detail_type IN ('base_salary', 'allowance')
    WHERE tc2.is_deleted = FALSE AND tc2.contract_status = 'active' AND tc2.employment_type = 'full_time'
    GROUP BY tc2.teacher_id
) fs ON fs.teacher_id = b.teacher_id
LEFT JOIN (
    SELECT teacher_id, DATE_TRUNC('month', bonus_date) AS month, SUM(amount) AS total_bonus
    FROM teacher_bonus_records WHERE is_deleted = FALSE
    GROUP BY teacher_id, DATE_TRUNC('month', bonus_date)
) bn ON bn.teacher_id = b.teacher_id
    AND bn.month = DATE_TRUNC('month', b.booking_date)
WHERE b.is_deleted = FALSE
  AND b.booking_status IN ('confirmed', 'completed')
  AND b.booking_type != 'trial'
GROUP BY t.name, DATE_TRUNC('month', b.booking_date), fs.base_salary, fs.allowance, bn.total_bonus
ORDER BY 月份 DESC, t.name;
```

---

## 四、每月課程毛利

> 毛利 = 學生收入 − 教師成本（教學費 + 加班費）。

```sql
SELECT
    TO_CHAR(b.booking_date, 'YYYY-MM')           AS 月份,
    c.course_name                                 AS 課程名稱,
    COUNT(*)                                      AS 預約數,
    SUM(b.lessons_used)                           AS 總堂數,
    -- 收入：學生每堂單價 × 堂數
    SUM(
        COALESCE(
            scd.amount,
            sc.total_amount / NULLIF(sc.total_lessons, 0)
        ) * b.lessons_used
    )                                             AS 學生收入,
    -- 成本：教師時薪 × 堂數 + 加班費
    SUM(b.teacher_hourly_rate * b.lessons_used)
        + SUM(COALESCE(b.overtime_pay, 0))        AS 教師成本,
    -- 毛利
    SUM(
        COALESCE(
            scd.amount,
            sc.total_amount / NULLIF(sc.total_lessons, 0)
        ) * b.lessons_used
    ) - SUM(b.teacher_hourly_rate * b.lessons_used)
      - SUM(COALESCE(b.overtime_pay, 0))          AS 毛利
FROM bookings b
JOIN courses c ON c.id = b.course_id
LEFT JOIN student_contracts sc ON sc.id = b.student_contract_id
LEFT JOIN student_contract_details scd
    ON scd.student_contract_id = b.student_contract_id
    AND scd.course_id = b.course_id
    AND scd.detail_type = 'lesson_price'
    AND scd.is_deleted = FALSE
WHERE b.is_deleted = FALSE
  AND b.booking_status IN ('confirmed', 'completed')
  AND b.booking_type != 'trial'
GROUP BY TO_CHAR(b.booking_date, 'YYYY-MM'), c.course_name
ORDER BY 月份 DESC, 毛利 DESC;
```

### 收入計算邏輯

學生單堂價格的取得優先順序：
1. `student_contract_details` 中 `detail_type = 'lesson_price'` 且 `course_id` 匹配 → 精確的課程單價
2. Fallback: `student_contracts.total_amount / total_lessons` → 合約均價

---

## 五、每月課程毛利率

> 在毛利基礎上加上毛利率百分比。

```sql
WITH course_profit AS (
    SELECT
        TO_CHAR(b.booking_date, 'YYYY-MM')       AS month,
        c.course_name,
        SUM(b.lessons_used)                       AS total_lessons,
        SUM(
            COALESCE(scd.amount, sc.total_amount / NULLIF(sc.total_lessons, 0))
            * b.lessons_used
        )                                         AS revenue,
        SUM(b.teacher_hourly_rate * b.lessons_used)
            + SUM(COALESCE(b.overtime_pay, 0))    AS cost
    FROM bookings b
    JOIN courses c ON c.id = b.course_id
    LEFT JOIN student_contracts sc ON sc.id = b.student_contract_id
    LEFT JOIN student_contract_details scd
        ON scd.student_contract_id = b.student_contract_id
        AND scd.course_id = b.course_id
        AND scd.detail_type = 'lesson_price'
        AND scd.is_deleted = FALSE
    WHERE b.is_deleted = FALSE
      AND b.booking_status IN ('confirmed', 'completed')
      AND b.booking_type != 'trial'
    GROUP BY TO_CHAR(b.booking_date, 'YYYY-MM'), c.course_name
)
SELECT
    month                                          AS 月份,
    course_name                                    AS 課程名稱,
    total_lessons                                  AS 總堂數,
    revenue                                        AS 學生收入,
    cost                                           AS 教師成本,
    revenue - cost                                 AS 毛利,
    CASE WHEN revenue > 0
         THEN ROUND((revenue - cost) / revenue * 100, 1)
         ELSE 0
    END                                            AS 毛利率
FROM course_profit
ORDER BY 月份 DESC, 毛利 DESC;
```

---

## 六、每月教師加班費明細

> 列出每位正職教師每月的加班費合計與加班堂數。

```sql
SELECT
    t.name                                          AS 教師姓名,
    TO_CHAR(b.booking_date, 'YYYY-MM')              AS 月份,
    COUNT(*)                                         AS 加班預約數,
    SUM(b.lessons_used)                              AS 加班堂數,
    SUM(b.overtime_pay)                              AS 加班費合計
FROM bookings b
JOIN teachers t ON t.id = b.teacher_id
WHERE b.is_deleted = FALSE
  AND b.booking_status IN ('confirmed', 'completed')
  AND b.overtime_pay IS NOT NULL
  AND b.overtime_pay > 0
GROUP BY t.name, TO_CHAR(b.booking_date, 'YYYY-MM')
ORDER BY 月份 DESC, 加班費合計 DESC;
```

---

## 七、每月獎金明細

> 依教師、月份、獎金類型分組。

```sql
SELECT
    t.name                                           AS 教師姓名,
    TO_CHAR(tbr.bonus_date, 'YYYY-MM')               AS 月份,
    tbr.bonus_type                                   AS 獎金類型,
    COUNT(*)                                          AS 筆數,
    SUM(tbr.amount)                                   AS 金額
FROM teacher_bonus_records tbr
JOIN teachers t ON t.id = tbr.teacher_id
WHERE tbr.is_deleted = FALSE
GROUP BY t.name, TO_CHAR(tbr.bonus_date, 'YYYY-MM'), tbr.bonus_type
ORDER BY 月份 DESC, t.name, tbr.bonus_type;
```

### 獎金類型對照

| bonus_type | 說明 | 觸發方式 |
|------------|------|---------|
| `trial_completed` | 試上完成獎金 | 自動（預約完成時） |
| `trial_to_formal` | 試上轉正獎金 | 自動（學生轉正時） |
| `performance` | 績效獎金 | 手動 |
| `substitute` | 代課獎金 | 手動 |
| `referral` | 推薦獎金 | 手動 |
| `other` | 其他 | 手動 |

---

## 八、學生合約消耗進度

> 追蹤每位學生的合約使用率。

```sql
SELECT
    s.name                                           AS 學生姓名,
    sc.contract_no                                   AS 合約編號,
    sc.contract_status                               AS 狀態,
    sc.total_lessons                                 AS 總堂數,
    sc.remaining_lessons                             AS 剩餘堂數,
    sc.total_lessons - sc.remaining_lessons          AS 已用堂數,
    ROUND(
        (sc.total_lessons - sc.remaining_lessons)::numeric
        / NULLIF(sc.total_lessons, 0) * 100, 1
    )                                                AS 使用率,
    sc.total_amount                                  AS 合約金額,
    ROUND(
        sc.total_amount / NULLIF(sc.total_lessons, 0), 0
    )                                                AS 平均單價,
    sc.start_date                                    AS 開始日,
    sc.end_date                                      AS 結束日
FROM student_contracts sc
JOIN students s ON s.id = sc.student_id
WHERE sc.is_deleted = FALSE
ORDER BY 使用率 DESC, s.name;
```

---

## 九、每月營收總覽（單一指標看板）

> 一個查詢產出月份級的總營收、總成本、總毛利。

```sql
SELECT
    TO_CHAR(b.booking_date, 'YYYY-MM')               AS 月份,
    COUNT(*)                                          AS 預約數,
    SUM(b.lessons_used)                               AS 總堂數,
    -- 營收
    SUM(
        COALESCE(scd.amount, sc.total_amount / NULLIF(sc.total_lessons, 0))
        * b.lessons_used
    )                                                 AS 總營收,
    -- 教師直接成本
    SUM(b.teacher_hourly_rate * b.lessons_used)
        + SUM(COALESCE(b.overtime_pay, 0))            AS 教師成本,
    -- 毛利
    SUM(
        COALESCE(scd.amount, sc.total_amount / NULLIF(sc.total_lessons, 0))
        * b.lessons_used
    ) - SUM(b.teacher_hourly_rate * b.lessons_used)
      - SUM(COALESCE(b.overtime_pay, 0))              AS 毛利
FROM bookings b
LEFT JOIN student_contracts sc ON sc.id = b.student_contract_id
LEFT JOIN student_contract_details scd
    ON scd.student_contract_id = b.student_contract_id
    AND scd.course_id = b.course_id
    AND scd.detail_type = 'lesson_price'
    AND scd.is_deleted = FALSE
WHERE b.is_deleted = FALSE
  AND b.booking_status IN ('confirmed', 'completed')
  AND b.booking_type != 'trial'
GROUP BY TO_CHAR(b.booking_date, 'YYYY-MM')
ORDER BY 月份 DESC;
```

> **注意**：此處的「教師成本」不含底薪和津貼（固定成本），僅含與上課直接相關的變動成本。如需完整成本，需加上查詢一的固定薪資。

---

## 十、指定月份完整損益

> 傳入月份參數，產出該月完整損益表。

```sql
-- 參數：$1 = '2026-04'（月份字串）

WITH month_revenue AS (
    SELECT
        SUM(
            COALESCE(scd.amount, sc.total_amount / NULLIF(sc.total_lessons, 0))
            * b.lessons_used
        ) AS revenue
    FROM bookings b
    LEFT JOIN student_contracts sc ON sc.id = b.student_contract_id
    LEFT JOIN student_contract_details scd
        ON scd.student_contract_id = b.student_contract_id
        AND scd.course_id = b.course_id
        AND scd.detail_type = 'lesson_price'
        AND scd.is_deleted = FALSE
    WHERE b.is_deleted = FALSE
      AND b.booking_status IN ('confirmed', 'completed')
      AND b.booking_type != 'trial'
      AND TO_CHAR(b.booking_date, 'YYYY-MM') = $1
),
month_teaching_cost AS (
    SELECT
        SUM(b.teacher_hourly_rate * b.lessons_used) AS teaching_cost,
        SUM(COALESCE(b.overtime_pay, 0))            AS overtime_cost
    FROM bookings b
    WHERE b.is_deleted = FALSE
      AND b.booking_status IN ('confirmed', 'completed')
      AND b.booking_type != 'trial'
      AND TO_CHAR(b.booking_date, 'YYYY-MM') = $1
),
month_fixed_salary AS (
    -- 正職教師月固定成本（底薪 + 津貼），只計算該月有 active 合約的教師
    SELECT
        SUM(CASE WHEN tcd.detail_type = 'base_salary' THEN tcd.amount ELSE 0 END) AS base_salary,
        SUM(CASE WHEN tcd.detail_type = 'allowance'   THEN tcd.amount ELSE 0 END) AS allowance
    FROM teacher_contracts tc
    JOIN teacher_contract_details tcd ON tcd.teacher_contract_id = tc.id
        AND tcd.is_deleted = FALSE AND tcd.detail_type IN ('base_salary', 'allowance')
    WHERE tc.is_deleted = FALSE
      AND tc.employment_type = 'full_time'
      AND tc.contract_status = 'active'
      AND tc.start_date <= (TO_DATE($1, 'YYYY-MM') + INTERVAL '1 month' - INTERVAL '1 day')::date
      AND tc.end_date   >= TO_DATE($1, 'YYYY-MM')
),
month_bonus AS (
    SELECT COALESCE(SUM(amount), 0) AS total_bonus
    FROM teacher_bonus_records
    WHERE is_deleted = FALSE
      AND TO_CHAR(bonus_date, 'YYYY-MM') = $1
)
SELECT
    $1                                                              AS 月份,
    COALESCE(r.revenue, 0)                                          AS 營收,
    COALESCE(tc.teaching_cost, 0)                                   AS 教學費,
    COALESCE(tc.overtime_cost, 0)                                   AS 加班費,
    COALESCE(fs.base_salary, 0)                                     AS 底薪,
    COALESCE(fs.allowance, 0)                                       AS 津貼,
    COALESCE(bn.total_bonus, 0)                                     AS 獎金,
    -- 總成本
    COALESCE(tc.teaching_cost, 0)
        + COALESCE(tc.overtime_cost, 0)
        + COALESCE(fs.base_salary, 0)
        + COALESCE(fs.allowance, 0)
        + COALESCE(bn.total_bonus, 0)                               AS 總成本,
    -- 淨利
    COALESCE(r.revenue, 0)
        - COALESCE(tc.teaching_cost, 0)
        - COALESCE(tc.overtime_cost, 0)
        - COALESCE(fs.base_salary, 0)
        - COALESCE(fs.allowance, 0)
        - COALESCE(bn.total_bonus, 0)                               AS 淨利
FROM month_revenue r, month_teaching_cost tc, month_fixed_salary fs, month_bonus bn;
```

---

## 注意事項

1. **試上預約不計費**：所有財務查詢都排除 `booking_type = 'trial'`，因為試上的 `teacher_hourly_rate = 0` 且不扣學生合約。

2. **學生單堂價格的取得**：
   - 優先：`student_contract_details` 的 `lesson_price`（依 `course_id` 精確匹配）
   - Fallback：`total_amount / total_lessons`（合約均價）
   - **建議**：建立學生合約時務必填入 `lesson_price` 明細，確保課程毛利精確。

3. **加班費已持久化**：`bookings.overtime_pay` 在建立預約時自動計算並寫入 DB，可直接 `SUM()` 聚合，無需在查詢時動態計算。

4. **底薪/津貼是月固定**：不隨上課次數變動，在損益表中屬於固定成本。查詢時應確認合約在目標月份仍為 `active` 狀態。

5. **匯率/幣別**：目前系統所有金額為同一幣別（TWD），無匯率轉換需求。

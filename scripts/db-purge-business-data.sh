#!/bin/bash
# 硬刪除所有「業務資料」（合約、預約、請假、代課、獎金、附約 等），
# 但完整保留所有帳號與實體（teachers / students / employees / users / 角色 / 權限）。
#
# 適用情境：跑過幾輪測試後想把預約/合約/堂數歸零，但不想重新建學生/老師/帳號。
#
# 保留：
#   • users / user_profiles / line_user_bindings / user_page_overrides
#   • employees / teachers / students（實體 row）
#   • roles / role_pages / page_permissions
#   • courses（課程主檔）
#   • google_drive_config / zoom_accounts / teacher_zoom_accounts（帳號/授權狀態）
#   • teacher_details / student_details（人員 profile 上傳檔資訊）
#   • notification_preferences（使用者通知偏好）
#   • _migrations / auto_number_sequences 相關
#
# 硬刪除（單一 transaction，失敗 rollback）：
#   • bookings + 子表（zoom_meeting_logs / teacher_bonus_records / substitute_details /
#                     leave_records / booking_details / booking_calendar_events CASCADE）
#   • teacher_available_slots / teacher_work_schedules
#   • contract_addendums（polymorphic FK，不會 CASCADE，必須先刪）
#   • teacher_contracts（teacher_contract_details CASCADE）
#   • student_contracts（student_contract_details / student_contract_leave_records CASCADE）
#   • student_courses / student_teacher_preferences
#   • notification_logs / line_notification_logs / notification_queue / system_alerts
#
# 使用方式：
#   ./scripts/db-purge-business-data.sh                       # 互動式確認
#   ./scripts/db-purge-business-data.sh --yes                 # 跳過確認 (CI/cron 用)
#   ./scripts/db-purge-business-data.sh --dry-run             # 只顯示會刪幾筆，不實際刪
#   CONTAINER=teaching-platform-db ./scripts/db-purge-business-data.sh   # 自訂 container 名
#
# ⚠️ 動作不可逆。預設拒絕在非本機環境跑：
#    - 必須能 docker exec 到 ${CONTAINER}
#    - CONTAINER 名稱必須含 'teaching-platform' 或 'local'
#    - 若想跑遠端，自行 export ALLOW_REMOTE=1 並對自己風險負責

set -euo pipefail

CONTAINER="${CONTAINER:-teaching-platform-db}"
PG_USER="${PG_USER:-postgres}"
PG_DB="${PG_DB:-postgres}"

DRY_RUN=0
ASSUME_YES=0
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        --yes|-y) ASSUME_YES=1 ;;
        -h|--help) sed -n '2,/^$/p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "Unknown arg: $arg" >&2; exit 2 ;;
    esac
done

# Safety: 拒絕在 production 風格的 container 名稱跑
if [[ "$CONTAINER" != *"local"* && "$CONTAINER" != *"teaching-platform"* && "${ALLOW_REMOTE:-0}" != "1" ]]; then
    echo "[abort] CONTAINER='$CONTAINER' 不像本機 docker，請設 ALLOW_REMOTE=1 自行確認再跑" >&2
    exit 3
fi

if ! docker exec "$CONTAINER" true >/dev/null 2>&1; then
    echo "[abort] 連不到 container '$CONTAINER'" >&2
    exit 4
fi

psql() {
    docker exec -i "$CONTAINER" psql -U "$PG_USER" -d "$PG_DB" "$@"
}

# ─── 1. 預覽：列出將被影響的筆數 ───
echo "==> 影響範圍（執行前）"
psql -At <<'SQL' | column -t -s '|'
SELECT 'bookings',                count(*) FROM bookings
UNION ALL SELECT 'zoom_meeting_logs',       count(*) FROM zoom_meeting_logs
UNION ALL SELECT 'teacher_bonus_records',   count(*) FROM teacher_bonus_records
UNION ALL SELECT 'substitute_details',      count(*) FROM substitute_details
UNION ALL SELECT 'leave_records',           count(*) FROM leave_records
UNION ALL SELECT 'booking_details',         count(*) FROM booking_details
UNION ALL SELECT 'teacher_available_slots', count(*) FROM teacher_available_slots
UNION ALL SELECT 'teacher_work_schedules',  count(*) FROM teacher_work_schedules
UNION ALL SELECT 'contract_addendums',      count(*) FROM contract_addendums
UNION ALL SELECT 'teacher_contracts',       count(*) FROM teacher_contracts
UNION ALL SELECT 'teacher_contract_details',count(*) FROM teacher_contract_details
UNION ALL SELECT 'student_contracts',       count(*) FROM student_contracts
UNION ALL SELECT 'student_contract_details',count(*) FROM student_contract_details
UNION ALL SELECT 'student_contract_leave_records', count(*) FROM student_contract_leave_records
UNION ALL SELECT 'student_courses',         count(*) FROM student_courses
UNION ALL SELECT 'student_teacher_preferences', count(*) FROM student_teacher_preferences
UNION ALL SELECT 'notification_logs',       count(*) FROM notification_logs
UNION ALL SELECT 'line_notification_logs',  count(*) FROM line_notification_logs
UNION ALL SELECT 'notification_queue',      count(*) FROM notification_queue
UNION ALL SELECT 'system_alerts',           count(*) FROM system_alerts
ORDER BY 1;
SQL
echo

echo "==> 保留不動（執行前後皆相同）"
psql -At <<'SQL' | column -t -s '|'
SELECT 'users',         count(*) FROM users
UNION ALL SELECT 'employees',   count(*) FROM employees
UNION ALL SELECT 'teachers',    count(*) FROM teachers
UNION ALL SELECT 'students',    count(*) FROM students
UNION ALL SELECT 'roles',       count(*) FROM roles
UNION ALL SELECT 'pages',       count(*) FROM pages
UNION ALL SELECT 'courses',     count(*) FROM courses
ORDER BY 1;
SQL
echo

if [[ "$DRY_RUN" == "1" ]]; then
    echo "[dry-run] 結束，未實際刪除"
    exit 0
fi

# ─── 2. 互動確認 ───
if [[ "$ASSUME_YES" != "1" ]]; then
    echo "⚠️  以上業務資料即將從 container '$CONTAINER' 硬刪除（不可還原）。"
    echo "    所有 user / teacher / student / employee 帳號跟角色權限會原封不動保留。"
    read -r -p "輸入 'yes' 繼續：" answer
    [[ "$answer" == "yes" ]] || { echo "[abort] 取消"; exit 5; }
fi

# ─── 3. 執行：單一 transaction，失敗自動 rollback ───
echo "==> 開始刪除..."
psql -e -v ON_ERROR_STOP=1 <<'SQL'
BEGIN;

-- 解開 bookings ↔ substitute_details 的循環 FK
UPDATE bookings SET substitute_detail_id = NULL
WHERE substitute_detail_id IS NOT NULL;

-- L1: bookings 的子表
DELETE FROM zoom_meeting_logs;
DELETE FROM teacher_bonus_records;
DELETE FROM substitute_details;
DELETE FROM leave_records;
DELETE FROM booking_details;

-- L2: bookings (booking_calendar_events 自動 CASCADE)
DELETE FROM bookings;

-- L3: teacher schedule / slots
DELETE FROM teacher_available_slots;
DELETE FROM teacher_work_schedules;

-- L4: contract addendums (polymorphic FK，無 CASCADE，需要在 contracts 前刪)
DELETE FROM contract_addendums;

-- L5: contracts (details / leave_records on contract CASCADE)
DELETE FROM teacher_contracts;
DELETE FROM student_contracts;

-- L6: student 其他關聯
DELETE FROM student_courses;
DELETE FROM student_teacher_preferences;

-- L7: notification / alert log
DELETE FROM notification_logs;
DELETE FROM line_notification_logs;
DELETE FROM notification_queue;
DELETE FROM system_alerts;

COMMIT;
SQL

# ─── 4. 驗證後狀態 ───
echo
echo "==> 執行後狀態"
psql -At <<'SQL' | column -t -s '|'
SELECT 'bookings',                count(*) FROM bookings
UNION ALL SELECT 'teacher_contracts',       count(*) FROM teacher_contracts
UNION ALL SELECT 'student_contracts',       count(*) FROM student_contracts
UNION ALL SELECT 'leave_records',           count(*) FROM leave_records
UNION ALL SELECT 'teacher_available_slots', count(*) FROM teacher_available_slots
UNION ALL SELECT '— 保留 —',                 NULL::bigint
UNION ALL SELECT 'users (kept)',            count(*) FROM users
UNION ALL SELECT 'teachers (kept)',         count(*) FROM teachers
UNION ALL SELECT 'students (kept)',         count(*) FROM students
UNION ALL SELECT 'employees (kept)',        count(*) FROM employees
UNION ALL SELECT 'roles (kept)',            count(*) FROM roles
UNION ALL SELECT 'courses (kept)',          count(*) FROM courses
ORDER BY 1;
SQL

echo
echo "✓ 完成"

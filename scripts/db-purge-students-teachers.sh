#!/bin/bash
# 硬刪除所有學生、老師、預約與相關資料 (本機 docker DB 專用)
#
# 保留：employees、employee 對應的 users / user_profiles、courses、roles、
#       page_permissions、google_drive_config、zoom_accounts、_migrations 等
#       與 teacher/student/booking 無關的資料。
#
# 使用方式：
#   ./scripts/db-purge-students-teachers.sh                       # 互動式確認
#   ./scripts/db-purge-students-teachers.sh --yes                 # 跳過確認 (CI/cron 用)
#   ./scripts/db-purge-students-teachers.sh --dry-run             # 只顯示會刪幾筆，不實際刪
#   CONTAINER=teaching-platform-db ./scripts/db-purge-students-teachers.sh   # 自訂 container 名
#
# ⚠️ 動作不可逆。預設拒絕在非本機環境跑：
#    - 必須能 docker exec 到 ${CONTAINER}
#    - DATABASE_URL host 必須是 'db' 或 'localhost'
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
SELECT 'teachers' AS tbl, count(*) FROM teachers
UNION ALL SELECT 'students',                count(*) FROM students
UNION ALL SELECT 'bookings',                count(*) FROM bookings
UNION ALL SELECT 'zoom_meeting_logs',       count(*) FROM zoom_meeting_logs
UNION ALL SELECT 'teacher_bonus_records',   count(*) FROM teacher_bonus_records
UNION ALL SELECT 'substitute_details',      count(*) FROM substitute_details
UNION ALL SELECT 'leave_records',           count(*) FROM leave_records
UNION ALL SELECT 'booking_details',         count(*) FROM booking_details
UNION ALL SELECT 'teacher_available_slots', count(*) FROM teacher_available_slots
UNION ALL SELECT 'teacher_work_schedules',  count(*) FROM teacher_work_schedules
UNION ALL SELECT 'teacher_contracts',       count(*) FROM teacher_contracts
UNION ALL SELECT 'teacher_contract_details',count(*) FROM teacher_contract_details
UNION ALL SELECT 'teacher_zoom_accounts',   count(*) FROM teacher_zoom_accounts
UNION ALL SELECT 'teacher_details',         count(*) FROM teacher_details
UNION ALL SELECT 'student_contracts',       count(*) FROM student_contracts
UNION ALL SELECT 'student_contract_details',count(*) FROM student_contract_details
UNION ALL SELECT 'student_courses',         count(*) FROM student_courses
UNION ALL SELECT 'student_teacher_preferences', count(*) FROM student_teacher_preferences
UNION ALL SELECT 'student_details',         count(*) FROM student_details
UNION ALL SELECT 'user_profiles (teacher/student)', count(*)
                FROM user_profiles WHERE teacher_id IS NOT NULL OR student_id IS NOT NULL
UNION ALL SELECT 'users (linked)',          count(*)
                FROM users u
                JOIN user_profiles up ON up.id = u.id
                WHERE up.teacher_id IS NOT NULL OR up.student_id IS NOT NULL
ORDER BY tbl;
SQL
echo

if [[ "$DRY_RUN" == "1" ]]; then
    echo "[dry-run] 結束，未實際刪除"
    exit 0
fi

# ─── 2. 互動確認 ───
if [[ "$ASSUME_YES" != "1" ]]; then
    echo "⚠️  以上資料即將從 container '$CONTAINER' 硬刪除（不可還原）。"
    read -r -p "輸入 'yes' 繼續：" answer
    [[ "$answer" == "yes" ]] || { echo "[abort] 取消"; exit 5; }
fi

# ─── 3. 執行：單一 transaction，失敗自動 rollback ───
echo "==> 開始刪除..."
psql -e -v ON_ERROR_STOP=1 <<'SQL'
BEGIN;

CREATE TEMP TABLE _del_users AS
SELECT id FROM user_profiles
WHERE teacher_id IS NOT NULL OR student_id IS NOT NULL;

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

-- L3: teacher 子表 (slots/schedules → contracts → 其他)
DELETE FROM teacher_available_slots;
DELETE FROM teacher_work_schedules;
DELETE FROM teacher_contracts;        -- teacher_contract_details CASCADE
DELETE FROM teacher_zoom_accounts;
DELETE FROM teacher_details;

-- L3: student 子表
DELETE FROM student_courses;
DELETE FROM student_teacher_preferences;
DELETE FROM student_contracts;        -- student_contract_details / leave_records CASCADE
DELETE FROM student_details;

-- L3: 教師/學生對應的 user_profiles
DELETE FROM user_profiles
WHERE teacher_id IS NOT NULL OR student_id IS NOT NULL;

-- L4: teachers, students
DELETE FROM teachers;
DELETE FROM students;

-- L5: 對應 users (CASCADE 自動清 line_user_bindings / user_page_overrides 等)
DELETE FROM users WHERE id IN (SELECT id FROM _del_users);

COMMIT;
SQL

# ─── 4. 驗證後狀態 ───
echo
echo "==> 執行後狀態"
psql -At <<'SQL' | column -t -s '|'
SELECT 'teachers',              count(*) FROM teachers
UNION ALL SELECT 'students',    count(*) FROM students
UNION ALL SELECT 'bookings',    count(*) FROM bookings
UNION ALL SELECT 'employees (kept)', count(*) FROM employees
UNION ALL SELECT 'users (remaining)', count(*) FROM users
UNION ALL SELECT 'user_profiles (remaining)', count(*) FROM user_profiles
ORDER BY 1;
SQL

echo
echo "✓ 完成"

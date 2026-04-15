-- 021: 新增 bookings.lessons_used 並移除 booking_details.lessons_used
-- 用於支援多堂課預約（例如 10:00-12:00 = 2 堂 60 分鐘課程）

-- 1. 新增 bookings.lessons_used
ALTER TABLE bookings ADD COLUMN lessons_used INT NOT NULL DEFAULT 1;

-- 回填現有資料：根據預約時長 / 課程時長計算
UPDATE bookings b
SET lessons_used = GREATEST(1,
  (EXTRACT(EPOCH FROM (b.end_time - b.start_time)) / 60
  / COALESCE((SELECT c.duration_minutes FROM courses c WHERE c.id = b.course_id), 60))
)::INT;

-- 2. 移除 booking_details.lessons_used（改由 bookings.lessons_used 統一管理）
ALTER TABLE booking_details DROP COLUMN IF EXISTS lessons_used;

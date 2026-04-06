-- 050: 預約加班費持久化
-- 將 overtime_pay 從純動態計算改為存入 bookings 表，方便月報 SQL 直接聚合

ALTER TABLE bookings ADD COLUMN overtime_pay DECIMAL(10,2) DEFAULT NULL;

COMMENT ON COLUMN bookings.overtime_pay IS '加班費 = overtime_lessons × overtime_rate，僅正職教師預約有值';

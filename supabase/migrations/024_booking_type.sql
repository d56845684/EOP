-- 024: Add booking_type column to bookings table
-- 讓每筆預約自帶 trial/regular 標記，避免依賴 student_type 回推

ALTER TABLE bookings ADD COLUMN booking_type VARCHAR(20) DEFAULT 'regular' NOT NULL;
ALTER TABLE bookings ADD CONSTRAINT chk_booking_type CHECK (booking_type IN ('trial', 'regular'));

-- 回填：沒有學生合約的視為試上
UPDATE bookings SET booking_type = 'trial' WHERE student_contract_id IS NULL;

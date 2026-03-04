-- 插入血糖记录示例
INSERT INTO blood_sugar_records (time, glucose_level, meal_type)
VALUES 
('2026-03-04 08:00:00', 5.6, '餐前'),
('2026-03-04 10:00:00', 7.8, '餐后');

-- 插入血压记录示例
INSERT INTO blood_pressure_records (time, systolic, diastolic)
VALUES 
('2026-03-04 07:30:00', 120, 80),
('2026-03-04 19:00:00', 118, 78);

-- 插入睡眠记录示例
INSERT INTO sleep_records (sleep_time, wake_time, light_sleep_duration, deep_sleep_duration, rem_duration)
VALUES 
('2026-03-03 23:00:00', '2026-03-04 07:00:00', 272, 130, 53);

-- 插入体重记录示例
INSERT INTO weight_records (time, weight)
VALUES 
('2026-03-04 08:00:00', 72.3);
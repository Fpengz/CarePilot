-- 1. 血糖记录表
CREATE TABLE blood_sugar_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    time DATETIME NOT NULL,                    -- 时间
    glucose_level REAL NOT NULL,               -- 血糖浓度
    meal_type TEXT,                             -- 餐前or餐后 (可选值：'餐前', '餐后', NULL)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 血压记录表
CREATE TABLE blood_pressure_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    time DATETIME NOT NULL,                    -- 时间
    systolic INTEGER NOT NULL,                 -- 收缩压（高压）
    diastolic INTEGER NOT NULL,                -- 舒张压（低压）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. 睡眠记录表
CREATE TABLE sleep_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sleep_time DATETIME NOT NULL,              -- 入睡时间
    wake_time DATETIME NOT NULL,               -- 清醒时间
    light_sleep_duration INTEGER,              -- 浅睡时长（分钟）
    deep_sleep_duration INTEGER,               -- 深睡时长（分钟）
    rem_duration INTEGER,                      -- 快速眼动时长（分钟）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. 体重表
CREATE TABLE weight_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    time DATETIME NOT NULL,                    -- 时间
    weight REAL NOT NULL,                      -- 数值（公斤）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引以提高查询性能
CREATE INDEX idx_blood_sugar_time ON blood_sugar_records(time);
CREATE INDEX idx_blood_pressure_time ON blood_pressure_records(time);
CREATE INDEX idx_sleep_time ON sleep_records(sleep_time);
CREATE INDEX idx_weight_time ON weight_records(time);
-- ==========================================
-- 1. 创建表结构
-- ==========================================

-- 1.1 用户表 (users)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user',
    region VARCHAR(100),
    real_name VARCHAR(100)
);

-- 1.2 医院/客户表 (hospitals)
CREATE TABLE IF NOT EXISTS hospitals (
    id SERIAL PRIMARY KEY,
    code VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    region VARCHAR(100)
);

-- 1.3 系统配置字典表 (system_configs)
CREATE TABLE IF NOT EXISTS system_configs (
    id SERIAL PRIMARY KEY,
    config_type VARCHAR(100) NOT NULL,
    label VARCHAR(255) NOT NULL
);

-- 1.4 活动日志表 (activity_logs)
CREATE TABLE IF NOT EXISTS activity_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    user_name VARCHAR(100),
    hospital_code VARCHAR(100) REFERENCES hospitals(code) ON DELETE CASCADE,
    contact_person VARCHAR(255),
    visit_time_start TIMESTAMP,
    visit_time_end TIMESTAMP,
    purpose TEXT,
    activity_types JSONB,  -- 使用 JSONB 存储数组类型更高效
    next_step TEXT,
    opportunities JSONB
);

-- ==========================================
-- 2. 注入初始种子数据 (Seed Data)
-- ==========================================

-- 2.1 注入系统配置字典 (原系统中动态获取的任务类型和机会类型)
INSERT INTO system_configs (config_type, label) VALUES 
('visit_type', 'CCM 售前支持'),
('visit_type', '分析仪售前支持'),
('visit_type', 'StarWars 专项'),
('visit_type', 'Sparkling 同台竞技'),
('visit_type', '常规拜访交流'),
('opportunity_type', 'KOL 发展'),
('opportunity_type', 'ShowCase 潜力'),
('opportunity_type', '区域标杆客户')
ON CONFLICT DO NOTHING;

-- 2.2 注入全员 51 人名单及管理员 (复用之前的 init_users.sql 数据)
INSERT INTO users (username, password_hash, role, region, real_name) VALUES 
('guoe1', '123456', 'user', '北二', '郭恩意'),
('liul81', '123456', 'user', '北二', '刘磊'),
('liux146', '123456', 'user', '北二', '刘晓平'),
('zhangc96', '123456', 'user', '北二', '张春燕'),
('chenh41', '123456', 'user', '北一', '陈海山'),
('chenw26', '123456', 'user', '北一', '陈雯雯'),
('liangq11', '123456', 'user', '北一', '梁强强'),
('liuy120', '123456', 'user', '北一', '刘玉宽'),
('max51', '123456', 'user', '北一', '马晓敏'),
('suiz', '123456', 'user', '北一', '随志芳'),
('yum12', '123456', 'user', '北一', '于淼'),
('jinj49','123456','user','东二','金佳琨'),
('lvc10', '123456', 'user', '东二', '吕正闯'),
('wangy360', '123456', 'user', '东二', '汪翊杨'),
('wangm93', '123456', 'user', '东二', '王懋'),
('wul72', '123456', 'user', '东二', '吴泠奎'),
('zhanl267', '123456', 'user', '东二', '张礼俊'),
('zhany286', '123456', 'user', '东二', '张韵若'),
('dait1', '123456', 'user', '东一', '代涛'),
('houj14', '123456', 'user', '东一', '侯金运'),
('houw4', '123456', 'user', '东一', '侯文洋'),
('lis114', '123456', 'user', '东一', '李硕'),
('liy303', '123456', 'user', '东一', '李宇航'),
('weny23', '123456', 'user', '东一', '温飏'),
('xuh55', '123456', 'user', '东一', '徐海东'),
('zhouc30', '123456', 'user', '东一', '周伟承'),
('chenf15', '123456', 'user', '南二', '陈飞'),
('dais', '123456', 'user', '南二', '戴仕友'),
('liw65', '123456', 'user', '南二', '李维'),
('linz34', '123456', 'user', '南二', '林振涛'),
('yiz1', '123456', 'user', '南二', '弋舟'),
('yud24', '123456', 'user', '南二', '余大伟'),
('guany5', '123456', 'user', '南一', '管运钦'),
('liz135', '123456', 'user', '南一', '李忠旺'),
('liug24', '123456', 'user', '南一', '刘桂治'),
('panx22', '123456', 'user', '南一', '潘鑫伟'),
('xuj105', '123456', 'user', '南一', '徐江洲'),
('zhengy23', '123456', 'user', '南一', '郑奕斌'),
('caos15', '123456', 'user', '西二', '曹世宇'),
('wangw97', '123456', 'user', '西二', '王维'),
('zhouy178', '123456', 'user', '西二', '周宇航'),
('zenga2', '123456', 'user', '西一', '曾安权'),
('hej42', '123456', 'user', '西一', '何俊迁'),
('tany46', '123456', 'user', '西一', '谭莹'),
('wuk37', '123456', 'user', '西一', '伍恺朋'),
('zhanh221', '123456', 'user', '西一', '张和哲'),
('zhouj88', '123456', 'admin', 'Central', '周骏群'),
('zhuj38', '123456', 'user', 'Central', '朱建涌'),
('xul77', '123456', 'admin', 'Central', '许立波'),
('liud25', '123456', 'user', 'Central', '刘大泉'),
('lic86', '123456', 'user', 'Central', '李成琛'),
('xut44', '123456', 'user', 'Central', '徐童周'),
('admin', 'admin123', 'admin', 'System', '超级管理员')
ON CONFLICT (username) DO NOTHING;

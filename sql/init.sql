SET NAMES utf8mb4;
SET character_set_client = utf8mb4;

-- ============================================
-- 药品销售管理系统 - 数据库初始化脚本
-- 基于ER图设计
-- 数据库：MySQL 8.0+
-- ============================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS pharmacy_db DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE pharmacy_db;

-- 禁用外键检查
SET FOREIGN_KEY_CHECKS = 0;

-- ============================================
-- 一、删除已存在的表（按依赖顺序）
-- ============================================
DROP TABLE IF EXISTS t_sales_return;
DROP TABLE IF EXISTS t_purchase_return;
DROP TABLE IF EXISTS t_sales_detail;
DROP TABLE IF EXISTS t_sales_order;
DROP TABLE IF EXISTS t_inventory_check;
DROP TABLE IF EXISTS t_purchase_detail;
DROP TABLE IF EXISTS t_purchase_order;
DROP TABLE IF EXISTS t_stock_batch;
DROP TABLE IF EXISTS t_finance_daily;
DROP TABLE IF EXISTS t_medicine;
DROP TABLE IF EXISTS t_customer;
DROP TABLE IF EXISTS t_supplier;
DROP TABLE IF EXISTS t_employee;

-- ============================================
-- 二、基础信息表
-- ============================================

-- 1. 员工表
CREATE TABLE t_employee (
    emp_id INT PRIMARY KEY COMMENT '工号(登录账号)',
    emp_name VARCHAR(50) NOT NULL COMMENT '员工姓名',
    pwd VARCHAR(64) NOT NULL COMMENT '登录密码(MD5)',
    role ENUM('Admin', 'Sales', 'Stock') NOT NULL DEFAULT 'Sales' COMMENT '角色',
    phone VARCHAR(20) UNIQUE COMMENT '联系电话',
    status TINYINT DEFAULT 1 COMMENT '状态(1:在职,0:离职)',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='员工表';

-- 2. 供应商表
CREATE TABLE t_supplier (
    sup_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '供应商ID',
    sup_name VARCHAR(100) NOT NULL UNIQUE COMMENT '供应商名称',
    contact_name VARCHAR(50) COMMENT '联系人',
    phone VARCHAR(20) NOT NULL COMMENT '联系电话',
    address VARCHAR(200) COMMENT '地址',
    license_no VARCHAR(50) COMMENT '许可证号',
    status TINYINT DEFAULT 1 COMMENT '状态(1:合作中,0:停止)',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='供应商表';

-- 3. 客户表
CREATE TABLE t_customer (
    cus_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '客户ID',
    cus_name VARCHAR(50) NOT NULL COMMENT '客户姓名',
    gender ENUM('男', '女', '未知') DEFAULT '未知' COMMENT '性别',
    phone VARCHAR(20) UNIQUE COMMENT '手机号',
    age INT CHECK (age > 0 AND age < 150) COMMENT '年龄',
    medical_history TEXT COMMENT '病史/过敏史',
    total_consume DECIMAL(12,2) DEFAULT 0.00 COMMENT '累计消费',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='客户表';

-- 4. 药品信息表
CREATE TABLE t_medicine (
    med_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '药品ID',
    med_name VARCHAR(100) NOT NULL COMMENT '药品名称',
    spec VARCHAR(50) NOT NULL COMMENT '规格',
    category VARCHAR(20) DEFAULT 'OTC' COMMENT '类别',
    unit VARCHAR(10) DEFAULT '盒' COMMENT '单位',
    factory VARCHAR(100) COMMENT '生产厂家',
    ref_buy_price DECIMAL(10,2) CHECK (ref_buy_price > 0) COMMENT '参考进价',
    ref_sell_price DECIMAL(10,2) CHECK (ref_sell_price > 0) COMMENT '参考售价',
    total_stock INT DEFAULT 0 COMMENT '总库存',
    alert_qty INT DEFAULT 10 COMMENT '预警线',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='药品信息表';

-- ============================================
-- 三、进货管理表
-- ============================================

-- 5. 进货单主表
CREATE TABLE t_purchase_order (
    po_id VARCHAR(20) PRIMARY KEY COMMENT '进货单号',
    sup_id INT NOT NULL COMMENT '供应商ID',
    emp_id INT NOT NULL COMMENT '经手人',
    total_amount DECIMAL(12,2) DEFAULT 0.00 COMMENT '总金额',
    purchase_date DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '进货日期',
    status TINYINT DEFAULT 1 COMMENT '状态(1:正常,0:撤销)',
    FOREIGN KEY (sup_id) REFERENCES t_supplier(sup_id),
    FOREIGN KEY (emp_id) REFERENCES t_employee(emp_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='进货单主表';

-- 6. 进货明细表
CREATE TABLE t_purchase_detail (
    pd_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '明细ID',
    po_id VARCHAR(20) NOT NULL COMMENT '进货单号',
    med_id INT NOT NULL COMMENT '药品ID',
    batch_no VARCHAR(30) NOT NULL COMMENT '批号',
    produce_date DATE COMMENT '生产日期',
    expiry_date DATE NOT NULL COMMENT '有效期',
    quantity INT NOT NULL CHECK (quantity > 0) COMMENT '数量',
    unit_purc_price DECIMAL(10,2) NOT NULL COMMENT '进货单价',
    FOREIGN KEY (po_id) REFERENCES t_purchase_order(po_id),
    FOREIGN KEY (med_id) REFERENCES t_medicine(med_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='进货明细表';

-- ============================================
-- 四、库存管理表
-- ============================================

-- 7. 库存批次表
CREATE TABLE t_stock_batch (
    batch_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '批次ID',
    med_id INT NOT NULL COMMENT '药品ID',
    batch_no VARCHAR(30) NOT NULL COMMENT '批号',
    expiry_date DATE NOT NULL COMMENT '有效期',
    cur_batch_qty INT DEFAULT 0 CHECK (cur_batch_qty >= 0) COMMENT '当前库存',
    create_time DATE COMMENT '创建时间',
    FOREIGN KEY (med_id) REFERENCES t_medicine(med_id),
    UNIQUE KEY uk_med_batch (med_id, batch_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='库存批次表';

-- 8. 盘点记录表
CREATE TABLE t_inventory_check (
    check_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '盘点ID',
    batch_id INT NOT NULL COMMENT '批次ID',
    book_qty INT NOT NULL COMMENT '账面数量',
    actual_qty INT NOT NULL COMMENT '实物数量',
    diff_qty INT AS (actual_qty - book_qty) STORED COMMENT '差异',
    diff_amount DECIMAL(12,2) COMMENT '盈亏金额',
    emp_id INT NOT NULL COMMENT '盘点人',
    check_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '盘点时间',
    remark VARCHAR(200) COMMENT '备注',
    FOREIGN KEY (batch_id) REFERENCES t_stock_batch(batch_id),
    FOREIGN KEY (emp_id) REFERENCES t_employee(emp_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='盘点记录表';

-- ============================================
-- 五、销售管理表
-- ============================================

-- 9. 销售单主表
CREATE TABLE t_sales_order (
    so_id VARCHAR(20) PRIMARY KEY COMMENT '销售单号',
    emp_id INT NOT NULL COMMENT '销售员',
    cus_id INT COMMENT '客户ID',
    sale_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '销售时间',
    total_price DECIMAL(12,2) DEFAULT 0.00 COMMENT '总价',
    status TINYINT DEFAULT 1 COMMENT '状态(1:正常,0:退货)',
    FOREIGN KEY (emp_id) REFERENCES t_employee(emp_id),
    FOREIGN KEY (cus_id) REFERENCES t_customer(cus_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='销售单主表';

-- 10. 销售明细表
CREATE TABLE t_sales_detail (
    sd_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '明细ID',
    so_id VARCHAR(20) NOT NULL COMMENT '销售单号',
    batch_id INT NOT NULL COMMENT '批次ID',
    med_id INT NOT NULL COMMENT '药品ID',
    quantity INT NOT NULL CHECK (quantity > 0) COMMENT '数量',
    unit_sell_price DECIMAL(10,2) NOT NULL COMMENT '售价',
    FOREIGN KEY (so_id) REFERENCES t_sales_order(so_id),
    FOREIGN KEY (batch_id) REFERENCES t_stock_batch(batch_id),
    FOREIGN KEY (med_id) REFERENCES t_medicine(med_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='销售明细表';

-- ============================================
-- 六、退货管理表
-- ============================================

-- 11. 购进退货表
CREATE TABLE t_purchase_return (
    pr_id VARCHAR(20) PRIMARY KEY COMMENT '退货单号',
    po_id VARCHAR(20) NOT NULL COMMENT '原采购单号',
    sup_id INT NOT NULL COMMENT '供应商ID',
    batch_id INT NOT NULL COMMENT '批次ID',
    quantity INT NOT NULL CHECK (quantity > 0) COMMENT '退回数量',
    return_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '退货时间',
    reason VARCHAR(200) COMMENT '退货原因',
    status TINYINT DEFAULT 1 COMMENT '状态(1:处理,0:撤销)',
    emp_id INT NOT NULL COMMENT '处理人',
    FOREIGN KEY (po_id) REFERENCES t_purchase_order(po_id),
    FOREIGN KEY (sup_id) REFERENCES t_supplier(sup_id),
    FOREIGN KEY (batch_id) REFERENCES t_stock_batch(batch_id),
    FOREIGN KEY (emp_id) REFERENCES t_employee(emp_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='购进退货表';

-- 12. 销售退货表
CREATE TABLE t_sales_return (
    sr_id VARCHAR(20) PRIMARY KEY COMMENT '退货单号',
    so_id VARCHAR(20) NOT NULL COMMENT '原销售单号',
    batch_id INT NOT NULL COMMENT '批次ID',
    quantity INT NOT NULL CHECK (quantity > 0) COMMENT '退回数量',
    return_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '退货时间',
    reason VARCHAR(200) COMMENT '退货原因',
    status TINYINT DEFAULT 1 COMMENT '状态(1:处理,0:撤销)',
    emp_id INT NOT NULL COMMENT '处理人',
    FOREIGN KEY (so_id) REFERENCES t_sales_order(so_id),
    FOREIGN KEY (batch_id) REFERENCES t_stock_batch(batch_id),
    FOREIGN KEY (emp_id) REFERENCES t_employee(emp_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='销售退货表';

-- ============================================
-- 七、财务管理表
-- ============================================

-- 13. 财务日结表
CREATE TABLE t_finance_daily (
    day_id DATE PRIMARY KEY COMMENT '统计日期',
    sales_revenue DECIMAL(12,2) DEFAULT 0.00 COMMENT '销售收入',
    sales_profit DECIMAL(12,2) DEFAULT 0.00 COMMENT '销售毛利',
    sales_return_amt DECIMAL(12,2) DEFAULT 0.00 COMMENT '销售退货金额',
    purc_return_amt DECIMAL(12,2) DEFAULT 0.00 COMMENT '购进退货金额',
    inv_loss_amt DECIMAL(12,2) DEFAULT 0.00 COMMENT '盘亏金额',
    inv_gain_amt DECIMAL(12,2) DEFAULT 0.00 COMMENT '盘盈金额',
    net_profit DECIMAL(12,2) AS (sales_profit - sales_return_amt + purc_return_amt - inv_loss_amt + inv_gain_amt) STORED COMMENT '净利润',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='财务日结表';

-- 启用外键检查
SET FOREIGN_KEY_CHECKS = 1;

-- ============================================
-- 八、索引设计
-- ============================================

CREATE INDEX idx_medicine_name ON t_medicine(med_name);
CREATE INDEX idx_medicine_category ON t_medicine(category);
CREATE INDEX idx_stock_batch_no ON t_stock_batch(batch_no);
CREATE INDEX idx_stock_expiry ON t_stock_batch(expiry_date);
CREATE INDEX idx_purchase_date ON t_purchase_order(purchase_date);
CREATE INDEX idx_sales_time ON t_sales_order(sale_time);
CREATE INDEX idx_supplier_name ON t_supplier(sup_name);

-- ============================================
-- 九、视图设计
-- ============================================

-- 视图1: 过期药品视图
CREATE OR REPLACE VIEW v_expired_drugs AS
SELECT 
    sb.batch_id,
    m.med_id,
    m.med_name,
    m.spec,
    m.factory,
    sb.batch_no,
    sb.expiry_date,
    sb.cur_batch_qty,
    DATEDIFF(sb.expiry_date, CURDATE()) AS days_to_expire,
    CASE 
        WHEN sb.expiry_date <= CURDATE() THEN '已过期'
        WHEN sb.expiry_date <= DATE_ADD(CURDATE(), INTERVAL 1 MONTH) THEN '即将过期(1月内)'
        WHEN sb.expiry_date <= DATE_ADD(CURDATE(), INTERVAL 3 MONTH) THEN '临期(3月内)'
        ELSE '临期(6月内)'
    END AS expire_status
FROM t_stock_batch sb
JOIN t_medicine m ON sb.med_id = m.med_id
WHERE sb.cur_batch_qty > 0 
  AND sb.expiry_date <= DATE_ADD(CURDATE(), INTERVAL 6 MONTH)
ORDER BY sb.expiry_date ASC;

-- 视图2: 缺货预警视图
CREATE OR REPLACE VIEW v_low_stock AS
SELECT 
    m.med_id,
    m.med_name,
    m.spec,
    m.unit,
    m.factory,
    m.total_stock,
    m.alert_qty,
    (m.alert_qty - m.total_stock) AS shortage_qty,
    m.ref_buy_price,
    CASE 
        WHEN m.total_stock = 0 THEN '缺货'
        WHEN m.total_stock < m.alert_qty THEN '低库存'
        ELSE '正常'
    END AS stock_status
FROM t_medicine m
WHERE m.total_stock < m.alert_qty
ORDER BY m.total_stock ASC;

-- 视图3: 库存明细视图
CREATE OR REPLACE VIEW v_stock_detail AS
SELECT 
    m.med_id,
    m.med_name,
    m.spec,
    m.category,
    m.unit,
    m.factory,
    sb.batch_id,
    sb.batch_no,
    sb.expiry_date,
    sb.cur_batch_qty,
    m.ref_sell_price,
    CASE WHEN sb.expiry_date <= CURDATE() THEN 1 ELSE 0 END AS is_expired
FROM t_stock_batch sb
JOIN t_medicine m ON sb.med_id = m.med_id
WHERE sb.cur_batch_qty > 0
ORDER BY m.med_name, sb.expiry_date;

-- 视图4: 销售统计视图
CREATE OR REPLACE VIEW v_sales_statistics AS
SELECT 
    DATE(so.sale_time) AS sale_date,
    COUNT(DISTINCT so.so_id) AS order_count,
    SUM(sd.quantity) AS total_qty,
    SUM(sd.quantity * sd.unit_sell_price) AS total_sales
FROM t_sales_order so
JOIN t_sales_detail sd ON so.so_id = sd.so_id
WHERE so.status = 1
GROUP BY DATE(so.sale_time)
ORDER BY sale_date DESC;

-- 视图5: 畅销药品视图
CREATE OR REPLACE VIEW v_top_selling AS
SELECT 
    m.med_id,
    m.med_name,
    m.spec,
    m.category,
    SUM(sd.quantity) AS total_sold,
    SUM(sd.quantity * sd.unit_sell_price) AS total_revenue,
    COUNT(DISTINCT so.so_id) AS order_count
FROM t_sales_detail sd
JOIN t_stock_batch sb ON sd.batch_id = sb.batch_id
JOIN t_medicine m ON sb.med_id = m.med_id
JOIN t_sales_order so ON sd.so_id = so.so_id
WHERE so.status = 1
GROUP BY m.med_id, m.med_name, m.spec, m.category
ORDER BY total_sold DESC
LIMIT 10;

-- ============================================
-- 十、触发器设计
-- ============================================

DELIMITER //

-- 触发器1: 进货后自动更新库存
DROP TRIGGER IF EXISTS trg_after_purchase_detail_insert//
CREATE TRIGGER trg_after_purchase_detail_insert
AFTER INSERT ON t_purchase_detail
FOR EACH ROW
BEGIN
    DECLARE v_batch_id INT;
    
    SELECT batch_id INTO v_batch_id 
    FROM t_stock_batch 
    WHERE med_id = NEW.med_id AND batch_no = NEW.batch_no
    LIMIT 1;
    
    IF v_batch_id IS NULL THEN
        INSERT INTO t_stock_batch (med_id, batch_no, expiry_date, cur_batch_qty, create_time)
        VALUES (NEW.med_id, NEW.batch_no, NEW.expiry_date, NEW.quantity, CURDATE());
    ELSE
        UPDATE t_stock_batch 
        SET cur_batch_qty = cur_batch_qty + NEW.quantity
        WHERE batch_id = v_batch_id;
    END IF;
    
    UPDATE t_medicine 
    SET total_stock = total_stock + NEW.quantity
    WHERE med_id = NEW.med_id;
END//

-- 触发器2: 销售后自动扣减库存
DROP TRIGGER IF EXISTS trg_after_sales_detail_insert//
CREATE TRIGGER trg_after_sales_detail_insert
AFTER INSERT ON t_sales_detail
FOR EACH ROW
BEGIN
    UPDATE t_stock_batch 
    SET cur_batch_qty = cur_batch_qty - NEW.quantity
    WHERE batch_id = NEW.batch_id;
    
    UPDATE t_medicine 
    SET total_stock = total_stock - NEW.quantity
    WHERE med_id = NEW.med_id;
END//

-- 触发器3: 销售退货恢复库存
DROP TRIGGER IF EXISTS trg_after_sales_return_insert//
CREATE TRIGGER trg_after_sales_return_insert
AFTER INSERT ON t_sales_return
FOR EACH ROW
BEGIN
    DECLARE v_med_id INT;
    
    SELECT med_id INTO v_med_id 
    FROM t_stock_batch 
    WHERE batch_id = NEW.batch_id;
    
    UPDATE t_stock_batch 
    SET cur_batch_qty = cur_batch_qty + NEW.quantity
    WHERE batch_id = NEW.batch_id;
    
    UPDATE t_medicine 
    SET total_stock = total_stock + NEW.quantity
    WHERE med_id = v_med_id;
END//

-- 触发器4: 购进退货扣减库存
DROP TRIGGER IF EXISTS trg_after_purchase_return_insert//
CREATE TRIGGER trg_after_purchase_return_insert
AFTER INSERT ON t_purchase_return
FOR EACH ROW
BEGIN
    DECLARE v_med_id INT;
    
    SELECT med_id INTO v_med_id 
    FROM t_stock_batch 
    WHERE batch_id = NEW.batch_id;
    
    UPDATE t_stock_batch 
    SET cur_batch_qty = cur_batch_qty - NEW.quantity
    WHERE batch_id = NEW.batch_id;
    
    UPDATE t_medicine 
    SET total_stock = total_stock - NEW.quantity
    WHERE med_id = v_med_id;
END//

-- 触发器5: 盘点后调整库存
DROP TRIGGER IF EXISTS trg_after_inventory_check_insert//
CREATE TRIGGER trg_after_inventory_check_insert
AFTER INSERT ON t_inventory_check
FOR EACH ROW
BEGIN
    DECLARE v_med_id INT;
    DECLARE v_diff INT;
    
    SET v_diff = NEW.actual_qty - NEW.book_qty;
    
    IF v_diff != 0 THEN
        SELECT med_id INTO v_med_id FROM t_stock_batch WHERE batch_id = NEW.batch_id;
        
        UPDATE t_stock_batch 
        SET cur_batch_qty = NEW.actual_qty
        WHERE batch_id = NEW.batch_id;
        
        UPDATE t_medicine 
        SET total_stock = total_stock + v_diff
        WHERE med_id = v_med_id;
    END IF;
END//

DELIMITER ;

-- ============================================
-- 十一、存储函数/过程
-- ============================================

DELIMITER //

-- 函数1: 生成进货单号
DROP FUNCTION IF EXISTS fn_generate_po_id//
CREATE FUNCTION fn_generate_po_id() RETURNS VARCHAR(20)
DETERMINISTIC
BEGIN
    DECLARE v_date_str VARCHAR(8);
    DECLARE v_seq INT;
    
    SET v_date_str = DATE_FORMAT(CURDATE(), '%Y%m%d');
    
    SELECT IFNULL(MAX(CAST(RIGHT(po_id, 4) AS UNSIGNED)), 0) + 1 INTO v_seq
    FROM t_purchase_order
    WHERE po_id LIKE CONCAT('P', v_date_str, '%');
    
    RETURN CONCAT('P', v_date_str, LPAD(v_seq, 4, '0'));
END//

-- 函数2: 生成销售单号
DROP FUNCTION IF EXISTS fn_generate_so_id//
CREATE FUNCTION fn_generate_so_id() RETURNS VARCHAR(20)
DETERMINISTIC
BEGIN
    DECLARE v_date_str VARCHAR(8);
    DECLARE v_seq INT;
    
    SET v_date_str = DATE_FORMAT(CURDATE(), '%Y%m%d');
    
    SELECT IFNULL(MAX(CAST(RIGHT(so_id, 4) AS UNSIGNED)), 0) + 1 INTO v_seq
    FROM t_sales_order
    WHERE so_id LIKE CONCAT('S', v_date_str, '%');
    
    RETURN CONCAT('S', v_date_str, LPAD(v_seq, 4, '0'));
END//

-- 存储过程: 月度财务统计
DROP PROCEDURE IF EXISTS sp_monthly_report//
CREATE PROCEDURE sp_monthly_report(
    IN p_year INT,
    IN p_month INT
)
BEGIN
    DECLARE v_start_date DATE;
    DECLARE v_end_date DATE;
    
    SET v_start_date = CONCAT(p_year, '-', LPAD(p_month, 2, '0'), '-01');
    SET v_end_date = LAST_DAY(v_start_date);
    
    SELECT 
        DATE_FORMAT(v_start_date, '%Y年%m月') AS month_name,
        IFNULL(SUM(sd.quantity * sd.unit_sell_price), 0) AS total_sales,
        COUNT(DISTINCT so.so_id) AS order_count,
        IFNULL(SUM(diff_amount), 0) AS inventory_loss
    FROM t_sales_order so
    LEFT JOIN t_sales_detail sd ON so.so_id = sd.so_id
    LEFT JOIN t_inventory_check ic ON ic.check_time BETWEEN v_start_date AND v_end_date
    WHERE so.status = 1
      AND so.sale_time BETWEEN v_start_date AND v_end_date;
END//

DELIMITER ;

-- ============================================
-- 十二、初始测试数据
-- ============================================

-- 插入员工
INSERT INTO t_employee (emp_id, emp_name, pwd, role, phone) VALUES
(1001, '系统管理员', 'e10adc3949ba59abbe56e057f20f883e', 'Admin', '13800000001'),
(1002, '张库管', 'e10adc3949ba59abbe56e057f20f883e', 'Stock', '13800000002'),
(1003, '李销售', 'e10adc3949ba59abbe56e057f20f883e', 'Sales', '13800000003');
-- 密码: 123456 (MD5值)

-- 插入供应商
INSERT INTO t_supplier (sup_name, contact_name, phone, address, license_no) VALUES
('国药控股北京有限公司', '陈经理', '010-88886666', '北京市朝阳区建国路88号', 'YY-BJ-2023001'),
('华润医药商业集团', '刘经理', '021-66668888', '上海市浦东新区陆家嘴环路88号', 'YY-SH-2023002'),
('九州通医药集团', '王经理', '027-88889999', '武汉市东湖新技术开发区', 'YY-WH-2023003');

-- 插入药品
INSERT INTO t_medicine (med_name, spec, category, unit, factory, ref_buy_price, ref_sell_price, alert_qty) VALUES
('阿莫西林胶囊', '0.25g*24粒', '处方药', '盒', '哈药集团制药总厂', 8.50, 15.00, 50),
('布洛芬缓释胶囊', '0.3g*20粒', 'OTC', '盒', '中美史克制药', 12.00, 22.00, 30),
('感冒灵颗粒', '10g*9袋', 'OTC', '盒', '三九医药股份有限公司', 6.00, 12.80, 100),
('复方丹参滴丸', '27mg*180粒', 'OTC', '瓶', '天津天士力制药', 18.00, 32.00, 40),
('奥美拉唑肠溶胶囊', '20mg*14粒', '处方药', '盒', '阿斯利康制药', 25.00, 45.00, 30);

-- 插入客户
INSERT INTO t_customer (cus_name, gender, phone, age, medical_history) VALUES
('王女士', '女', '13912345678', 35, '无'),
('李先生', '男', '13823456789', 58, '高血压'),
('张阿姨', '女', '13734567890', 62, '青霉素过敏');

SELECT '数据库初始化完成！' AS message;

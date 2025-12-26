SET NAMES utf8mb4;
SET character_set_client = utf8mb4;
SET character_set_results = utf8mb4;

-- ============================================
-- 药品销售管理系统 - 数据库初始化脚本
-- 包含：表结构、触发器、存储过程、视图、索引
-- 数据库：MySQL 8.0+
-- ============================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS pharmacy_db DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE pharmacy_db;

-- ============================================
-- 一、基础信息类表
-- ============================================

-- 1. 药品信息表 (t_medicine)
DROP TABLE IF EXISTS t_medicine;
CREATE TABLE t_medicine (
    med_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '药品唯一标识',
    med_name VARCHAR(100) NOT NULL COMMENT '药品通用名',
    spec VARCHAR(50) NOT NULL COMMENT '规格 (如 0.25g*12片)',
    category VARCHAR(20) DEFAULT 'OTC' COMMENT '类别 (处方药/OTC)',
    unit VARCHAR(10) DEFAULT '盒' COMMENT '单位 (盒/瓶/支)',
    factory VARCHAR(100) COMMENT '生产厂家',
    ref_buy_price DECIMAL(10,2) CHECK (ref_buy_price > 0) COMMENT '参考进价',
    ref_sell_price DECIMAL(10,2) CHECK (ref_sell_price > 0) COMMENT '参考零售价',
    total_stock INT DEFAULT 0 COMMENT '全库总库存 (冗余字段)',
    alert_qty INT DEFAULT 10 COMMENT '库存预警线',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='药品信息表';

-- 2. 员工表 (t_employee)
DROP TABLE IF EXISTS t_employee;
CREATE TABLE t_employee (
    emp_id INT PRIMARY KEY COMMENT '工号 (登录账号)',
    emp_name VARCHAR(50) NOT NULL COMMENT '员工姓名',
    pwd VARCHAR(64) NOT NULL COMMENT '登录密码 (加密存储)',
    role ENUM('Admin', 'Sales', 'Stock', 'Finance') NOT NULL DEFAULT 'Sales' COMMENT '角色',
    phone VARCHAR(20) UNIQUE COMMENT '联系电话',
    status TINYINT DEFAULT 1 COMMENT '状态 (1:在职, 0:离职)',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='员工表';

-- 3. 供应商表 (t_supplier)
DROP TABLE IF EXISTS t_supplier;
CREATE TABLE t_supplier (
    sup_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '供应商唯一标识',
    sup_name VARCHAR(100) NOT NULL UNIQUE COMMENT '供应商全称',
    contact_name VARCHAR(50) COMMENT '业务联系人姓名',
    phone VARCHAR(20) NOT NULL COMMENT '联系电话',
    address VARCHAR(200) COMMENT '供应商详细地址',
    license_no VARCHAR(50) COMMENT '医药经营许可证号',
    status TINYINT DEFAULT 1 COMMENT '状态 (1:合作中, 0:停止往来)',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='供应商表';

-- 4. 客户表 (t_customer)
DROP TABLE IF EXISTS t_customer;
CREATE TABLE t_customer (
    cus_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '客户唯一标识',
    cus_name VARCHAR(50) NOT NULL COMMENT '客户姓名',
    gender ENUM('男', '女', '未知') DEFAULT '未知' COMMENT '性别',
    phone VARCHAR(20) UNIQUE COMMENT '手机号',
    age INT CHECK (age > 0 AND age < 150) COMMENT '年龄',
    medical_history TEXT COMMENT '简要病史/过敏史',
    total_consume DECIMAL(12,2) DEFAULT 0.00 COMMENT '累计消费金额',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='客户表';

-- ============================================
-- 二、进货核心业务表
-- ============================================

-- 5. 进货单主表 (t_purchase_order)
DROP TABLE IF EXISTS t_purchase_order;
CREATE TABLE t_purchase_order (
    po_id VARCHAR(20) PRIMARY KEY COMMENT '进货单号 (P+年月日+4位流水号)',
    sup_id INT NOT NULL COMMENT '供应商ID',
    emp_id INT NOT NULL COMMENT '经手库管员工号',
    total_amount DECIMAL(12,2) DEFAULT 0.00 COMMENT '该单总采购金额',
    purchase_date DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '入库日期',
    status TINYINT DEFAULT 1 COMMENT '状态 (1:正常, 0:已撤销)',
    FOREIGN KEY (sup_id) REFERENCES t_supplier(sup_id),
    FOREIGN KEY (emp_id) REFERENCES t_employee(emp_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='进货单主表';

-- 6. 进货明细表 (t_purchase_detail)
DROP TABLE IF EXISTS t_purchase_detail;
CREATE TABLE t_purchase_detail (
    pd_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '明细唯一ID',
    po_id VARCHAR(20) NOT NULL COMMENT '所属进货单号',
    med_id INT NOT NULL COMMENT '药品ID',
    batch_no VARCHAR(30) NOT NULL COMMENT '生产批号',
    produce_date DATE COMMENT '生产日期',
    expiry_date DATE NOT NULL COMMENT '有效期至',
    quantity INT NOT NULL CHECK (quantity > 0) COMMENT '入库数量',
    unit_purc_price DECIMAL(10,2) NOT NULL COMMENT '本次进货单价',
    FOREIGN KEY (po_id) REFERENCES t_purchase_order(po_id),
    FOREIGN KEY (med_id) REFERENCES t_medicine(med_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='进货明细表';

-- ============================================
-- 三、库存核心业务表
-- ============================================

-- 7. 库存批次表 (t_stock_batch)
DROP TABLE IF EXISTS t_stock_batch;
CREATE TABLE t_stock_batch (
    batch_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '批次ID',
    med_id INT NOT NULL COMMENT '药品ID',
    batch_no VARCHAR(30) NOT NULL COMMENT '批号',
    expiry_date DATE NOT NULL COMMENT '有效期',
    cur_batch_qty INT DEFAULT 0 CHECK (cur_batch_qty >= 0) COMMENT '该批次剩余实物数量',
    unit_cost DECIMAL(10,2) COMMENT '该批次成本单价',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (med_id) REFERENCES t_medicine(med_id),
    UNIQUE KEY uk_med_batch (med_id, batch_no) COMMENT '药品+批号唯一'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='库存批次表';

-- 8. 盘点记录表 (t_inventory_check)
DROP TABLE IF EXISTS t_inventory_check;
CREATE TABLE t_inventory_check (
    check_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '盘点ID',
    batch_id INT NOT NULL COMMENT '批次ID',
    book_qty INT NOT NULL COMMENT '账面数量',
    actual_qty INT NOT NULL COMMENT '实物数量',
    diff_qty INT GENERATED ALWAYS AS (actual_qty - book_qty) STORED COMMENT '差异数量',
    diff_amount DECIMAL(12,2) COMMENT '盈亏金额',
    emp_id INT NOT NULL COMMENT '盘点员工号',
    check_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '盘点时间',
    remark VARCHAR(200) COMMENT '备注',
    FOREIGN KEY (batch_id) REFERENCES t_stock_batch(batch_id),
    FOREIGN KEY (emp_id) REFERENCES t_employee(emp_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='盘点记录表';

-- ============================================
-- 四、销售与财务类表
-- ============================================

-- 9. 销售单主表 (t_sales_order)
DROP TABLE IF EXISTS t_sales_order;
CREATE TABLE t_sales_order (
    so_id VARCHAR(20) PRIMARY KEY COMMENT '销售单号 (S+年月日+4位流水号)',
    emp_id INT NOT NULL COMMENT '销售员工号',
    cus_id INT COMMENT '客户ID (可空表示散客)',
    sale_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '交易时间',
    total_price DECIMAL(12,2) DEFAULT 0.00 COMMENT '销售总额',
    status TINYINT DEFAULT 1 COMMENT '状态 (1:正常, 0:已退货)',
    FOREIGN KEY (emp_id) REFERENCES t_employee(emp_id),
    FOREIGN KEY (cus_id) REFERENCES t_customer(cus_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='销售单主表';

-- 10. 销售明细表 (t_sales_detail)
DROP TABLE IF EXISTS t_sales_detail;
CREATE TABLE t_sales_detail (
    sd_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '明细唯一ID',
    so_id VARCHAR(20) NOT NULL COMMENT '所属销售单号',
    batch_id INT NOT NULL COMMENT '从哪个批次扣的货',
    quantity INT NOT NULL CHECK (quantity > 0) COMMENT '销售数量',
    unit_sell_price DECIMAL(10,2) NOT NULL COMMENT '交易时单价',
    FOREIGN KEY (so_id) REFERENCES t_sales_order(so_id),
    FOREIGN KEY (batch_id) REFERENCES t_stock_batch(batch_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='销售明细表';

-- ============================================
-- 五、退货业务表
-- ============================================

-- 11. 购进退出表 (t_purchase_return)
DROP TABLE IF EXISTS t_purchase_return;
CREATE TABLE t_purchase_return (
    pr_id VARCHAR(20) PRIMARY KEY COMMENT '购进退出单号 (PR+年月日+4位流水号)',
    po_id VARCHAR(20) NOT NULL COMMENT '关联的原采购订单号',
    sup_id INT NOT NULL COMMENT '退货的目标供应商',
    batch_id INT NOT NULL COMMENT '退回批次ID',
    quantity INT NOT NULL CHECK (quantity > 0) COMMENT '退回数量',
    return_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '退货时间',
    reason VARCHAR(200) COMMENT '退货原因',
    status TINYINT DEFAULT 1 COMMENT '状态 (1:已处理, 0:已撤销)',
    emp_id INT NOT NULL COMMENT '处理员工工号',
    FOREIGN KEY (po_id) REFERENCES t_purchase_order(po_id),
    FOREIGN KEY (sup_id) REFERENCES t_supplier(sup_id),
    FOREIGN KEY (batch_id) REFERENCES t_stock_batch(batch_id),
    FOREIGN KEY (emp_id) REFERENCES t_employee(emp_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='购进退出表';

-- 12. 销售退货表 (t_sales_return)
DROP TABLE IF EXISTS t_sales_return;
CREATE TABLE t_sales_return (
    sr_id VARCHAR(20) PRIMARY KEY COMMENT '销售退货单号 (SR+年月日+4位流水号)',
    so_id VARCHAR(20) NOT NULL COMMENT '关联的原销售订单号',
    batch_id INT NOT NULL COMMENT '退回批次ID',
    quantity INT NOT NULL CHECK (quantity > 0) COMMENT '退回数量',
    return_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '退货时间',
    reason VARCHAR(200) COMMENT '退货原因',
    status TINYINT DEFAULT 1 COMMENT '状态 (1:已处理, 0:已撤销)',
    emp_id INT NOT NULL COMMENT '处理员工工号',
    FOREIGN KEY (so_id) REFERENCES t_sales_order(so_id),
    FOREIGN KEY (batch_id) REFERENCES t_stock_batch(batch_id),
    FOREIGN KEY (emp_id) REFERENCES t_employee(emp_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='销售退货表';

-- ============================================
-- 六、财务统计表
-- ============================================

-- 13. 财务日结统计表 (t_finance_daily)
DROP TABLE IF EXISTS t_finance_daily;
CREATE TABLE t_finance_daily (
    day_id DATE PRIMARY KEY COMMENT '统计日期',
    sales_revenue DECIMAL(12,2) DEFAULT 0.00 COMMENT '当日销售收入',
    sales_profit DECIMAL(12,2) DEFAULT 0.00 COMMENT '当日销售毛利润',
    sales_return_amt DECIMAL(12,2) DEFAULT 0.00 COMMENT '当日销售退货金额',
    purc_return_amt DECIMAL(12,2) DEFAULT 0.00 COMMENT '当日购进退出金额',
    inv_loss_amt DECIMAL(12,2) DEFAULT 0.00 COMMENT '当日盘点亏损金额',
    inv_gain_amt DECIMAL(12,2) DEFAULT 0.00 COMMENT '当日盘点盈余金额',
    net_profit DECIMAL(12,2) GENERATED ALWAYS AS (
        sales_profit - sales_return_amt + purc_return_amt - inv_loss_amt + inv_gain_amt
    ) STORED COMMENT '当日净利润',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='财务日结统计表';

-- ============================================
-- 五、索引设计 (优化查询性能)
-- ============================================

-- 药品名称索引 (支持模糊查询)
CREATE INDEX idx_medicine_name ON t_medicine(med_name);

-- 药品类别索引
CREATE INDEX idx_medicine_category ON t_medicine(category);

-- 批号索引 (库存批次表)
CREATE INDEX idx_stock_batch_no ON t_stock_batch(batch_no);

-- 有效期索引 (用于过期预警查询)
CREATE INDEX idx_stock_expiry ON t_stock_batch(expiry_date);

-- 进货日期索引
CREATE INDEX idx_purchase_date ON t_purchase_order(purchase_date);

-- 销售日期索引
CREATE INDEX idx_sales_time ON t_sales_order(sale_time);

-- 供应商名称索引
CREATE INDEX idx_supplier_name ON t_supplier(sup_name);

-- ============================================
-- 六、视图设计
-- ============================================

-- 视图1: 过期药品视图 (距失效日期6个月以内)
DROP VIEW IF EXISTS v_expired_drugs;
CREATE VIEW v_expired_drugs AS
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

-- 视图2: 缺货预警视图 (库存低于预警线)
DROP VIEW IF EXISTS v_low_stock;
CREATE VIEW v_low_stock AS
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

-- 视图3: 库存明细视图 (综合查看)
DROP VIEW IF EXISTS v_stock_detail;
CREATE VIEW v_stock_detail AS
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
    sb.unit_cost,
    m.ref_sell_price,
    (sb.cur_batch_qty * sb.unit_cost) AS batch_value,
    CASE WHEN sb.expiry_date <= CURDATE() THEN 1 ELSE 0 END AS is_expired
FROM t_stock_batch sb
JOIN t_medicine m ON sb.med_id = m.med_id
WHERE sb.cur_batch_qty > 0
ORDER BY m.med_name, sb.expiry_date;

-- 视图4: 销售统计视图
DROP VIEW IF EXISTS v_sales_statistics;
CREATE VIEW v_sales_statistics AS
SELECT 
    DATE(so.sale_time) AS sale_date,
    COUNT(DISTINCT so.so_id) AS order_count,
    SUM(sd.quantity) AS total_qty,
    SUM(sd.quantity * sd.unit_sell_price) AS total_sales,
    SUM(sd.quantity * (sd.unit_sell_price - sb.unit_cost)) AS total_profit
FROM t_sales_order so
JOIN t_sales_detail sd ON so.so_id = sd.so_id
JOIN t_stock_batch sb ON sd.batch_id = sb.batch_id
WHERE so.status = 1
GROUP BY DATE(so.sale_time)
ORDER BY sale_date DESC;

-- 视图5: 畅销药品视图 (Top10)
DROP VIEW IF EXISTS v_top_selling;
CREATE VIEW v_top_selling AS
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
-- 七、触发器设计
-- ============================================

DELIMITER //

-- 触发器1: 进货入库后自动更新总库存和创建批次
DROP TRIGGER IF EXISTS trg_after_purchase_detail_insert//
CREATE TRIGGER trg_after_purchase_detail_insert
AFTER INSERT ON t_purchase_detail
FOR EACH ROW
BEGIN
    DECLARE v_batch_id INT;
    
    -- 检查批次是否已存在
    SELECT batch_id INTO v_batch_id 
    FROM t_stock_batch 
    WHERE med_id = NEW.med_id AND batch_no = NEW.batch_no
    LIMIT 1;
    
    IF v_batch_id IS NULL THEN
        -- 创建新批次
        INSERT INTO t_stock_batch (med_id, batch_no, expiry_date, cur_batch_qty, unit_cost)
        VALUES (NEW.med_id, NEW.batch_no, NEW.expiry_date, NEW.quantity, NEW.unit_purc_price);
    ELSE
        -- 更新已有批次数量
        UPDATE t_stock_batch 
        SET cur_batch_qty = cur_batch_qty + NEW.quantity
        WHERE batch_id = v_batch_id;
    END IF;
    
    -- 更新药品总库存
    UPDATE t_medicine 
    SET total_stock = total_stock + NEW.quantity
    WHERE med_id = NEW.med_id;
END//

-- 触发器2: 销售出库后自动扣减库存
DROP TRIGGER IF EXISTS trg_after_sales_detail_insert//
CREATE TRIGGER trg_after_sales_detail_insert
AFTER INSERT ON t_sales_detail
FOR EACH ROW
BEGIN
    DECLARE v_med_id INT;
    
    -- 获取药品ID
    SELECT med_id INTO v_med_id FROM t_stock_batch WHERE batch_id = NEW.batch_id;
    
    -- 扣减批次库存
    UPDATE t_stock_batch 
    SET cur_batch_qty = cur_batch_qty - NEW.quantity
    WHERE batch_id = NEW.batch_id;
    
    -- 更新药品总库存
    UPDATE t_medicine 
    SET total_stock = total_stock - NEW.quantity
    WHERE med_id = v_med_id;
END//

-- 触发器3: 销售退货时恢复库存
DROP TRIGGER IF EXISTS trg_after_sales_order_update//
CREATE TRIGGER trg_after_sales_order_update
AFTER UPDATE ON t_sales_order
FOR EACH ROW
BEGIN
    DECLARE v_med_id INT;
    DECLARE v_batch_id INT;
    DECLARE v_qty INT;
    DECLARE done INT DEFAULT FALSE;
    DECLARE cur_details CURSOR FOR 
        SELECT batch_id, quantity FROM t_sales_detail WHERE so_id = NEW.so_id;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;
    
    -- 如果状态从正常变为退货
    IF OLD.status = 1 AND NEW.status = 0 THEN
        OPEN cur_details;
        read_loop: LOOP
            FETCH cur_details INTO v_batch_id, v_qty;
            IF done THEN
                LEAVE read_loop;
            END IF;
            
            -- 获取药品ID
            SELECT med_id INTO v_med_id FROM t_stock_batch WHERE batch_id = v_batch_id;
            
            -- 恢复批次库存
            UPDATE t_stock_batch 
            SET cur_batch_qty = cur_batch_qty + v_qty
            WHERE batch_id = v_batch_id;
            
            -- 恢复药品总库存
            UPDATE t_medicine 
            SET total_stock = total_stock + v_qty
            WHERE med_id = v_med_id;
        END LOOP;
        CLOSE cur_details;
        
        -- 扣减客户累计消费
        IF NEW.cus_id IS NOT NULL THEN
            UPDATE t_customer 
            SET total_consume = total_consume - NEW.total_price
            WHERE cus_id = NEW.cus_id;
        END IF;
    END IF;
END//

-- 触发器4: 销售完成后更新客户累计消费
DROP TRIGGER IF EXISTS trg_after_sales_order_insert//
CREATE TRIGGER trg_after_sales_order_insert
AFTER INSERT ON t_sales_order
FOR EACH ROW
BEGIN
    IF NEW.cus_id IS NOT NULL AND NEW.total_price > 0 THEN
        UPDATE t_customer 
        SET total_consume = total_consume + NEW.total_price
        WHERE cus_id = NEW.cus_id;
    END IF;
END//

-- 触发器5: 盘点后自动调整库存
DROP TRIGGER IF EXISTS trg_after_inventory_check_insert//
CREATE TRIGGER trg_after_inventory_check_insert
AFTER INSERT ON t_inventory_check
FOR EACH ROW
BEGIN
    DECLARE v_med_id INT;
    DECLARE v_diff INT;
    
    SET v_diff = NEW.actual_qty - NEW.book_qty;
    
    IF v_diff != 0 THEN
        -- 获取药品ID
        SELECT med_id INTO v_med_id FROM t_stock_batch WHERE batch_id = NEW.batch_id;
        
        -- 更新批次库存为实际数量
        UPDATE t_stock_batch 
        SET cur_batch_qty = NEW.actual_qty
        WHERE batch_id = NEW.batch_id;
        
        -- 更新药品总库存
        UPDATE t_medicine 
        SET total_stock = total_stock + v_diff
        WHERE med_id = v_med_id;
    END IF;
END//

-- 触发器6: 购进退出后自动扣减库存
DROP TRIGGER IF EXISTS trg_after_purchase_return_insert//
CREATE TRIGGER trg_after_purchase_return_insert
AFTER INSERT ON t_purchase_return
FOR EACH ROW
BEGIN
    DECLARE v_med_id INT;
    
    -- 获取药品ID
    SELECT med_id INTO v_med_id FROM t_stock_batch WHERE batch_id = NEW.batch_id;
    
    -- 扣减批次库存
    UPDATE t_stock_batch 
    SET cur_batch_qty = cur_batch_qty - NEW.quantity
    WHERE batch_id = NEW.batch_id;
    
    -- 更新药品总库存
    UPDATE t_medicine 
    SET total_stock = total_stock - NEW.quantity
    WHERE med_id = v_med_id;
END//

-- 触发器7: 销售退货后自动恢复库存
DROP TRIGGER IF EXISTS trg_after_sales_return_insert//
CREATE TRIGGER trg_after_sales_return_insert
AFTER INSERT ON t_sales_return
FOR EACH ROW
BEGIN
    DECLARE v_med_id INT;
    
    -- 获取药品ID
    SELECT med_id INTO v_med_id FROM t_stock_batch WHERE batch_id = NEW.batch_id;
    
    -- 恢复批次库存
    UPDATE t_stock_batch 
    SET cur_batch_qty = cur_batch_qty + NEW.quantity
    WHERE batch_id = NEW.batch_id;
    
    -- 更新药品总库存
    UPDATE t_medicine 
    SET total_stock = total_stock + NEW.quantity
    WHERE med_id = v_med_id;
END//

DELIMITER ;

-- ============================================
-- 八、存储过程设计
-- ============================================

DELIMITER //

-- 存储过程1: 生成进货单号
DROP PROCEDURE IF EXISTS sp_generate_po_id//
CREATE PROCEDURE sp_generate_po_id(OUT p_po_id VARCHAR(20))
BEGIN
    DECLARE v_date_str VARCHAR(8);
    DECLARE v_seq INT;
    
    SET v_date_str = DATE_FORMAT(CURDATE(), '%Y%m%d');
    
    -- 获取当日最大流水号
    SELECT IFNULL(MAX(CAST(RIGHT(po_id, 4) AS UNSIGNED)), 0) + 1 INTO v_seq
    FROM t_purchase_order
    WHERE po_id LIKE CONCAT('P', v_date_str, '%');
    
    SET p_po_id = CONCAT('P', v_date_str, LPAD(v_seq, 4, '0'));
END//

-- 存储过程2: 生成销售单号
DROP PROCEDURE IF EXISTS sp_generate_so_id//
CREATE PROCEDURE sp_generate_so_id(OUT p_so_id VARCHAR(20))
BEGIN
    DECLARE v_date_str VARCHAR(8);
    DECLARE v_seq INT;
    
    SET v_date_str = DATE_FORMAT(CURDATE(), '%Y%m%d');
    
    SELECT IFNULL(MAX(CAST(RIGHT(so_id, 4) AS UNSIGNED)), 0) + 1 INTO v_seq
    FROM t_sales_order
    WHERE so_id LIKE CONCAT('S', v_date_str, '%');
    
    SET p_so_id = CONCAT('S', v_date_str, LPAD(v_seq, 4, '0'));
END//

-- 存储过程3: 月度财务结算统计
DROP PROCEDURE IF EXISTS sp_monthly_financial_report//
CREATE PROCEDURE sp_monthly_financial_report(
    IN p_year INT,
    IN p_month INT,
    OUT p_total_sales DECIMAL(14,2),
    OUT p_total_cost DECIMAL(14,2),
    OUT p_gross_profit DECIMAL(14,2),
    OUT p_order_count INT,
    OUT p_inventory_loss DECIMAL(12,2)
)
BEGIN
    DECLARE v_start_date DATE;
    DECLARE v_end_date DATE;
    
    SET v_start_date = CONCAT(p_year, '-', LPAD(p_month, 2, '0'), '-01');
    SET v_end_date = LAST_DAY(v_start_date);
    
    -- 计算销售总额和成本
    SELECT 
        IFNULL(SUM(sd.quantity * sd.unit_sell_price), 0),
        IFNULL(SUM(sd.quantity * sb.unit_cost), 0),
        COUNT(DISTINCT so.so_id)
    INTO p_total_sales, p_total_cost, p_order_count
    FROM t_sales_order so
    JOIN t_sales_detail sd ON so.so_id = sd.so_id
    JOIN t_stock_batch sb ON sd.batch_id = sb.batch_id
    WHERE so.status = 1
      AND so.sale_time BETWEEN v_start_date AND v_end_date;
    
    -- 计算毛利
    SET p_gross_profit = p_total_sales - p_total_cost;
    
    -- 计算盘点盈亏
    SELECT IFNULL(SUM(diff_amount), 0) INTO p_inventory_loss
    FROM t_inventory_check
    WHERE check_time BETWEEN v_start_date AND v_end_date;
END//

-- 存储过程4: 销售开单 (含库存校验和先进先出)
DROP PROCEDURE IF EXISTS sp_create_sales_order//
CREATE PROCEDURE sp_create_sales_order(
    IN p_emp_id INT,
    IN p_cus_id INT,
    IN p_med_id INT,
    IN p_quantity INT,
    OUT p_result INT,
    OUT p_message VARCHAR(200)
)
BEGIN
    DECLARE v_so_id VARCHAR(20);
    DECLARE v_batch_id INT;
    DECLARE v_available_qty INT;
    DECLARE v_sell_price DECIMAL(10,2);
    DECLARE v_remaining_qty INT;
    DECLARE v_deduct_qty INT;
    DECLARE v_total_price DECIMAL(12,2) DEFAULT 0;
    DECLARE done INT DEFAULT FALSE;
    
    -- 游标: 按先进先出原则获取有效批次
    DECLARE cur_batches CURSOR FOR 
        SELECT batch_id, cur_batch_qty 
        FROM t_stock_batch 
        WHERE med_id = p_med_id 
          AND cur_batch_qty > 0 
          AND expiry_date > CURDATE()
        ORDER BY expiry_date ASC;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;
    
    -- 开始事务
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SET p_result = -1;
        SET p_message = '系统错误，请联系管理员';
    END;
    
    START TRANSACTION;
    
    -- 获取售价
    SELECT ref_sell_price INTO v_sell_price FROM t_medicine WHERE med_id = p_med_id;
    
    -- 检查总库存
    SELECT IFNULL(SUM(cur_batch_qty), 0) INTO v_available_qty 
    FROM t_stock_batch 
    WHERE med_id = p_med_id 
      AND cur_batch_qty > 0 
      AND expiry_date > CURDATE();
    
    IF v_available_qty < p_quantity THEN
        SET p_result = -2;
        SET p_message = CONCAT('库存不足，可用库存: ', v_available_qty);
        ROLLBACK;
    ELSE
        -- 生成销售单号
        CALL sp_generate_so_id(v_so_id);
        
        -- 创建销售单主表
        INSERT INTO t_sales_order (so_id, emp_id, cus_id, total_price)
        VALUES (v_so_id, p_emp_id, p_cus_id, 0);
        
        SET v_remaining_qty = p_quantity;
        
        -- 按FIFO扣减库存
        OPEN cur_batches;
        deduct_loop: LOOP
            IF v_remaining_qty <= 0 THEN
                LEAVE deduct_loop;
            END IF;
            
            FETCH cur_batches INTO v_batch_id, v_available_qty;
            IF done THEN
                LEAVE deduct_loop;
            END IF;
            
            -- 计算本批次扣减数量
            IF v_available_qty >= v_remaining_qty THEN
                SET v_deduct_qty = v_remaining_qty;
            ELSE
                SET v_deduct_qty = v_available_qty;
            END IF;
            
            -- 创建销售明细
            INSERT INTO t_sales_detail (so_id, batch_id, quantity, unit_sell_price)
            VALUES (v_so_id, v_batch_id, v_deduct_qty, v_sell_price);
            
            SET v_total_price = v_total_price + (v_deduct_qty * v_sell_price);
            SET v_remaining_qty = v_remaining_qty - v_deduct_qty;
        END LOOP;
        CLOSE cur_batches;
        
        -- 更新销售单总价
        UPDATE t_sales_order SET total_price = v_total_price WHERE so_id = v_so_id;
        
        -- 更新客户累计消费
        IF p_cus_id IS NOT NULL THEN
            UPDATE t_customer 
            SET total_consume = total_consume + v_total_price
            WHERE cus_id = p_cus_id;
        END IF;
        
        COMMIT;
        SET p_result = 1;
        SET p_message = CONCAT('销售成功，单号: ', v_so_id, '，总价: ', v_total_price);
    END IF;
END//

-- 存储过程5: 获取过期预警统计
DROP PROCEDURE IF EXISTS sp_get_expiry_alert//
CREATE PROCEDURE sp_get_expiry_alert()
BEGIN
    SELECT 
        '已过期' AS status,
        COUNT(*) AS batch_count,
        IFNULL(SUM(cur_batch_qty), 0) AS total_qty,
        IFNULL(SUM(cur_batch_qty * unit_cost), 0) AS total_value
    FROM t_stock_batch
    WHERE cur_batch_qty > 0 AND expiry_date <= CURDATE()
    
    UNION ALL
    
    SELECT 
        '1月内过期',
        COUNT(*),
        IFNULL(SUM(cur_batch_qty), 0),
        IFNULL(SUM(cur_batch_qty * unit_cost), 0)
    FROM t_stock_batch
    WHERE cur_batch_qty > 0 
      AND expiry_date > CURDATE() 
      AND expiry_date <= DATE_ADD(CURDATE(), INTERVAL 1 MONTH)
    
    UNION ALL
    
    SELECT 
        '3月内过期',
        COUNT(*),
        IFNULL(SUM(cur_batch_qty), 0),
        IFNULL(SUM(cur_batch_qty * unit_cost), 0)
    FROM t_stock_batch
    WHERE cur_batch_qty > 0 
      AND expiry_date > DATE_ADD(CURDATE(), INTERVAL 1 MONTH)
      AND expiry_date <= DATE_ADD(CURDATE(), INTERVAL 3 MONTH)
    
    UNION ALL
    
    SELECT 
        '6月内过期',
        COUNT(*),
        IFNULL(SUM(cur_batch_qty), 0),
        IFNULL(SUM(cur_batch_qty * unit_cost), 0)
    FROM t_stock_batch
    WHERE cur_batch_qty > 0 
      AND expiry_date > DATE_ADD(CURDATE(), INTERVAL 3 MONTH)
      AND expiry_date <= DATE_ADD(CURDATE(), INTERVAL 6 MONTH);
END//

-- 存储过程6: 生成购进退出单号
DROP PROCEDURE IF EXISTS sp_generate_pr_id//
CREATE PROCEDURE sp_generate_pr_id(OUT p_pr_id VARCHAR(20))
BEGIN
    DECLARE v_date_str VARCHAR(8);
    DECLARE v_seq INT;
    
    SET v_date_str = DATE_FORMAT(CURDATE(), '%Y%m%d');
    
    SELECT IFNULL(MAX(CAST(RIGHT(pr_id, 4) AS UNSIGNED)), 0) + 1 INTO v_seq
    FROM t_purchase_return
    WHERE pr_id LIKE CONCAT('PR', v_date_str, '%');
    
    SET p_pr_id = CONCAT('PR', v_date_str, LPAD(v_seq, 4, '0'));
END//

-- 存储过程7: 生成销售退货单号
DROP PROCEDURE IF EXISTS sp_generate_sr_id//
CREATE PROCEDURE sp_generate_sr_id(OUT p_sr_id VARCHAR(20))
BEGIN
    DECLARE v_date_str VARCHAR(8);
    DECLARE v_seq INT;
    
    SET v_date_str = DATE_FORMAT(CURDATE(), '%Y%m%d');
    
    SELECT IFNULL(MAX(CAST(RIGHT(sr_id, 4) AS UNSIGNED)), 0) + 1 INTO v_seq
    FROM t_sales_return
    WHERE sr_id LIKE CONCAT('SR', v_date_str, '%');
    
    SET p_sr_id = CONCAT('SR', v_date_str, LPAD(v_seq, 4, '0'));
END//

-- 存储过程8: 财务日结统计
DROP PROCEDURE IF EXISTS sp_daily_finance_settlement//
CREATE PROCEDURE sp_daily_finance_settlement(IN p_date DATE)
BEGIN
    DECLARE v_sales_revenue DECIMAL(12,2) DEFAULT 0.00;
    DECLARE v_sales_cost DECIMAL(12,2) DEFAULT 0.00;
    DECLARE v_sales_profit DECIMAL(12,2) DEFAULT 0.00;
    DECLARE v_sales_return_amt DECIMAL(12,2) DEFAULT 0.00;
    DECLARE v_purc_return_amt DECIMAL(12,2) DEFAULT 0.00;
    DECLARE v_inv_loss_amt DECIMAL(12,2) DEFAULT 0.00;
    DECLARE v_inv_gain_amt DECIMAL(12,2) DEFAULT 0.00;
    
    -- 计算当日销售收入和成本
    SELECT 
        IFNULL(SUM(sd.quantity * sd.unit_sell_price), 0),
        IFNULL(SUM(sd.quantity * sb.unit_cost), 0)
    INTO v_sales_revenue, v_sales_cost
    FROM t_sales_order so
    JOIN t_sales_detail sd ON so.so_id = sd.so_id
    JOIN t_stock_batch sb ON sd.batch_id = sb.batch_id
    WHERE so.status = 1
      AND DATE(so.sale_time) = p_date;
    
    SET v_sales_profit = v_sales_revenue - v_sales_cost;
    
    -- 计算当日销售退货金额
    SELECT IFNULL(SUM(sr.quantity * sb.unit_cost), 0)
    INTO v_sales_return_amt
    FROM t_sales_return sr
    JOIN t_stock_batch sb ON sr.batch_id = sb.batch_id
    WHERE sr.status = 1
      AND DATE(sr.return_time) = p_date;
    
    -- 计算当日购进退出金额
    SELECT IFNULL(SUM(pr.quantity * sb.unit_cost), 0)
    INTO v_purc_return_amt
    FROM t_purchase_return pr
    JOIN t_stock_batch sb ON pr.batch_id = sb.batch_id
    WHERE pr.status = 1
      AND DATE(pr.return_time) = p_date;
    
    -- 计算当日盘点盈亏
    SELECT 
        IFNULL(SUM(CASE WHEN diff_amount < 0 THEN ABS(diff_amount) ELSE 0 END), 0),
        IFNULL(SUM(CASE WHEN diff_amount > 0 THEN diff_amount ELSE 0 END), 0)
    INTO v_inv_loss_amt, v_inv_gain_amt
    FROM t_inventory_check
    WHERE DATE(check_time) = p_date;
    
    -- 插入或更新财务日结表
    INSERT INTO t_finance_daily (
        day_id, sales_revenue, sales_profit, sales_return_amt, 
        purc_return_amt, inv_loss_amt, inv_gain_amt
    ) VALUES (
        p_date, v_sales_revenue, v_sales_profit, v_sales_return_amt,
        v_purc_return_amt, v_inv_loss_amt, v_inv_gain_amt
    )
    ON DUPLICATE KEY UPDATE
        sales_revenue = v_sales_revenue,
        sales_profit = v_sales_profit,
        sales_return_amt = v_sales_return_amt,
        purc_return_amt = v_purc_return_amt,
        inv_loss_amt = v_inv_loss_amt,
        inv_gain_amt = v_inv_gain_amt,
        updated_at = CURRENT_TIMESTAMP;
END//

DELIMITER ;

-- ============================================
-- 九、初始测试数据
-- ============================================

-- 插入默认管理员
INSERT INTO t_employee (emp_id, emp_name, pwd, role, phone) VALUES
(1001, '系统管理员', 'e10adc3949ba59abbe56e057f20f883e', 'Admin', '13800000001'),
(1002, '张库管', 'e10adc3949ba59abbe56e057f20f883e', 'Stock', '13800000002'),
(1003, '李销售', 'e10adc3949ba59abbe56e057f20f883e', 'Sales', '13800000003'),
(1004, '王财务', 'e10adc3949ba59abbe56e057f20f883e', 'Finance', '13800000004');
-- 密码均为 123456 的 MD5 值

-- 插入供应商数据
INSERT INTO t_supplier (sup_name, contact_name, phone, address, license_no) VALUES
('国药控股北京有限公司', '陈经理', '010-88886666', '北京市朝阳区建国路88号', 'YY-BJ-2023001'),
('华润医药商业集团', '刘经理', '021-66668888', '上海市浦东新区陆家嘴环路88号', 'YY-SH-2023002'),
('九州通医药集团', '王经理', '027-88889999', '武汉市东湖新技术开发区', 'YY-WH-2023003');

-- 插入药品数据
INSERT INTO t_medicine (med_name, spec, category, unit, factory, ref_buy_price, ref_sell_price, alert_qty) VALUES
('阿莫西林胶囊', '0.25g*24粒', '处方药', '盒', '哈药集团制药总厂', 8.50, 15.00, 50),
('布洛芬缓释胶囊', '0.3g*20粒', 'OTC', '盒', '中美史克制药', 12.00, 22.00, 30),
('感冒灵颗粒', '10g*9袋', 'OTC', '盒', '三九医药股份有限公司', 6.00, 12.80, 100),
('复方丹参滴丸', '27mg*180粒', 'OTC', '瓶', '天津天士力制药', 18.00, 32.00, 40),
('奥美拉唑肠溶胶囊', '20mg*14粒', '处方药', '盒', '阿斯利康制药', 25.00, 45.00, 30),
('头孢克肟分散片', '0.1g*6片', '处方药', '盒', '广州白云山制药', 15.00, 28.00, 40),
('维生素C片', '0.1g*100片', 'OTC', '瓶', '东北制药集团', 3.50, 8.00, 80),
('板蓝根颗粒', '10g*20袋', 'OTC', '盒', '广州白云山中一药业', 8.00, 16.00, 100);

-- 插入客户数据
INSERT INTO t_customer (cus_name, gender, phone, age, medical_history) VALUES
('王女士', '女', '13912345678', 35, '无'),
('李先生', '男', '13823456789', 58, '高血压、糖尿病'),
('张阿姨', '女', '13734567890', 62, '青霉素过敏');

-- 说明：初始数据已插入，可根据业务需要调整
SELECT '数据库初始化完成！' AS message;

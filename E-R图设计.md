## 1. E-R

![](assets/ER图.png)

## 2. 数据库表设计

### 一、 基础信息类表

#### 表1：药品信息表 (t_medicine)

**描述**：存储药品的基本静态属性，是整个系统的核心数据源。

| **字段名**         | **数据类型**  | **约束**           | **描述**                        |
| ------------------ | ------------- | ------------------ | ------------------------------- |
| **med_id**         | INT           | PK, Auto_Increment | 药品唯一标识                    |
| **med_name**       | VARCHAR(100)  | NOT NULL           | 药品通用名                      |
| **spec**           | VARCHAR(50)   | NOT NULL           | 规格 (如 0.25g*12片)            |
| **category**       | VARCHAR(20)   | -                  | 类别 (处方药/OTC)               |
| **unit**           | VARCHAR(10)   | -                  | 单位 (盒/瓶/支)                 |
| **factory**        | VARCHAR(100)  | -                  | 生产厂家                        |
| **ref_buy_price**  | DECIMAL(10,2) | CHECK > 0          | 参考进价                        |
| **ref_sell_price** | DECIMAL(10,2) | CHECK > 0          | 参考零售价                      |
| **total_stock**    | INT           | DEFAULT 0          | 全库总库存 (冗余字段，方便查询) |
| **alert_qty**      | INT           | DEFAULT 10         | 库存预警线                      |

#### 表2：员工表 (t_employee)

**描述**：管理系统用户身份、登录凭证及操作权限。

| **字段名**   | **数据类型** | **约束**                | **描述**                  |
| ------------ | ------------ | ----------------------- | ------------------------- |
| **emp_id**   | INT          | PK                      | 工号 (登录账号)           |
| **emp_name** | VARCHAR(50)  | NOT NULL                | 员工姓名                  |
| **pwd**      | VARCHAR(64)  | NOT NULL                | 登录密码 (建议加密存储)   |
| **role**     | ENUM         | 'Admin','Sales','Stock' | 角色 (管理员/销售员/库管) |
| **phone**    | VARCHAR(20)  | UNIQUE                  | 联系电话                  |



#### 表3：供应商表 (t_supplier)

**描述**：存储药品的来源渠道信息，用于进货管理及资质追溯。

| **字段名**       | **数据类型** | **约束**           | **描述**                       |
| ---------------- | ------------ | ------------------ | ------------------------------ |
| **sup_id**       | INT          | PK, Auto_Increment | 供应商唯一标识                 |
| **sup_name**     | VARCHAR(100) | NOT NULL, UNIQUE   | 供应商全称                     |
| **contact_name** | VARCHAR(50)  | -                  | 业务联系人姓名                 |
| **phone**        | VARCHAR(20)  | NOT NULL           | 联系电话（用于采购沟通）       |
| **address**      | VARCHAR(200) | -                  | 供应商详细地址                 |
| **license_no**   | VARCHAR(50)  | -                  | 医药经营许可证号（合规性检查） |
| **status**       | TINYINT      | DEFAULT 1          | 状态（1:合作中，0:停止往来）   |

#### 表 4：客户表 (t_customer)

**描述**：存储终端购药客户或长期合作单位的信息，用于销售统计及客户关系维护。

| **字段名**          | **数据类型**  | **约束**           | **描述**                        |
| ------------------- | ------------- | ------------------ | ------------------------------- |
| **cus_id**          | INT           | PK, Auto_Increment | 客户唯一标识                    |
| **cus_name**        | VARCHAR(50)   | NOT NULL           | 客户姓名 / 单位名称             |
| **gender**          | ENUM          | '男','女','未知'   | 性别                            |
| **phone**           | VARCHAR(20)   | UNIQUE             | 手机号                          |
| **age**             | INT           | CHECK (age > 0)    | 年龄                            |
| **medical_history** | TEXT          | -                  | 简要病史/过敏史（保证用药安全） |
| **total_consume**   | DECIMAL(12,2) | DEFAULT 0.00       | 累计消费金额（用于财务分析）    |

### 二、 进货核心业务表

#### 表5：进货单主表 (t_purchase_order)

**描述**：记录采购行为的整体信息（谁、什么时候、找谁买、总共多少钱）。

| **字段名**        | **数据类型**  | **约束**                  | **描述**                                          |
| ----------------- | ------------- | ------------------------- | ------------------------------------------------- |
| **po_id**         | VARCHAR(20)   | PK                        | 进货单号 (业务唯一主键，格式：P+年月日+4位流水号) |
| **sup_id**        | INT           | FK -> t_supplier          | 供应商ID (标识这批货是从哪家公司采购的)           |
| **emp_id**        | INT           | FK -> t_employee          | 经手库管员工号 (记录是谁负责本次入库登记的)       |
| **total_amount**  | DECIMAL(12,2) | -                         | 该单总采购金额                                    |
| **purchase_date** | DATETIME      | DEFAULT CURRENT_TIMESTAMP | 入库日期                                          |



#### 表6：进货明细表 (t_purchase_detail)

**描述**：记录每一单中具体药品的批次、价格及有效期信息。

| **字段名**          | **数据类型**  | **约束**               | **描述**     |
| ------------------- | ------------- | ---------------------- | ------------ |
| **pd_id**           | INT           | PK, Auto_Increment     | 明细唯一ID   |
| **po_id**           | VARCHAR(20)   | FK -> t_purchase_order | 所属进货单号 |
| **med_id**          | INT           | FK -> t_medicine       | 药品ID       |
| **batch_no**        | VARCHAR(30)   | NOT NULL               | 生产批号     |
| **produce_date**    | DATE          | -                      | 生产日期     |
| **expiry_date**     | DATE          | NOT NULL               | 有效期至     |
| **quantity**        | INT           | CHECK > 0              | 入库数量     |
| **unit_purc_price** | DECIMAL(10,2) | NOT NULL               | 本次进货单价 |



### 三、库存核心业务表

#### 表7：库存批次表 (t_stock_batch)

**描述**：**系统枢纽**，记录每一具体批次药品的实时剩余实物数量。

| **字段名**         | **数据类型** | **约束**           | **描述**           |
| ------------------ | ------------ | ------------------ | ------------------ |
| **batch_id**       | INT          | PK, Auto_Increment | 批次ID             |
| **med_id**         | INT          | FK -> t_medicine   | 药品ID             |
| **batch_no**       | VARCHAR(30)  | NOT NULL           | 批号               |
| **expiry_date**    | DATE         | -                  | 有效期             |
| **cur_batch__qty** | INT          | CHECK >= 0         | 该批次剩余实物数量 |

------

### 四、 销售与财务类表

#### 表8：销售单主表 (t_sales_order)

**描述**：记录每一笔面向客户的交易概况。

| **字段名**      | **数据类型**  | **约束**         | **描述**                    |
| --------------- | ------------- | ---------------- | --------------------------- |
| **so_id**       | VARCHAR(20)   | PK               | 销售单号 (如 S202512200001) |
| **emp_id**      | INT           | FK -> t_employee | 销售员工号                  |
| **cus_id**      | INT           | FK ->t_customer  | 客户ID                      |
| **sale_time**   | DATETIME      | DEFAULT NOW()    | 交易时间                    |
| **total_price** | DECIMAL(12,2) | -                | 销售总额                    |

#### 表9：销售明细表 (t_sales_detail)

**描述**：记录交易的具体药品及扣减的批次信息，用于售后追溯。

| **字段名**          | **数据类型**  | **约束**            | **描述**         |
| ------------------- | ------------- | ------------------- | ---------------- |
| **sd_id**           | INT           | PK, Auto_Increment  | 明细唯一ID       |
| **so_id**           | VARCHAR(20)   | FK -> t_sales_order | 所属销售单号     |
| **batch_id**        | INT           | FK -> t_stock_batch | 从哪个批次扣的货 |
| **quantity**        | INT           | CHECK > 0           | 销售数量         |
| **unit_sell_price** | DECIMAL(10,2) | -                   | 交易时单价       |


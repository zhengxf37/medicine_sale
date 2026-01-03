"""
数据库模型定义
对应 E-R 图设计中的所有表
"""
from datetime import datetime
from flask_login import UserMixin
from app import db


class Employee(UserMixin, db.Model):
    """员工表"""
    __tablename__ = 't_employee'
    
    emp_id = db.Column(db.Integer, primary_key=True, comment='工号')
    emp_name = db.Column(db.String(50), nullable=False, comment='员工姓名')
    pwd = db.Column(db.String(64), nullable=False, comment='登录密码')
    role = db.Column(db.Enum('Admin', 'Sales', 'Stock', 'Finance'), 
                     default='Sales', comment='角色')
    phone = db.Column(db.String(20), unique=True, comment='联系电话')
    status = db.Column(db.SmallInteger, default=1, comment='状态')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    
    # 关系
    purchase_orders = db.relationship('PurchaseOrder', backref='employee', lazy='dynamic')
    sales_orders = db.relationship('SalesOrder', backref='employee', lazy='dynamic')
    
    def __repr__(self):
        return f'<Employee {self.emp_name}>'
    
    # Flask-Login 所需方法
    def get_id(self):
        return str(self.emp_id)
    
    @property
    def is_authenticated(self):
        return True
    
    @property
    def is_active(self):
        return self.status == 1
    
    @property
    def is_anonymous(self):
        return False
    
    @property
    def role_name(self):
        role_map = {
            'Admin': '管理员',
            'Sales': '销售员',
            'Stock': '库管员',
            'Finance': '财务'
        }
        return role_map.get(self.role, '未知')


class Supplier(db.Model):
    """供应商表"""
    __tablename__ = 't_supplier'
    
    sup_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sup_name = db.Column(db.String(100), nullable=False, unique=True, comment='供应商全称')
    contact_name = db.Column(db.String(50), comment='联系人姓名')
    phone = db.Column(db.String(20), nullable=False, comment='联系电话')
    address = db.Column(db.String(200), comment='详细地址')
    license_no = db.Column(db.String(50), comment='经营许可证号')
    status = db.Column(db.SmallInteger, default=1, comment='状态')
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # 关系
    purchase_orders = db.relationship('PurchaseOrder', backref='supplier', lazy='dynamic')
    
    def __repr__(self):
        return f'<Supplier {self.sup_name}>'


class Customer(db.Model):
    """客户表"""
    __tablename__ = 't_customer'
    
    cus_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cus_name = db.Column(db.String(50), nullable=False, comment='客户姓名')
    gender = db.Column(db.Enum('男', '女', '未知'), default='未知')
    phone = db.Column(db.String(20), unique=True, comment='手机号')
    age = db.Column(db.Integer, comment='年龄')
    medical_history = db.Column(db.Text, comment='病史/过敏史')
    total_consume = db.Column(db.Numeric(12, 2), default=0.00, comment='累计消费')
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # 关系
    sales_orders = db.relationship('SalesOrder', backref='customer', lazy='dynamic')
    
    def __repr__(self):
        return f'<Customer {self.cus_name}>'


class Medicine(db.Model):
    """药品信息表"""
    __tablename__ = 't_medicine'
    
    med_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    med_name = db.Column(db.String(100), nullable=False, comment='药品名称')
    spec = db.Column(db.String(50), nullable=False, comment='规格')
    category = db.Column(db.String(20), default='OTC', comment='类别')
    unit = db.Column(db.String(10), default='盒', comment='单位')
    factory = db.Column(db.String(100), comment='生产厂家')
    ref_buy_price = db.Column(db.Numeric(10, 2), comment='参考进价')
    ref_sell_price = db.Column(db.Numeric(10, 2), comment='参考售价')
    total_stock = db.Column(db.Integer, default=0, comment='总库存')
    alert_qty = db.Column(db.Integer, default=10, comment='预警线')
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关系
    stock_batches = db.relationship('StockBatch', backref='medicine', lazy='dynamic')
    purchase_details = db.relationship('PurchaseDetail', backref='medicine', lazy='dynamic')
    
    def __repr__(self):
        return f'<Medicine {self.med_name}>'
    
    @property
    def is_low_stock(self):
        """是否低库存"""
        return self.total_stock < self.alert_qty


class StockBatch(db.Model):
    """库存批次表"""
    __tablename__ = 't_stock_batch'
    
    batch_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    med_id = db.Column(db.Integer, db.ForeignKey('t_medicine.med_id'), nullable=False)
    batch_no = db.Column(db.String(30), nullable=False, comment='批号')
    expiry_date = db.Column(db.Date, nullable=False, comment='有效期')
    cur_batch_qty = db.Column(db.Integer, default=0, comment='当前批次数量')
    create_time = db.Column(db.Date, comment='创建时间')
    
    # 关系
    sales_details = db.relationship('SalesDetail', backref='stock_batch', lazy='dynamic')
    
    # 唯一约束
    __table_args__ = (
        db.UniqueConstraint('med_id', 'batch_no', name='uk_med_batch'),
    )
    
    def __repr__(self):
        return f'<StockBatch {self.batch_no}>'
    
    @property
    def is_expired(self):
        """是否已过期"""
        from datetime import date
        return self.expiry_date <= date.today()
    
    @property
    def days_to_expire(self):
        """距过期天数"""
        from datetime import date
        return (self.expiry_date - date.today()).days


class PurchaseOrder(db.Model):
    """进货单主表"""
    __tablename__ = 't_purchase_order'
    
    po_id = db.Column(db.String(20), primary_key=True, comment='进货单号')
    sup_id = db.Column(db.Integer, db.ForeignKey('t_supplier.sup_id'), nullable=False)
    emp_id = db.Column(db.Integer, db.ForeignKey('t_employee.emp_id'), nullable=False)
    total_amount = db.Column(db.Numeric(12, 2), default=0.00, comment='总金额')
    purchase_date = db.Column(db.DateTime, default=datetime.now, comment='入库日期')
    status = db.Column(db.SmallInteger, default=1, comment='状态')
    
    # 关系
    details = db.relationship('PurchaseDetail', backref='order', lazy='dynamic',
                              cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<PurchaseOrder {self.po_id}>'


class PurchaseDetail(db.Model):
    """进货明细表"""
    __tablename__ = 't_purchase_detail'
    
    pd_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    po_id = db.Column(db.String(20), db.ForeignKey('t_purchase_order.po_id'), nullable=False)
    med_id = db.Column(db.Integer, db.ForeignKey('t_medicine.med_id'), nullable=False)
    batch_no = db.Column(db.String(30), nullable=False, comment='批号')
    produce_date = db.Column(db.Date, comment='生产日期')
    expiry_date = db.Column(db.Date, nullable=False, comment='有效期')
    quantity = db.Column(db.Integer, nullable=False, comment='数量')
    unit_purc_price = db.Column(db.Numeric(10, 2), nullable=False, comment='进货单价')
    
    def __repr__(self):
        return f'<PurchaseDetail {self.pd_id}>'
    
    @property
    def subtotal(self):
        """小计金额"""
        return float(self.quantity) * float(self.unit_purc_price)


class SalesOrder(db.Model):
    """销售单主表"""
    __tablename__ = 't_sales_order'
    
    so_id = db.Column(db.String(20), primary_key=True, comment='销售单号')
    emp_id = db.Column(db.Integer, db.ForeignKey('t_employee.emp_id'), nullable=False)
    cus_id = db.Column(db.Integer, db.ForeignKey('t_customer.cus_id'), nullable=True)
    sale_time = db.Column(db.DateTime, default=datetime.now, comment='交易时间')
    total_price = db.Column(db.Numeric(12, 2), default=0.00, comment='总价')
    status = db.Column(db.SmallInteger, default=1, comment='状态')
    
    # 关系
    details = db.relationship('SalesDetail', backref='order', lazy='dynamic',
                              cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<SalesOrder {self.so_id}>'
    
    @property
    def status_text(self):
        return '正常' if self.status == 1 else '已退货'


class SalesDetail(db.Model):
    """销售明细表"""
    __tablename__ = 't_sales_detail'
    
    sd_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    so_id = db.Column(db.String(20), db.ForeignKey('t_sales_order.so_id'), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey('t_stock_batch.batch_id'), nullable=False)
    med_id = db.Column(db.Integer, db.ForeignKey('t_medicine.med_id'), nullable=False, comment='药品ID')
    quantity = db.Column(db.Integer, nullable=False, comment='数量')
    unit_sell_price = db.Column(db.Numeric(10, 2), nullable=False, comment='售价')
    
    def __repr__(self):
        return f'<SalesDetail {self.sd_id}>'
    
    @property
    def subtotal(self):
        """小计金额"""
        return float(self.quantity) * float(self.unit_sell_price)


class InventoryCheck(db.Model):
    """盘点记录表"""
    __tablename__ = 't_inventory_check'
    
    check_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    batch_id = db.Column(db.Integer, db.ForeignKey('t_stock_batch.batch_id'), nullable=False)
    book_qty = db.Column(db.Integer, nullable=False, comment='账面数量')
    actual_qty = db.Column(db.Integer, nullable=False, comment='实物数量')
    diff_amount = db.Column(db.Numeric(12, 2), comment='盈亏金额')
    emp_id = db.Column(db.Integer, db.ForeignKey('t_employee.emp_id'), nullable=False)
    check_time = db.Column(db.DateTime, default=datetime.now, comment='盘点时间')
    remark = db.Column(db.String(200), comment='备注')
    
    # 关系
    stock_batch = db.relationship('StockBatch', backref='checks')
    employee = db.relationship('Employee', backref='inventory_checks')
    
    def __repr__(self):
        return f'<InventoryCheck {self.check_id}>'
    
    @property
    def diff_qty(self):
        """差异数量"""
        return self.actual_qty - self.book_qty


class PurchaseReturn(db.Model):
    """购进退出表"""
    __tablename__ = 't_purchase_return'
    
    pr_id = db.Column(db.String(20), primary_key=True, comment='退货单号')
    po_id = db.Column(db.String(20), db.ForeignKey('t_purchase_order.po_id'), nullable=False)
    sup_id = db.Column(db.Integer, db.ForeignKey('t_supplier.sup_id'), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey('t_stock_batch.batch_id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, comment='退回数量')
    return_time = db.Column(db.DateTime, default=datetime.now, comment='退货时间')
    reason = db.Column(db.String(200), comment='退货原因')
    status = db.Column(db.SmallInteger, default=1, comment='状态')
    emp_id = db.Column(db.Integer, db.ForeignKey('t_employee.emp_id'), nullable=False)
    
    # 关系
    purchase_order = db.relationship('PurchaseOrder', backref='returns')
    supplier = db.relationship('Supplier', backref='purchase_returns')
    stock_batch = db.relationship('StockBatch', backref='purchase_returns')
    employee = db.relationship('Employee', backref='purchase_returns')
    
    def __repr__(self):
        return f'<PurchaseReturn {self.pr_id}>'
    
    @property
    def status_text(self):
        return '已处理' if self.status == 1 else '已撤销'


class SalesReturn(db.Model):
    """销售退货表"""
    __tablename__ = 't_sales_return'
    
    sr_id = db.Column(db.String(20), primary_key=True, comment='退货单号')
    so_id = db.Column(db.String(20), db.ForeignKey('t_sales_order.so_id'), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey('t_stock_batch.batch_id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, comment='退回数量')
    return_time = db.Column(db.DateTime, default=datetime.now, comment='退货时间')
    reason = db.Column(db.String(200), comment='退货原因')
    status = db.Column(db.SmallInteger, default=1, comment='状态')
    emp_id = db.Column(db.Integer, db.ForeignKey('t_employee.emp_id'), nullable=False)
    
    # 关系
    sales_order = db.relationship('SalesOrder', backref='returns')
    stock_batch = db.relationship('StockBatch', backref='sales_returns')
    employee = db.relationship('Employee', backref='sales_returns')
    
    def __repr__(self):
        return f'<SalesReturn {self.sr_id}>'
    
    @property
    def status_text(self):
        return '已处理' if self.status == 1 else '已撤销'


class FinanceDaily(db.Model):
    """财务日结统计表"""
    __tablename__ = 't_finance_daily'
    
    day_id = db.Column(db.Date, primary_key=True, comment='统计日期')
    sales_revenue = db.Column(db.Numeric(12, 2), default=0.00, comment='销售收入')
    sales_profit = db.Column(db.Numeric(12, 2), default=0.00, comment='销售毛利润')
    sales_return_amt = db.Column(db.Numeric(12, 2), default=0.00, comment='销售退货金额')
    purc_return_amt = db.Column(db.Numeric(12, 2), default=0.00, comment='购进退出金额')
    inv_loss_amt = db.Column(db.Numeric(12, 2), default=0.00, comment='盘点亏损金额')
    inv_gain_amt = db.Column(db.Numeric(12, 2), default=0.00, comment='盘点盈余金额')
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f'<FinanceDaily {self.day_id}>'
    
    @property
    def net_profit(self):
        """净利润"""
        return (float(self.sales_profit or 0) - float(self.sales_return_amt or 0) + 
                float(self.purc_return_amt or 0) - float(self.inv_loss_amt or 0) + 
                float(self.inv_gain_amt or 0))

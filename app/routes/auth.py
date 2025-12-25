"""
认证路由 - 登录/登出/主页
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app import db
from app.models import Employee
import hashlib

auth_bp = Blueprint('auth', __name__)


def md5(password):
    """MD5加密"""
    return hashlib.md5(password.encode()).hexdigest()


def login_required(f):
    """登录验证装饰器"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('请先登录', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles):
    """角色验证装饰器"""
    def decorator(f):
        from functools import wraps
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_role' not in session:
                flash('请先登录', 'warning')
                return redirect(url_for('auth.login'))
            if session['user_role'] not in roles:
                flash('您没有权限访问此页面', 'danger')
                return redirect(url_for('auth.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


@auth_bp.route('/')
def index():
    """首页/仪表盘"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    # 获取统计数据
    from app.models import Medicine, StockBatch, SalesOrder, PurchaseOrder
    from datetime import date, datetime
    from sqlalchemy import func
    
    today = date.today()
    
    # 药品总数
    medicine_count = Medicine.query.count()
    
    # 低库存药品数
    low_stock_count = Medicine.query.filter(Medicine.total_stock < Medicine.alert_qty).count()
    
    # 临期药品数 (6个月内)
    from datetime import timedelta
    expiry_threshold = today + timedelta(days=180)
    expiring_count = db.session.query(func.count(func.distinct(StockBatch.med_id))).filter(
        StockBatch.cur_batch_qty > 0,
        StockBatch.expiry_date <= expiry_threshold
    ).scalar()
    
    # 今日销售额
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    today_sales = db.session.query(func.sum(SalesOrder.total_price)).filter(
        SalesOrder.sale_time.between(today_start, today_end),
        SalesOrder.status == 1
    ).scalar() or 0
    
    # 今日进货额
    today_purchase = db.session.query(func.sum(PurchaseOrder.total_amount)).filter(
        PurchaseOrder.purchase_date.between(today_start, today_end),
        PurchaseOrder.status == 1
    ).scalar() or 0
    
    return render_template('index.html', 
                          medicine_count=medicine_count,
                          low_stock_count=low_stock_count,
                          expiring_count=expiring_count,
                          today_sales=float(today_sales),
                          today_purchase=float(today_purchase))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
    if request.method == 'POST':
        emp_id = request.form.get('emp_id')
        password = request.form.get('password')
        
        if not emp_id or not password:
            flash('请输入工号和密码', 'warning')
            return render_template('login.html')
        
        employee = Employee.query.get(int(emp_id))
        
        if employee and employee.pwd == md5(password):
            if employee.status != 1:
                flash('账号已被禁用，请联系管理员', 'danger')
                return render_template('login.html')
            
            session['user_id'] = employee.emp_id
            session['user_name'] = employee.emp_name
            session['user_role'] = employee.role
            flash(f'欢迎回来，{employee.emp_name}！', 'success')
            return redirect(url_for('auth.index'))
        else:
            flash('工号或密码错误', 'danger')
    
    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    """登出"""
    session.clear()
    flash('已安全退出', 'success')
    return redirect(url_for('auth.login'))


@auth_bp.route('/employees')
@login_required
@role_required('Admin')
def employee_list():
    """员工管理列表"""
    employees = Employee.query.order_by(Employee.emp_id).all()
    return render_template('employee_list.html', employees=employees)


@auth_bp.route('/employee/add', methods=['GET', 'POST'])
@login_required
@role_required('Admin')
def employee_add():
    """添加员工"""
    if request.method == 'POST':
        emp_id = int(request.form.get('emp_id'))
        emp_name = request.form.get('emp_name')
        password = request.form.get('password')
        role = request.form.get('role')
        phone = request.form.get('phone')
        
        if Employee.query.get(emp_id):
            flash('工号已存在', 'danger')
            return render_template('employee_form.html', action='add')
        
        employee = Employee(
            emp_id=emp_id,
            emp_name=emp_name,
            pwd=md5(password),
            role=role,
            phone=phone if phone else None
        )
        db.session.add(employee)
        db.session.commit()
        flash('员工添加成功', 'success')
        return redirect(url_for('auth.employee_list'))
    
    return render_template('employee_form.html', action='add')


@auth_bp.route('/employee/edit/<int:emp_id>', methods=['GET', 'POST'])
@login_required
@role_required('Admin')
def employee_edit(emp_id):
    """编辑员工"""
    employee = Employee.query.get_or_404(emp_id)
    
    if request.method == 'POST':
        employee.emp_name = request.form.get('emp_name')
        employee.role = request.form.get('role')
        employee.phone = request.form.get('phone') or None
        employee.status = int(request.form.get('status', 1))
        
        new_password = request.form.get('password')
        if new_password:
            employee.pwd = md5(new_password)
        
        db.session.commit()
        flash('员工信息更新成功', 'success')
        return redirect(url_for('auth.employee_list'))
    
    return render_template('employee_form.html', action='edit', employee=employee)

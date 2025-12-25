"""
客户管理路由
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app import db
from app.models import Customer
from app.routes.auth import login_required

customer_bp = Blueprint('customer', __name__)


@customer_bp.route('/')
@login_required
def list():
    """客户列表"""
    page = request.args.get('page', 1, type=int)
    keyword = request.args.get('keyword', '')
    
    query = Customer.query
    if keyword:
        query = query.filter(
            (Customer.cus_name.like(f'%{keyword}%')) |
            (Customer.phone.like(f'%{keyword}%'))
        )
    
    pagination = query.order_by(Customer.cus_id.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    
    return render_template('customer/list.html', 
                          pagination=pagination, 
                          keyword=keyword)


@customer_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """添加客户"""
    if request.method == 'POST':
        customer = Customer(
            cus_name=request.form.get('cus_name'),
            gender=request.form.get('gender'),
            phone=request.form.get('phone') or None,
            age=int(request.form.get('age')) if request.form.get('age') else None,
            medical_history=request.form.get('medical_history')
        )
        db.session.add(customer)
        db.session.commit()
        flash('客户添加成功', 'success')
        return redirect(url_for('customer.list'))
    
    return render_template('customer/form.html', action='add')


@customer_bp.route('/edit/<int:cus_id>', methods=['GET', 'POST'])
@login_required
def edit(cus_id):
    """编辑客户"""
    customer = Customer.query.get_or_404(cus_id)
    
    if request.method == 'POST':
        customer.cus_name = request.form.get('cus_name')
        customer.gender = request.form.get('gender')
        customer.phone = request.form.get('phone') or None
        customer.age = int(request.form.get('age')) if request.form.get('age') else None
        customer.medical_history = request.form.get('medical_history')
        
        db.session.commit()
        flash('客户信息更新成功', 'success')
        return redirect(url_for('customer.list'))
    
    return render_template('customer/form.html', action='edit', customer=customer)


@customer_bp.route('/detail/<int:cus_id>')
@login_required
def detail(cus_id):
    """客户详情 - 包含购买历史"""
    customer = Customer.query.get_or_404(cus_id)
    orders = customer.sales_orders.order_by(db.desc('sale_time')).limit(20).all()
    
    return render_template('customer/detail.html', 
                          customer=customer, 
                          orders=orders)


@customer_bp.route('/api/search')
@login_required
def api_search():
    """客户搜索API"""
    keyword = request.args.get('q', '')
    customers = Customer.query.filter(
        (Customer.cus_name.like(f'%{keyword}%')) |
        (Customer.phone.like(f'%{keyword}%'))
    ).limit(20).all()
    
    return jsonify([{
        'id': c.cus_id,
        'name': c.cus_name,
        'phone': c.phone,
        'medical_history': c.medical_history
    } for c in customers])

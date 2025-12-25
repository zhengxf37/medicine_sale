"""
供应商管理路由
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app import db
from app.models import Supplier
from app.routes.auth import login_required

supplier_bp = Blueprint('supplier', __name__)


@supplier_bp.route('/')
@login_required
def list():
    """供应商列表"""
    page = request.args.get('page', 1, type=int)
    keyword = request.args.get('keyword', '')
    
    query = Supplier.query
    if keyword:
        query = query.filter(Supplier.sup_name.like(f'%{keyword}%'))
    
    pagination = query.order_by(Supplier.sup_id.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    
    return render_template('supplier/list.html', 
                          pagination=pagination, 
                          keyword=keyword)


@supplier_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """添加供应商"""
    if request.method == 'POST':
        supplier = Supplier(
            sup_name=request.form.get('sup_name'),
            contact_name=request.form.get('contact_name'),
            phone=request.form.get('phone'),
            address=request.form.get('address'),
            license_no=request.form.get('license_no')
        )
        db.session.add(supplier)
        db.session.commit()
        flash('供应商添加成功', 'success')
        return redirect(url_for('supplier.list'))
    
    return render_template('supplier/form.html', action='add')


@supplier_bp.route('/edit/<int:sup_id>', methods=['GET', 'POST'])
@login_required
def edit(sup_id):
    """编辑供应商"""
    supplier = Supplier.query.get_or_404(sup_id)
    
    if request.method == 'POST':
        supplier.sup_name = request.form.get('sup_name')
        supplier.contact_name = request.form.get('contact_name')
        supplier.phone = request.form.get('phone')
        supplier.address = request.form.get('address')
        supplier.license_no = request.form.get('license_no')
        supplier.status = int(request.form.get('status', 1))
        
        db.session.commit()
        flash('供应商信息更新成功', 'success')
        return redirect(url_for('supplier.list'))
    
    return render_template('supplier/form.html', action='edit', supplier=supplier)


@supplier_bp.route('/api/list')
@login_required
def api_list():
    """供应商列表API"""
    suppliers = Supplier.query.filter_by(status=1).all()
    return jsonify([{
        'id': s.sup_id,
        'name': s.sup_name
    } for s in suppliers])

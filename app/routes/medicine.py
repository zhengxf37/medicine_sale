"""
药品管理路由
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app import db
from app.models import Medicine, StockBatch
from app.routes.auth import login_required

medicine_bp = Blueprint('medicine', __name__)


@medicine_bp.route('/')
@login_required
def list():
    """药品列表"""
    page = request.args.get('page', 1, type=int)
    keyword = request.args.get('keyword', '')
    category = request.args.get('category', '')
    
    query = Medicine.query
    
    if keyword:
        query = query.filter(Medicine.med_name.like(f'%{keyword}%'))
    if category:
        query = query.filter(Medicine.category == category)
    
    pagination = query.order_by(Medicine.med_id.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    
    return render_template('medicine/list.html', 
                          pagination=pagination,
                          keyword=keyword,
                          category=category)


@medicine_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """添加药品"""
    if request.method == 'POST':
        medicine = Medicine(
            med_name=request.form.get('med_name'),
            spec=request.form.get('spec'),
            category=request.form.get('category'),
            unit=request.form.get('unit'),
            factory=request.form.get('factory'),
            ref_buy_price=float(request.form.get('ref_buy_price') or 0),
            ref_sell_price=float(request.form.get('ref_sell_price') or 0),
            alert_qty=int(request.form.get('alert_qty') or 10)
        )
        db.session.add(medicine)
        db.session.commit()
        flash('药品添加成功', 'success')
        return redirect(url_for('medicine.list'))
    
    return render_template('medicine/form.html', action='add')


@medicine_bp.route('/edit/<int:med_id>', methods=['GET', 'POST'])
@login_required
def edit(med_id):
    """编辑药品"""
    medicine = Medicine.query.get_or_404(med_id)
    
    if request.method == 'POST':
        medicine.med_name = request.form.get('med_name')
        medicine.spec = request.form.get('spec')
        medicine.category = request.form.get('category')
        medicine.unit = request.form.get('unit')
        medicine.factory = request.form.get('factory')
        medicine.ref_buy_price = float(request.form.get('ref_buy_price') or 0)
        medicine.ref_sell_price = float(request.form.get('ref_sell_price') or 0)
        medicine.alert_qty = int(request.form.get('alert_qty') or 10)
        
        db.session.commit()
        flash('药品信息更新成功', 'success')
        return redirect(url_for('medicine.list'))
    
    return render_template('medicine/form.html', action='edit', medicine=medicine)


@medicine_bp.route('/detail/<int:med_id>')
@login_required
def detail(med_id):
    """药品详情 - 包含批次库存"""
    medicine = Medicine.query.get_or_404(med_id)
    batches = StockBatch.query.filter_by(med_id=med_id).filter(
        StockBatch.cur_batch_qty > 0
    ).order_by(StockBatch.expiry_date).all()
    
    return render_template('medicine/detail.html', 
                          medicine=medicine, 
                          batches=batches)


@medicine_bp.route('/delete/<int:med_id>', methods=['POST'])
@login_required
def delete(med_id):
    """删除药品"""
    medicine = Medicine.query.get_or_404(med_id)
    
    # 检查是否有库存
    if medicine.total_stock > 0:
        flash('该药品还有库存，无法删除', 'danger')
        return redirect(url_for('medicine.list'))
    
    db.session.delete(medicine)
    db.session.commit()
    flash('药品删除成功', 'success')
    return redirect(url_for('medicine.list'))


@medicine_bp.route('/api/search')
@login_required
def api_search():
    """药品搜索API (用于下拉选择)"""
    keyword = request.args.get('q', '')
    medicines = Medicine.query.filter(
        Medicine.med_name.like(f'%{keyword}%')
    ).limit(20).all()
    
    return jsonify([{
        'id': m.med_id,
        'name': m.med_name,
        'spec': m.spec,
        'unit': m.unit,
        'stock': m.total_stock,
        'buy_price': float(m.ref_buy_price or 0),
        'sell_price': float(m.ref_sell_price or 0)
    } for m in medicines])

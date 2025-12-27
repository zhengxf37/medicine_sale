"""
进货管理路由
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from app import db
from app.models import PurchaseOrder, PurchaseDetail, Medicine, Supplier
from app.routes.auth import login_required, role_required
from datetime import datetime
from sqlalchemy import text

purchase_bp = Blueprint('purchase', __name__)


def generate_po_id():
    """生成进货单号"""
    date_str = datetime.now().strftime('%Y%m%d')
    prefix = f'P{date_str}'
    
    # 查询当日最大单号
    result = db.session.query(db.func.max(PurchaseOrder.po_id)).filter(
        PurchaseOrder.po_id.like(f'{prefix}%')
    ).scalar()
    
    if result:
        seq = int(result[-4:]) + 1
    else:
        seq = 1
    
    return f'{prefix}{seq:04d}'


@purchase_bp.route('/')
@login_required
def list():
    """进货单列表"""
    page = request.args.get('page', 1, type=int)
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    sup_id = request.args.get('sup_id', '', type=int)
    
    query = PurchaseOrder.query
    
    if start_date:
        query = query.filter(PurchaseOrder.purchase_date >= start_date)
    if end_date:
        query = query.filter(PurchaseOrder.purchase_date <= end_date + ' 23:59:59')
    if sup_id:
        query = query.filter(PurchaseOrder.sup_id == sup_id)
    
    pagination = query.order_by(PurchaseOrder.purchase_date.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    
    suppliers = Supplier.query.filter_by(status=1).all()
    
    return render_template('purchase/list.html', 
                          pagination=pagination,
                          suppliers=suppliers,
                          start_date=start_date,
                          end_date=end_date,
                          sup_id=sup_id)


@purchase_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'Stock')
def create():
    """创建进货单"""
    if request.method == 'POST':
        data = request.get_json()
        
        if not data or not data.get('items'):
            return jsonify({'success': False, 'message': '请添加进货明细'})
        
        try:
            # 生成单号
            po_id = generate_po_id()
            
            # 计算总金额
            total_amount = sum(
                item['quantity'] * item['unit_price'] 
                for item in data['items']
            )
            
            # 创建进货单
            order = PurchaseOrder(
                po_id=po_id,
                sup_id=int(data['sup_id']),
                emp_id=session['user_id'],
                total_amount=total_amount
            )
            db.session.add(order)
            
            # 创建明细 (触发器会自动更新库存)
            for item in data['items']:
                detail = PurchaseDetail(
                    po_id=po_id,
                    med_id=int(item['med_id']),
                    batch_no=item['batch_no'],
                    produce_date=datetime.strptime(item['produce_date'], '%Y-%m-%d').date() if item.get('produce_date') else None,
                    expiry_date=datetime.strptime(item['expiry_date'], '%Y-%m-%d').date(),
                    quantity=int(item['quantity']),
                    unit_purc_price=float(item['unit_price'])
                )
                db.session.add(detail)
            
            db.session.commit()
            return jsonify({'success': True, 'message': f'进货单 {po_id} 创建成功', 'po_id': po_id})
        
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'创建失败: {str(e)}'})
    
    suppliers = Supplier.query.filter_by(status=1).all()
    # medicines = Medicine.query.all()
    # return render_template('purchase/create.html', 
    #                       suppliers=suppliers, 
    #                       medicines=medicines)
    medicines = Medicine.query.all()
    medicines_data = [{
        'med_id': m.med_id,
        'med_name': m.med_name,
        'spec': m.spec,
        'ref_buy_price': float(m.ref_buy_price or 0)
    } for m in medicines]
    return render_template('purchase/create.html', 
                        suppliers=suppliers, 
                        medicines=medicines_data)


@purchase_bp.route('/detail/<po_id>')
@login_required
def detail(po_id):
    """进货单详情"""
    order = PurchaseOrder.query.get_or_404(po_id)
    details = PurchaseDetail.query.filter_by(po_id=po_id).all()
    
    return render_template('purchase/detail.html', 
                          order=order, 
                          details=details)


@purchase_bp.route('/cancel/<po_id>', methods=['POST'])
@login_required
@role_required('Admin', 'Stock')
def cancel(po_id):
    """撤销进货单"""
    order = PurchaseOrder.query.get_or_404(po_id)
    
    if order.status != 1:
        flash('该进货单已被撤销', 'warning')
        return redirect(url_for('purchase.detail', po_id=po_id))
    
    # 检查是否有药品已被销售
    for detail in order.details:
        from app.models import StockBatch
        batch = StockBatch.query.filter_by(
            med_id=detail.med_id, 
            batch_no=detail.batch_no
        ).first()
        
        if batch and batch.cur_batch_qty < detail.quantity:
            flash(f'药品 {detail.medicine.med_name} 批号 {detail.batch_no} 已有部分被销售，无法撤销', 'danger')
            return redirect(url_for('purchase.detail', po_id=po_id))
    
    # 撤销：扣减库存
    for detail in order.details:
        from app.models import StockBatch
        batch = StockBatch.query.filter_by(
            med_id=detail.med_id, 
            batch_no=detail.batch_no
        ).first()
        
        if batch:
            batch.cur_batch_qty -= detail.quantity
            medicine = Medicine.query.get(detail.med_id)
            medicine.total_stock -= detail.quantity
    
    order.status = 0
    db.session.commit()
    flash('进货单已撤销', 'success')
    return redirect(url_for('purchase.list'))

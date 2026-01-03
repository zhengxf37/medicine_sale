"""
退货管理路由
包括购进退出和销售退货
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date
from sqlalchemy import func, and_, or_, text
from app import db
from app.models import (PurchaseReturn, SalesReturn, PurchaseOrder, SalesOrder, 
                        StockBatch, Medicine, Supplier, Employee, Customer, SalesDetail, PurchaseDetail)

bp = Blueprint('return_manage', __name__, url_prefix='/return')

def generate_return_id(model, prefix_char):
    """在Python中生成退货单号，避免数据库校对规则冲突"""
    date_str = datetime.now().strftime('%Y%m%d')
    prefix = f'{prefix_char}{date_str}'
    # 根据模型获取对应的ID字段名
    id_attr = model.pr_id if prefix_char == 'PR' else model.sr_id
    
    result = db.session.query(func.max(id_attr)).filter(
        id_attr.like(f'{prefix}%')
    ).scalar()
    
    if result:
        seq = int(result[-4:]) + 1
    else:
        seq = 1
    return f'{prefix}{seq:04d}'

@bp.route('/purchase')
@login_required
def purchase_return_list():
    """购进退出列表"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    query = PurchaseReturn.query.order_by(PurchaseReturn.return_time.desc())
    
    # 搜索条件
    keyword = request.args.get('keyword', '').strip()
    if keyword:
        query = query.join(PurchaseReturn.purchase_order).filter(
            or_(
                PurchaseReturn.pr_id.like(f'%{keyword}%'),
                PurchaseReturn.po_id.like(f'%{keyword}%'),
                PurchaseReturn.reason.like(f'%{keyword}%')
            )
        )
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    returns = pagination.items
    
    return render_template('return_manage/purchase_list.html',
                         returns=returns,
                         pagination=pagination,
                         keyword=keyword)


@bp.route('/purchase/create', methods=['GET', 'POST'])
@login_required
def create_purchase_return():
    """创建购进退出单"""
    if request.method == 'POST':
        try:
            po_id = request.form.get('po_id')
            batch_id = request.form.get('batch_id')
            quantity = int(request.form.get('quantity', 0))
            reason = request.form.get('reason', '').strip()
            
            # 验证采购订单
            purchase_order = PurchaseOrder.query.get(po_id)
            if not purchase_order:
                flash('采购订单不存在', 'danger')
                return redirect(url_for('return_manage.create_purchase_return'))
            
            # 验证批次
            batch = StockBatch.query.get(batch_id)
            if not batch:
                flash('批次不存在', 'danger')
                return redirect(url_for('return_manage.create_purchase_return'))
            
            # 检查库存是否足够
            if batch.cur_batch_qty < quantity:
                flash(f'库存不足，当前库存：{batch.cur_batch_qty}', 'danger')
                return redirect(url_for('return_manage.create_purchase_return'))
            
            # 生成退货单号
            pr_id = generate_return_id(PurchaseReturn, 'PR')
            
            # 创建退货记录
            purchase_return = PurchaseReturn(
                pr_id=pr_id,
                po_id=po_id,
                sup_id=purchase_order.sup_id,
                batch_id=batch_id,
                quantity=quantity,
                reason=reason,
                emp_id=current_user.emp_id,
                return_time=datetime.now()
            )
            
            db.session.add(purchase_return)
            db.session.commit()
            
            flash(f'购进退出单 {pr_id} 创建成功', 'success')
            return redirect(url_for('return_manage.purchase_return_list'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'创建失败：{str(e)}', 'danger')
            return redirect(url_for('return_manage.create_purchase_return'))
    
    # GET请求
    purchase_orders = PurchaseOrder.query.filter_by(status=1).order_by(
        PurchaseOrder.purchase_date.desc()).limit(100).all()
    
    return render_template('return_manage/purchase_form.html',
                         purchase_orders=purchase_orders)


@bp.route('/sales')
@login_required
def sales_return_list():
    """销售退货列表"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    query = SalesReturn.query.order_by(SalesReturn.return_time.desc())
    
    # 搜索条件
    keyword = request.args.get('keyword', '').strip()
    if keyword:
        query = query.join(SalesReturn.sales_order).filter(
            or_(
                SalesReturn.sr_id.like(f'%{keyword}%'),
                SalesReturn.so_id.like(f'%{keyword}%'),
                SalesReturn.reason.like(f'%{keyword}%')
            )
        )
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    returns = pagination.items
    
    return render_template('return_manage/sales_list.html',
                         returns=returns,
                         pagination=pagination,
                         keyword=keyword)


@bp.route('/sales/create', methods=['GET', 'POST'])
@login_required
def create_sales_return():
    """创建销售退货单"""
    if request.method == 'POST':
        try:
            so_id = request.form.get('so_id')
            batch_id = request.form.get('batch_id')
            quantity = int(request.form.get('quantity', 0))
            reason = request.form.get('reason', '').strip()
            
            # 验证销售订单
            sales_order = SalesOrder.query.get(so_id)
            if not sales_order:
                flash('销售订单不存在', 'danger')
                return redirect(url_for('return_manage.create_sales_return'))
            
            # 验证批次
            batch = StockBatch.query.get(batch_id)
            if not batch:
                flash('批次不存在', 'danger')
                return redirect(url_for('return_manage.create_sales_return'))
            
            # 生成退货单号
            sr_id = generate_return_id(SalesReturn, 'SR')
            
            # 创建退货记录
            sales_return = SalesReturn(
                sr_id=sr_id,
                so_id=so_id,
                batch_id=batch_id,
                quantity=quantity,
                reason=reason,
                emp_id=current_user.emp_id,
                return_time=datetime.now()
            )
            
            db.session.add(sales_return)
            db.session.commit()
            
            flash(f'销售退货单 {sr_id} 创建成功', 'success')
            return redirect(url_for('return_manage.sales_return_list'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'创建失败：{str(e)}', 'danger')
            return redirect(url_for('return_manage.create_sales_return'))
    
    # GET请求
    sales_orders = SalesOrder.query.filter_by(status=1).order_by(
        SalesOrder.sale_time.desc()).limit(100).all()
    
    # 修正：移除 status=1 的过滤条件
    customers = Customer.query.all()
    
    return render_template('return_manage/sales_form.html',
                         sales_orders=sales_orders,
                         customers=customers)

@bp.route('/api/order_batches/<order_id>')
@login_required
def get_order_batches(order_id):
    """获取订单关联的批次（用于退货）"""
    try:
        # 判断是采购订单还是销售订单
        if order_id.startswith('P'):
            # 采购订单：修复关联逻辑，确保获取所有药品的批次
            details = db.session.query(
                StockBatch.batch_id,
                Medicine.med_name,
                StockBatch.batch_no,
                StockBatch.cur_batch_qty
            ).join(Medicine, StockBatch.med_id == Medicine.med_id)\
             .join(PurchaseDetail, and_(
                 PurchaseDetail.po_id == order_id,
                 PurchaseDetail.med_id == StockBatch.med_id
             )).all()
        else:
            # 销售订单：修复关联逻辑
            # 确保 SalesDetail 和 StockBatch 正确关联
            details = db.session.query(
                StockBatch.batch_id,
                Medicine.med_name,
                StockBatch.batch_no,
                StockBatch.cur_batch_qty
            ).join(Medicine, StockBatch.med_id == Medicine.med_id)\
             .join(SalesDetail, SalesDetail.batch_id == StockBatch.batch_id)\
             .filter(SalesDetail.so_id == order_id).all()
        
        batches = [{
            'batch_id': b.batch_id,
            'med_name': b.med_name,
            'batch_no': b.batch_no,
            'cur_qty': b.cur_batch_qty
        } for b in details]
        
        return jsonify(batches)
    except Exception as e:
        print(f"Error getting batches for order {order_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

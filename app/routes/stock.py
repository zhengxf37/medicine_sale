"""
库存管理路由
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from app import db
from app.models import Medicine, StockBatch, InventoryCheck
from app.routes.auth import login_required, role_required
from datetime import date, timedelta
from sqlalchemy import func

stock_bp = Blueprint('stock', __name__)


@stock_bp.route('/')
@login_required
def overview():
    """库存概览"""
    # 总库存价值（使用药品参考进价计算）
    total_value = db.session.query(
        func.sum(StockBatch.cur_batch_qty * Medicine.ref_buy_price)
    ).join(Medicine).filter(StockBatch.cur_batch_qty > 0).scalar() or 0
    
    # 药品总数
    medicine_count = Medicine.query.count()
    
    # 批次总数
    batch_count = StockBatch.query.filter(StockBatch.cur_batch_qty > 0).count()
    
    # 低库存药品
    low_stock = Medicine.query.filter(
        Medicine.total_stock < Medicine.alert_qty
    ).order_by(Medicine.total_stock).limit(10).all()
    
    # 临期药品统计
    today = date.today()
    expiry_stats = {
        'expired': StockBatch.query.filter(
            StockBatch.cur_batch_qty > 0,
            StockBatch.expiry_date <= today
        ).count(),
        'month1': StockBatch.query.filter(
            StockBatch.cur_batch_qty > 0,
            StockBatch.expiry_date > today,
            StockBatch.expiry_date <= today + timedelta(days=30)
        ).count(),
        'month3': StockBatch.query.filter(
            StockBatch.cur_batch_qty > 0,
            StockBatch.expiry_date > today + timedelta(days=30),
            StockBatch.expiry_date <= today + timedelta(days=90)
        ).count(),
        'month6': StockBatch.query.filter(
            StockBatch.cur_batch_qty > 0,
            StockBatch.expiry_date > today + timedelta(days=90),
            StockBatch.expiry_date <= today + timedelta(days=180)
        ).count()
    }
    
    return render_template('stock/overview.html',
                          total_value=float(total_value),
                          medicine_count=medicine_count,
                          batch_count=batch_count,
                          low_stock=low_stock,
                          expiry_stats=expiry_stats)


@stock_bp.route('/batch')
@login_required
def batch_list():
    """批次库存列表"""
    page = request.args.get('page', 1, type=int)
    keyword = request.args.get('keyword', '')
    show_empty = request.args.get('show_empty', '0') == '1'
    
    query = db.session.query(StockBatch, Medicine).join(
        Medicine, StockBatch.med_id == Medicine.med_id
    )
    
    if keyword:
        query = query.filter(
            (Medicine.med_name.like(f'%{keyword}%')) |
            (StockBatch.batch_no.like(f'%{keyword}%'))
        )
    
    if not show_empty:
        query = query.filter(StockBatch.cur_batch_qty > 0)
    
    query = query.order_by(StockBatch.expiry_date)
    
    pagination = query.paginate(page=page, per_page=15, error_out=False)
    
    return render_template('stock/batch_list.html',
                          pagination=pagination,
                          keyword=keyword,
                          show_empty=show_empty)


@stock_bp.route('/expiring')
@login_required
def expiring():
    """临期药品预警"""
    filter_type = request.args.get('type', 'all')
    today = date.today()
    
    query = db.session.query(StockBatch, Medicine).join(
        Medicine, StockBatch.med_id == Medicine.med_id
    ).filter(StockBatch.cur_batch_qty > 0)
    
    if filter_type == 'expired':
        query = query.filter(StockBatch.expiry_date <= today)
    elif filter_type == 'month1':
        query = query.filter(
            StockBatch.expiry_date > today,
            StockBatch.expiry_date <= today + timedelta(days=30)
        )
    elif filter_type == 'month3':
        query = query.filter(
            StockBatch.expiry_date > today + timedelta(days=30),
            StockBatch.expiry_date <= today + timedelta(days=90)
        )
    elif filter_type == 'month6':
        query = query.filter(
            StockBatch.expiry_date > today + timedelta(days=90),
            StockBatch.expiry_date <= today + timedelta(days=180)
        )
    else:
        query = query.filter(StockBatch.expiry_date <= today + timedelta(days=180))
    
    batches = query.order_by(StockBatch.expiry_date).all()
    
    return render_template('stock/expiring.html',
                          batches=batches,
                          filter_type=filter_type,
                          today=today)


@stock_bp.route('/low')
@login_required
def low_stock():
    """低库存预警"""
    medicines = Medicine.query.filter(
        Medicine.total_stock < Medicine.alert_qty
    ).order_by(Medicine.total_stock).all()
    
    return render_template('stock/low_stock.html', medicines=medicines)


@stock_bp.route('/check', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'Stock')
def inventory_check():
    """库存盘点"""
    if request.method == 'POST':
        data = request.get_json()
        
        try:
            batch = StockBatch.query.get(data['batch_id'])
            book_qty = batch.cur_batch_qty
            actual_qty = int(data['actual_qty'])
            diff_qty = actual_qty - book_qty
            
            # 计算盈亏金额
            diff_amount = diff_qty * float(batch.medicine.ref_buy_price or 0)
            
            # 创建盘点记录 (触发器会自动调整库存)
            check = InventoryCheck(
                batch_id=batch.batch_id,
                book_qty=book_qty,
                actual_qty=actual_qty,
                diff_amount=diff_amount,
                emp_id=session['user_id'],
                remark=data.get('remark', '')
            )
            db.session.add(check)
            
            # 手动调整库存 (因为触发器是在数据库层面)
            medicine = Medicine.query.get(batch.med_id)
            medicine.total_stock += diff_qty
            batch.cur_batch_qty = actual_qty
            
            db.session.commit()
            return jsonify({'success': True, 'message': '盘点完成'})
        
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)})
    
    # GET: 显示可盘点的批次
    batches = db.session.query(StockBatch, Medicine).join(
        Medicine, StockBatch.med_id == Medicine.med_id
    ).filter(StockBatch.cur_batch_qty > 0).order_by(Medicine.med_name).all()
    
    return render_template('stock/check.html', batches=batches)


@stock_bp.route('/check/history')
@login_required
def check_history():
    """盘点历史"""
    page = request.args.get('page', 1, type=int)
    
    query = db.session.query(
        InventoryCheck, StockBatch, Medicine
    ).join(
        StockBatch, InventoryCheck.batch_id == StockBatch.batch_id
    ).join(
        Medicine, StockBatch.med_id == Medicine.med_id
    ).order_by(InventoryCheck.check_time.desc())
    
    pagination = query.paginate(page=page, per_page=15, error_out=False)
    
    return render_template('stock/check_history.html', pagination=pagination)

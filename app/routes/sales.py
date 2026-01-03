"""
销售管理路由
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import current_user
from app import db
from app.models import SalesOrder, SalesDetail, Customer, Medicine, StockBatch, Employee
from app.routes.auth import login_required, role_required
from datetime import datetime, date

sales_bp = Blueprint('sales', __name__)


def generate_so_id():
    """生成销售单号"""
    date_str = datetime.now().strftime('%Y%m%d')
    prefix = f'S{date_str}'
    
    # 使用 cast 确保校对规则一致，防止 Illegal mix of collations 错误
    result = db.session.query(db.func.max(SalesOrder.so_id)).filter(
        SalesOrder.so_id.cast(db.String).like(f'{prefix}%')
    ).scalar()
    
    if result:
        seq = int(result[-4:]) + 1
    else:
        seq = 1
    
    return f'{prefix}{seq:04d}'


@sales_bp.route('/')
@login_required
def list():
    """销售单列表"""
    page = request.args.get('page', 1, type=int)
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    keyword = request.args.get('keyword', '')
    
    query = SalesOrder.query
    
    if start_date:
        query = query.filter(SalesOrder.sale_time >= start_date)
    if end_date:
        query = query.filter(SalesOrder.sale_time <= end_date + ' 23:59:59')
    if keyword:
        query = query.filter(SalesOrder.so_id.like(f'%{keyword}%'))
    
    pagination = query.order_by(SalesOrder.sale_time.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    
    return render_template('sales/list.html', 
                          pagination=pagination,
                          start_date=start_date,
                          end_date=end_date,
                          keyword=keyword)


@sales_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'Sales')
def create():
    """创建销售单"""
    if request.method == 'POST':
        # 尝试获取JSON数据，silent=True表示如果不是JSON不报错返回None
        data = request.get_json(silent=True)
        is_json_request = data is not None
        
        # 如果不是JSON请求，尝试从表单解析数据
        if not data:
            try:
                cust_id = request.form.get('cus_id')
                med_ids = request.form.getlist('med_id[]')
                quantities = request.form.getlist('quantity[]')
                
                items = []
                if med_ids and quantities:
                    for i, med_id in enumerate(med_ids):
                        if i < len(quantities) and med_id and quantities[i]:
                            # 从数据库查询药品价格（比前端传值更安全）
                            medicine = Medicine.query.get(med_id)
                            if medicine:
                                items.append({
                                    'med_id': med_id,
                                    'quantity': quantities[i],
                                    # 优先使用 sale_price，如果没有则尝试 ref_sell_price
                                    'unit_price': float(getattr(medicine, 'sale_price', getattr(medicine, 'ref_sell_price', 0)) or 0)
                                })
                
                data = {
                    'cus_id': cust_id,
                    'items': items
                }
            except Exception as e:
                flash(f'表单数据解析失败: {str(e)}', 'danger')
                return redirect(url_for('sales.create'))
        
        if not data or not data.get('items'):
            msg = '请添加销售明细'
            if is_json_request:
                return jsonify({'success': False, 'message': msg})
            else:
                flash(msg, 'warning')
                return redirect(url_for('sales.create'))
        
        try:
            so_id = generate_so_id()
            total_price = 0
            
            cust_id = data.get('cus_id')
            if not cust_id:
                msg = '请选择客户！所有购买者必须先登记为顾客。'
                if is_json_request:
                    return jsonify({'success': False, 'message': msg})
                else:
                    flash(msg, 'warning')
                    return redirect(url_for('sales.create'))
            
            # 创建销售单
            order = SalesOrder(
                so_id=so_id,
                emp_id=current_user.emp_id,
                cus_id=int(cust_id),
                total_price=0
            )
            db.session.add(order)
            db.session.flush()  # 获取ID但不提交
            
            # 处理每个销售项 (按先进先出原则扣减库存)
            for item in data['items']:
                med_id = int(item['med_id'])
                sell_qty = int(item['quantity'])
                sell_price = float(item['unit_price'])
                
                # 获取未过期的有效批次 (按过期日期排序 - FIFO)
                batches = StockBatch.query.filter(
                    StockBatch.med_id == med_id,
                    StockBatch.cur_batch_qty > 0,
                    StockBatch.expiry_date > date.today()
                ).order_by(StockBatch.expiry_date).all()
                
                # 检查总库存
                available_qty = sum(b.cur_batch_qty for b in batches)
                if available_qty < sell_qty:
                    raise Exception(f'药品库存不足，可用库存: {available_qty}')
                
                remaining_qty = sell_qty
                
                for batch in batches:
                    if remaining_qty <= 0:
                        break
                    
                    # 计算本批次扣减数量
                    deduct_qty = min(batch.cur_batch_qty, remaining_qty)
                    
                    # 创建销售明细（触发器会自动扣减库存）
                    detail = SalesDetail(
                        so_id=so_id,
                        batch_id=batch.batch_id,
                        med_id=med_id,
                        quantity=deduct_qty,
                        unit_sell_price=sell_price
                    )
                    db.session.add(detail)
                    
                    total_price += deduct_qty * sell_price
                    remaining_qty -= deduct_qty
            
            # 更新订单总价
            order.total_price = total_price
            
            # 更新客户累计消费
            if order.cus_id:
                customer = Customer.query.get(order.cus_id)
                if customer:
                    customer.total_consume = float(customer.total_consume or 0) + total_price
            
            db.session.commit()
            
            if is_json_request:
                return jsonify({
                    'success': True, 
                    'message': f'销售单 {so_id} 创建成功',
                    'so_id': so_id,
                    'total': total_price
                })
            else:
                flash(f'销售单 {so_id} 创建成功，总金额: ¥{total_price:.2f}', 'success')
                return redirect(url_for('sales.list'))
        
        except Exception as e:
            db.session.rollback()
            if is_json_request:
                return jsonify({'success': False, 'message': str(e)})
            else:
                flash(f'销售失败: {str(e)}', 'danger')
                return redirect(url_for('sales.create'))
    
    # GET请求
    customers = Customer.query.all()
    medicines = Medicine.query.all()
    
    return render_template('sales/create.html', 
                         customers=customers,
                         medicines=medicines)


@sales_bp.route('/detail/<so_id>')
@login_required
def detail(so_id):
    """销售单详情"""
    order = SalesOrder.query.get_or_404(so_id)
    details = db.session.query(
        SalesDetail, StockBatch, Medicine
    ).join(
        StockBatch, SalesDetail.batch_id == StockBatch.batch_id
    ).join(
        Medicine, StockBatch.med_id == Medicine.med_id
    ).filter(
        SalesDetail.so_id == so_id
    ).all()
    
    return render_template('sales/detail.html', 
                          order=order, 
                          details=details)


@sales_bp.route('/refund/<so_id>', methods=['POST'])
@login_required
@role_required('Admin', 'Sales')
def refund(so_id):
    """销售退货"""
    order = SalesOrder.query.get_or_404(so_id)
    
    if order.status != 1:
        flash('该订单已退货', 'warning')
        return redirect(url_for('sales.detail', so_id=so_id))
    
    try:
        # 创建销售退货记录（由触发器自动恢复库存）
        from app.models import SalesReturn
        
        for detail in order.details:
            # 创建退货记录
            sr_id = f"SR{datetime.now().strftime('%Y%m%d%H%M%S')}"
            sales_return = SalesReturn(
                sr_id=sr_id,
                so_id=so_id,
                batch_id=detail.batch_id,  # INT类型
                quantity=detail.quantity,
                return_time=datetime.now(),
                reason='销售退货',
                status=1,
                emp_id=current_user.emp_id
            )
            db.session.add(sales_return)
        
        # 扣减客户累计消费
        if order.cus_id:
            customer = Customer.query.get(order.cus_id)
            if customer:
                customer.total_consume = float(customer.total_consume or 0) - float(order.total_price)
        
        order.status = 0
        db.session.commit()
        flash('退货成功，库存已恢复', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'退货失败: {str(e)}', 'danger')
    
    return redirect(url_for('sales.detail', so_id=so_id))


@sales_bp.route('/api/available_stock/<int:med_id>')
@login_required
def api_available_stock(med_id):
    """获取药品可用库存"""
    batches = StockBatch.query.filter(
        StockBatch.med_id == med_id,
        StockBatch.cur_batch_qty > 0,
        StockBatch.expiry_date > date.today()
    ).order_by(StockBatch.expiry_date).all()
    
    total_available = sum(b.cur_batch_qty for b in batches)
    
    medicine = Medicine.query.get(med_id)
    
    return jsonify({
        'med_id': med_id,
        'med_name': medicine.med_name if medicine else '',
        'total_available': total_available,
        'sell_price': float(medicine.ref_sell_price or 0) if medicine else 0,
        'batches': [{
            'batch_id': b.batch_id,
            'batch_no': b.batch_no,
            'qty': b.cur_batch_qty,
            'expiry_date': b.expiry_date.strftime('%Y-%m-%d'),
            'days_to_expire': b.days_to_expire
        } for b in batches]
    })

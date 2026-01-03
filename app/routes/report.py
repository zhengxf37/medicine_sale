"""
报表统计路由
"""
from flask import Blueprint, render_template, request, jsonify
from app import db
from app.models import SalesOrder, SalesDetail, PurchaseOrder, PurchaseDetail, StockBatch, Medicine
from app.routes.auth import login_required, role_required
from datetime import datetime, date, timedelta
from sqlalchemy import func, text

report_bp = Blueprint('report', __name__)


@report_bp.route('/')
@login_required
@role_required('Admin', 'Finance')
def index():
    """报表首页"""
    return render_template('report/index.html')


@report_bp.route('/sales')
@login_required
@role_required('Admin', 'Finance', 'Sales')
def sales_report():
    """销售报表"""
    report_type = request.args.get('type', 'daily')  # daily/monthly
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    today = date.today()
    
    if not start_date:
        start_date = (today - timedelta(days=30)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = today.strftime('%Y-%m-%d')
    
    if report_type == 'daily':
        # 日报表
        query = db.session.query(
            func.date(SalesOrder.sale_time).label('sale_date'),
            func.count(func.distinct(SalesOrder.so_id)).label('order_count'),
            func.sum(SalesDetail.quantity).label('total_qty'),
            func.sum(SalesDetail.quantity * SalesDetail.unit_sell_price).label('total_sales'),
            func.sum(SalesDetail.quantity * (SalesDetail.unit_sell_price - Medicine.ref_buy_price)).label('total_profit')
        ).join(
            SalesDetail, SalesOrder.so_id == SalesDetail.so_id
        ).join(
            StockBatch, SalesDetail.batch_id == StockBatch.batch_id
        ).join(
            Medicine, StockBatch.med_id == Medicine.med_id
        ).filter(
            SalesOrder.status == 1,
            SalesOrder.sale_time >= start_date,
            SalesOrder.sale_time <= end_date + ' 23:59:59'
        ).group_by(
            func.date(SalesOrder.sale_time)
        ).order_by(
            func.date(SalesOrder.sale_time).desc()
        ).all()
    else:
        # 月报表
        query = db.session.query(
            func.date_format(SalesOrder.sale_time, '%Y-%m').label('sale_month'),
            func.count(func.distinct(SalesOrder.so_id)).label('order_count'),
            func.sum(SalesDetail.quantity).label('total_qty'),
            func.sum(SalesDetail.quantity * SalesDetail.unit_sell_price).label('total_sales'),
            func.sum(SalesDetail.quantity * (SalesDetail.unit_sell_price - Medicine.ref_buy_price)).label('total_profit')
        ).join(
            SalesDetail, SalesOrder.so_id == SalesDetail.so_id
        ).join(
            StockBatch, SalesDetail.batch_id == StockBatch.batch_id
        ).join(
            Medicine, StockBatch.med_id == Medicine.med_id
        ).filter(
            SalesOrder.status == 1,
            SalesOrder.sale_time >= start_date,
            SalesOrder.sale_time <= end_date + ' 23:59:59'
        ).group_by(
            func.date_format(SalesOrder.sale_time, '%Y-%m')
        ).order_by(
            func.date_format(SalesOrder.sale_time, '%Y-%m').desc()
        ).all()
    
    # 计算汇总
    summary = {
        'total_orders': sum(r.order_count or 0 for r in query),
        'total_qty': sum(r.total_qty or 0 for r in query),
        'total_sales': sum(float(r.total_sales or 0) for r in query),
        'total_profit': sum(float(r.total_profit or 0) for r in query)
    }
    
    return render_template('report/sales.html',
                          data=query,
                          summary=summary,
                          report_type=report_type,
                          start_date=start_date,
                          end_date=end_date)


@report_bp.route('/top_selling')
@login_required
@role_required('Admin', 'Finance', 'Sales')
def top_selling():
    """畅销榜单"""
    days = request.args.get('days', 30, type=int)
    limit = request.args.get('limit', 10, type=int)
    
    start_date = date.today() - timedelta(days=days)
    
    query = db.session.query(
        Medicine.med_id,
        Medicine.med_name,
        Medicine.spec,
        Medicine.category,
        func.sum(SalesDetail.quantity).label('total_sold'),
        func.sum(SalesDetail.quantity * SalesDetail.unit_sell_price).label('total_revenue'),
        func.count(func.distinct(SalesOrder.so_id)).label('order_count')
    ).join(
        StockBatch, Medicine.med_id == StockBatch.med_id
    ).join(
        SalesDetail, StockBatch.batch_id == SalesDetail.batch_id
    ).join(
        SalesOrder, SalesDetail.so_id == SalesOrder.so_id
    ).filter(
        SalesOrder.status == 1,
        SalesOrder.sale_time >= start_date
    ).group_by(
        Medicine.med_id, Medicine.med_name, Medicine.spec, Medicine.category
    ).order_by(
        func.sum(SalesDetail.quantity).desc()
    ).limit(limit).all()
    
    return render_template('report/top_selling.html',
                          data=query,
                          days=days,
                          limit=limit)


@report_bp.route('/profit')
@login_required
@role_required('Admin', 'Finance')
def profit_analysis():
    """利润分析"""
    year = request.args.get('year', date.today().year, type=int)
    month = request.args.get('month', date.today().month, type=int)
    
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)
    
    # 销售统计
    sales_data = db.session.query(
        func.sum(SalesDetail.quantity * SalesDetail.unit_sell_price).label('total_sales'),
        func.sum(SalesDetail.quantity * Medicine.ref_buy_price).label('total_cost'),
        func.sum(SalesDetail.quantity * (SalesDetail.unit_sell_price - Medicine.ref_buy_price)).label('gross_profit')
    ).join(
        SalesOrder, SalesDetail.so_id == SalesOrder.so_id
    ).join(
        Medicine, SalesDetail.med_id == Medicine.med_id
    ).filter(
        SalesOrder.status == 1,
        SalesOrder.sale_time >= start_date,
        SalesOrder.sale_time <= end_date
    ).first()
    
    # 进货统计
    purchase_total = db.session.query(
        func.sum(PurchaseOrder.total_amount)
    ).filter(
        PurchaseOrder.status == 1,
        PurchaseOrder.purchase_date >= start_date,
        PurchaseOrder.purchase_date <= end_date
    ).scalar() or 0
    
    # 盘点损益
    from app.models import InventoryCheck
    inventory_loss = db.session.query(
        func.sum(InventoryCheck.diff_amount)
    ).filter(
        InventoryCheck.check_time >= start_date,
        InventoryCheck.check_time <= end_date
    ).scalar() or 0
    
    result = {
        'year': year,
        'month': month,
        'total_sales': float(sales_data.total_sales or 0),
        'total_cost': float(sales_data.total_cost or 0),
        'gross_profit': float(sales_data.gross_profit or 0),
        'purchase_total': float(purchase_total),
        'inventory_loss': float(inventory_loss),
        'gross_margin': round(float(sales_data.gross_profit or 0) / float(sales_data.total_sales) * 100, 2) if sales_data.total_sales else 0
    }
    
    return render_template('report/profit.html', data=result)


@report_bp.route('/inventory_value')
@login_required
@role_required('Admin', 'Finance', 'Stock')
def inventory_value():
    """库存资产评估"""
    # 按药品分类统计
    by_category = db.session.query(
        Medicine.category,
        func.count(func.distinct(Medicine.med_id)).label('medicine_count'),
        func.sum(StockBatch.cur_batch_qty).label('total_qty'),
        func.sum(StockBatch.cur_batch_qty * Medicine.ref_buy_price).label('total_cost'),
        func.sum(StockBatch.cur_batch_qty * Medicine.ref_sell_price).label('total_value')
    ).join(
        StockBatch, Medicine.med_id == StockBatch.med_id
    ).filter(
        StockBatch.cur_batch_qty > 0
    ).group_by(
        Medicine.category
    ).all()
    
    # 总计
    total = db.session.query(
        func.sum(StockBatch.cur_batch_qty).label('total_qty'),
        func.sum(StockBatch.cur_batch_qty * Medicine.ref_buy_price).label('total_cost'),
        func.sum(StockBatch.cur_batch_qty * Medicine.ref_sell_price).label('total_value')
    ).join(
        Medicine, StockBatch.med_id == Medicine.med_id
    ).filter(
        StockBatch.cur_batch_qty > 0
    ).first()
    
    summary = {
        'total_qty': total.total_qty or 0,
        'total_cost': float(total.total_cost or 0),
        'total_value': float(total.total_value or 0)
    }
    
    return render_template('report/inventory_value.html',
                          by_category=by_category,
                          summary=summary)


@report_bp.route('/api/sales_chart')
@login_required
def api_sales_chart():
    """销售趋势图表数据"""
    days = request.args.get('days', 7, type=int)
    start_date = date.today() - timedelta(days=days-1)
    
    query = db.session.query(
        func.date(SalesOrder.sale_time).label('sale_date'),
        func.sum(SalesOrder.total_price).label('total_sales')
    ).filter(
        SalesOrder.status == 1,
        SalesOrder.sale_time >= start_date
    ).group_by(
        func.date(SalesOrder.sale_time)
    ).order_by(
        func.date(SalesOrder.sale_time)
    ).all()
    
    # 填充没有销售的日期
    data = {r.sale_date: float(r.total_sales) for r in query}
    labels = []
    values = []
    
    for i in range(days):
        d = start_date + timedelta(days=i)
        labels.append(d.strftime('%m-%d'))
        values.append(data.get(d, 0))
    
    return jsonify({
        'labels': labels,
        'values': values
    })

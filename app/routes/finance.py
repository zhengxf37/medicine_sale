"""
财务管理路由
包括日结统计、月度报表等
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from sqlalchemy import func, and_, or_, extract, text
from app import db
from app.models import FinanceDaily, SalesOrder, SalesDetail, StockBatch, InventoryCheck

bp = Blueprint('finance', __name__, url_prefix='/finance')


@bp.route('/daily')
@login_required
def daily_report():
    """财务日结报表"""
    page = request.args.get('page', 1, type=int)
    per_page = 31
    
    # 获取查询月份
    year = request.args.get('year', date.today().year, type=int)
    month = request.args.get('month', date.today().month, type=int)
    
    # 查询该月的财务数据
    query = FinanceDaily.query.filter(
        extract('year', FinanceDaily.day_id) == year,
        extract('month', FinanceDaily.day_id) == month
    ).order_by(FinanceDaily.day_id.desc())
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    records = pagination.items
    
    # 计算月度合计
    month_sum = db.session.query(
        func.sum(FinanceDaily.sales_revenue).label('total_revenue'),
        func.sum(FinanceDaily.sales_profit).label('total_profit'),
        func.sum(FinanceDaily.sales_return_amt).label('total_sales_return'),
        func.sum(FinanceDaily.purc_return_amt).label('total_purc_return'),
        func.sum(FinanceDaily.inv_loss_amt).label('total_inv_loss'),
        func.sum(FinanceDaily.inv_gain_amt).label('total_inv_gain')
    ).filter(
        extract('year', FinanceDaily.day_id) == year,
        extract('month', FinanceDaily.day_id) == month
    ).first()
    
    # 处理空结果
    if month_sum:
        total_revenue = float(month_sum.total_revenue or 0)
        total_profit = float(month_sum.total_profit or 0)
        total_sales_return = float(month_sum.total_sales_return or 0)
        total_purc_return = float(month_sum.total_purc_return or 0)
        total_inv_loss = float(month_sum.total_inv_loss or 0)
        total_inv_gain = float(month_sum.total_inv_gain or 0)
        
        month_sum_dict = {
            'total_revenue': total_revenue,
            'total_profit': total_profit,
            'total_sales_return': total_sales_return,
            'total_purc_return': total_purc_return,
            'total_inv_loss': total_inv_loss,
            'total_inv_gain': total_inv_gain
        }
    else:
        month_sum_dict = {
            'total_revenue': 0,
            'total_profit': 0,
            'total_sales_return': 0,
            'total_purc_return': 0,
            'total_inv_loss': 0,
            'total_inv_gain': 0
        }
    
    return render_template('finance/daily.html',
                         records=records,
                         pagination=pagination,
                         year=year,
                         month=month,
                         month_sum=month_sum_dict)


@bp.route('/daily/settlement', methods=['POST'])
@login_required
def daily_settlement():
    """执行日结统计"""
    try:
        # 获取要结算的日期
        settle_date = request.form.get('settle_date')
        if not settle_date:
            settle_date = date.today()
        else:
            settle_date = datetime.strptime(settle_date, '%Y-%m-%d').date()
        
        # 调用存储过程进行日结
        db.session.execute(
            text('CALL sp_daily_finance_settlement(:p_date)'),
            {'p_date': settle_date}
        )
        db.session.commit()
        
        flash(f'{settle_date} 日结统计完成', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'日结失败：{str(e)}', 'danger')
    
    return redirect(url_for('finance.daily_report'))


@bp.route('/monthly')
@login_required
def monthly_report():
    """月度财务报表"""
    year = request.args.get('year', date.today().year, type=int)
    month = request.args.get('month', date.today().month, type=int)
    
    # 调用存储过程获取月度汇总
    proc_result = db.session.execute(
        text('CALL sp_monthly_report(:p_year, :p_month)'),
        {'p_year': year, 'p_month': month}
    ).fetchone()
    
    monthly_data_dict = {
        'total_revenue': 0.0,
        'total_profit': 0.0,
        'total_sales_return': 0.0,
        'total_purc_return': 0.0,
        'total_inv_loss': 0.0,
        'total_inv_gain': 0.0,
        'days_count': FinanceDaily.query.filter(
            extract('year', FinanceDaily.day_id) == year,
            extract('month', FinanceDaily.day_id) == month
        ).count(),
        'order_count': 0
    }
    
    if proc_result:
        monthly_data_dict['total_revenue'] = float(proc_result.total_sales or 0)
        monthly_data_dict['total_inv_loss'] = float(proc_result.inventory_loss or 0)
        monthly_data_dict['order_count'] = int(proc_result.order_count or 0)
    
    # 计算净利润（目前存储过程未返回利润相关字段，默认以0处理）
    net_profit = 0
    
    # 获取每日趋势数据
    daily_trend = FinanceDaily.query.filter(
        extract('year', FinanceDaily.day_id) == year,
        extract('month', FinanceDaily.day_id) == month
    ).order_by(FinanceDaily.day_id).all()
    
    return render_template('finance/monthly.html',
                         monthly_data=monthly_data_dict,
                         net_profit=net_profit,
                         daily_trend=daily_trend,
                         year=year,
                         month=month)


@bp.route('/annual')
@login_required
def annual_report():
    """年度财务报表"""
    year = request.args.get('year', date.today().year, type=int)
    
    # 按月份统计年度数据
    monthly_stats = db.session.query(
        extract('month', FinanceDaily.day_id).label('month'),
        func.sum(FinanceDaily.sales_revenue).label('revenue'),
        func.sum(FinanceDaily.sales_profit).label('profit'),
        func.sum(FinanceDaily.sales_return_amt).label('sales_return'),
        func.sum(FinanceDaily.purc_return_amt).label('purc_return'),
        func.sum(FinanceDaily.inv_loss_amt).label('inv_loss'),
        func.sum(FinanceDaily.inv_gain_amt).label('inv_gain')
    ).filter(
        extract('year', FinanceDaily.day_id) == year
    ).group_by('month').order_by('month').all()
    
    # 计算年度总计
    annual_sum = db.session.query(
        func.sum(FinanceDaily.sales_revenue).label('total_revenue'),
        func.sum(FinanceDaily.sales_profit).label('total_profit'),
        func.sum(FinanceDaily.sales_return_amt).label('total_sales_return'),
        func.sum(FinanceDaily.purc_return_amt).label('total_purc_return'),
        func.sum(FinanceDaily.inv_loss_amt).label('total_inv_loss'),
        func.sum(FinanceDaily.inv_gain_amt).label('total_inv_gain')
    ).filter(
        extract('year', FinanceDaily.day_id) == year
    ).first()
    
    # 处理空结果
    if annual_sum:
        total_revenue = float(annual_sum.total_revenue or 0)
        total_profit = float(annual_sum.total_profit or 0)
        total_sales_return = float(annual_sum.total_sales_return or 0)
        total_purc_return = float(annual_sum.total_purc_return or 0)
        total_inv_loss = float(annual_sum.total_inv_loss or 0)
        total_inv_gain = float(annual_sum.total_inv_gain or 0)
        
        annual_sum_dict = {
            'total_revenue': total_revenue,
            'total_profit': total_profit,
            'total_sales_return': total_sales_return,
            'total_purc_return': total_purc_return,
            'total_inv_loss': total_inv_loss,
            'total_inv_gain': total_inv_gain
        }
    else:
        annual_sum_dict = {
            'total_revenue': 0,
            'total_profit': 0,
            'total_sales_return': 0,
            'total_purc_return': 0,
            'total_inv_loss': 0,
            'total_inv_gain': 0
        }
    
    # 计算年度净利润
    annual_net_profit = 0
    if annual_sum_dict['total_profit']:
        annual_net_profit = (float(annual_sum_dict['total_profit'] or 0) - 
                            float(annual_sum_dict['total_sales_return'] or 0) +
                            float(annual_sum_dict['total_purc_return'] or 0) -
                            float(annual_sum_dict['total_inv_loss'] or 0) +
                            float(annual_sum_dict['total_inv_gain'] or 0))
    
    return render_template('finance/annual.html',
                         monthly_stats=monthly_stats,
                         annual_sum=annual_sum_dict,
                         annual_net_profit=annual_net_profit,
                         year=year)


@bp.route('/api/chart_data')
@login_required
def get_chart_data():
    """获取图表数据"""
    chart_type = request.args.get('type', 'daily')
    year = request.args.get('year', date.today().year, type=int)
    month = request.args.get('month', date.today().month, type=int)
    
    if chart_type == 'daily':
        # 日度数据
        records = FinanceDaily.query.filter(
            extract('year', FinanceDaily.day_id) == year,
            extract('month', FinanceDaily.day_id) == month
        ).order_by(FinanceDaily.day_id).all()
        
        data = {
            'dates': [r.day_id.strftime('%Y-%m-%d') for r in records],
            'revenue': [float(r.sales_revenue or 0) for r in records],
            'profit': [float(r.sales_profit or 0) for r in records],
            'net_profit': [r.net_profit for r in records]
        }
    else:
        # 月度数据
        monthly_stats = db.session.query(
            extract('month', FinanceDaily.day_id).label('month'),
            func.sum(FinanceDaily.sales_revenue).label('revenue'),
            func.sum(FinanceDaily.sales_profit).label('profit')
        ).filter(
            extract('year', FinanceDaily.day_id) == year
        ).group_by('month').order_by('month').all()
        
        data = {
            'months': [f'{int(m.month)}月' for m in monthly_stats],
            'revenue': [float(m.revenue or 0) for m in monthly_stats],
            'profit': [float(m.profit or 0) for m in monthly_stats]
        }
    
    return jsonify(data)

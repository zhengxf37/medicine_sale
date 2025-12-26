"""
Flask 应用工厂
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import config

db = SQLAlchemy()
login_manager = LoginManager()


def create_app(config_name='default'):
    """应用工厂函数"""
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # 初始化扩展
    db.init_app(app)
    login_manager.init_app(app)
    
    # 配置 Flask-Login
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录'
    login_manager.login_message_category = 'warning'
    
    # 用户加载回调
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import Employee
        return Employee.query.get(int(user_id))
    
    # 注册蓝图
    from app.routes.auth import auth_bp
    from app.routes.medicine import medicine_bp
    from app.routes.supplier import supplier_bp
    from app.routes.customer import customer_bp
    from app.routes.purchase import purchase_bp
    from app.routes.sales import sales_bp
    from app.routes.stock import stock_bp
    from app.routes.report import report_bp
    from app.routes.return_manage import bp as return_bp
    from app.routes.finance import bp as finance_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(medicine_bp, url_prefix='/medicine')
    app.register_blueprint(supplier_bp, url_prefix='/supplier')
    app.register_blueprint(customer_bp, url_prefix='/customer')
    app.register_blueprint(purchase_bp, url_prefix='/purchase')
    app.register_blueprint(sales_bp, url_prefix='/sales')
    app.register_blueprint(stock_bp, url_prefix='/stock')
    app.register_blueprint(report_bp, url_prefix='/report')
    app.register_blueprint(return_bp, url_prefix='/return')
    app.register_blueprint(finance_bp, url_prefix='/finance')
    
    # 注册自定义过滤器
    @app.template_filter('currency')
    def currency_filter(value):
        """货币格式化过滤器"""
        if value is None:
            return '¥0.00'
        return f'¥{value:,.2f}'
    
    return app

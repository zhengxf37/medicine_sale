# Medicine Sales Management System - AI Coding Guidelines

## Project Overview
Flask-based pharmacy management system with MySQL database. Manages medicine inventory, sales, purchases, customers, suppliers, and financial reporting. Four user roles: Admin, Sales, Stock, Finance.

## Architecture
- **Factory Pattern**: `create_app()` in `app/__init__.py` initializes Flask app with blueprints
- **Blueprints**: Modular routes in `app/routes/` (auth, medicine, supplier, customer, purchase, sales, stock, report, return_manage, finance)
- **Models**: SQLAlchemy ORM in `app/models.py` with table prefix `t_` (e.g., `t_employee`)
- **Templates**: Jinja2 in `app/templates/` with role-based access control
- **Config**: Environment-based config in `config.py` (development/production)

## Key Workflows
- **Run App**: `python run.py` (starts on http://127.0.0.1:5000, debug=True)
- **Database Setup**: Execute `sql/init.sql` in MySQL to create tables, triggers, procedures, views, indexes
- **Dependencies**: `pip install -r requirements.txt` (Flask 3.0, SQLAlchemy 2.0, PyMySQL, Flask-Login)
- **Default Login**: admin / 123456 (MD5 hashed)

## Conventions
- **Authentication**: Use `@login_required` and `@role_required('Admin', 'Sales')` decorators
- **Database**: Table names `t_<name>`, foreign keys with proper relationships, computed properties (e.g., `subtotal`, `is_low_stock`)
- **Security**: Passwords stored as MD5 hash (project-specific, not production-ready)
- **Pagination**: `ITEMS_PER_PAGE = 10` from config
- **Currency**: Use `{{ value | currency }}` template filter for ¥ formatting
- **Status Fields**: `status` column (1=active, 0=inactive) common across tables

## Examples
- **Add Route**: Register in blueprint, use `url_prefix` (e.g., `/medicine` for medicine routes)
- **Query with Role Check**: `if current_user.role in ['Admin', 'Finance']:`
- **Database Transaction**: Wrap sales/purchase in `db.session.begin()` for consistency
- **Template Structure**: Base template `base.html`, role-specific content in subfolders

## Integration Points
- **MySQL Triggers**: Auto-update `total_stock` on insert/update/delete in batch tables
- **Views**: `v_expired_drugs`, `v_low_stock` for efficient queries
- **Stored Procedures**: Complex financial calculations in database layer
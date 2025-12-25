#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
药品销售管理系统 - 启动入口
"""

from app import create_app

app = create_app()

if __name__ == '__main__':
    print("=" * 50)
    print("药品销售管理系统启动中...")
    print("=" * 50)
    print("访问地址: http://127.0.0.1:5000")
    print("默认账号: admin")
    print("默认密码: 123456")
    print("=" * 50)
    print("注意：请先执行 sql/init.sql 初始化数据库")
    print("=" * 50)
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )

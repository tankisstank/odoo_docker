# -*- coding: utf-8 -*-
"""
Script để di chuyển dữ liệu từ CSDL SQL Server cũ sang Odoo.

Yêu cầu:
1. Cài đặt thư viện pyodbc: pip install pyodbc
2. Đảm bảo bạn có SQL Server ODBC Driver phù hợp đã được cài đặt trên máy.
3. Chạy script này từ một môi trường có thể kết nối tới cả SQL Server và Odoo.

Thứ tự di chuyển dữ liệu:
1. Đơn vị tính (Units of Measure)
2. Danh mục sản phẩm (Product Categories)
3. Khách hàng/Đối tác (Partners)
4. Sản phẩm (Products)
5. Đơn hàng (Sale Orders)
6. Công nợ (Debts)
"""

import logging
from migrator_core import OdooMigrator

# Import individual migration functions
from migrate_uom import migrate_uom
from migrate_categories import migrate_product_categories
from migrate_partners import migrate_partners
from migrate_users import migrate_users
from migrate_products import migrate_products_from_sp
from migrate_sales import migrate_sale_orders
from migrate_debts import migrate_debts


# Cấu hình kết nối SQL Server
SQL_SERVER_CONFIG = {
    'server': '100.71.131.103,1433',  # Thay bằng IP hoặc tên server của bạn
    'database': 'DSQL',
    'username': 'sa',
    'password': 'Dbtruong@',
    # Nếu dùng Windows Authentication, có thể cần thay đổi chuỗi kết nối
    # driver: '{ODBC Driver 17 for SQL Server}' # Đảm bảo driver tồn tại
}

# Cấu hình kết nối Odoo
# !! QUAN TRỌNG !!
# Kịch bản này BẮT BUỘC phải chạy với quyền của Quản trị viên cao nhất (Superuser).
# Hãy điền thông tin đăng nhập của tài khoản Admin gốc (tài khoản có UID = 1).
# Đây thường là tài khoản đầu tiên được tạo khi bạn thiết lập database Odoo.
ODOO_CONFIG = {
    'url': 'http://localhost:8069',
    'db': 'odoo_test',
    'username': 'admin',  # Email/login của tài khoản Admin gốc
    'password': 'abc123'  # Mật khẩu của tài khoản Admin gốc (hãy thay bằng mật khẩu bạn đã reset)
}

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Dynamically add migration functions as methods to OdooMigrator class
OdooMigrator.migrate_uom = migrate_uom
OdooMigrator.migrate_product_categories = migrate_product_categories
OdooMigrator.migrate_partners = migrate_partners
OdooMigrator.migrate_users = migrate_users
OdooMigrator.migrate_products_from_sp = migrate_products_from_sp
OdooMigrator.migrate_sale_orders = migrate_sale_orders
OdooMigrator.migrate_debts = migrate_debts


class MainMigration:
    def __init__(self):
        self.migrator = OdooMigrator(SQL_SERVER_CONFIG, ODOO_CONFIG)

    def run_all_migrations(self):
        """Chạy toàn bộ quy trình di chuyển dữ liệu."""
        logging.info("=== BẮT ĐẦU QUÁ TRÌNH DI CHUYỂN DỮ LIỆU ===")
        
        self.migrator.migrate_uom()
        self.migrator.migrate_product_categories()
        self.migrator.migrate_partners()
        self.migrator.migrate_users()
        self.migrator.migrate_products_from_sp()
        self.migrator.migrate_sale_orders()
        self.migrator.migrate_debts()
        
        logging.info("=== QUÁ TRÌNH DI CHUYỂN DỮ LIỆU HOÀN TẤT ===")


if __name__ == '__main__':
    main_migrator = MainMigration()
    main_migrator.run_all_migrations()

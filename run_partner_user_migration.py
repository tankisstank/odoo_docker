# -*- coding: utf-8 -*-
import logging
from main_migration import SQL_SERVER_CONFIG, ODOO_CONFIG, MainMigration
from migrator_core import OdooMigrator
from migrate_partners import migrate_partners
from migrate_users import migrate_users

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Patch Migrator
OdooMigrator.migrate_partners = migrate_partners
OdooMigrator.migrate_users = migrate_users

if __name__ == '__main__':
    logging.info("=== BẮT ĐẦU DI CHUYỂN DỮ LIỆU (CHỈ KHÁCH HÀNG & NGƯỜI DÙNG) ===")
    
    migrator = OdooMigrator(SQL_SERVER_CONFIG, ODOO_CONFIG)
    
    # 1. Migrate Partners
    try:
        migrator.migrate_partners()
    except Exception as e:
        logging.error(f"Lỗi khi di chuyển Khách hàng: {e}")
        
    # 2. Migrate Users
    try:
        migrator.migrate_users()
    except Exception as e:
        logging.error(f"Lỗi khi di chuyển Người dùng: {e}")
        
    logging.info("=== HOÀN TẤT ===")

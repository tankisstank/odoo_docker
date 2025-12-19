# -*- coding: utf-8 -*-
import xmlrpc.client
import sys
import pyodbc
import logging

class OdooMigrator:
    def __init__(self, sql_config, odoo_config):
        self.sql_conn = self._connect_sql_server(sql_config)
        self.odoo_models, self.uid = self._connect_odoo(odoo_config)
        self.odoo_password = odoo_config['password']
        self.db_name = odoo_config['db']

        self.mapping = {
            'uom': {},
            'category': {},
            'partner': {},
            'user': {},
            'product': {},
            'order': {},
            'debt': set(),
            'group_info': {}, # Lưu TenNhomCon theo MaNhomCon
        }

    def _connect_sql_server(self, config):
        try:
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={config['server']};"
                f"DATABASE={config['database']};"
                f"UID={config['username']};"
                f"PWD={config['password']};"
            )
            conn = pyodbc.connect(conn_str)
            logging.info("Kết nối SQL Server thành công.")
            return conn
        except Exception as e:
            logging.error(f"Lỗi kết nối SQL Server: {e}")
            sys.exit(1)

    def _connect_odoo(self, config):
        try:
            common = xmlrpc.client.ServerProxy(f'{config["url"]}/xmlrpc/2/common')
            uid = common.authenticate(config['db'], config['username'], config['password'], {})
            if not uid:
                logging.error("Xác thực Odoo thất bại. Vui lòng kiểm tra thông tin đăng nhập trong ODOO_CONFIG.")
                sys.exit(1)
            
            if uid != 1:
                logging.error(f"LỖI: Người dùng '{config['username']}' có UID là {uid}, không phải Superuser (UID=1).")
                sys.exit(1)

            models = xmlrpc.client.ServerProxy(f'{config["url"]}/xmlrpc/2/object', allow_none=True)
            logging.info(f"Xác thực Odoo thành công với Superuser '{config['username']}' (UID: {uid}).")
            return models, uid
        except Exception as e:
            logging.error(f"Lỗi kết nối Odoo: {e}")
            sys.exit(1)

    def execute_odoo_kw(self, model, method, args_list=None, kw_dict=None):
        if args_list is None:
            args_list = []
        if kw_dict is None:
            kw_dict = {}
        return self.odoo_models.execute_kw(
            self.db_name, 
            self.uid, 
            self.odoo_password, 
            model, 
            method, 
            args_list,
            kw_dict
        )

# The migration functions will be added as methods to this class in separate files.
# For example:
# from .migrate_uom import migrate_uom
# OdooMigrator.migrate_uom = migrate_uom

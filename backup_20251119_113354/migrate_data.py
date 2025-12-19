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
"""

import xmlrpc.client
import sys
import pyodbc
import logging

# --- Cấu hình ---

# Cấu hình kết nối SQL Server
SQL_SERVER_CONFIG = {
    'server': 'localhost',  # Thay bằng IP hoặc tên server của bạn
    'database': 'DSQL',
    'username': 'your_username',  # Thay bằng username
    'password': 'your_password',  # Thay bằng password
    # Nếu dùng Windows Authentication, có thể cần thay đổi chuỗi kết nối
    # driver: '{ODBC Driver 17 for SQL Server}' # Đảm bảo driver tồn tại
}

# Cấu hình kết nối Odoo
ODOO_CONFIG = {
    'url': 'http://localhost:8069',
    'db': 'gold_business',  # Tên database Odoo bạn đã tạo
    'username': 'admin',
    'password': 'admin'  # Mật khẩu admin của Odoo
}

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class OdooMigrator:
    def __init__(self, sql_config, odoo_config):
        self.sql_conn = self._connect_sql_server(sql_config)
        self.odoo_models, self.uid = self._connect_odoo(odoo_config)
        self.odoo_password = odoo_config['password']
        self.db_name = odoo_config['db']

        # Dùng để lưu mapping giữa ID cũ và ID mới
        self.mapping = {
            'uom': {},
            'category': {},
            'partner': {},
            'product': {},
            'order': {},
        }

    def _connect_sql_server(self, config):
        """Kết nối đến SQL Server."""
        try:
            # Chuỗi kết nối có thể cần điều chỉnh tùy theo driver và phương thức xác thực
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
        """Kết nối đến Odoo."""
        try:
            common = xmlrpc.client.ServerProxy(f'{config["url"]}/xmlrpc/2/common')
            uid = common.authenticate(config['db'], config['username'], config['password'], {})
            if not uid:
                logging.error("Không thể kết nối đến Odoo. Vui lòng kiểm tra thông tin đăng nhập.")
                sys.exit(1)
            
            models = xmlrpc.client.ServerProxy(f'{config["url"]}/xmlrpc/2/object')
            logging.info(f"Kết nối Odoo thành công với UID: {uid}.")
            return models, uid
        except Exception as e:
            logging.error(f"Lỗi kết nối Odoo: {e}")
            sys.exit(1)

    def execute_odoo_kw(self, model, method, *args, **kwargs):
        """Hàm helper để gọi API của Odoo."""
        return self.odoo_models.execute_kw(self.db_name, self.uid, self.odoo_password, model, method, *args, **kwargs)

    def migrate_uom(self):
        """
        Di chuyển Đơn vị tính.
        Trong Odoo, 'chỉ' và 'lượng' đã được cấu hình thủ công hoặc qua script.
        Hàm này sẽ kiểm tra và tạo nếu chưa có.
        """
        logging.info("Bắt đầu di chuyển Đơn vị tính (UoM)...")
        
        # 1. Tạo/Lấy UoM Category
        uom_categ_name = 'Trọng lượng Vàng'
        categ_ids = self.execute_odoo_kw('uom.category', 'search', [[('name', '=', uom_categ_name)]])
        if not categ_ids:
            logging.info(f"Tạo UoM Category: {uom_categ_name}")
            uom_categ_id = self.execute_odoo_kw('uom.category', 'create', [{'name': uom_categ_name}])
        else:
            uom_categ_id = categ_ids[0]
        logging.info(f"Sử dụng UoM Category ID: {uom_categ_id}")

        # 2. Ánh xạ và tạo UoM
        uoms_to_migrate = {
            'chỉ': {'type': 'reference', 'ratio': 1.0},
            'lượng': {'type': 'bigger', 'ratio': 10.0},
            'gram': {'type': 'smaller', 'ratio': 1 / 3.75} # 1 chỉ ~ 3.75g
        }

        for uom_name, uom_data in uoms_to_migrate.items():
            existing_uom = self.execute_odoo_kw('uom.uom', 'search', [[('name', '=', uom_name), ('category_id', '=', uom_categ_id)]])
            if not existing_uom:
                logging.info(f"Tạo UoM: {uom_name}")
                new_uom_id = self.execute_odoo_kw('uom.uom', 'create', [{
                    'name': uom_name,
                    'category_id': uom_categ_id,
                    'uom_type': uom_data['type'],
                    'ratio': uom_data['ratio'],
                    'rounding': 0.001
                }])
                self.mapping['uom'][uom_name] = new_uom_id
            else:
                logging.info(f"UoM '{uom_name}' đã tồn tại.")
                self.mapping['uom'][uom_name] = existing_uom[0]
        
        logging.info("Di chuyển Đơn vị tính hoàn tất.")

    def migrate_product_categories(self):
        """Di chuyển danh mục sản phẩm từ tb_NhomSP và tb_NhomCon."""
        logging.info("Bắt đầu di chuyển Danh mục sản phẩm...")
        cursor = self.sql_conn.cursor()

        # Di chuyển danh mục cha (tb_NhomSP)
        cursor.execute("SELECT MaNhomSP, TenNhomSP FROM tb_NhomSP WHERE TinhTrang = 1")
        for row in cursor.fetchall():
            old_id, name = row
            existing_cat = self.execute_odoo_kw('product.category', 'search', [[('name', '=', name)]])
            if not existing_cat:
                logging.info(f"Tạo danh mục cha: {name}")
                new_id = self.execute_odoo_kw('product.category', 'create', [{'name': name}])
                self.mapping['category'][f'parent_{old_id}'] = new_id
            else:
                self.mapping['category'][f'parent_{old_id}'] = existing_cat[0]

        # Di chuyển danh mục con (tb_NhomCon)
        cursor.execute("SELECT MaNhomCon, MaNhomSP, TenNhomCon FROM tb_NhomCon WHERE TinhTrang = 1")
        for row in cursor.fetchall():
            old_id, parent_old_id, name = row
            parent_new_id = self.mapping['category'].get(f'parent_{parent_old_id}')
            
            cat_data = {'name': name}
            if parent_new_id:
                cat_data['parent_id'] = parent_new_id

            existing_cat = self.execute_odoo_kw('product.category', 'search', [[('name', '=', name), ('parent_id', '=', parent_new_id)]])
            if not existing_cat:
                logging.info(f"Tạo danh mục con: {name}")
                new_id = self.execute_odoo_kw('product.category', 'create', [cat_data])
                self.mapping['category'][f'child_{old_id}'] = new_id
            else:
                self.mapping['category'][f'child_{old_id}'] = existing_cat[0]

        logging.info("Di chuyển Danh mục sản phẩm hoàn tất.")

    def migrate_partners(self):
        """Di chuyển khách hàng/đối tác từ tb_BH."""
        logging.info("Bắt đầu di chuyển Đối tác (Khách hàng)...")
        cursor = self.sql_conn.cursor()
        cursor.execute("SELECT MaBH, TenBH, DienThoai, DiaChi FROM tb_BH WHERE TinhTrang = 1")
        
        for row in cursor.fetchall():
            old_id, name, phone, address = row
            
            partner_data = {
                'name': name.strip(),
                'phone': phone.strip() if phone else None,
                'street': address.strip() if address else None,
                'is_company': False, # Giả định tất cả là cá nhân
            }
            
            # Kiểm tra đối tác đã tồn tại chưa (dựa vào tên)
            existing_partner = self.execute_odoo_kw('res.partner', 'search', [[('name', '=', partner_data['name'])]])
            if not existing_partner:
                logging.info(f"Tạo đối tác: {partner_data['name']}")
                try:
                    new_id = self.execute_odoo_kw('res.partner', 'create', [partner_data])
                    self.mapping['partner'][old_id] = new_id
                except Exception as e:
                    logging.error(f"Lỗi khi tạo đối tác '{partner_data['name']}': {e}")
            else:
                self.mapping['partner'][old_id] = existing_partner[0]

        logging.info("Di chuyển Đối tác hoàn tất.")

    def migrate_products(self):
        """Di chuyển sản phẩm từ tb_SP."""
        logging.info("Bắt đầu di chuyển Sản phẩm...")
        cursor = self.sql_conn.cursor()
        
        # Lấy ID của đơn vị 'chỉ' để làm mặc định
        uom_chi_id = self.mapping['uom'].get('chỉ')
        if not uom_chi_id:
            logging.error("Không tìm thấy UoM 'chỉ' trong Odoo. Vui lòng chạy migrate_uom() trước.")
            return

        query = """
            SELECT MaSP, TenSP, MaNhomCon, TienCongTrenSPXuat, TienCongTrenSPNhap, DVTNhap 
            FROM tb_SP WHERE TinhTrang = 1
        """
        cursor.execute(query)

        for row in cursor.fetchall():
            old_id, name, old_cat_id, sale_price, cost_price, uom_name_old = row
            
            category_new_id = self.mapping['category'].get(f'child_{old_cat_id}')
            
            # Lấy UoM, nếu không có thì mặc định là 'chỉ'
            uom_id = self.mapping['uom'].get(uom_name_old.lower(), uom_chi_id)

            product_data = {
                'name': name.strip(),
                'sale_ok': True,
                'purchase_ok': True,
                'type': 'product',  # 'product' for storable
                'categ_id': category_new_id,
                'list_price': float(sale_price or 0.0),      # Giá bán
                'standard_price': float(cost_price or 0.0), # Giá vốn (giá mua vào)
                'uom_id': uom_id,
                'uom_po_id': uom_id,
            }

            # Kiểm tra sản phẩm đã tồn tại chưa
            existing_product = self.execute_odoo_kw('product.product', 'search', [[('name', '=', product_data['name'])]])
            if not existing_product:
                logging.info(f"Tạo sản phẩm: {product_data['name']}")
                try:
                    new_id = self.execute_odoo_kw('product.product', 'create', [product_data])
                    self.mapping['product'][old_id] = new_id
                except Exception as e:
                    logging.error(f"Lỗi khi tạo sản phẩm '{product_data['name']}': {e}")
            else:
                self.mapping['product'][old_id] = existing_product[0]

        logging.info("Di chuyển Sản phẩm hoàn tất.")

    def migrate_sale_orders(self):
        """Di chuyển đơn hàng từ tb_GD và tb_CTGD."""
        logging.info("Bắt đầu di chuyển Đơn hàng...")
        cursor = self.sql_conn.cursor()

        # Lấy các giao dịch bán hàng (ví dụ LoaiPhieu = 2 là phiếu bán)
        # Cần xác định đúng ý nghĩa của LoaiPhieu
        cursor.execute("SELECT MaGD, MaBH, ThoiGian, GhiChu FROM tb_GD WHERE LoaiPhieu = 2")
        
        orders = cursor.fetchall()
        total_orders = len(orders)
        logging.info(f"Tìm thấy {total_orders} đơn hàng để di chuyển.")

        for i, row in enumerate(orders):
            old_order_id, old_partner_id, date_order, notes = row
            
            partner_new_id = self.mapping['partner'].get(old_partner_id)
            if not partner_new_id:
                logging.warning(f"Bỏ qua đơn hàng ID={old_order_id} vì không tìm thấy đối tác ID={old_partner_id}.")
                continue

            order_data = {
                'partner_id': partner_new_id,
                'date_order': date_order.strftime('%Y-%m-%d %H:%M:%S'),
                'state': 'sale', # Mặc định chuyển thành đơn hàng đã xác nhận
                'note': notes,
            }
            
            logging.info(f"[{i+1}/{total_orders}] Tạo đơn hàng cho đối tác ID (cũ): {old_partner_id}")
            try:
                new_order_id = self.execute_odoo_kw('sale.order', 'create', [order_data])
                self.mapping['order'][old_order_id] = new_order_id
                
                # Bây giờ di chuyển các dòng đơn hàng (order lines)
                self._migrate_order_lines(old_order_id, new_order_id)

                # Trigger recompute
                self.execute_odoo_kw('sale.order', 'write', [[new_order_id], {}])
                logging.info(f"Tạo thành công đơn hàng Odoo ID {new_order_id} từ ID cũ {old_order_id}")

            except Exception as e:
                logging.error(f"Lỗi khi tạo đơn hàng từ ID cũ {old_order_id}: {e}")

        logging.info("Di chuyển Đơn hàng hoàn tất.")

    def _migrate_order_lines(self, old_order_id, new_order_id):
        """Di chuyển các dòng chi tiết của một đơn hàng."""
        cursor = self.sql_conn.cursor()
        
        # Giả định: LoaiCTGD = 1 là bán ra, LoaiCTGD = 2 là mua vào (trade-in)
        query = "SELECT MaSP, SL, HeSoQD1, LoaiCTGD FROM tb_CTGD WHERE MaGD = ?"
        cursor.execute(query, old_order_id)

        for line_row in cursor.fetchall():
            old_product_id, qty, price_unit, line_type = line_row
            
            product_new_id = self.mapping['product'].get(old_product_id)
            if not product_new_id:
                logging.warning(f"Bỏ qua dòng sản phẩm ID={old_product_id} vì không tìm thấy sản phẩm tương ứng.")
                continue

            is_trade_in = (line_type == 2)
            
            line_data = {
                'order_id': new_order_id,
                'product_id': product_new_id,
                'product_uom_qty': float(qty),
                'price_unit': float(price_unit),
                'is_trade_in': is_trade_in,
            }
            
            try:
                self.execute_odoo_kw('sale.order.line', 'create', [line_data])
            except Exception as e:
                logging.error(f"Lỗi khi tạo dòng đơn hàng cho Odoo Order ID {new_order_id}: {e}")

    def run_migration(self):
        """Chạy toàn bộ quy trình di chuyển dữ liệu."""
        logging.info("=== BẮT ĐẦU QUÁ TRÌNH DI CHUYỂN DỮ LIỆU ===")
        
        self.migrate_uom()
        self.migrate_product_categories()
        self.migrate_partners()
        self.migrate_products()
        self.migrate_sale_orders()
        
        logging.info("=== QUÁ TRÌNH DI CHUYỂN DỮ LIỆU HOÀN TẤT ===")


if __name__ == '__main__':
    # Chú ý: Cần điền đúng thông tin kết nối ở đầu file.
    # Chạy script này sẽ bắt đầu di chuyển dữ liệu.
    
    migrator = OdooMigrator(SQL_SERVER_CONFIG, ODOO_CONFIG)
    migrator.run_migration()

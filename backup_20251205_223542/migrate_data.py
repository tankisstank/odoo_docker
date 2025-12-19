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
    'username': 'sa',  # Thay bằng username
    'password': 'Dbtruong@',  # Thay bằng password
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
            'user': {},
            'tygia_product': {}, # Thay thế self.mapping['product']
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
        """
        Kết nối đến Odoo và kiểm tra quyền Superuser (UID=1).
        """
        try:
            common = xmlrpc.client.ServerProxy(f'{config["url"]}/xmlrpc/2/common')
            uid = common.authenticate(config['db'], config['username'], config['password'], {})
            if not uid:
                logging.error("Xác thực Odoo thất bại. Vui lòng kiểm tra thông tin đăng nhập trong ODOO_CONFIG.")
                sys.exit(1)
            
            # BẮT BUỘC phải chạy với quyền Superuser
            if uid != 1:
                logging.error(f"LỖI: Người dùng '{config['username']}' có UID là {uid}, không phải Superuser (UID=1).")
                logging.error("Vui lòng cập nhật ODOO_CONFIG với thông tin đăng nhập của tài khoản Admin gốc (UID=1).")
                sys.exit(1)

            models = xmlrpc.client.ServerProxy(f'{config["url"]}/xmlrpc/2/object', allow_none=True)
            logging.info(f"Xác thực Odoo thành công với Superuser '{config['username']}' (UID: {uid}).")
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
        """
        Di chuyển đối tác.
        1. Lấy danh sách ID đối tác duy nhất từ các bảng giao dịch (tb_GD, tb_CTNo, tb_CTGD).
        2. Tải thông tin chi tiết (Tên, SĐT, Địa chỉ) từ bảng chính tb_BH.
        3. Khi tạo đối tác, ưu tiên sử dụng thông tin từ tb_BH. Nếu không có, dùng tên chung.
        """
        logging.info("Bắt đầu di chuyển Đối tác...")
        cursor = self.sql_conn.cursor()
        
        # 1. Tải trước thông tin chi tiết từ tb_BH vào một dictionary
        partner_details = {}
        logging.info("Tải thông tin chi tiết đối tác từ tb_BH...")
        cursor.execute("SELECT MaBH, TenBH, DienThoai, DiaChi FROM tb_BH WHERE TinhTrang = 1")
        for row in cursor.fetchall():
            # Đảm bảo key là string để đối chiếu nhất quán
            old_id, name, phone, address = row
            partner_details[str(old_id)] = {
                'name': name.strip() if name else '',
                'phone': phone.strip() if phone else None,
                'street': address.strip() if address else None,
            }
        logging.info(f"Đã tải {len(partner_details)} chi tiết đối tác từ tb_BH.")

        # 2. Thu thập tất cả ID đối tác duy nhất từ các bảng giao dịch
        unique_partner_ids = set()
        logging.info("Thu thập ID đối tác từ các bảng giao dịch...")
        
        cursor.execute("SELECT DISTINCT MaBH FROM tb_GD WHERE MaBH IS NOT NULL")
        for row in cursor.fetchall():
            unique_partner_ids.add(str(row[0]))

        cursor.execute("SELECT DISTINCT MaBH FROM tb_CTNo WHERE MaBH IS NOT NULL")
        for row in cursor.fetchall():
            unique_partner_ids.add(str(row[0]))
            
        cursor.execute("SELECT DISTINCT MaTK FROM tb_CTGD WHERE MaTK IS NOT NULL")
        for row in cursor.fetchall():
            unique_partner_ids.add(str(row[0]))

        logging.info(f"Tìm thấy tổng cộng {len(unique_partner_ids)} đối tác duy nhất từ các giao dịch.")

        # 3. Tạo hoặc cập nhật đối tác trong Odoo
        for old_id in unique_partner_ids:
            # Dùng ref để kiểm tra sự tồn tại, đảm bảo tính idempotent
            search_domain = [('ref', '=', old_id)]
            existing_partner_ids = self.execute_odoo_kw('res.partner', 'search', [search_domain], {'limit': 1})

            # Lấy thông tin chi tiết nếu có, nếu không thì dùng giá trị mặc định
            details = partner_details.get(old_id)
            if details:
                partner_name = details['name'] or f"Khách hàng {old_id}"
                phone = details['phone']
                street = details['street']
            else:
                partner_name = f"Khách hàng {old_id}"
                phone = None
                street = None

            partner_data = {
                'name': partner_name,
                'ref': old_id,
                'phone': phone,
                'street': street,
                'is_company': False,
                'is_gold_partner': True, # Đánh dấu là đối tác từ hệ thống cũ
            }

            if not existing_partner_ids:
                logging.info(f"Tạo đối tác mới: {partner_name} (ID: {old_id})")
                try:
                    new_id = self.execute_odoo_kw('res.partner', 'create', [partner_data])
                    self.mapping['partner'][old_id] = new_id
                except Exception as e:
                    logging.error(f"Lỗi khi tạo đối tác với ID cũ '{old_id}': {e}")
            else:
                partner_id = existing_partner_ids[0]
                logging.info(f"Cập nhật đối tác: {partner_name} (ID: {old_id})")
                try:
                    # Bỏ qua 'ref' khi cập nhật vì nó không thay đổi
                    update_payload = partner_data.copy()
                    del update_payload['ref']
                    self.execute_odoo_kw('res.partner', 'write', [[partner_id], update_payload])
                    self.mapping['partner'][old_id] = partner_id
                except Exception as e:
                    logging.error(f"Lỗi khi cập nhật đối tác với ID cũ '{old_id}': {e}")

        logging.info("Di chuyển Đối tác hoàn tất.")

    def migrate_products_from_sp(self):
        """
        Di chuyển sản phẩm từ tb_SP.
        """
        logging.info("Bắt đầu di chuyển Sản phẩm từ tb_SP...")
        cursor = self.sql_conn.cursor()
        
        query = "SELECT MaSP, TenSP, MaNhomCon, DVTNhap, DVTXuat FROM tb_SP WHERE TinhTrang = 1"
        cursor.execute(query)
        products_to_migrate = cursor.fetchall()
        logging.info(f"Tìm thấy {len(products_to_migrate)} sản phẩm hợp lệ trong tb_SP.")

        for row in products_to_migrate:
            old_masp, tensp, old_nhom_con, dvt_nhap, dvt_xuat = row
            old_masp_str = str(old_masp)
            tensp = tensp.strip() if tensp else f"Sản phẩm {old_masp_str}"

            existing_products = self.execute_odoo_kw('product.product', 'search', [[('default_code', '=', old_masp_str)]], {'limit': 1})
            if existing_products:
                product_data = self.execute_odoo_kw('product.product', 'read', [existing_products[0]], ['product_tmpl_id'])
                self.mapping['product'][old_masp_str] = product_data[0]['product_tmpl_id'][0]
                continue

            uom_id = self.mapping['uom'].get(str(dvt_xuat).strip().lower())
            uom_po_id = self.mapping['uom'].get(str(dvt_nhap).strip().lower(), uom_id)

            if not uom_id:
                logging.warning(f"Không tìm thấy DVT '{dvt_xuat}' cho sản phẩm '{tensp}'. Dùng UOM mặc định.")
                uom_id = 1
            if not uom_po_id:
                 uom_po_id = uom_id

            categ_id = self.mapping['category'].get(f'child_{old_nhom_con}')
            
            product_data = {
                'name': tensp,
                'default_code': old_masp_str,
                'type': 'product',
                'sale_ok': True,
                'purchase_ok': True,
                'uom_id': uom_id,
                'uom_po_id': uom_po_id,
                'categ_id': categ_id or 1,
            }

            try:
                logging.info(f"Tạo sản phẩm: {tensp} (Mã cũ: {old_masp_str})")
                new_template_id = self.execute_odoo_kw('product.template', 'create', [product_data])
                self.mapping['product'][old_masp_str] = new_template_id
            except Exception as e:
                logging.error(f"Lỗi khi tạo sản phẩm '{tensp}': {e}")
        
        logging.info("Di chuyển sản phẩm từ tb_SP hoàn tất.")

    def migrate_users(self):
        """Di chuyển người dùng từ tb_TK."""
        logging.info("Bắt đầu di chuyển Người dùng (Users)...")
        cursor = self.sql_conn.cursor()
        cursor.execute("SELECT MaTK, TenTK FROM tb_TK WHERE TinhTrang = 1")
        users_to_migrate = cursor.fetchall()
        logging.info(f"Tìm thấy {len(users_to_migrate)} người dùng từ 'tb_TK'.")

        try:
            # Lấy ID của group "Sales / User: All Documents"
            sales_group_ids = self.execute_odoo_kw('res.groups', 'search', [[('name', 'ilike', 'Sales')]])
            sales_group_id = None
            if sales_group_ids:
                # Tìm group chuẩn xác hơn
                groups_data = self.execute_odoo_kw('res.groups', 'read', [sales_group_ids], {'fields': ['name', 'full_name']})
                for group in groups_data:
                    if 'Sales / User: All Documents' in group['full_name']:
                        sales_group_id = group['id']
                        break
            if not sales_group_id:
                logging.warning("Không tìm thấy nhóm 'Sales / User: All Documents'. Người dùng mới sẽ không được thêm vào nhóm bán hàng.")
        except Exception as e:
            logging.error(f"Lỗi khi tìm nhóm Sales: {e}")
            sales_group_id = None

        for old_id, name in users_to_migrate:
            old_id_str = str(old_id)
            name = name.strip() if name else f"User {old_id_str}"
            login_email = f"user_{old_id_str}@example.com".lower() # Tạo email placeholder

            # Kiểm tra user đã tồn tại qua login chưa
            existing_user_ids = self.execute_odoo_kw('res.users', 'search', [[('login', '=', login_email)]])
            if existing_user_ids:
                logging.info(f"Người dùng '{name}' với login '{login_email}' đã tồn tại. Lấy ID.")
                self.mapping['user'][old_id_str] = existing_user_ids[0]
                continue
            
            user_data = {
                'name': name,
                'login': login_email,
            }
            if sales_group_id:
                # [(4, group_id)] thêm user vào group đã có
                user_data['groups_id'] = [(4, sales_group_id)]
            
            try:
                logging.info(f"Tạo người dùng mới: '{name}' (ID cũ: {old_id_str})")
                new_user_id = self.execute_odoo_kw('res.users', 'create', [user_data])
                self.mapping['user'][old_id_str] = new_user_id
            except Exception as e:
                logging.error(f"Lỗi khi tạo người dùng '{name}': {e}")

        logging.info("Di chuyển Người dùng hoàn tất.")



    def run_migration(self):
        """Chạy toàn bộ quy trình di chuyển dữ liệu."""
        logging.info("=== BẮT ĐẦU QUÁ TRÌNH DI CHUYỂN DỮ LIỆU ===")
        
        self._rebuild_product_mapping()
        # self.migrate_uom()
        # self.migrate_product_categories()
        # self.migrate_partners()
        
        # Chạy logic di chuyển sản phẩm và lịch sử giá mới
        # PLACEHOLDER_START_OLD_PRODUCT_MIGRATION
        
        self.migrate_users()
        self.migrate_sale_orders()
        self.migrate_debts()
        
        logging.info("=== QUÁ TRÌNH DI CHUYỂN DỮ LIỆU HOÀN TẤT ===")


    def migrate_sale_orders(self):
        """Di chuyển các đơn hàng cũ từ tb_GD và tb_CTGD."""
        logging.info("Bắt đầu di chuyển Đơn hàng (Sales Orders)...")
        cursor = self.sql_conn.cursor()

        # 1. Lấy tất cả các giao dịch bán hàng
        cursor.execute("SELECT MaGD, MaBH, ThoiGian, MaND FROM tb_GD ORDER BY ThoiGian ASC")
        sales_transactions = cursor.fetchall()
        total_orders = len(sales_transactions)
        logging.info(f"Tìm thấy {total_orders} giao dịch bán hàng trong tb_GD.")

        for i, (ma_gd, ma_bh, thoi_gian, ma_nd) in enumerate(sales_transactions):
            ma_gd = str(ma_gd).strip()
            ma_bh = str(ma_bh) if ma_bh is not None else None
            ma_nd_str = str(ma_nd) if ma_nd is not None else None

            # Idempotency check
            if ma_gd in self.mapping['order']:
                logging.info(f"[{i+1}/{total_orders}] Đơn hàng '{ma_gd}' đã được di chuyển. Bỏ qua.")
                continue

            # Tìm đối tác Odoo tương ứng bằng 'ref'
            partner_id = None
            if ma_bh:
                partner_ids = self.execute_odoo_kw('res.partner', 'search', [[('ref', '=', ma_bh)]], {'limit': 1})
                if partner_ids:
                    partner_id = partner_ids[0]

            if not partner_id:
                logging.warning(f"[{i+1}/{total_orders}] Không tìm thấy đối tác cho MaBH '{ma_bh}' của đơn hàng '{ma_gd}'. Bỏ qua đơn hàng.")
                continue
            
            # Tìm người bán hàng (salesperson) Odoo tương ứng
            user_id = self.uid # Mặc định là admin
            if ma_nd_str:
                user_id = self.mapping['user'].get(ma_nd_str, self.uid)

            # 2. Tạo Sale Order
            order_data = {
                'partner_id': partner_id,
                'state': 'sale',  # Giả định các đơn hàng cũ đều đã hoàn thành
                'date_order': thoi_gian.strftime('%Y-%m-%d %H:%M:%S'),
                'user_id': user_id,
            }
            
            try:
                logging.info(f"[{i+1}/{total_orders}] Đang tạo đơn hàng cho MaGD: {ma_gd}")
                new_order_id = self.execute_odoo_kw('sale.order', 'create', [order_data])

                # 3. Lấy và tạo các dòng đơn hàng (Sale Order Lines)
                line_cursor = self.sql_conn.cursor()
                line_query = "SELECT DVT, SL, ThanhTien FROM tb_CTGD WHERE MaGD = ?"
                line_cursor.execute(line_query, ma_gd)
                order_lines = line_cursor.fetchall()

                for line in order_lines:
                    dvt, so_luong, thanh_tien = line
                    old_product_id = dvt.strip() if dvt else None
                    if not old_product_id:
                        continue
                    
                    so_luong = float(so_luong or 0.0)
                    thanh_tien = float(thanh_tien or 0.0)
                    don_gia = thanh_tien / so_luong if so_luong else 0.0


                    # Tìm sản phẩm Odoo tương ứng
                    product_template_id = self.mapping['tygia_product'].get(old_product_id)
                    if not product_template_id:
                        logging.warning(f"Không tìm thấy sản phẩm cho DVT/MaTyGia '{old_product_id}' trong đơn hàng '{ma_gd}'. Bỏ qua dòng này.")
                        continue
                    
                    # Lấy product.product từ product.template
                    product_ids = self.execute_odoo_kw('product.product', 'search', [[('product_tmpl_id', '=', product_template_id)]])
                    if not product_ids:
                        logging.warning(f"Không tìm thấy product.product cho template ID '{product_template_id}'. Bỏ qua dòng này.")
                        continue
                    product_id = product_ids[0]

                    line_data = {
                        'order_id': new_order_id,
                        'product_id': product_id,
                        'product_uom_qty': so_luong,
                        'price_unit': don_gia,
                    }
                    self.execute_odoo_kw('sale.order.line', 'create', [line_data])
                
                # Xác nhận đơn hàng để tính toán tổng tiền
                self.execute_odoo_kw('sale.order', 'action_confirm', [[new_order_id]])
                logging.info(f"Đã tạo và xác nhận thành công đơn hàng ID: {new_order_id} (từ MaGD: {ma_gd})")
                self.mapping['order'][ma_gd] = new_order_id

            except Exception as e:
                logging.error(f"Lỗi khi di chuyển đơn hàng '{ma_gd}': {e}")

        logging.info("Di chuyển Đơn hàng (Sales Orders) hoàn tất.")


    def migrate_debts(self):
        """
        Di chuyển công nợ cũ từ tb_CTNo thành các bút toán nhật ký (account.move).
        - 'N' (Nợ) được chuyển thành Hóa đơn khách hàng (Customer Invoice).
        - 'C' (Có) được chuyển thành Hóa đơn trả hàng (Credit Note).
        """
        logging.info("Bắt đầu di chuyển Công nợ (Debts)...")
        
        # 1. Thiết lập ban đầu: Lấy các tài khoản và nhật ký cần thiết
        try:
            # Lấy nhật ký bán hàng
            sale_journal_ids = self.execute_odoo_kw('account.journal', 'search', [[('type', '=', 'sale')]], {'limit': 1})
            if not sale_journal_ids:
                logging.error("Không tìm thấy nhật ký bán hàng (Sales Journal). Dừng di chuyển công nợ.")
                return
            sale_journal_id = sale_journal_ids[0]

            # Lấy tài khoản phải thu và tài khoản doanh thu mặc định
            user_company = self.execute_odoo_kw('res.users', 'read', [self.uid], ['company_id'])[0]
            company_id = user_company['company_id'][0]
            
            receivable_account_id = self.execute_odoo_kw('ir.property', 'get', ['property_account_receivable_id', 'res.partner'])
            receivable_account_id = receivable_account_id.get('value_reference') and int(receivable_account_id['value_reference'].split(',')[1])

            income_account_ids = self.execute_odoo_kw('account.account', 'search', 
                [[('account_type', '=', 'income'), ('company_id', '=', company_id)]], {'limit': 1})
            if not income_account_ids:
                logging.error("Không tìm thấy tài khoản doanh thu. Dừng di chuyển công nợ.")
                return
            income_account_id = income_account_ids[0]

            if not receivable_account_id:
                logging.error("Không thể xác định tài khoản phải thu. Dừng di chuyển công nợ.")
                return

            logging.info(f"Sử dụng Nhật ký ID: {sale_journal_id}, TK Phải thu ID: {receivable_account_id}, TK Doanh thu ID: {income_account_id}")

        except Exception as e:
            logging.error(f"Lỗi khi thiết lập ban đầu cho di chuyển công nợ: {e}")
            return

        # 2. Lấy dữ liệu công nợ
        cursor = self.sql_conn.cursor()
        cursor.execute("SELECT MaNghoeo, MaBH, Ngay, SoTien, Loai FROM tb_CTNo ORDER BY Ngay ASC")
        debt_transactions = cursor.fetchall()
        total_debts = len(debt_transactions)
        logging.info(f"Tìm thấy {total_debts} giao dịch công nợ trong tb_CTNo.")

        if 'debt' not in self.mapping:
            self.mapping['debt'] = set()

        for i, (ma_nghoeo, ma_bh, ngay, so_tien, loai) in enumerate(debt_transactions):
            ma_bh = str(ma_bh) if ma_bh is not None else None
            loai = loai.strip().upper()
            amount = float(so_tien or 0.0)

            # Idempotency check: Tạo một key duy nhất cho mỗi giao dịch
            idempotency_key = f"{ma_nghoeo}-{ma_bh}-{ngay}-{amount}-{loai}"
            if idempotency_key in self.mapping['debt']:
                logging.info(f"[{i+1}/{total_debts}] Giao dịch công nợ '{idempotency_key}' đã được di chuyển. Bỏ qua.")
                continue

            # Tìm đối tác Odoo tương ứng bằng 'ref'
            partner_id = None
            if ma_bh:
                partner_ids = self.execute_odoo_kw('res.partner', 'search', [[('ref', '=', ma_bh)]], {'limit': 1})
                if partner_ids:
                    partner_id = partner_ids[0]

            if not partner_id:
                logging.warning(f"[{i+1}/{total_debts}] Không tìm thấy đối tác cho MaBH '{ma_bh}'. Bỏ qua giao dịch công nợ.")
                continue
            
            # Xác định loại bút toán
            if loai == 'N':
                move_type = 'out_invoice' # Hóa đơn khách hàng
                log_msg = "Hóa đơn"
            elif loai == 'C':
                move_type = 'out_refund' # Hóa đơn trả hàng
                log_msg = "Hóa đơn trả"
            else:
                logging.warning(f"[{i+1}/{total_debts}] Loại công nợ '{loai}' không xác định. Bỏ qua.")
                continue

            # 3. Tạo bút toán (account.move)
            move_data = {
                'move_type': move_type,
                'partner_id': partner_id,
                'journal_id': sale_journal_id,
                'date': ngay.strftime('%Y-%m-%d'),
                'ref': str(ma_nghoeo).strip() if ma_nghoeo else None,
                'invoice_line_ids': [(0, 0, {
                    'name': f"Di chuyển công nợ cũ (Ref: {str(ma_nghoeo).strip() if ma_nghoeo else 'N/A'})",
                    'account_id': income_account_id,
                    'price_unit': amount,
                    'quantity': 1,
                })]
            }

            try:
                logging.info(f"[{i+1}/{total_debts}] Tạo {log_msg} cho đối tác '{ma_bh}' với số tiền {amount}")
                new_move_id = self.execute_odoo_kw('account.move', 'create', [move_data])
                
                # Xác nhận bút toán
                if new_move_id:
                    self.execute_odoo_kw('account.move', 'action_post', [new_move_id])
                    logging.info(f"Đã tạo và xác nhận thành công Bút toán ID: {new_move_id} (từ MaNghoeo: {ma_nghoeo})")
                    self.mapping['debt'].add(idempotency_key)

            except Exception as e:
                logging.error(f"Lỗi khi di chuyển công nợ cho MaBH '{ma_bh}', Ref '{ma_nghoeo}': {e}")

        logging.info("Di chuyển Công nợ (Debts) hoàn tất.")


if __name__ == '__main__':
    # Chú ý: Cần điền đúng thông tin kết nối ở đầu file.
    # Chạy script này sẽ bắt đầu di chuyển dữ liệu.
    
    migrator = OdooMigrator(SQL_SERVER_CONFIG, ODOO_CONFIG)
    migrator.run_migration()

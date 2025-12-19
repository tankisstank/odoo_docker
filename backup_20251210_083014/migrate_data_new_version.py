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
            'product': {},  # Mapping cho sản phẩm từ tb_SP
            'order': {},
            'debt': set(),
        }

    def _connect_sql_server(self, config):
        """Kết nối đến SQL Server."""
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
        """Kết nối đến Odoo và kiểm tra quyền Superuser (UID=1)."""
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
        """Hàm helper để gọi API của Odoo, đảm bảo args_list và kw_dict được truyền đúng."""
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
            args_list,  # Đây phải là một list các đối số vị trí
            kw_dict     # Đây phải là một dictionary của các đối số từ khóa
        )

    def migrate_uom(self):
        """Di chuyển Đơn vị tính một cách linh động từ tb_DVT."""
        logging.info("Bắt đầu di chuyển Đơn vị tính (UoM)...")
        uom_categ_name = 'Trọng lượng Vàng'
        categ_ids = self.execute_odoo_kw('uom.category', 'search', args_list=[[('name', '=', uom_categ_name)]])
        uom_categ_id = categ_ids[0] if categ_ids else self.execute_odoo_kw('uom.category', 'create', args_list=[{'name': uom_categ_name}])
        
        # 1. Đảm bảo UoM 'chỉ' tồn tại và là UoM tham chiếu
        reference_uom_name = 'chỉ'
        existing_ref_uom_ids = self.execute_odoo_kw('uom.uom', 'search', args_list=[[('name', '=', reference_uom_name), ('category_id', '=', uom_categ_id)]])
        if not existing_ref_uom_ids:
            logging.info(f"Tạo UoM tham chiếu: {reference_uom_name.capitalize()}")
            reference_uom_id = self.execute_odoo_kw('uom.uom', 'create', args_list=[{
                'name': reference_uom_name.capitalize(),
                'category_id': uom_categ_id,
                'uom_type': 'reference',
                'ratio': 1.0,
                'rounding': 0.001
            }])
        else:
            reference_uom_id = existing_ref_uom_ids[0]
            logging.info(f"UoM tham chiếu '{reference_uom_name.capitalize()}' đã tồn tại.")
        self.mapping['uom'][reference_uom_name] = reference_uom_id

        # 2. Lấy tất cả DVT từ SQL Server
        cursor = self.sql_conn.cursor()
        cursor.execute("SELECT DISTINCT DVT FROM tb_DVT WHERE DVT IS NOT NULL")
        uoms_from_sql = {row[0].strip().lower() for row in cursor.fetchall() if row[0]}
        
        # Lấy các UoM hiện có trong Odoo để tránh tạo trùng lặp
        uom_data = self.execute_odoo_kw('uom.uom', 'search_read', args_list=[[('category_id', '=', uom_categ_id)]], kw_dict={'fields': ['name']})
        self.mapping['uom'].update({uom['name'].lower(): uom['id'] for uom in uom_data})

        # 3. Tạo các UoM còn lại từ SQL, đặt type và ratio phù hợp
        for uom_name in uoms_from_sql:
            if uom_name == reference_uom_name:
                continue

            # Kiểm tra xem UoM đã tồn tại trong Odoo chưa
            existing_uom_ids = self.execute_odoo_kw('uom.uom', 'search', args_list=[[('name', '=', uom_name.capitalize()), ('category_id', '=', uom_categ_id)]])
            if existing_uom_ids:
                self.mapping['uom'][uom_name] = existing_uom_ids[0]
                logging.info(f"UoM '{uom_name.capitalize()}' đã tồn tại (Odoo ID: {existing_uom_ids[0]}). Bỏ qua tạo mới.")
                continue

            uom_type = 'smaller'
            ratio = 1.0 
            if uom_name == 'lượng':
                uom_type = 'bigger'
                ratio = 10.0
            elif uom_name == 'gram':
                uom_type = 'smaller'
                ratio = 1 / 3.75 

            logging.info(f"Tạo UoM mới: {uom_name.capitalize()} (Type: {uom_type}, Ratio: {ratio})")
            new_uom_id = self.execute_odoo_kw('uom.uom', 'create', args_list=[{
                'name': uom_name.capitalize(),
                'category_id': uom_categ_id,
                'uom_type': uom_type,
                'ratio': ratio,
                'rounding': 0.001
            }])
            self.mapping['uom'][uom_name] = new_uom_id
        
        logging.info("Di chuyển Đơn vị tính hoàn tất.")

    def migrate_product_categories(self):
        """Di chuyển danh mục sản phẩm từ tb_NhomSP và tb_NhomCon."""
        logging.info("Bắt đầu di chuyển Danh mục sản phẩm...")
        cursor = self.sql_conn.cursor()
        cursor.execute("SELECT MaNhomSP, TenNhomSP FROM tb_NhomSP WHERE TinhTrang = 1")
        for old_id, name in cursor.fetchall():
            existing_cat = self.execute_odoo_kw('product.category', 'search', args_list=[[('name', '=', name), ('parent_id', '=', False)]])
            if not existing_cat:
                new_id = self.execute_odoo_kw('product.category', 'create', args_list=[{'name': name}])
                logging.info(f"Tạo danh mục cha: {name} (Odoo ID: {new_id})")
                self.mapping['category'][f'parent_{old_id}'] = new_id
            else:
                new_id = existing_cat[0]
                logging.info(f"Danh mục cha '{name}' đã tồn tại (Odoo ID: {new_id}).")
                self.mapping['category'][f'parent_{old_id}'] = new_id

        cursor.execute("SELECT MaNhomCon, MaNhomSP, TenNhomCon FROM tb_NhomCon WHERE TinhTrang = 1")
        for old_id, parent_old_id, name in cursor.fetchall():
            parent_new_id = self.mapping['category'].get(f'parent_{parent_old_id}')
            cat_data = {'name': name}
            if parent_new_id:
                cat_data['parent_id'] = parent_new_id

            existing_cat = self.execute_odoo_kw('product.category', 'search', args_list=[[('name', '=', name), ('parent_id', '=', parent_new_id)]])
            if not existing_cat:
                new_id = self.execute_odoo_kw('product.category', 'create', [cat_data])
                logging.info(f"Tạo danh mục con: {name} (Odoo ID: {new_id})")
                self.mapping['category'][f'child_{old_id}'] = new_id
            else:
                new_id = existing_cat[0]
                logging.info(f"Danh mục con '{name}' đã tồn tại (Odoo ID: {new_id}).")
                self.mapping['category'][f'child_{old_id}'] = new_id
        logging.info("Di chuyển Danh mục sản phẩm hoàn tất.")

    def migrate_partners(self):
        """Di chuyển đối tác từ tb_BH."""
        logging.info("Bắt đầu di chuyển Đối tác...")
        cursor = self.sql_conn.cursor()
        
        partner_details = {} 
        logging.info("Tải thông tin chi tiết đối tác từ tb_BH...")
        cursor.execute("SELECT MaBH, TenBH, DienThoai, DiaChi FROM tb_BH WHERE TinhTrang = 1")
        for old_id, name, phone, address in cursor.fetchall():
            partner_details[str(old_id)] = {
                'name': name.strip() if name else '',
                'phone': phone.strip() if phone else None,
                'street': address.strip() if address else None,
            }
        logging.info(f"Đã tải {len(partner_details)} chi tiết đối tác từ tb_BH.")

        unique_partner_ids = set()
        logging.info("Thu thập ID đối tác từ các bảng giao dịch...")
        cursor.execute("SELECT DISTINCT MaBH FROM tb_GD WHERE MaBH IS NOT NULL")
        unique_partner_ids.update({str(row[0]) for row in cursor.fetchall()})
        cursor.execute("SELECT DISTINCT MaBH FROM tb_CTNo WHERE MaBH IS NOT NULL")
        unique_partner_ids.update({str(row[0]) for row in cursor.fetchall()})
        cursor.execute("SELECT DISTINCT MaTK FROM tb_CTGD WHERE MaTK IS NOT NULL")
        unique_partner_ids.update({str(row[0]) for row in cursor.fetchall()})
        logging.info(f"Tìm thấy tổng cộng {len(unique_partner_ids)} đối tác duy nhất từ các giao dịch.")

        for old_id in unique_partner_ids:
            search_domain = [('ref', '=', old_id)]
            existing_partner_ids = self.execute_odoo_kw('res.partner', 'search', [search_domain], {'limit': 1})

            details = partner_details.get(old_id)
            if not details:
                logging.warning(f"Không tìm thấy chi tiết đối tác trong tb_BH cho MaBH '{old_id}'. Tạo đối tác chung.")
                partner_name = f"Khách hàng {old_id}"
                phone = None
                street = None
            else:
                partner_name = details['name'] or f"Khách hàng {old_id}"
                phone = details['phone']
                street = details['street']

            partner_data = {
                'name': partner_name,
                'ref': old_id,
                'phone': phone,
                'street': street,
                'is_company': False,
                'is_gold_partner': True,
            }

            if not existing_partner_ids:
                logging.info(f"Tạo đối tác mới: {partner_name} (MaBH gốc: {old_id})")
                try:
                    new_id = self.execute_odoo_kw('res.partner', 'create', [partner_data])
                    self.mapping['partner'][old_id] = new_id
                except Exception as e:
                    logging.error(f"Lỗi khi tạo đối tác với MaBH gốc '{old_id}': {e}")
            else:
                partner_id = existing_partner_ids[0]
                logging.info(f"Tìm thấy đối tác hiện có: {partner_name} (MaBH gốc: {old_id}, Odoo ID: {partner_id}). Cập nhật.")
                try:
                    update_payload = partner_data.copy()
                    del update_payload['ref']
                    self.execute_odoo_kw('res.partner', 'write', [[partner_id], update_payload])
                    self.mapping['partner'][old_id] = partner_id
                except Exception as e:
                    logging.error(f"Lỗi khi cập nhật đối tác với MaBH gốc '{old_id}': {e}")

    def migrate_users(self):
        """Di chuyển người dùng từ tb_TK."""
        logging.info("Bắt đầu di chuyển Người dùng (Users)...")
        cursor = self.sql_conn.cursor()
        cursor.execute("SELECT MaTK, TenTK FROM tb_TK WHERE TinhTrang = 1")
        
        # Lấy ID của group "Sales / User: All Documents"
        sales_group_ids = self.execute_odoo_kw('res.groups', 'search', [[('name', 'ilike', 'Sales')]])
        sales_group_id = None
        if sales_group_ids:
            groups_data = self.execute_odoo_kw('res.groups', 'read', [sales_group_ids], {'fields': ['name', 'full_name']})
            for group in groups_data:
                if 'Sales / User: All Documents' in group['full_name']:
                    sales_group_id = group['id']
                    break

        for old_id, name in cursor.fetchall():
            old_id_str = str(old_id)
            login_email = f"user_{old_id_str}@example.com".lower()
            existing_ids = self.execute_odoo_kw('res.users', 'search', [[('login', '=', login_email)]])
            if existing_ids:
                self.mapping['user'][old_id_str] = existing_ids[0]
                logging.info(f"Người dùng '{name}' với login '{login_email}' đã tồn tại (Odoo ID: {existing_ids[0]}). Bỏ qua tạo mới.")
                continue
            
            user_data = {'name': name.strip(), 'login': login_email}
            if sales_group_id:
                user_data['groups_id'] = [(4, sales_group_id)]
            try:
                new_user_id = self.execute_odoo_kw('res.users', 'create', [user_data])
                self.mapping['user'][old_id_str] = new_user_id
                logging.info(f"Đã tạo thành công người dùng: '{name}' (Odoo ID: {new_user_id}).")
            except Exception as e:
                logging.error(f"Lỗi khi tạo người dùng '{name}': {e}")
        logging.info("Di chuyển Người dùng hoàn tất.")

    def migrate_products_from_sp(self):
        """Di chuyển sản phẩm từ tb_SP."""
        logging.info("Bắt đầu di chuyển Sản phẩm từ tb_SP...")
        cursor = self.sql_conn.cursor()
        
        query = "SELECT MaSP, TenSP, MaNhomCon, DVTNhap, DVTXuat FROM tb_SP WHERE TinhTrang = 1"
        cursor.execute(query)
        
        for old_masp, tensp, old_nhom_con, dvt_nhap, dvt_xuat in cursor.fetchall():
            old_masp_str = str(old_masp)
            tensp = tensp.strip() if tensp else f"Sản phẩm {old_masp_str}"
            
            existing = self.execute_odoo_kw('product.product', 'search', [[('default_code', '=', old_masp_str)]], {'limit': 1})
            if existing:
                prod_data = self.execute_odoo_kw('product.product', 'read', [existing[0]], fields=['product_tmpl_id'])
                self.mapping['product'][old_masp_str] = prod_data[0]['product_tmpl_id'][0]
                logging.info(f"Sản phẩm '{tensp}' (Mã cũ: {old_masp_str}) đã tồn tại. Odoo ID: {prod_data[0]['product_tmpl_id'][0]}.")
                continue

            uom_id = self.mapping['uom'].get(str(dvt_xuat).strip().lower(), 1)
            uom_po_id = self.mapping['uom'].get(str(dvt_nhap).strip().lower(), uom_id)
            categ_id = self.mapping['category'].get(f'child_{old_nhom_con}', 1)
            
            product_data = {
                'name': tensp, 'default_code': old_masp_str, 'type': 'product',
                'sale_ok': True, 'purchase_ok': True, 'uom_id': uom_id,
                'uom_po_id': uom_po_id, 'categ_id': categ_id,
            }
            try:
                logging.info(f"Đang tạo sản phẩm: '{tensp}' (Mã cũ: {old_masp_str}, UoM: {dvt_xuat}, Cat: {old_nhom_con})")
                new_tmpl_id = self.execute_odoo_kw('product.template', 'create', [product_data])
                self.mapping['product'][old_masp_str] = new_tmpl_id
                logging.info(f"Đã tạo thành công sản phẩm: '{tensp}' (Odoo ID: {new_tmpl_id}).")
            except Exception as e:
                logging.error(f"Lỗi khi tạo sản phẩm '{tensp}' (Mã cũ: {old_masp_str}): {e}")
        logging.info("Di chuyển sản phẩm từ tb_SP hoàn tất.")

    def run_migration(self):
        """Chạy toàn bộ quy trình di chuyển dữ liệu."""
        logging.info("=== BẮT ĐẦU QUÁ TRÌNH DI CHUYỂN DỮ LIỆU ===")
        
        self.migrate_uom()
        self.migrate_product_categories()
        self.migrate_partners()
        self.migrate_users()
        self.migrate_products_from_sp()
        self.migrate_sale_orders()
        # self.migrate_debts()
        
        logging.info("=== QUÁ TRÌNH DI CHUYỂN DỮ LIỆU HOÀN TẤT ===")


    def migrate_sale_orders(self):
        """Di chuyển các đơn hàng cũ từ tb_GD và tb_CTGD."""
        logging.info("Bắt đầu di chuyển Đơn hàng (Sales Orders)...")
        cursor = self.sql_conn.cursor()

        cursor.execute("SELECT MaGD, MaBH, ThoiGian, MaND FROM tb_GD ORDER BY ThoiGian ASC")
        sales_transactions = cursor.fetchall()
        logging.info(f"Tìm thấy {len(sales_transactions)} giao dịch bán hàng trong tb_GD.")

        for i, (ma_gd, ma_bh, thoi_gian, ma_nd) in enumerate(sales_transactions):
            ma_gd_str = str(ma_gd).strip()
            ma_bh_str = str(ma_bh) if ma_bh is not None else None
            ma_nd_str = str(ma_nd) if ma_nd is not None else None

            if ma_gd_str in self.mapping['order']:
                logging.info(f"[{i+1}/{len(sales_transactions)}] Đơn hàng với MaGD '{ma_gd_str}' đã được di chuyển. Bỏ qua.")
                continue

            partner_id = None
            if ma_bh_str:
                partner_ids = self.execute_odoo_kw('res.partner', 'search', [[('ref', '=', ma_bh_str)]], {'limit': 1})
                if partner_ids:
                    partner_id = partner_ids[0]

            if not partner_id:
                logging.warning(f"[{i+1}/{len(sales_transactions)}] Không tìm thấy đối tác cho MaBH '{ma_bh_str}' của đơn hàng '{ma_gd_str}'. Bỏ qua đơn hàng.")
                continue
            
            user_id = self.mapping['user'].get(ma_nd_str, self.uid)

            order_data = {
                'partner_id': partner_id,
                'state': 'sale',
                'date_order': thoi_gian.strftime('%Y-%m-%d %H:%M:%S'),
                'user_id': user_id,
                'name': f"SO/{ma_gd_str}"
            }
            
            try:
                logging.info(f"[{i+1}/{len(sales_transactions)}] Đang tạo đơn hàng cho MaGD: {ma_gd_str}")
                new_order_id = self.execute_odoo_kw('sale.order', 'create', [order_data])
                self.mapping['order'][ma_gd_str] = new_order_id # Store the new Odoo order ID
                
                line_cursor = self.sql_conn.cursor()
                line_query = "SELECT MaSP, SL, ThanhTien FROM tb_CTGD WHERE MaGD = ?"
                line_cursor.execute(line_query, ma_gd)

                for line_idx, (old_masp, so_luong, thanh_tien) in enumerate(line_cursor.fetchall()):
                    if not old_masp: 
                        logging.warning(f"[{i+1}/{len(sales_transactions)}] Dòng đơn hàng {line_idx+1} của '{ma_gd_str}' thiếu MaSP. Bỏ qua.")
                        continue
                    old_masp_str = str(old_masp).strip()
                    product_tmpl_id = self.mapping['product'].get(old_masp_str)
                    
                    if not product_tmpl_id:
                        logging.warning(f"[{i+1}/{len(sales_transactions)}] Không tìm thấy product.template cho MaSP '{old_masp_str}' trong đơn hàng '{ma_gd_str}'. Bỏ qua dòng này.")
                        continue
                    
                    product_ids = self.execute_odoo_kw('product.product', 'search', [[('product_tmpl_id', '=', product_tmpl_id)]])
                    if not product_ids: 
                        logging.warning(f"[{i+1}/{len(sales_transactions)}] Không tìm thấy product.product cho template ID '{product_tmpl_id}' (MaSP: {old_masp_str}). Bỏ qua dòng này.")
                        continue
                    
                    so_luong_f = float(so_luong or 0.0)
                    price_unit = (float(thanh_tien or 0.0) / so_luong_f) if so_luong_f else 0.0

                    self.execute_odoo_kw('sale.order.line', 'create', [{'order_id': new_order_id, 'product_id': product_ids[0], 'product_uom_qty': so_luong_f, 'price_unit': price_unit}])
                
                logging.info(f"[{i+1}/{len(sales_transactions)}] Xác nhận đơn hàng Odoo ID: {new_order_id} (MaGD: {ma_gd_str})")
                self.execute_odoo_kw('sale.order', 'action_confirm', [[new_order_id]])
            except Exception as e:
                logging.error(f"Lỗi khi di chuyển đơn hàng '{ma_gd_str}': {e}")
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

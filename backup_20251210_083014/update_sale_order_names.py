# -*- coding: utf-8 -*-
import xmlrpc.client
import logging

# Cấu hình kết nối Odoo
ODOO_CONFIG = {
    'url': 'http://localhost:8069',
    'db': 'odoo_test',
    'username': 'admin',  # Email/login của tài khoản Admin gốc
    'password': 'abc123'  # Mật khẩu của tài khoản Admin gốc
}

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def update_order_names():
    """Cập nhật tên các đơn hàng từ SO/[MaGD] sang QTU/[MaGD]."""
    try:
        common = xmlrpc.client.ServerProxy(f'{ODOO_CONFIG["url"]}/xmlrpc/2/common')
        uid = common.authenticate(ODOO_CONFIG['db'], ODOO_CONFIG['username'], ODOO_CONFIG['password'], {})
        if not uid:
            logging.error("Xác thực Odoo thất bại.")
            return
        
        models = xmlrpc.client.ServerProxy(f'{ODOO_CONFIG["url"]}/xmlrpc/2/object')
        
        logging.info("Bắt đầu cập nhật tên đơn hàng...")
        
        # Tìm tất cả các đơn hàng có tên bắt đầu bằng SO/
        order_ids = models.execute_kw(
            ODOO_CONFIG['db'], uid, ODOO_CONFIG['password'],
            'sale.order', 'search',
            [[('name', 'like', 'SO/')]]
        )
        
        if not order_ids:
            logging.info("Không tìm thấy đơn hàng nào cần cập nhật.")
            return

        orders = models.execute_kw(
            ODOO_CONFIG['db'], uid, ODOO_CONFIG['password'],
            'sale.order', 'read',
            [order_ids],
            {'fields': ['name']}
        )
        
        count = 0
        for order in orders:
            old_name = order['name']
            if old_name.startswith('SO/'):
                new_name = old_name.replace('SO/', 'QTU/', 1)
                try:
                    models.execute_kw(
                        ODOO_CONFIG['db'], uid, ODOO_CONFIG['password'],
                        'sale.order', 'write',
                        [[order['id']], {'name': new_name}]
                    )
                    count += 1
                    # logging.info(f"Đã đổi tên: {old_name} -> {new_name}")
                except Exception as e:
                    logging.error(f"Lỗi khi đổi tên đơn hàng ID {order['id']} ({old_name}): {e}")
        
        logging.info(f"Đã cập nhật thành công {count}/{len(orders)} đơn hàng.")

    except Exception as e:
        logging.error(f"Lỗi kết nối hoặc thực thi: {e}")

if __name__ == "__main__":
    update_order_names()

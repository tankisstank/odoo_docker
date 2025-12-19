# -*- coding: utf-8 -*-
import xmlrpc.client
import pyodbc
import logging

# Cấu hình kết nối SQL Server
SQL_SERVER_CONFIG = {
    'server': '100.71.131.103,1433',
    'database': 'DSQL',
    'username': 'sa',
    'password': 'Dbtruong@',
}

# Cấu hình kết nối Odoo
ODOO_CONFIG = {
    'url': 'https://qlv.loophole.site',
    'db': 'odoo', # Thường là 'odoo' hoặc tên db bạn đã tạo. Tôi sẽ thử 'odoo' hoặc 'odoo_test' nếu lỗi.
    'username': 'c0508g@gmail.com',
    'password': 'abc123'
}

logging.basicConfig(level=logging.INFO, format='%(message)s')

def verify_data():
    # 1. Kết nối SQL Server
    try:
        # Cú pháp chuẩn hơn cho cổng: server,port
        server_str = SQL_SERVER_CONFIG['server'] 
        # Nếu server_str chưa có tcp: thì thêm vào (để chắc chắn)
        if not server_str.startswith('tcp:'):
            server_str = f"tcp:{server_str}"
            
        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={server_str};"
            f"DATABASE={SQL_SERVER_CONFIG['database']};"
            f"UID={SQL_SERVER_CONFIG['username']};"
            f"PWD={SQL_SERVER_CONFIG['password']};"
        )
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        logging.info("Kết nối SQL Server thành công.")
    except Exception as e:
        logging.error(f"Lỗi kết nối SQL Server: {e}")
        return

    # 2. Kết nối Odoo
    try:
        common = xmlrpc.client.ServerProxy(f'{ODOO_CONFIG["url"]}/xmlrpc/2/common')
        # Thử xác thực với DB 'odoo' trước, nếu sai thử 'odoo_test' (hoặc lấy từ list db nếu có thể)
        # Giả định DB tên là 'odoo' dựa trên URL production, nhưng context cũ là 'odoo_test'. 
        # Tôi sẽ thử 'odoo_test' trước vì script migration dùng cái đó.
        db_name = 'odoo_test' 
        uid = common.authenticate(db_name, ODOO_CONFIG['username'], ODOO_CONFIG['password'], {})
        if not uid:
            db_name = 'odoo' # Thử lại với 'odoo'
            uid = common.authenticate(db_name, ODOO_CONFIG['username'], ODOO_CONFIG['password'], {})
        
        if not uid:
            logging.error("Xác thực Odoo thất bại. Kiểm tra lại DB/User/Pass.")
            return
            
        models = xmlrpc.client.ServerProxy(f'{ODOO_CONFIG["url"]}/xmlrpc/2/object')
        logging.info(f"Kết nối Odoo thành công (DB: {db_name}, UID: {uid}).")
    except Exception as e:
        logging.exception("Lỗi kết nối Odoo:")
        return

    # 3. Lấy 10 đơn hàng từ ngày 26/11/2025
    print("\n" + "="*80)
    print(f"{ 'MaGD':<10} | {'SQL Qty':<10} | {'SQL Price':<12} | {'Odoo Qty':<10} | {'Odoo Price':<12} | {'Khớp?'}")
    print("="*80)

    cursor.execute("SELECT TOP 10 MaGD FROM tb_GD WHERE ThoiGian >= '2025-11-26 00:00:00' AND ThoiGian < '2025-11-27 00:00:00' ORDER BY ThoiGian ASC")
    recent_orders = [str(row.MaGD) for row in cursor.fetchall()]

    for ma_gd in recent_orders:
        # Lấy chi tiết từ SQL
        cursor.execute("SELECT TTLThuc, TTL, HeSoQD2, LoaiCTGD, MaSP FROM tb_CTGD WHERE MaGD = ?", ma_gd)
        sql_lines = cursor.fetchall()
        
        # Lấy chi tiết từ Odoo (Cập nhật tìm kiếm theo QTU/)
        odoo_orders = models.execute_kw(db_name, uid, ODOO_CONFIG['password'],
            'sale.order', 'search_read',
            [[('name', '=', f"QTU/{ma_gd}")]],
            {'fields': ['id', 'order_line']}
        )
        
        if not odoo_orders:
            # Thử tìm lại với SO/ nếu chưa đổi hết
            odoo_orders = models.execute_kw(db_name, uid, ODOO_CONFIG['password'],
                'sale.order', 'search_read',
                [[('name', '=', f"SO/{ma_gd}")]],
                {'fields': ['id', 'order_line']}
            )

        if not odoo_orders:
            print(f"{ma_gd:<10} | {'KHÔNG TÌM THẤY TRONG ODOO':<50}")
            continue
            
        odoo_order_id = odoo_orders[0]['id']
        odoo_line_ids = odoo_orders[0]['order_line']
        
        odoo_lines = models.execute_kw(db_name, uid, ODOO_CONFIG['password'],
            'sale.order.line', 'read',
            [odoo_line_ids],
            {'fields': ['product_uom_qty', 'price_unit', 'product_id']} # product_id trả về (id, name)
        )

        # So sánh từng dòng (Logic khớp đơn giản: so tổng số lượng và giá trị trung bình hoặc so từng dòng nếu số lượng dòng ít)
        # Ở đây ta in ra để người dùng tự đánh giá cho trực quan
        print(f"--- Đơn hàng {ma_gd} ---")
        
        # In dòng SQL
        print("  [SQL Server]")
        sql_total_val = 0
        for row in sql_lines:
            qty = float(row.TTLThuc or row.TTL or 0)
            price = float(row.HeSoQD2 or 0)
            loai = row.LoaiCTGD
            if loai == -1: price = -price # Trade-in
            val = qty * price
            sql_total_val += val
            print(f"    MaSP: {row.MaSP:<5} | Qty: {qty:<10.4f} | Price: {price:<12.2f} | Val: {val:,.2f}")

        # In dòng Odoo
        print("  [Odoo]")
        odoo_total_val = 0
        for line in odoo_lines:
            qty = line['product_uom_qty']
            price = line['price_unit']
            val = qty * price
            odoo_total_val += val
            prod_name = line['product_id'][1] if line['product_id'] else 'N/A'
            print(f"    Prod: {prod_name[:15]:<15} | Qty: {qty:<10.4f} | Price: {price:<12.2f} | Val: {val:,.2f}")
            
        diff = abs(sql_total_val - odoo_total_val)
        status = "OK" if diff < 100 else f"LỆCH {diff:,.2f}"
        print(f"  => Tổng SQL: {sql_total_val:,.2f} | Tổng Odoo: {odoo_total_val:,.2f} | Trạng thái: {status}")
        print("-" * 80)

if __name__ == "__main__":
    verify_data()

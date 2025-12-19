# -*- coding: utf-8 -*-
import pyodbc
import pandas as pd
import logging

# --- Cấu hình ---
SQL_SERVER_CONFIG = {
    'server': 'localhost',
    'database': 'DSQL',
    'username': 'sa',
    'password': 'Dbtruong@',
    'driver': '{ODBC Driver 17 for SQL Server}'
}

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def check_table_counts():
    """
    Kiểm tra số lượng bản ghi trong các bảng quan trọng.
    """
    logging.info("--- Bắt đầu kiểm tra số lượng bản ghi ---")
    try:
        conn_str = (
            f"DRIVER={SQL_SERVER_CONFIG['driver']};"
            f"SERVER={SQL_SERVER_CONFIG['server']};"
            f"DATABASE={SQL_SERVER_CONFIG['database']};"
            f"UID={SQL_SERVER_CONFIG['username']};"
            f"PWD={SQL_SERVER_CONFIG['password']};"
        )
        conn = pyodbc.connect(conn_str)
        logging.info("Kiểm tra số lượng: Kết nối SQL Server thành công.")
    except Exception as e:
        logging.error(f"Kiểm tra số lượng: Lỗi kết nối SQL Server: {e}")
        return

    tables_to_check = ['tb_TK', 'tb_GD', 'tb_CTNo']
    try:
        for table in tables_to_check:
            query = f"SELECT COUNT(*) FROM {table}"
            # Sử dụng pandas để thực thi và lấy kết quả
            count = pd.read_sql_query(query, conn).iloc[0, 0]
            if count == 0:
                logging.error(f">>> LỖI NGHIÊM TRỌNG: Bảng '{table}' không có dữ liệu (0 bản ghi).")
            else:
                logging.info(f"Bảng '{table}' có {count} bản ghi.")

    except Exception as e:
        logging.error(f"Lỗi trong quá trình đếm bản ghi: {e}")
    finally:
        conn.close()
        logging.info("Kiểm tra số lượng: Đã đóng kết nối SQL Server.")


if __name__ == '__main__':
    logging.info("=== BẮT ĐẦU QUÁ TRÌNH KIỂM TRA DỮ LIỆU NGUỒN ===")
    check_table_counts()
    logging.info("=== HOÀN TẤT ===")
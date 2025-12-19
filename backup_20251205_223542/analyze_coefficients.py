import pyodbc

def analyze_coefficients():
    try:
        conn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER=c0508g-46684.portmap.host,46684;DATABASE=DSQL;UID=sa;PWD=Dbtruong@')
        cursor = conn.cursor()
        
        # Truy vấn kết hợp CTGD và NhomCon để xem định nghĩa của từng hệ số
        query = """
        SELECT TOP 30 
            c.MaGD, 
            c.MaSP, 
            n.TenNhomCon,
            c.DVT as DVT_Goc,
            c.TTLThuc as SL_Thuc,
            
            -- Cặp giá trị 1
            c.HeSoQD1, 
            n.DVTQDTheoHeSoQD1 as DVT_Dich_1, -- Đích đến của hệ số 1 là gì? (Vàng hay Tiền?)
            (c.TTLThuc * c.HeSoQD1) as GiaTri_QD1, -- Thử tính
            
            -- Cặp giá trị 2
            c.HeSoQD2, 
            n.DVTQDTheoHeSoQD2 as DVT_Dich_2, -- Đích đến của hệ số 2 là gì?
            (c.TTLThuc * c.HeSoQD2) as GiaTri_QD2, -- Thử tính
            
            c.TTLQD as TTLQD_Goc, -- Giá trị hệ thống lưu
            c.DVTQD as DVTQD_Goc
            
        FROM tb_CTGD c
        LEFT JOIN tb_NhomCon n ON c.MaNhomCon = n.MaNhomCon
        WHERE c.TTLThuc <> 0 -- Chỉ lấy dòng có số lượng
        ORDER BY c.MaGD DESC
        """
        
        print(f"{'MaGD':<8} | {'Nhóm':<10} | {'DVT':<5} | {'SL':<6} | {'HS_1':<7} -> {'DVT_1':<5} | {'HS_2':<10} -> {'DVT_2':<5} | {'TTLQD (DB)':<12} | {'DVT_Chot':<5}")
        print("-" * 120)
        
        cursor.execute(query)
        for row in cursor.fetchall():
            ma_gd = str(row.MaGD)
            nhom = str(row.TenNhomCon)[:10]
            dvt = str(row.DVT_Goc)
            sl = float(row.SL_Thuc or 0)
            
            hs1 = float(row.HeSoQD1 or 0)
            dvt1 = str(row.DVT_Dich_1)
            
            hs2 = float(row.HeSoQD2 or 0)
            dvt2 = str(row.DVT_Dich_2)
            
            ttl_db = float(row.TTLQD_Goc or 0)
            dvt_chot = str(row.DVTQD_Goc)

            print(f"{ma_gd:<8} | {nhom:<10} | {dvt:<5} | {sl:<6.2f} | {hs1:<7.4f} -> {dvt1:<5} | {hs2:<10.0f} -> {dvt2:<5} | {ttl_db:<12.0f} | {dvt_chot:<5}")

            # Phân tích logic ngay tại dòng
            logic = ""
            if dvt_chot == dvt2 and abs(sl * hs2 - ttl_db) < 10:
                logic = "=> Chốt theo Cặp 2 (Thường là Tiền)"
            elif dvt_chot == dvt1 and abs(sl * hs1 - ttl_db) < 0.1:
                logic = "=> Chốt theo Cặp 1 (Thường là Vàng)"
            
            if logic:
                print(f"         {logic}")
            print("-" * 120)

    except Exception as e:
        print(f"Lỗi: {e}")

if __name__ == "__main__":
    analyze_coefficients()

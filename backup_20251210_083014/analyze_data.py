import pyodbc

def analyze_debt_data():
    try:
        conn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER=c0508g-46684.portmap.host,46684;DATABASE=DSQL;UID=sa;PWD=Dbtruong@')
        cursor = conn.cursor()
        
        query = """
        SELECT TOP 20 
            MaCTNo, MaGD, MaBH, ThoiGian, 
            HinhThucNo, 
            TTL, DVT, 
            TTLQD, DVTQD,
            TienBu, 
            MaNghoeo
        FROM tb_CTNo
        ORDER BY ThoiGian DESC
        """
        
        print(f"{'MaCTNo':<8} | {'MaGD':<8} | {'MaBH':<6} | {'HinhThuc':<10} | {'TTL':<10} | {'DVT':<5} | {'TTLQD':<15} | {'DVTQD':<5}")
        print("-" * 100)
        
        cursor.execute(query)
        for row in cursor.fetchall():
            print(f"{str(row.MaCTNo):<8} | {str(row.MaGD):<8} | {str(row.MaBH):<6} | {str(row.HinhThucNo):<10} | {float(row.TTL or 0):<10.3f} | {str(row.DVT):<5} | {float(row.TTLQD or 0):<15.2f} | {str(row.DVTQD):<5}")

    except Exception as e:
        print(f"Lỗi: {e}")

if __name__ == "__main__":
    analyze_debt_data()

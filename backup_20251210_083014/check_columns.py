import pyodbc

def check_columns():
    try:
        conn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER=c0508g-46684.portmap.host,46684;DATABASE=DSQL;UID=sa;PWD=Dbtruong@')
        cursor = conn.cursor()
        print("--- Cấu trúc bảng tb_CTNo ---")
        cursor.execute("SELECT TOP 1 * FROM tb_CTNo")
        columns = [column[0] for column in cursor.description]
        print(columns)
    except Exception as e:
        print(f"Lỗi: {e}")

if __name__ == "__main__":
    check_columns()


# file: odoo_behavior_check.py
import xmlrpc.client

ODOO_CONFIG = {
    'url': 'http://localhost:8069',
    'db': 'qlv_new',
    'username': 'c0508g@gmail.com',
    'password': 'abc123',
}

def rpc():
    common = xmlrpc.client.ServerProxy(f"{ODOO_CONFIG['url']}/xmlrpc/2/common")
    uid = common.authenticate(ODOO_CONFIG['db'], ODOO_CONFIG['username'], ODOO_CONFIG['password'], {})
    if not uid:
        raise RuntimeError("Không đăng nhập được Odoo – kiểm tra username/password/URL")
    models = xmlrpc.client.ServerProxy(f"{ODOO_CONFIG['url']}/xmlrpc/2/object")
    return uid, models

def search_names(q, limit=20):
    uid, models = rpc()
    res = models.execute_kw(
        ODOO_CONFIG['db'], uid, ODOO_CONFIG['password'],
        'res.partner', 'search_read',
        [[('display_name', 'ilike', q)]],
        {'fields': ['id', 'display_name'], 'limit': limit}
    )
    return res

def log(msg):
    with open("verify_result.txt", "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg)

def show(title, rows):
    log(f"\n--- {title} ---")
    if not rows:
        log("(Không có kết quả)")
    else:
        for r in rows:
            log(f"{r['id']:>6}  {r['display_name']}")

def contains_name(rows, name):
    target = (name or "").strip().lower()
    for r in rows:
        if (r.get('display_name') or '').strip().lower() == target:
            return True
    return False

if __name__ == "__main__":
    # Các test cơ bản
    res_dung = search_names("dung", limit=50)
    res_du   = search_names("du",   limit=50)
    res_dung_accent = search_names("Dũng", limit=50)

    show("ILIKE 'dung'", res_dung)
    show("ILIKE 'du'",   res_du)
    show("ILIKE 'Dũng'", res_dung_accent)

    # Suy luận unaccent:
    # Nếu 'Dũng' xuất hiện trong kết quả khi tìm 'dung' -> unaccent đang hoạt động.
    has_dung_on_dung = any("dũng" in (r['display_name'] or '').lower() for r in res_dung)

    log("\n==> Kết luận:")
    if has_dung_on_dung:
        log("- Có vẻ DB đã bật unaccent và Odoo đang áp dụng accent-insensitive cho ILIKE (tìm 'dung' ra 'Dũng').")
        log("- Bạn có thể tối ưu thêm bằng pg_trgm + index để tăng tốc fuzzy/autocomplete.")
    else:
        log("- Tìm 'dung' KHÔNG ra 'Dũng' -> nhiều khả năng extension 'unaccent' CHƯA hoạt động trong DB hoặc Odoo chưa nhận.")
        log("  Hãy thực hiện các bước sau:")
        log("  1) Bật extension trong DB Odoo:")
        log("     CREATE EXTENSION IF NOT EXISTS unaccent;")
        log("  2) Khởi động lại Odoo service (để ORM nhận biết).")
        log("  3) Thử lại script này.")
        log("  4) Nếu vẫn không được, cân nhắc cài OCA base_search_unaccent hoặc ghi đè name_search() dùng trường 'không dấu'.")

    # Gợi ý fuzzy
    print("\n==> Khuyến nghị thêm (fuzzy):")
    print("- Bật pg_trgm và tạo index trigram cho các trường tên:")
    print("  CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    print("  CREATE INDEX IF NOT EXISTS res_partner_display_name_trgm_gin")
    print("  ON res_partner USING gin (display_name gin_trgm_ops);")

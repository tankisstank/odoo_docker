import xmlrpc.client

url = "https://qlv.loophole.site/"
db = "qlv"
username = "c0508g@gmail.com"
password = "abc123"

try:
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, username, password, {})
    
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
    
    # Tìm sản phẩm 760
    ids = models.execute_kw(db, uid, password, 'product.product', 'search', [[['default_code', '=', '760']]])
    print(f"Product 760 IDs: {ids}")
    
    if ids:
        data = models.execute_kw(db, uid, password, 'product.product', 'read', [ids], {'fields': ['name', 'uom_id', 'categ_id']})
        print("Data:", data)
        
        # Tìm UoM
        uom_id = data[0]['uom_id'][0]
        uom_data = models.execute_kw(db, uid, password, 'uom.uom', 'read', [[uom_id]], {'fields': ['name', 'category_id']})
        print("UoM Data:", uom_data)

except Exception as e:
    print("Lỗi:", e)

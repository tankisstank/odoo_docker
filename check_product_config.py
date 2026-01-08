import xmlrpc.client

url = "http://localhost:8069"
db = "qlv_new"
username = "c0508g@gmail.com"
password = "abc123"

print(f"Connecting to {url}...")
try:
    common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
    uid = common.authenticate(db, username, password, {})
    models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
    print(f"Connected. UID: {uid}")

    # Check Money Products
    print("\n--- CHECKING MONEY PRODUCTS ---")
    vals = models.execute_kw(db, uid, password, 'product.product', 'search_read', 
        [[['categ_id.name', 'in', ['Tiền', 'Money', 'Ngoại tệ']]]], 
        {'fields': ['name', 'detailed_type', 'type', 'route_ids']})
    
    for p in vals:
        print(f"Product: {p['name']}")
        print(f"  Type: {p.get('detailed_type') or p.get('type')}")
        print(f"  Routes: {p['route_ids']}")

except Exception as e:
    print(f"Error: {e}")


import xmlrpc.client

url = 'http://localhost:8069'
db = 'qlv_new'
username = 'c0508g@gmail.com'
password = 'abc123'

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

print("\n--- FIND ROUTES ---")
routes = models.execute_kw(db, uid, password, 'stock.route', 'search_read', [[]], {'fields': ['id', 'name']})
for r in routes:
    print(f"{r['id']}: {r['name']}")

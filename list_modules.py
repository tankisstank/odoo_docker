import xmlrpc.client

url = "http://localhost:8069"
db = "qlv_new"
username = "c0508g@gmail.com"
password = "abc123"

common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")

print(f"Connected to {db} as UID {uid}")

modules = models.execute_kw(db, uid, password, 'ir.module.module', 'search_read', [[['state', '=', 'installed']]], {'fields': ['name']})
print("Installed Modules:")
for m in modules:
    print(m['name'])

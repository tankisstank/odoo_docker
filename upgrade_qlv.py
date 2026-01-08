import xmlrpc.client

url = "http://localhost:8069"
db = "qlv_new"
username = "c0508g@gmail.com"
password = "abc123"

common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")

print(f"Connected to {db} as UID {uid}")

# Find Module
mids = models.execute_kw(db, uid, password, 'ir.module.module', 'search', [[['name', '=', 'qlv']]])
if not mids:
    print("Module 'qlv' NOT FOUND!")
    exit(1)

print(f"Found QLV Module ID: {mids[0]}")

# Trigger Upgrade
print("Triggering Upgrade...")
models.execute_kw(db, uid, password, 'ir.module.module', 'button_immediate_upgrade', [mids])
print("Upgrade Triggered! (Connection might close)")

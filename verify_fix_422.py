import xmlrpc.client
import sys

# Redirect output
sys.stdout = open('verify_fix_422_output.txt', 'w', encoding='utf-8')

url = "http://localhost:8069"
db = "qlv_new"
username = "c0508g@gmail.com"
password = "abc123"

common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object", allow_none=True)

print(f"Connected as UID {uid}")

def verify_guard_clause(name_old):
    print(f"\n--- VERIFYING GUARD CLAUSE: {name_old} ---")
    oids_old = models.execute_kw(db, uid, password, 'sale.order', 'search', [[['name', '=', name_old]]])
    if not oids_old:
        print("Order not found.")
        return
    oid_old = oids_old[0]
    
    # Create Dummy Target
    pid = models.execute_kw(db, uid, password, 'res.partner', 'search', [[]], {'limit': 1})[0]
    oid_new = models.execute_kw(db, uid, password, 'sale.order', 'create', [{'partner_id': pid}])
    
    print(f"Attempting Settle from {name_old} to New Order (ID {oid_new})...")
    res = models.execute_kw(db, uid, password, 'sale.order', 'action_settle_debt', [oid_old], {'context': {'target_order_id': oid_new}})
    
    if isinstance(res, dict) and res.get('type') == 'ir.actions.act_window':
        print("SUCCESS: Guard Clause Triggered (Redirect returned).")
        print(f" - Res Model: {res.get('res_model')}")
        print(f" - Res ID: {res.get('res_id')}")
    elif res is True:
        print("FAILURE: Guard Clause IGNORED (Returned True).")
    else:
        print(f"UNKNOWN RESULT: {res}")

verify_guard_clause("QTU/00422")

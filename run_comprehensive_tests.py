import xmlrpc.client
import time

url = "http://localhost:8069"
db = "qlv_new"
username = "c0508g@gmail.com"
password = "abc123"

common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")

print(f"Connected to {db} as UID {uid}")

def log(msg, level="INFO"):
    print(f"[{level}] {msg}")

def get_product(name_pattern):
    ids = models.execute_kw(db, uid, password, 'product.product', 'search', [[['name', 'ilike', name_pattern]]], {'limit': 1})
    return ids[0] if ids else None

def get_partner():
    return models.execute_kw(db, uid, password, 'res.partner', 'search', [[]], {'limit': 1})[0]

# --- SCENARIOS ---

def test_1_trade_in_split():
    log("Running Test 1: Trade-in Split (Receipts)...")
    p1 = get_product('3 số')
    p2 = get_product('4 số')
    partner = get_partner()
    
    vals = {
        'partner_id': partner,
        'order_line': [
            (0, 0, {'product_id': p1, 'product_uom_qty': 1, 'price_unit': -100, 'is_trade_in': True, 'sequence': 10}),
            (0, 0, {'product_id': p2, 'product_uom_qty': 1, 'price_unit': -200, 'is_trade_in': True, 'sequence': 11})
        ]
    }
    
    oid = models.execute_kw(db, uid, password, 'sale.order', 'create', [vals])
    name = models.execute_kw(db, uid, password, 'sale.order', 'read', [oid], {'fields': ['name']})[0]['name']
    log(f"Created Order {name}")
    
    models.execute_kw(db, uid, password, 'sale.order', 'action_confirm', [oid])
    
    # Check Pickings
    pickings = models.execute_kw(db, uid, password, 'stock.picking', 'search_read', 
        [[['origin', 'ilike', name], ['picking_type_code', '=', 'incoming']]], {'fields': ['name', 'origin', 'state']})
    
    count = len(pickings)
    log(f"Found {count} Receipt Pickings.")
    
    if count >= 2:
        # Check Origins
        origins = set(p['origin'] for p in pickings)
        if len(origins) >= 2:
             log("SUCCESS: Pickings are split with unique origins.", "PASS")
             return True
        else:
             log("FAIL: Pickings exist but share origins?", "FAIL")
             return False
    else:
        log("FAIL: Pickings matched/merged.", "FAIL")
        return False

def test_2_sell_split():
    log("\nRunning Test 2: Sell Split (Deliveries)...")
    p1 = get_product('3 số')
    p2 = get_product('4 số')
    partner = get_partner()
    
    vals = {
        'partner_id': partner,
        'order_line': [
            (0, 0, {'product_id': p1, 'product_uom_qty': 1, 'price_unit': 100, 'is_trade_in': False, 'sequence': 10}),
            (0, 0, {'product_id': p2, 'product_uom_qty': 1, 'price_unit': 200, 'is_trade_in': False, 'sequence': 11})
        ]
    }
    
    oid = models.execute_kw(db, uid, password, 'sale.order', 'create', [vals])
    name = models.execute_kw(db, uid, password, 'sale.order', 'read', [oid], {'fields': ['name']})[0]['name']
    
    models.execute_kw(db, uid, password, 'sale.order', 'action_confirm', [oid])
    
    pickings = models.execute_kw(db, uid, password, 'stock.picking', 'search_read', 
        [[['origin', 'ilike', name], ['picking_type_code', '=', 'outgoing']]], {'fields': ['name']})
        
    count = len(pickings)
    if count >= 2:
        log("SUCCESS: Delivery Pickings are split.", "PASS")
        return True
    else:
        log(f"FAIL: Found {count} delivery pickings.", "FAIL")
        return False

def test_3_mixed_money():
    log("\nRunning Test 3: Mixed Order (Sell + Money)...")
    p_gold = get_product('3 số')
    p_money = get_product('Tiền Việt Nam')
    partner = get_partner()
    
    vals = {
        'partner_id': partner,
        'order_line': [
            (0, 0, {'product_id': p_gold, 'product_uom_qty': 1, 'price_unit': 1000, 'is_trade_in': False}),
            (0, 0, {'product_id': p_money, 'product_uom_qty': 1, 'price_unit': -1000, 'is_trade_in': True, 'is_auto_balance': True})
        ]
    }
    
    oid = models.execute_kw(db, uid, password, 'sale.order', 'create', [vals])
    name = models.execute_kw(db, uid, password, 'sale.order', 'read', [oid], {'fields': ['name']})[0]['name']
    models.execute_kw(db, uid, password, 'sale.order', 'action_confirm', [oid])
    
    pickings = models.execute_kw(db, uid, password, 'stock.picking', 'search_read', 
        [[['origin', 'ilike', name]]], {'fields': ['name', 'picking_type_code']})
        
    # Expect: 1 Out (Gold), 1 In (Money, since Storable)
    types = [p['picking_type_code'] for p in pickings]
    if 'outgoing' in types and 'incoming' in types:
        log("SUCCESS: Mixed Pickings generated correctly (Gold Out, Money In).", "PASS")
        return True
    else:
        log(f"FAIL: Missing pickings. Types found: {types}", "FAIL")
        return False

def test_4_deferred_debt():
    log("\nRunning Test 4: Deferred Debt Settlement...")
    p_gold = get_product('3 số')
    partner = get_partner()
    
    # Setup Old Order (Customer owes 1 Gold)
    # Sell 1 Gold
    vals = {
        'partner_id': partner,
        'order_line': [(0, 0, {'product_id': p_gold, 'product_uom_qty': 1, 'price_unit': 5000, 'is_trade_in': False})]
    }
    old_id = models.execute_kw(db, uid, password, 'sale.order', 'create', [vals])
    old_name = models.execute_kw(db, uid, password, 'sale.order', 'read', [old_id], {'fields': ['name']})[0]['name']
    models.execute_kw(db, uid, password, 'sale.order', 'action_confirm', [old_id])
    
    # Validate Delivery to establish debt
    pickings = models.execute_kw(db, uid, password, 'stock.picking', 'search', [[['origin', 'ilike', old_name]]])
    for pid in pickings:
         try:
            # 1. Check Availability
            models.execute_kw(db, uid, password, 'stock.picking', 'action_assign', [[pid]])
            
            # 2. Set Qty Done
            p_data = models.execute_kw(db, uid, password, 'stock.picking', 'read', [[pid]], {'fields': ['move_ids_without_package']})[0]
            m_ids = p_data['move_ids_without_package']
            
            for mid in m_ids:
                m = models.execute_kw(db, uid, password, 'stock.move', 'read', [[mid]], {'fields': ['product_uom_qty']})[0]
                models.execute_kw(db, uid, password, 'stock.move', 'write', [[mid], {'quantity_done': m['product_uom_qty']}])
            
            # 3. Validate
            models.execute_kw(db, uid, password, 'stock.picking', 'button_validate', [[pid]])
         except Exception as e:
             log(f"Picking Validation Warning: {e}", "WARN")
    
    log(f"Setup Old Order {old_name} (Confirmed & Delivered).")
    
    # Create New Order
    new_vals = {'partner_id': partner}
    new_id = models.execute_kw(db, uid, password, 'sale.order', 'create', [new_vals])
    new_name = models.execute_kw(db, uid, password, 'sale.order', 'read', [new_id], {'fields': ['name']})[0]['name']
    log(f"Created New Order {new_name}.")
    
    # Settle Debt
    try:
        models.execute_kw(db, uid, password, 'sale.order', 'action_settle_debt', [old_id], {'context': {'target_order_id': new_id}})
    except Exception as e:
        log(f"Error calling settle debt: {e}", "FAIL")
        return False
        
    # CHECK 1: Lines created?
    lines = models.execute_kw(db, uid, password, 'sale.order.line', 'search_read', 
        [[['order_id', '=', new_id], ['settled_order_id', '=', old_id]]], {'fields': ['name']})
    
    if not lines:
        log("FAIL: No settlement lines created.", "FAIL")
        return False
    log(f"Settlement line created: {lines[0]['name']}")
    
    # CHECK 2: Old Order NOT Locked
    old_state = models.execute_kw(db, uid, password, 'sale.order', 'read', [old_id], {'fields': ['state']})[0]['state']
    if old_state == 'done':
        log(f"FAIL: Old Order {old_name} was locked IMMEDIATELY.", "FAIL")
        return False
    log(f"Old Order State: {old_state} (Correct - Not Locked).")
    
    # Action: Confirm New Order
    models.execute_kw(db, uid, password, 'sale.order', 'action_confirm', [new_id])
    
    # CHECK 3: Old Order LOCKED
    old_state = models.execute_kw(db, uid, password, 'sale.order', 'read', [old_id], {'fields': ['state']})[0]['state']
    if old_state == 'done':
        log(f"SUCCESS: Old Order {old_name} locked AFTER confirmation.", "PASS")
        return True
    else:
        log(f"FAIL: Old Order {old_name} still not locked: {old_state}", "FAIL")
        return False

def test_5_debt_ignore_autobalance():
    log("\nRunning Test 5: Debt Logic (Ignore Auto-Balance)...")
    p_gold = get_product('3 số')
    p_money = get_product('Tiền Việt Nam')
    partner = get_partner()
    
    # Setup Order with 1 Gold Sell and 1 Money AutoBalance
    vals = {
        'partner_id': partner,
        'order_line': [
            (0, 0, {'product_id': p_gold, 'product_uom_qty': 1, 'price_unit': 5000, 'is_trade_in': False}),
            (0, 0, {'product_id': p_money, 'product_uom_qty': 1, 'price_unit': -5000, 'is_trade_in': True, 'is_auto_balance': True})
        ]
    }
    old_id = models.execute_kw(db, uid, password, 'sale.order', 'create', [vals])
    old_name = models.execute_kw(db, uid, password, 'sale.order', 'read', [old_id], {'fields': ['name']})[0]['name']
    models.execute_kw(db, uid, password, 'sale.order', 'action_confirm', [old_id])
    
    # Validate Deliveries to establish debt
    pickings = models.execute_kw(db, uid, password, 'stock.picking', 'search', [[['origin', 'ilike', old_name]]])
    for pid in pickings:
         try:
            # 1. Check Availability
            models.execute_kw(db, uid, password, 'stock.picking', 'action_assign', [[pid]])
            
            # 2. Set Qty Done
            p_data = models.execute_kw(db, uid, password, 'stock.picking', 'read', [[pid]], {'fields': ['move_ids_without_package']})[0]
            m_ids = p_data['move_ids_without_package']
            
            for mid in m_ids:
                m = models.execute_kw(db, uid, password, 'stock.move', 'read', [[mid]], {'fields': ['product_uom_qty']})[0]
                models.execute_kw(db, uid, password, 'stock.move', 'write', [[mid], {'quantity_done': m['product_uom_qty']}])

            # 3. Validate
            models.execute_kw(db, uid, password, 'stock.picking', 'button_validate', [[pid]])
         except Exception as e:
             log(f"Picking Validation Warning: {e}", "WARN")
             
    # Create Target
    new_vals = {'partner_id': partner}
    new_id = models.execute_kw(db, uid, password, 'sale.order', 'create', [new_vals])
    
    # Settle
    models.execute_kw(db, uid, password, 'sale.order', 'action_settle_debt', [old_id], {'context': {'target_order_id': new_id}})
    
    # Check Result: Should only have "Thu hồi nợ: 3 số". Should NOT have Money line.
    lines = models.execute_kw(db, uid, password, 'sale.order.line', 'search_read', 
        [[['order_id', '=', new_id]]], {'fields': ['product_id', 'is_trade_in']})
        
    found_gold = False
    found_money = False
    
    for l in lines:
        p_name = l['product_id'][1]
        if '3 số' in p_name: found_gold = True
        if 'Tiền' in p_name: found_money = True
        
    if found_gold and not found_money:
        log("SUCCESS: Debt contains Gold but ignores Auto-Balance Money.", "PASS")
        return True
    elif found_money:
        log("FAIL: Debt includes Auto-Balance Money!", "FAIL")
        return False
    else:
        log("FAIL: No debt lines created?", "FAIL")
        return False

# --- RUN ALL ---
res1 = test_1_trade_in_split()
res2 = test_2_sell_split()
res3 = test_3_mixed_money()
res4 = test_4_deferred_debt()
res5 = test_5_debt_ignore_autobalance()

print("\n=== FINAL REPORT ===")
print(f"Test 1 (Trade-in Split): {'PASS' if res1 else 'FAIL'}")
print(f"Test 2 (Sell Split):     {'PASS' if res2 else 'FAIL'}")
print(f"Test 3 (Mixed Logic):    {'PASS' if res3 else 'FAIL'}")
print(f"Test 4 (Deferred Lock):  {'PASS' if res4 else 'FAIL'}")
print(f"Test 5 (Auto-Balance):   {'PASS' if res5 else 'FAIL'}")

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

def validate_picking(pid, partial_qty_map=None):
    """
    Validate a picking.
    partial_qty_map: Dict {product_id: qty_to_done}. If None, validate all.
    """
    try:
        # 1. Check Availability
        models.execute_kw(db, uid, password, 'stock.picking', 'action_assign', [[pid]])
        
        # 2. Set Qty Done
        p_data = models.execute_kw(db, uid, password, 'stock.picking', 'read', [[pid]], {'fields': ['move_ids_without_package']})[0]
        m_ids = p_data['move_ids_without_package']
        
        has_done = False
        for mid in m_ids:
            m = models.execute_kw(db, uid, password, 'stock.move', 'read', [[mid]], {'fields': ['product_id', 'product_uom_qty']})[0]
            pid_prod = m['product_id'][0]
            
            qty_to_set = m['product_uom_qty'] # Default Full
            if partial_qty_map and pid_prod in partial_qty_map:
                qty_to_set = partial_qty_map[pid_prod]
            elif partial_qty_map:
                qty_to_set = 0 # If partial map exists but product not in it, set 0? Or skip? Let's set 0 for partial logic.
            
            if qty_to_set > 0:
                models.execute_kw(db, uid, password, 'stock.move', 'write', [[mid], {'quantity_done': qty_to_set}])
                has_done = True

        # 3. Validate
        if has_done:
            # Context skip_backorder=True to close the picking even if partial (no backorder created)
            models.execute_kw(db, uid, password, 'stock.picking', 'with_context', [{'skip_backorder': True}], 'button_validate', [[pid]])
            return True
        else:
            log(f"Skipping validation of {pid} (No qty done)", "WARN")
            return False
            
    except Exception as e:
        log(f"Validation Error {pid}: {e}", "FAIL")
        return False

# --- SCENARIOS ---

def test_6_complex_sell():
    log("\n--- Test 6: Complex Sell (Multiple Lines/Products) ---")
    p1 = get_product('3 số')
    p2 = get_product('4 số')
    partner = get_partner()
    
    # 2 lines of P1, 1 line of P2
    vals = {
        'partner_id': partner,
        'order_line': [
            (0, 0, {'product_id': p1, 'product_uom_qty': 1, 'price_unit': 100, 'name': 'Line 1', 'sequence': 10}),
            (0, 0, {'product_id': p1, 'product_uom_qty': 2, 'price_unit': 110, 'name': 'Line 2 Different Price', 'sequence': 11}), # Same product, diff price
            (0, 0, {'product_id': p2, 'product_uom_qty': 1, 'price_unit': 200, 'sequence': 12})
        ]
    }
    oid = models.execute_kw(db, uid, password, 'sale.order', 'create', [vals])
    name = models.execute_kw(db, uid, password, 'sale.order', 'read', [oid], {'fields': ['name']})[0]['name']
    models.execute_kw(db, uid, password, 'sale.order', 'action_confirm', [oid])
    
    # Check Pickings
    pickings = models.execute_kw(db, uid, password, 'stock.picking', 'search_read', 
        [[['origin', 'ilike', name], ['picking_type_code', '=', 'outgoing']]], {'fields': ['name']})
    
    log(f"Order: {name}. Found {len(pickings)} Delivery Pickings.")
    if len(pickings) >= 3:
        log("SUCCESS: Split into 3 pickings (1 per line).", "PASS")
    elif len(pickings) == 2:
        log("WARN: Split into 2 pickings (Likely grouped by product).", "WARN")
    else:
        log("FAIL: Merged.", "FAIL")

def test_7_complex_buy():
    log("\n--- Test 7: Complex Buy/Trade-in (Multiple Lines/Products) ---")
    p1 = get_product('3 số')
    p2 = get_product('4 số')
    partner = get_partner()
    
    vals = {
        'partner_id': partner,
        'order_line': [
            (0, 0, {'product_id': p1, 'product_uom_qty': 1, 'price_unit': -100, 'is_trade_in': True, 'sequence': 10}),
            (0, 0, {'product_id': p1, 'product_uom_qty': 2, 'price_unit': -110, 'is_trade_in': True, 'sequence': 11}),
            (0, 0, {'product_id': p2, 'product_uom_qty': 1, 'price_unit': -200, 'is_trade_in': True, 'sequence': 12})
        ]
    }
    oid = models.execute_kw(db, uid, password, 'sale.order', 'create', [vals])
    name = models.execute_kw(db, uid, password, 'sale.order', 'read', [oid], {'fields': ['name']})[0]['name']
    models.execute_kw(db, uid, password, 'sale.order', 'action_confirm', [oid])
    
    pickings = models.execute_kw(db, uid, password, 'stock.picking', 'search_read', 
        [[['origin', 'ilike', name], ['picking_type_code', '=', 'incoming']]], {'fields': ['name']})
    
    log(f"Order: {name}. Found {len(pickings)} Receipt Pickings.")
    if len(pickings) >= 3:
        log("SUCCESS: Split into 3 pickings.", "PASS")
    else:
        log("FAIL: Pickings merged.", "FAIL")

def test_8_manual_money():
    log("\n--- Test 8: Manual Money Line (Real Debt, Not Auto) ---")
    p_gold = get_product('3 số')
    p_money = get_product('Tiền Việt Nam')
    partner = get_partner()
    
    vals = {
        'partner_id': partner,
        'order_line': [
            (0, 0, {'product_id': p_gold, 'product_uom_qty': 1, 'price_unit': 1000, 'is_trade_in': False}),
            # Manual Money: is_trade_in=True (Received Money), is_auto_balance=False
            (0, 0, {'product_id': p_money, 'product_uom_qty': 1, 'price_unit': -500, 'is_trade_in': True, 'is_auto_balance': False})
        ]
    }
    oid = models.execute_kw(db, uid, password, 'sale.order', 'create', [vals])
    name = models.execute_kw(db, uid, password, 'sale.order', 'read', [oid], {'fields': ['name']})[0]['name']
    models.execute_kw(db, uid, password, 'sale.order', 'action_confirm', [oid])
    
    # 1. Check Pickings: Money should generate picking (since Storable)
    money_pick = models.execute_kw(db, uid, password, 'stock.picking', 'search', [[['origin', 'ilike', name], ['picking_type_code', '=', 'incoming']]])
    if money_pick:
        log("Money Picking generated (Correct - Asset Logic).", "PASS")
    else:
        log("Money Picking MISSING.", "FAIL")
        
    # 2. Check Debt Calculation: Should include Money (since not Auto)
    # To test this, we simulate settlement call
    # Need target order
    new_vals = {'partner_id': partner}
    new_id = models.execute_kw(db, uid, password, 'sale.order', 'create', [new_vals])
    
    # Validate pickings first to have qty_delivered
    all_picks = models.execute_kw(db, uid, password, 'stock.picking', 'search', [[['origin', 'ilike', name]]])
    for p in all_picks: validate_picking(p)
    
    models.execute_kw(db, uid, password, 'sale.order', 'action_settle_debt', [oid], {'context': {'target_order_id': new_id}})
    
    lines = models.execute_kw(db, uid, password, 'sale.order.line', 'search_read', [[['order_id', '=', new_id]]], {'fields': ['product_id', 'is_trade_in']})
    has_money_debt = any('Tiền' in l['product_id'][1] for l in lines)
    
    if has_money_debt:
        log("Debt Calculation includes Manual Money (Correct).", "PASS")
    else:
         log("Debt Calculation ignored Manual Money?", "FAIL")


def test_status_checks(scenario_name, validate_receipts=False, validate_deliveries=False, partial=False):
    log(f"\n--- Test: {scenario_name} ---")
    p_in = get_product('3 số') # Trade-in
    p_out = get_product('4 số') # Sell
    partner = get_partner()
    
    # Order with 1 IN, 1 OUT
    vals = {
        'partner_id': partner,
        'order_line': [
            (0, 0, {'product_id': p_out, 'product_uom_qty': 2, 'price_unit': 100, 'is_trade_in': False}),
            (0, 0, {'product_id': p_in, 'product_uom_qty': 2, 'price_unit': -100, 'is_trade_in': True})
        ]
    }
    oid = models.execute_kw(db, uid, password, 'sale.order', 'create', [vals])
    name = models.execute_kw(db, uid, password, 'sale.order', 'read', [oid], {'fields': ['name']})[0]['name']
    models.execute_kw(db, uid, password, 'sale.order', 'action_confirm', [oid])
    
    # Get Pickings
    picks_in = models.execute_kw(db, uid, password, 'stock.picking', 'search', [[['origin', 'ilike', name], ['picking_type_code', '=', 'incoming']]])
    picks_out = models.execute_kw(db, uid, password, 'stock.picking', 'search', [[['origin', 'ilike', name], ['picking_type_code', '=', 'outgoing']]])
    
    # Execute Validations
    if validate_receipts:
        for p in picks_in:
            # If partial, map p_in to 1 qty (Requested 2)
            pmap = {p_in: 1} if partial else None
            validate_picking(p, pmap)
            
    if validate_deliveries:
        for p in picks_out:
            pmap = {p_out: 1} if partial else None
            validate_picking(p, pmap)
            
    # Check Status
    # We check: state, custom_state (if exists), transaction_status (implied)
    order = models.execute_kw(db, uid, password, 'sale.order', 'read', [oid], 
        {'fields': ['state', 'custom_state', 'legacy_transaction_status']})[0]
        
    log(f"Picking Status: Rec={validate_receipts}, Del={validate_deliveries}, Partial={partial}")
    log(f"Order Result: State={order['state']}, CustomState={order.get('custom_state')}, LegacyStatus={order.get('legacy_transaction_status')}")

# --- EXECUTE ---

test_6_complex_sell()
test_7_complex_buy()
test_8_manual_money()

# 9. Full All
test_status_checks("9. Picking ALL Full", validate_receipts=True, validate_deliveries=True, partial=False)

# 10. Partial In (Only Receipts)
test_status_checks("10. Picking Only Receipts (Full)", validate_receipts=True, validate_deliveries=False, partial=False)

# 11. Partial Out (Only Deliveries)
test_status_checks("11. Picking Only Deliveries (Full)", validate_receipts=False, validate_deliveries=True, partial=False)

# 12. Full In, Partial Out
test_status_checks("12. Full In, Partial Out", validate_receipts=True, validate_deliveries=True, partial=True) 
# Note: Logic in helper validates ALL picks passed. So 'validate_deliveries=True, partial=True' means PARTIAL OUT.
# But 'validate_receipts=True' will ALSO use partial map if I pass it to both. 
# My helper is too simple for mixed partiality in one call. 
# Re-implementing Scenario 12/13 specifically?
# Actually 'partial=True' applies to whatever is validated.
# So Scenario 12: validate_receipts(full), validate_deliveries(partial).

def test_12_mixed_partial():
    log(f"\n--- Test: 12. Full In, Partial Out ---")
    p_in = get_product('3 số')
    p_out = get_product('4 số')
    partner = get_partner()
    vals = {
        'partner_id': partner,
        'order_line': [
            (0, 0, {'product_id': p_out, 'product_uom_qty': 2, 'price_unit': 100, 'is_trade_in': False}),
            (0, 0, {'product_id': p_in, 'product_uom_qty': 2, 'price_unit': -100, 'is_trade_in': True})
        ]
    }
    oid = models.execute_kw(db, uid, password, 'sale.order', 'create', [vals])
    name = models.execute_kw(db, uid, password, 'sale.order', 'read', [oid], {'fields': ['name']})[0]['name']
    models.execute_kw(db, uid, password, 'sale.order', 'action_confirm', [oid])
    
    picks_in = models.execute_kw(db, uid, password, 'stock.picking', 'search', [[['origin', 'ilike', name], ['picking_type_code', '=', 'incoming']]])
    picks_out = models.execute_kw(db, uid, password, 'stock.picking', 'search', [[['origin', 'ilike', name], ['picking_type_code', '=', 'outgoing']]])
    
    # 1. Full In
    for p in picks_in: validate_picking(p, None) # Full
    # 2. Partial Out
    for p in picks_out: validate_picking(p, {p_out: 1}) # Partial
    
    order = models.execute_kw(db, uid, password, 'sale.order', 'read', [oid], {'fields': ['state', 'custom_state', 'legacy_transaction_status']})[0]
    log(f"Order Result: State={order['state']}, CustomState={order.get('custom_state')}")

test_12_mixed_partial()

def test_13_full_out_partial_in():
    log(f"\n--- Test: 13. Full Out, Partial In ---")
    p_in = get_product('3 số')
    p_out = get_product('4 số')
    partner = get_partner()
    vals = {
        'partner_id': partner,
        'order_line': [
            (0, 0, {'product_id': p_out, 'product_uom_qty': 2, 'price_unit': 100, 'is_trade_in': False}),
            (0, 0, {'product_id': p_in, 'product_uom_qty': 2, 'price_unit': -100, 'is_trade_in': True})
        ]
    }
    oid = models.execute_kw(db, uid, password, 'sale.order', 'create', [vals])
    name = models.execute_kw(db, uid, password, 'sale.order', 'read', [oid], {'fields': ['name']})[0]['name']
    models.execute_kw(db, uid, password, 'sale.order', 'action_confirm', [oid])
    
    picks_in = models.execute_kw(db, uid, password, 'stock.picking', 'search', [[['origin', 'ilike', name], ['picking_type_code', '=', 'incoming']]])
    picks_out = models.execute_kw(db, uid, password, 'stock.picking', 'search', [[['origin', 'ilike', name], ['picking_type_code', '=', 'outgoing']]])
    
    # 1. Full Out
    for p in picks_out: validate_picking(p, None) 
    # 2. Partial In
    for p in picks_in: validate_picking(p, {p_in: 1}) 
    
    order = models.execute_kw(db, uid, password, 'sale.order', 'read', [oid], {'fields': ['state', 'custom_state', 'legacy_transaction_status']})[0]
    log(f"Order Result: State={order['state']}, CustomState={order.get('custom_state')}")

test_13_full_out_partial_in()

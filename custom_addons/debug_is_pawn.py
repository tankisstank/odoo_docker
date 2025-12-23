
print(">>> DEBUG START")
try:
    # In odoo shell, 'env' is globally available.
    # checking IrUiView
    print(">>> SEARCHING VIEWS...")
    views = env['ir.ui.view'].search([('arch_db', 'ilike', 'is_pawn')])
    if views:
        print(f"!!! FOUND {len(views)} VIEW(S):")
        for v in views:
            print(f"  - ID: {v.id} | Name: {v.name} | Model: {v.model} | Key: {v.key}")
    else:
        print(">>> No Views found.")

    # checking IrFilters
    print(">>> SEARCHING FILTERS...")
    filters = env['ir.filters'].search([('domain', 'ilike', 'is_pawn')])
    if filters:
        print(f"!!! FOUND {len(filters)} FILTER(S):")
        for f in filters:
            print(f"  - ID: {f.id} | Name: {f.name} | Model: {f.model_id}")
    else:
        print(">>> No Filters found.")
        
    # checking IrModelFields
    print(">>> SEARCHING FIELD DEFINITIONS...")
    fields_rec = env['ir.model.fields'].search([('name', '=', 'is_pawn'), ('model', '=', 'sale.order')])
    if fields_rec:
        print(f"!!! FOUND FIELD RECORD: {fields_rec.id} (Module: {fields_rec.modules})")
    else:
        print(">>> No Field Definition found.")

    # checking Modules
    print(">>> CHECKING MODULES...")
    modules = env['ir.module.module'].search([('state', '=', 'installed'), ('name', 'in', ['sale_trade_in', 'gold_shop_branding', 'qlv'])])
    for m in modules:
        print(f"  - Module: {m.name} | State: {m.state}")

except Exception as e:
    print(f"ERROR: {e}")
print(">>> DEBUG END")

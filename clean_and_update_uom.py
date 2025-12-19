import xmlrpc.client
import sys

ODOO_URL = 'http://localhost:8069'
DB_NAME = 'qlv_new'
USERNAME = 'c0508g@gmail.com'
PASSWORD = 'abc123'

PRODUCT_ID = 2
TARGET_UOM_NAME = 'Lượng'

def clean_and_update():
    try:
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
        uid = common.authenticate(DB_NAME, USERNAME, PASSWORD, {})
        models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')

        # 1. Check Product
        product = models.execute_kw(DB_NAME, uid, PASSWORD, 'product.product', 'read', 
                                    [PRODUCT_ID], {'fields': ['name', 'uom_id']})
        if not product:
            print("Product not found.")
            return

        print(f"Product: {product[0]['name']}")
        print(f"Current UoM ID: {product[0]['uom_id'][0]} ({product[0]['uom_id'][1]})")

        # 2. Find Target UoM
        uoms = models.execute_kw(DB_NAME, uid, PASSWORD, 'uom.uom', 'search_read',
                                 [[['name', '=', TARGET_UOM_NAME]]], {'fields': ['id', 'category_id']})
        if not uoms:
            print(f"Target UoM '{TARGET_UOM_NAME}' not found.")
            return
        
        target_uom_id = uoms[0]['id']
        target_cat_id = uoms[0]['category_id'][0]
        print(f"Target UoM ID: {target_uom_id} ({TARGET_UOM_NAME})")

        # 3. Clean Stock Moves and Quants
        # Find moves
        move_ids = models.execute_kw(DB_NAME, uid, PASSWORD, 'stock.move', 'search', [[['product_id', '=', PRODUCT_ID]]])
        if move_ids:
            print(f"Found {len(move_ids)} blocking stock moves. Deleting...")
            
            # Reset to draft and delete to avoid constraint errors
            # In some cases, we need to set state='draft' directly via write if button_cancel doesn't work for done moves
            models.execute_kw(DB_NAME, uid, PASSWORD, 'stock.move', 'write', [move_ids, {'state': 'draft'}])
            models.execute_kw(DB_NAME, uid, PASSWORD, 'stock.move', 'unlink', [move_ids])
            print("✓ Deleted stock moves.")
        
        # Find quants (Inventory on hand)
        quant_ids = models.execute_kw(DB_NAME, uid, PASSWORD, 'stock.quant', 'search', [[['product_id', '=', PRODUCT_ID]]])
        if quant_ids:
            print(f"Found {len(quant_ids)} inventory records. Deleting...")
            # Quants can usually be unlinked if user has rights
            try:
                models.execute_kw(DB_NAME, uid, PASSWORD, 'stock.quant', 'unlink', [quant_ids])
                print("✓ Deleted stock quants.")
            except Exception as e:
                # If cannot delete, try setting quantity to 0?
                # But unlink is best for cleaning history
                print(f"Warning: Could not delete quants: {e}")

        # 4. Update UoM
        print("Updating Product UoM...")
        try:
            models.execute_kw(DB_NAME, uid, PASSWORD, 'product.product', 'write', [[PRODUCT_ID], {'uom_id': target_uom_id, 'uom_po_id': target_uom_id}])
            print(f"✓ SUCCESS: Product UoM updated to {TARGET_UOM_NAME}")
        except Exception as e:
            print(f"✗ FAILED to update UoM: {e}")
            print("Likely there are still hidden dependencies (Evaluation, Layers, etc).")
            
            # Check Valuation Layers? (stock.valuation.layer)
            layer_ids = models.execute_kw(DB_NAME, uid, PASSWORD, 'stock.valuation.layer', 'search', [[['product_id', '=', PRODUCT_ID]]])
            if layer_ids:
                print(f"Found {len(layer_ids)} valuation layers. These cannot be easily deleted via RPC safely.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    confirm = input("This will DELETE stock history for the product to change UoM. Proceed? (y/n): ")
    if confirm.lower() == 'y':
        clean_and_update()

import xmlrpc.client
import sys

ODOO_URL = 'http://localhost:8069'
DB_NAME = 'qlv_new'
USERNAME = 'c0508g@gmail.com'
PASSWORD = 'abc123'

PRODUCT_ID = 2

def inspect_dependencies():
    try:
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
        uid = common.authenticate(DB_NAME, USERNAME, PASSWORD, {})
        models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')

        print(f"Inspecting Product ID: {PRODUCT_ID}")
        
        # 1. Product Info
        product = models.execute_kw(DB_NAME, uid, PASSWORD, 'product.product', 'read', 
                                    [PRODUCT_ID], {'fields': ['name', 'uom_id', 'uom_po_id']})
        if not product:
            # Try template id if product_id 2 is not found (User gave URL with id=2 on product.template)
            print("Product variant not found, checking template...")
            # The URL was model=product.template. So ID 2 is likely the template ID.
            # We need to find the variants.
            template = models.execute_kw(DB_NAME, uid, PASSWORD, 'product.template', 'read',
                                        [PRODUCT_ID], {'fields': ['name', 'uom_id', 'product_variant_ids']})
            if not template:
                print("Product Template ID 2 not found.")
                return
            
            print(f"Product Template: {template[0]['name']} (UoM: {template[0]['uom_id']})")
            variant_ids = template[0]['product_variant_ids']
        else:
            print(f"Product Variant: {product[0]['name']} (UoM: {product[0]['uom_id']})")
            variant_ids = [PRODUCT_ID]

        print(f"Variants: {variant_ids}")

        # Check dependencies for all variants
        for vid in variant_ids:
            print(f"\n--- Checking Variant ID {vid} ---")
            
            # Stock Moves
            moves = models.execute_kw(DB_NAME, uid, PASSWORD, 'stock.move', 'search_count', [[['product_id', '=', vid]]])
            print(f"Stock Moves: {moves}")
            
            # Stock Quants (On Hand)
            quants = models.execute_kw(DB_NAME, uid, PASSWORD, 'stock.quant', 'search_count', [[['product_id', '=', vid]]])
            print(f"Stock Quants (Inventory): {quants}")

            # Sale Lines
            sol = models.execute_kw(DB_NAME, uid, PASSWORD, 'sale.order.line', 'search_count', [[['product_id', '=', vid]]])
            print(f"Sale Order Lines: {sol}")

            # Purchase Lines
            pol = models.execute_kw(DB_NAME, uid, PASSWORD, 'purchase.order.line', 'search_count', [[['product_id', '=', vid]]])
            print(f"Purchase Order Lines: {pol}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_dependencies()

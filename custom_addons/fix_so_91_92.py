from odoo import api, SUPERUSER_ID
import sys
import odoo
from odoo.tools import config

def fix_orders(env):
    print(">>> FIXING SO 91 & 92 (Partner 155)")
    
    for so_id in [91, 92]:
        so = env['sale.order'].browse(so_id)
        print(f"\nProcessing SO {so.name}...")
        
        # Find VND Line
        # Need to be careful to find the exact line causing issue (Where Delivered != Ordered)
        for line in so.order_line:
            if line.qty_delivered != line.product_uom_qty:
                print(f"  MISMATCH Line {line.id} ({line.product_id.name}): Ordered={line.product_uom_qty}, Delivered={line.qty_delivered}")
                
                # Fix: Update Ordered to match Delivered
                # This accepts the rounding that happened during delivery.
                line.write({'product_uom_qty': line.qty_delivered})
                print("  -> FIXED: Updated Ordered Qty to match Delivered.")
                
        # Force recompute of invoice status
        so._compute_invoice_status()
        print(f"  New Invoice Status: {so.invoice_status}")
        
        # Check if we can set custom_state to 'invoiced' now?
        # If invoice_status is 'invoiced' or 'no', and Invoice exists.
        if so.invoice_status in ('invoiced', 'no') and so.invoice_ids:
             # My custom logic usually does this automatically on action?
             # Or I can manually set it to be consistent
             so.write({'custom_state': 'invoiced'})
             print("  -> Updated custom_state to 'invoiced'")
             
    env.cr.commit()
    print(">>> FIX COMPLETE")

if __name__ == "__main__":
    try:
        db_name = sys.argv[1]
        config.parse_config([
            '-c', '/etc/odoo/odoo.conf',
            '--db_host=db',
            '--db_port=5432',
            '--db_user=odoo',
            '--db_password=odoo'
        ])
        registry = odoo.registry(db_name)
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            fix_orders(env)
    except Exception as e:
        print(f"CRASH: {e}")

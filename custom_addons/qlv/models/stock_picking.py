from odoo import models

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        # 1. Calls native Validate logic
        res = super(StockPicking, self).button_validate()
        
        # 2. Check if this completion triggers Auto-Invoice on the Sale Order
        # Loop through related sales orders (usually picking.sale_id is set)
        
        # Note: res might be a wizard action (if backorder needed), or True/False.
        # We only want to auto-invoice if the picking is effectively 'done'.
        
        for picking in self:
            if picking.state == 'done' and picking.sale_id:
                # Trigger Auto-Invoice Check on the related Sale Order
                picking.sale_id._check_auto_invoice()
                
        return res


from odoo import models, api

class StockRule(models.Model):
    _inherit = 'stock.rule'

    @api.model
    def _get_stock_move_values(self, product_id, product_qty, product_uom, location_id, name, origin, company_id, values):
        """
        Override to allow enforcing Product and Quantity from values (Sales Order Line overrides).
        Standard Odoo ignores values['product_id'] and values['product_uom_qty'] in favor of arguments.
        We need this for:
        1. Trade-in: Using Original Product ID instead of Converted Product.
        2. Trade-in: Using Physical Weight (Original Qty) instead of Converted Qty.
        """
        res = super(StockRule, self)._get_stock_move_values(product_id, product_qty, product_uom, location_id, name, origin, company_id, values)
        
        # Override Quantity if provided in values
        if values.get('product_uom_qty'):
            res['product_uom_qty'] = values['product_uom_qty']
        
        # Override Product if provided in values (Critical for Gold Mapping)
        if values.get('product_id'):
            res['product_id'] = values['product_id']
            # Re-compute name/description if product changed? 
            # Or trust the "name" passed? Usually name comes from SO Line Description, which is fine.
            
        return res

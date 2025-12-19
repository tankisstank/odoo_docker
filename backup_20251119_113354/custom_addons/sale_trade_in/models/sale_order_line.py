from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_trade_in = fields.Boolean('Trade-in Product')
    trade_in_price_unit = fields.Float('Trade-in Price (Unit)')

    @api.onchange('is_trade_in', 'product_id')
    def _onchange_is_trade_in(self):
        for line in self:
            if line.is_trade_in and line.product_id:
                line.trade_in_price_unit = line.product_id.standard_price
            elif not line.is_trade_in:
                line.trade_in_price_unit = 0.0

    @api.depends('price_unit', 'discount', 'product_uom_qty', 'tax_id', 'trade_in_price_unit', 'is_trade_in')
    def _compute_amount(self):
        super(SaleOrderLine, self)._compute_amount()
        for line in self:
            if line.is_trade_in:
                line.update({
                    'price_subtotal': 0.0,
                    'price_tax': 0.0,
                    'price_total': 0.0,
                }) 
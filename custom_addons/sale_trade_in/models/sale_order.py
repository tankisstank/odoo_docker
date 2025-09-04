from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    trade_in_total = fields.Monetary('Total Trade-in', compute='_compute_trade_in_total', store=True, currency_field='currency_id')

    @api.depends('order_line.is_trade_in', 'order_line.trade_in_price_unit', 'order_line.product_uom_qty')
    def _compute_trade_in_total(self):
        for order in self:
            order.trade_in_total = sum(
                line.trade_in_price_unit * line.product_uom_qty
                for line in order.order_line if line.is_trade_in
            )

    @api.depends('order_line.price_total', 'trade_in_total')
    def _amount_all(self):
        for order in self:
            # Tổng tiền các dòng không phải trade-in
            amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
                if not line.is_trade_in:
                    amount_untaxed += line.price_subtotal
                    amount_tax += line.price_tax
            order.amount_untaxed = amount_untaxed
            order.amount_tax = amount_tax
            order.amount_total = amount_untaxed + amount_tax - order.trade_in_total 
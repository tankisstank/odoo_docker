import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Ràng buộc các trường tổng vào compute tùy chỉnh
    amount_untaxed = fields.Monetary(compute='_amount_all', store=True, currency_field='currency_id')
    amount_tax = fields.Monetary(compute='_amount_all', store=True, currency_field='currency_id')
    amount_total = fields.Monetary(compute='_amount_all', store=True, currency_field='currency_id')

    trade_in_total = fields.Monetary('Total Trade-in', compute='_compute_trade_in_total', store=True, currency_field='currency_id')

    @api.depends('order_line.is_trade_in', 'order_line.trade_in_price_unit', 'order_line.product_uom_qty', 'currency_id')
    def _compute_trade_in_total(self):
        for order in self:
            currency = order.currency_id or order.company_id.currency_id
            trade_total = sum(
                line.trade_in_price_unit * line.product_uom_qty
                for line in order.order_line if line.is_trade_in
            )
            rounded_trade_total = currency.round(trade_total) if currency else trade_total
            order.trade_in_total = rounded_trade_total
            _logger.debug(
                "[sale_trade_in] Order %s trade_in_total computed: raw=%s rounded=%s currency=%s",
                order.name, trade_total, rounded_trade_total, currency.name if currency else None
            )

    @api.depends(
        'order_line.price_total', 'order_line.price_subtotal', 'order_line.price_tax',
        'order_line.is_trade_in', 'order_line.trade_in_price_unit', 'order_line.product_uom_qty',
        'order_line.discount', 'order_line.price_unit', 'order_line.tax_id', 'trade_in_total'
    )
    @api.depends_context('company_id', 'force_company')
    def _amount_all(self):
        _logger.debug("[sale_trade_in] _amount_all triggered for %s orders", len(self))
        for order in self:
            currency = order.currency_id or order.company_id.currency_id
            non_trade_lines = order.order_line.filtered(lambda l: not l.is_trade_in and not l.display_type)
            trade_lines = order.order_line.filtered(lambda l: l.is_trade_in and not l.display_type)
            amount_untaxed = sum(non_trade_lines.mapped('price_subtotal'))
            amount_tax = sum(non_trade_lines.mapped('price_tax'))
            rounded_untaxed = currency.round(amount_untaxed) if currency else amount_untaxed
            rounded_tax = currency.round(amount_tax) if currency else amount_tax
            rounded_total = (rounded_untaxed + rounded_tax) - (order.trade_in_total or 0.0)
            _logger.debug(
                "[sale_trade_in] Order %s before adjust -> non_trade_lines=%s",
                order.name, len(non_trade_lines)
            )
            for line in trade_lines:
                _logger.debug(
                    "[sale_trade_in] Trade line %s subtotal=%s tax=%s qty=%s trade_price_unit=%s",
                    line.display_name or line.name, line.price_subtotal, line.price_tax, line.product_uom_qty, line.trade_in_price_unit
                )
            order.amount_untaxed = rounded_untaxed
            order.amount_tax = rounded_tax
            order.amount_total = rounded_total if currency else (rounded_untaxed + rounded_tax - (order.trade_in_total or 0.0))
            _logger.debug(
                "[sale_trade_in] Order %s after adjust -> untaxed=%s tax=%s trade_in_total=%s final_total=%s",
                order.name, order.amount_untaxed, order.amount_tax, order.trade_in_total, order.amount_total
            )

    @api.onchange('order_line', 'trade_in_total')
    def _onchange_trade_in_totals(self):
        _logger.debug("[sale_trade_in] Onchange triggered for order %s -> force compute totals", self.display_name)
        self._amount_all()
        _logger.debug(
            "[sale_trade_in] Onchange post-compute -> untaxed=%s tax=%s trade_in_total=%s total=%s",
            self.amount_untaxed, self.amount_tax, self.trade_in_total, self.amount_total
        )
        return 
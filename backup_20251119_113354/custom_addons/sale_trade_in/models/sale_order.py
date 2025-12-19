import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

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
    def _prepare_trade_in_picking(self):
        self.ensure_one()
        # Find the correct incoming picking type for the order's warehouse
        incoming_picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'incoming'),
            ('warehouse_id', '=', self.warehouse_id.id),
        ], limit=1)
        if not incoming_picking_type:
            raise UserError(_("No 'Receipts' operation type found for warehouse %s. Please configure one.", self.warehouse_id.name))

        return {
            'picking_type_id': incoming_picking_type.id,
            'partner_id': self.partner_id.id,
            'origin': self.name,
            'company_id': self.company_id.id,
            'location_dest_id': incoming_picking_type.default_location_dest_id.id,
            'location_id': self.partner_id.property_stock_customer.id,
        }

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()

        for order in self:
            # Find all moves related to trade-in lines from the pickings just created
            # In Odoo 16, the correct field is 'move_ids_without_package', not 'move_lines'
            trade_in_moves = order.picking_ids.move_ids_without_package.filtered(
                lambda m: m.sale_line_id and m.sale_line_id.is_trade_in
            )

            if not trade_in_moves:
                continue

            # Find an existing receipt or create a new one for the trade-in items
            receipt_picking = order.picking_ids.filtered(
                lambda p: p.picking_type_id.code == 'incoming' and p.state not in ('done', 'cancel')
            )
            if not receipt_picking:
                picking_vals = order._prepare_trade_in_picking()
                receipt_picking = self.env['stock.picking'].create(picking_vals)

            # Move the trade-in stock moves to the receipt picking and correct their locations
            trade_in_moves.write({
                'picking_id': receipt_picking.id,
                'location_id': receipt_picking.location_id.id,
                'location_dest_id': receipt_picking.location_dest_id.id,
            })

            # After moving, if an original delivery order is now empty, cancel it.
            for picking in order.picking_ids:
                if picking.picking_type_id.code == 'outgoing' and not picking.move_ids_without_package:
                    picking.action_cancel()
        return res

    def _compute_picking_counts(self):
        for order in self:
            delivery_pickings = order.picking_ids.filtered(lambda p: p.picking_type_id.code == 'outgoing')
            receipt_pickings = order.picking_ids.filtered(lambda p: p.picking_type_id.code == 'incoming')
            order.delivery_picking_count = len(delivery_pickings)
            order.receipt_picking_count = len(receipt_pickings)

    def action_view_delivery_pickings(self):
        self.ensure_one()
        pickings = self.picking_ids.filtered(lambda p: p.picking_type_id.code == 'outgoing')
        action = self.env['ir.actions.act_window']._for_xml_id('stock.action_picking_tree_all')
        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif pickings:
            action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
            action['res_id'] = pickings.id
        return action

    def action_view_receipt_pickings(self):
        self.ensure_one()
        pickings = self.picking_ids.filtered(lambda p: p.picking_type_id.code == 'incoming')
        action = self.env['ir.actions.act_window']._for_xml_id('stock.action_picking_tree_all')
        # Đổi tên action cho rõ ràng
        action['display_name'] = 'Trade-in Receipts'
        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif pickings:
            action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
            action['res_id'] = pickings.id
        return action
    def action_view_combined_transfers(self):
        """
        This function returns an action that displays the pickings related to
        this sale order. It explicitly ensures that the list view is opened first.
        """
        action = self.env['ir.actions.act_window']._for_xml_id('stock.action_picking_tree_all')

        # === START: Make the action more robust ===
        # 1. Remove any leftover res_id to prevent opening a form view directly
        action.pop('res_id', None)
        # 2. Explicitly define the view modes to ensure list view is prioritized
        action['view_mode'] = 'tree,kanban,form'
        # === END: Make the action more robust ===

        # Set the domain to our specific pickings
        action['domain'] = [('id', 'in', self.picking_ids.ids)]

        context = {}
        if action.get('context'):
            eval_context = {'allowed_company_ids': self.env.companies.ids}
            context = safe_eval(action['context'], globals_dict=eval_context)
        
        # Keep the default grouping
        context['search_default_picking_type'] = 1
        action['context'] = context
        
        return action


    @api.onchange('order_line', 'trade_in_total')
    def _onchange_trade_in_totals(self):
        _logger.debug("[sale_trade_in] Onchange triggered for order %s -> force compute totals", self.display_name)
        self._amount_all()
        _logger.debug(
            "[sale_trade_in] Onchange post-compute -> untaxed=%s tax=%s trade_in_total=%s total=%s",
            self.amount_untaxed, self.amount_tax, self.trade_in_total, self.amount_total
        )
        return 
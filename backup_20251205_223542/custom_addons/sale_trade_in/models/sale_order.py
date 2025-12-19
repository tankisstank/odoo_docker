import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    trade_in_total = fields.Monetary('Total Trade-in', compute='_compute_trade_in_total', store=True, currency_field='currency_id')
    trade_in_summary = fields.Char('Hàng Nhập', compute='_compute_trade_in_total', store=True)
    sell_total = fields.Monetary('Total Sell', compute='_compute_trade_in_total', store=True, currency_field='currency_id')
    sell_summary = fields.Char('Hàng Xuất', compute='_compute_trade_in_total', store=True)

    pending_order_ids = fields.One2many('sale.order', compute='_compute_pending_order_ids', string='Đơn hàng chưa hoàn thành')

    def _compute_pending_order_ids(self):
        for order in self:
            if not order.partner_id:
                order.pending_order_ids = False
                continue

            # Find other orders for the same partner that are not cancelled
            domain = [
                ('partner_id', '=', order.partner_id.id),
                ('id', '!=', order.id),
                ('state', 'not in', ('cancel', 'draft')), # Include only confirmed orders? Or maybe keep draft out.
            ]
            partner_orders = self.search(domain)
            
            pending_orders = self.env['sale.order']
            for o in partner_orders:
                # Check for incomplete Pickings (Receipts/Transfers)
                # "chưa thực hiện xong việc nhập, chuyển kho"
                # Looking for any picking that is not done or cancelled
                incomplete_picking = o.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))
                
                # Check for Debt (Nợ)
                # Invoice created but not fully paid
                # If no invoice exists, it might be "pending invoice" but that depends on policy.
                # Usually "Nợ" means Invoiced but not Paid. 
                # If not invoiced but delivered => To Invoice (also a kind of incomplete).
                # Let's check:
                # 1. Has unpaid invoices
                has_unpaid_invoices = o.invoice_ids.filtered(lambda i: i.state == 'posted' and i.payment_state not in ('paid', 'reversed', 'in_payment'))
                
                # 2. Or invoice_status is 'to invoice' (delivered but not invoiced yet) - this is also "incomplete"
                is_to_invoice = o.invoice_status == 'to invoice'

                if incomplete_picking or has_unpaid_invoices or is_to_invoice:
                    pending_orders += o
            
            order.pending_order_ids = pending_orders

    @api.depends('order_line.is_trade_in', 'order_line.price_subtotal', 'currency_id')
    def _compute_trade_in_total(self):
        for order in self:
            currency = order.currency_id or order.company_id.currency_id
            
            # Trade-in calculation
            # Logic mới: price_unit đã âm cho trade-in, nên price_subtotal cũng âm.
            # Trade-in Total cần hiển thị số dương (giá trị hàng nhập).
            trade_in_lines = order.order_line.filtered(lambda l: l.is_trade_in)
            trade_total = sum(abs(line.price_subtotal) for line in trade_in_lines)
            
            # Sell calculation
            sell_lines = order.order_line.filtered(lambda l: not l.is_trade_in)
            sell_total_val = sum(line.price_subtotal for line in sell_lines)

            # Summaries
            def get_summary(lines):
                summary_parts = []
                for line in lines:
                    qty = line.product_uom_qty
                    # Remove trailing zeros for integer quantities
                    qty_str = '{:g}'.format(qty)
                    product_name = line.product_id.name or ''
                    summary_parts.append(f"{qty_str}({product_name})")
                return ", ".join(summary_parts)

            order.trade_in_summary = get_summary(trade_in_lines)
            order.sell_summary = get_summary(sell_lines)
            
            rounded_trade_total = currency.round(trade_total) if currency else trade_total
            order.trade_in_total = rounded_trade_total
            
            rounded_sell_total = currency.round(sell_total_val) if currency else sell_total_val
            order.sell_total = rounded_sell_total

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

    def _create_invoices(self, grouped=False, final=False, date=None):
        moves = super(SaleOrder, self)._create_invoices(grouped, final, date)
        for move in moves:
            if move.move_type == 'out_refund':
                for line in move.invoice_line_ids:
                    # Check if line is linked to a trade-in SO line
                    # Note: line.sale_line_ids might be empty if not correctly linked, but usually it is.
                    # We can also check the new is_trade_in field on account.move.line if we added it to the model.
                    is_trade_in = line.is_trade_in if hasattr(line, 'is_trade_in') else False
                    if not is_trade_in and line.sale_line_ids:
                        is_trade_in = any(sl.is_trade_in for sl in line.sale_line_ids)
                    
                    if is_trade_in:
                        # Flip price to positive if it's negative
                        if line.price_unit < 0:
                            line.price_unit = -line.price_unit
                        # Ensure quantity is positive if it's negative
                        if line.quantity < 0:
                            line.quantity = -line.quantity
        return moves

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
            # Move the trade-in stock moves to the receipt picking and correct their locations
            trade_in_moves.write({
                'picking_id': receipt_picking.id,
                'location_id': receipt_picking.location_id.id,
                'location_dest_id': receipt_picking.location_dest_id.id,
            })
            
            # CRITICAL FIX: Explicitly update the move lines to point to the new picking
            # Standard Odoo might not propagate this change if the moves are already reserved/assigned
            trade_in_moves.move_line_ids.write({
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
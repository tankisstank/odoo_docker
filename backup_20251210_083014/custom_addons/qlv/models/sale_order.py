from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval


class SaleOrder(models.Model):
    _inherit = 'sale.order'


    pending_order_ids = fields.One2many('sale.order', compute='_compute_pending_order_ids', string='Đơn hàng chưa hoàn thành')
    auto_balance_money = fields.Boolean('Tự động thanh toán Tiền mặt', default=True, help="Nếu bật, hệ thống sẽ tự động thêm dòng Tiền mặt để cân bằng đơn hàng về 0.")

    # === Fields for Custom List View ===
    summary_goods_in = fields.Char('Hàng Nhập', compute='_compute_custom_list_view_summary', store=True)
    summary_goods_out = fields.Char('Hàng Xuất', compute='_compute_custom_list_view_summary', store=True)
    money_total_in = fields.Monetary('Tiền Nhập', compute='_compute_custom_list_view_summary', store=True, currency_field='currency_id')
    money_total_in = fields.Monetary('Tiền Nhập', compute='_compute_custom_list_view_summary', store=True, currency_field='currency_id')
    money_total_out = fields.Monetary('Tiền Xuất', compute='_compute_custom_list_view_summary', store=True, currency_field='currency_id')

    custom_state = fields.Selection([
        ('draft', 'Báo giá'),
        ('sent', 'Báo giá đã gửi'),
        ('sale', 'Đơn hàng'),
        ('partial', 'Đã giao một phần'),
        ('done_delivery', 'Giao xong (Chờ hóa đơn)'),
        ('invoiced', 'Đã xuất hóa đơn'),
        ('cancel', 'Đã hủy'),
    ], string='Tình trạng', compute='_compute_custom_state', store=True)

    @api.depends('state', 'picking_ids.state', 'invoice_status', 'invoice_ids.state')
    def _compute_custom_state(self):
        for order in self:
            # 1. Base State validation
            if order.state in ('draft', 'sent', 'cancel'):
                order.custom_state = order.state
                continue

            # 2. Check Invoiced State
            if order.invoice_status == 'invoiced':
                order.custom_state = 'invoiced'
                continue

            # 3. Check Picking States
            pickings = order.picking_ids.filtered(lambda p: p.state != 'cancel')
            if not pickings:
                # No pickings yet (Service only?) or just confirmed
                order.custom_state = 'sale'
                continue

            # Count states
            done_count = len(pickings.filtered(lambda p: p.state == 'done'))
            total_count = len(pickings)

            if done_count == total_count:
                # All pickings are Done
                order.custom_state = 'done_delivery'
            elif done_count > 0:
                # Some done, some not
                order.custom_state = 'partial'
            else:
                # Confirmed but no picking done yet
                order.custom_state = 'sale'

    def _check_auto_invoice(self):
        """
        Triggered by Stock Picking validation.
        Checks if Order is ready for Auto-Invoice.
        """
        for order in self:
            # Only proceed if fully delivered (done_delivery) AND not yet invoiced
            if order.custom_state == 'done_delivery' and order.invoice_status == 'to invoice':
                try:
                    # 1. Create Invoice
                    invoices = order._create_invoices()
                    # 2. Post Invoice (Auto-Confirm)
                     # Iterate in case multiple invoices created
                    for inv in invoices:
                        if inv.state == 'draft':
                            inv.action_post()
                except Exception as e:
                    # Log error but don't crash the picking validation
                    # Ideally log to chatter
                    order.message_post(body=f"Auto-Invoice failed: {str(e)}")

    @api.depends('order_line.product_id', 'order_line.product_uom_qty', 'order_line.price_subtotal', 'order_line.is_trade_in')
    def _compute_custom_list_view_summary(self):
        for order in self:
            goods_in_list = []
            goods_out_list = []
            val_in = 0.0 # Money In (Revenue from Sold Goods)
            val_out = 0.0 # Money Out (Expense for Bought Goods)
            
            money_product_id = order.company_id.money_product_id.id if order.company_id.money_product_id else False

            for line in order.order_line:
                # Skip Note/Section lines
                if line.display_type:
                    continue
                
                # Check if it is the "Money Product" (handling cash)
                is_money_product = line.product_id.id == money_product_id
                
                if is_money_product:
                    # Ignore the "Money Product" lines for goods summary
                    # But DO NOT double count value if we base it on Goods Value
                    continue

                qty = line.product_uom_qty
                # Use default code or part of name
                # Format: QTY(CODE)
                name_ref = line.product_id.default_code or line.product_id.name
                # Truncate name if too long to keep list clean? User example shows "9999", "X". 
                # Let's keep it simple.
                
                # Format string
                item_str = f"{float(qty):g}({name_ref})"

                if line.is_trade_in:
                    # Trade-in Item (Goods In) -> Expense (Money Out)
                    goods_in_list.append(item_str)
                    # Trade-in price is negative, so we subtract it from total (or take abs)
                    # Logic: "Tiền Xuất" = Value of Goods we bought.
                    # Price Subtotal is negative for trade-in.
                    val_out += abs(line.price_subtotal) 
                else:
                    # Sell Item (Goods Out) -> Revenue (Money In)
                    goods_out_list.append(item_str)
                    val_in += line.price_subtotal

            order.summary_goods_in = ", ".join(goods_in_list)
            order.summary_goods_out = ", ".join(goods_out_list)
            order.money_total_in = val_in
            order.money_total_out = val_out

    @api.onchange('order_line', 'auto_balance_money')
    def _onchange_balance_money(self):
        """
        Tự động tính toán dòng tiền để cân bằng đơn hàng.
        """
        if not self.auto_balance_money:
            return

        company = self.company_id or self.env.company
        money_product = company.money_product_id
        if not money_product:
            return

        # 1. Initialize variables
        grand_total_goods = 0.0
        money_lines = []

        # 2. Iterate lines to separate "Goods" from "Money"
        for line in self.order_line:
            # Check if line is a Money line (either by flag or by product)
            is_money_line = line.is_auto_balance or (line.product_id and line.product_id.id == money_product.id)
            
            if is_money_line:
                money_lines.append(line)
            else:
                grand_total_goods += line.price_subtotal

        # 3. Calculate Balance Needed
        # Target: Total Order = 0.
        # Total Order = Goods + Money.
        # 0 = Goods + Money -> Money = -Goods.
        balance_needed = -grand_total_goods

        # 4. Handle "Zero Balance" (Perfectly balanced without extra money)
        # Use currency rounding or a small epsilon (e.g. 0.001 if user wants 3 decimals)
        # Better: Use company currency rounding.
        rounding_precision = company.currency_id.rounding or 0.001
        if abs(balance_needed) < rounding_precision:
            if money_lines:
                # If balanced but we have money lines, we must remove/zero them.
                # Remove all money lines.
                self.order_line -= self.env['sale.order.line'].concat(*money_lines)
            return

        # 5. Prepare Values for Money Line
        vals = {
            'product_id': money_product.id,
            'is_auto_balance': True,
            'sequence': 9999,
            'product_uom': money_product.uom_id.id,
            'name': 'Thanh toán tiền mặt (Tự động)',
        }

        if balance_needed < 0:
            # Need to collect money (Trade-in Money)
            vals.update({
                'is_trade_in': True,
                'price_unit_base': 1.0,
                'product_uom_qty': abs(balance_needed),
                'price_unit': -1.0,
            })
        else:
            # Need to pay money (Sell Money)
            vals.update({
                'is_trade_in': False,
                'price_unit_base': 1.0,
                'product_uom_qty': abs(balance_needed),
                'price_unit': 1.0,
            })

        # 6. specific logic to Update or Create
        if money_lines:
            # Update the FIRST money line
            first_line = money_lines[0]
            first_line.update(vals)
            
            # Remove any duplicate/extra money lines
            if len(money_lines) > 1:
                extras = self.env['sale.order.line'].concat(*money_lines[1:])
                self.order_line -= extras
        else:
            # Create new line
            new_line = self.env['sale.order.line'].new(vals)
            self.order_line += new_line
        
        # 7. Auto-Sorting Logic
        # Goals: Sort lines into Sections: "Hàng Bán" -> "Hàng Mua" -> "Thanh Toán"
        
        # Identify lines again (including newly added one)
        all_lines = self.order_line
        
        # Helper to find or create section
        def find_section(name):
            for l in all_lines:
                if l.display_type == 'line_section' and l.name == name:
                    return l
            # Create new section
            section_vals = {
                'display_type': 'line_section',
                'name': name,
                'sequence': 0, # Temp
            }
            new_section = self.env['sale.order.line'].new(section_vals)
            return new_section

        section_sell = find_section('Hàng Bán (Xuất)')
        section_buy = find_section('Hàng Mua (Nhập)')

        # If sections don't exist in 'all_lines' yet (created as new), add them
        if section_sell not in all_lines:
            self.order_line += section_sell
        if section_buy not in all_lines:
            self.order_line += section_buy
            
        # Re-fetch lines after potential addition
        all_lines = self.order_line

        # Categorize
        sell_items = []
        buy_items = []
        money_items = [] 
        others = [] # For Notes/Section markers (if any leftover)

        for l in all_lines:
            # Skip the specific sections we Manage
            if l.display_type == 'line_section' and l.name in ['Hàng Bán (Xuất)', 'Hàng Mua (Nhập)']:
                continue
            
            if l.display_type == 'line_section':
                 # Other sections? Keep them as 'others'. 
                 others.append(l)
            elif l.display_type == 'line_note':
                # Notes: Append to sell_items by default or 'others'
                sell_items.append(l)
            elif l.is_auto_balance or (money_product and l.product_id == money_product):
                money_items.append(l)
            elif l.is_trade_in:
                buy_items.append(l)
            else:
                sell_items.append(l)

        # Assign Sequences
        current_seq = 10
        
        # 1. Hàng Bán Section (Always Top)
        section_sell.sequence = current_seq
        current_seq += 30
        
        # 2. Sell Items (and Notes)
        for item in sell_items:
            item.sequence = current_seq
            current_seq += 1
            
        # 3. Other generic sections if any (put them here?)
        for item in others:
            item.sequence = current_seq
            current_seq += 1
            
        # 4. Hàng Mua Section
        section_buy.sequence = current_seq
        current_seq += 30
        
        # 5. Buy Items
        for item in buy_items:
            item.sequence = current_seq
            current_seq += 1
            
        # 6. Money Line (Always Last)
        for item in money_items:
            item.sequence = 9999
            
        # FORCE RE-ORDERING
        # Combine all processed items in strictly this order
        sorted_list = [section_sell] + sell_items + others + [section_buy] + buy_items + money_items
        
        # Context validation: Ensure strictly SaleOrderLine objects
        valid_lines = self.env['sale.order.line'].concat(*sorted_list)
        
        # Re-assign to trigger UI update
        # CRITICAL: To force the UI to re-render the list in the correct order for NewIds,
        # sometimes we need to clear and re-set, or just ensure the assignment represents a "change".
        # We try to set it to an empty recordset first (in memory) then back.
        # But for Onchange, a simple assignment should work if the sequence changed.
        # We will try the "Clear and Set" approach which is cleaner for sorting.
        # UPDATE: Removing the "Clear" (Reset) step as it might cause new products to be detached or appended incorrectly.
        # Just re-assigning valid_lines should be enough given sequences are updated.
        self.order_line = valid_lines

    def _compute_pending_order_ids(self):
        for order in self:
            if not order.partner_id:
                order.pending_order_ids = False
                continue

            # Find other orders for the same partner that are NOT fully completed
            # Criteria:
            # 1. Same Partner
            # 2. Not the current order
            # 3. State is 'sale' (Confirmed)
            # 4. Custom State is NOT 'invoiced' (includes sale, partial, done_delivery)
            #    - 'sale': Confirmed, no action yet.
            #    - 'partial': Partially delivered.
            #    - 'done_delivery': Delivered, waiting for invoice (or auto-invoice failed).
            domain = [
                ('partner_id', '=', order.partner_id.id),
                ('id', '!=', order.id),
                ('state', '=', 'sale'),
                ('custom_state', 'in', ('sale', 'partial', 'done_delivery')),
            ]
            order.pending_order_ids = self.search(domain)


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
        # context['search_default_picking_type'] = 1
        action['context'] = context
        
        return action
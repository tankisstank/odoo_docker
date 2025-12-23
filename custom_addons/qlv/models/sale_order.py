from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def create(self, vals):
        if 'order_line' in vals:
            # _logger.info("QLV DEBUG CREATE: Checking Order Lines...")
            clean_lines = []
            for i, cmd in enumerate(vals['order_line']):
                # _logger.info(f"QLV DEBUG CREATE Line {i}: {cmd}")
                # Check for bad lines
                if cmd[0] == 0:
                     v = cmd[2]
                     # Sanitize Input: Drop Ghost Lines
                     if not v.get('name') and not v.get('product_id') and not v.get('display_type'):
                         _logger.warning(f"QLV INFO: Dropped ghost/empty line at creation index {i}")
                         continue 
                clean_lines.append(cmd)
            vals['order_line'] = clean_lines

        return super(SaleOrder, self).create(vals)

    def write(self, values):
        if 'order_line' in values:
             _logger.info("QLV DEBUG WRITE: Checking Order Lines...")
             for i, cmd in enumerate(values['order_line']):
                 _logger.info(f"QLV DEBUG WRITE Line {i}: {cmd}")
        # 1. Check Locking Condition
        # If order is formally "Done" (Invoiced or Delivered), block critical edits.
        # Allow system updates (e.g. from stock moves) or whitelist fields if needed.
        # But user wants strict constraint.
        for order in self:
            is_locked = order.invoice_status == 'invoiced' or order.custom_state == 'done_delivery'
            # Allow state changes or updates from system context (bypass checks if user is superuser or specific context?)
            # Simplest approach: If locked, raise Error unless it's a state change or innocuous field.
            
            # Checks:
            if is_locked and not self.env.context.get('bypass_lock'):
                # Check what is being modified.
                # If modifying lines, partner, or date -> Block.
                critical_fields = {'order_line', 'partner_id', 'date_order', 'picking_ids'}
                if any(f in values for f in critical_fields):
                     raise UserError(_("Đơn hàng đã hoàn tất (Đã xuất hàng/hóa đơn). Không thể chỉnh sửa! Vui lòng Hủy đơn hàng để làm lại."))
        
        # 2. SANITIZE INPUT: Drop "Ghost" lines (Empty lines) preventing "Missing Description" error.
        # When clicking Confirm, Odoo saves edits. If an empty line exists, it sends (0, 0, {}) or similar.
        # We must filter these out before they hit DB validation.
        if 'order_line' in values:
            clean_lines = []
            for cmd in values['order_line']:
                # cmd format: [operation, id, vals]
                # operation 0 = Create
                if cmd[0] == 0:
                    vals = cmd[2]
                    # Check if essentially empty (No name, no product, no display_type)
                    has_content = vals.get('name') or vals.get('product_id') or vals.get('display_type')
                    if not has_content:
                        continue # Skip this ghost line
                clean_lines.append(cmd)
            values['order_line'] = clean_lines

        return super(SaleOrder, self).write(values)

    def action_super_cancel(self):
        """
        Nút Hủy đơn hàng quyền lực (Super Cancel):
        1. Hủy hóa đơn (Nội bộ & Khách hàng).
        2. Hủy lệnh chuyển hàng (Hoặc trả hàng).
        3. Hủy đơn hàng -> Set về Draft.
        """
        for order in self:
            # 1. Cancel Invoices
            invoices = order.invoice_ids.filtered(lambda i: i.state != 'cancel')
            if invoices:
                # If Posted, try to Reset to Draft first (if Journal allows) or just Cancel
                # Often need access rights or Journal setting "Allow cancelling".
                # We assume standard flow: Draft -> Cancel.
                for inv in invoices:
                    if inv.state == 'posted':
                        inv.button_draft()
                    inv.button_cancel()
            
            # 2. Cancel Pickings
            # If picking is Done, we cannot cancel it easily in standard Odoo.
            # We strictly should create a Return. But user requested "Revert".
            # "Revert" implies "Make it as if it never happened".
            # For "Done" pickings, we can try to "Return" them all?
            # Or if it's "Draft/Waiting", cancel.
            pickings = order.picking_ids.filtered(lambda p: p.state != 'cancel')
            for picking in pickings:
                if picking.state == 'done':
                    # Automate Return: Create -> Process -> Validate
                    # 1. Initialize Return Wizard
                    StockReturnPicking = self.env['stock.return.picking']
                    # Context is strictly needed for the wizard to know which picking to return
                    ctx = {'active_id': picking.id, 'active_ids': [picking.id], 'active_model': 'stock.picking'}
                    return_wiz = StockReturnPicking.with_context(ctx).create({})
                    
                    # 2. Create Returns
                    # create_returns returns an action dict, we extract the new picking ID
                    res = return_wiz.create_returns()
                    return_pick_id = res.get('res_id')
                    
                    if return_pick_id:
                        return_pick = self.env['stock.picking'].browse(return_pick_id)
                        
                        # 3. Auto-Validate the Return
                        # Ensure quantities are set to avoid "Immediate Transfer" wizard
                        for move in return_pick.move_ids:
                            move.quantity_done = move.product_uom_qty
                        
                        return_pick.button_validate()
                else:
                    picking.action_cancel()

            # 3. Cancel Sale Order
            if order.state not in ('draft', 'cancel'):
                order.with_context(bypass_lock=True).action_cancel()
            
            # 4. Set to Draft (Reset)
            order.with_context(bypass_lock=True).action_draft()
            
        return True


    pending_order_ids = fields.One2many('sale.order', compute='_compute_pending_order_ids', string='Đơn hàng chưa hoàn thành')
    pending_pawn_ids = fields.One2many('pawn.order', compute='_compute_pending_order_ids', string='Đơn Cầm cố đang hiệu lực')
    auto_balance_money = fields.Boolean('Tự động thanh toán Tiền mặt', default=True, help="Nếu bật, hệ thống sẽ tự động thêm dòng Tiền mặt để cân bằng đơn hàng về 0.")

    # === Fields for Custom List View ===
    summary_goods_in = fields.Char('Hàng Nhập', compute='_compute_custom_list_view_summary', store=True)
    summary_goods_out = fields.Char('Hàng Xuất', compute='_compute_custom_list_view_summary', store=True)
    money_total_in = fields.Monetary('Tiền Nhập', compute='_compute_custom_list_view_summary', store=True, currency_field='currency_id')
    money_total_out = fields.Monetary('Tiền Xuất', compute='_compute_custom_list_view_summary', store=True, currency_field='currency_id')

    # === Separate Tabs for Sales & Trade-in ===
    # These fields provide a filtered view of 'order_line' for easier management.
    # Note: Editing these fields will update 'order_line' due to the shared inverse 'order_id'.
    order_line_sell = fields.One2many(
        'sale.order.line', 'order_id', 
        string='Chi tiết Bán hàng',
        domain=[('is_trade_in', '=', False)],
        help="Dòng hàng Bán (Doanh thu)."
    )
    order_line_trade_in = fields.One2many(
        'sale.order.line', 'order_id', 
        string='Chi tiết Mua hàng',
        domain=[('is_trade_in', '=', True)],
        context={'default_is_trade_in': True},
        help="Dòng hàng Mua vào (Cầm đồ/Đổi hàng)."
    )

    custom_state = fields.Selection([
        ('draft', 'Đang lập phiếu'), # Was Báo giá/Draft
        ('sent', 'Đang lập phiếu đã gửi'), # Was Báo giá đã gửi
        ('sale', 'Hợp đồng'), # Was Đơn hàng
        ('partial', 'Đang giao dịch'), # Was Đã giao một phần
        ('done_delivery', 'Đã giao dịch (Chờ hóa đơn)'), # Was Giao xong
        ('invoiced', 'Đã giao dịch'), # Was Đã xuất hóa đơn -> Unified concept 'Đã giao dịch' or 'Xong'? User said 'invoiced' -> 'Đã giao dịch'.
        ('cancel', 'Đã hủy'),
    ], string='Tình trạng', compute='_compute_custom_state', store=True)

    trade_in_total = fields.Monetary(string='Tổng tiền Thu mua', compute='_compute_trade_in_total', store=True)

    @api.depends('order_line.price_subtotal', 'order_line.is_trade_in')
    def _compute_trade_in_total(self):
        for order in self:
            # Sum of all lines where is_trade_in is True
            # Note: price_subtotal for trade-in is typically negative in our current logic.
            # But the report might want to show the absolute value or the net effect.
            # Let's check how price_subtotal is stored.
            # In Models, we set price_unit to negative. So price_subtotal is negative.
            # The report likely wants to show positive absolute value for "Trade-in Total".
            total = sum(l.price_subtotal for l in order.order_line if l.is_trade_in and not l.display_type)
            order.trade_in_total = abs(total)

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
                    # Trade-in price is negative.
                    # User Request: "Mua hàng (Buy): Là chi tiền ra -> Hiển thị (-)."
                    # Previously: val_out += abs(line.price_subtotal) (Positive)
                    # Now: Keep actual negative value or ensure result is negative.
                    # Since price_subtotal is already negative for Trade In, we just add it to val_out accumulator?
                    # No, val_out field is likely expected to be "Total Amount". 
                    # If field is Monetary, -100 displays as "-100".
                    # So we want val_out to be -100.
                    # line.price_subtotal is -100.
                    # So: val_out += line.price_subtotal.
                    
                    val_out += line.price_subtotal 
                else:
                    # Sell Item (Goods Out) -> Revenue (Money In)
                    goods_out_list.append(item_str)
                    # Sell item subtotal is Positive (+).
                    # User Request: "Bán hàng (Sell): Là thu tiền về -> Hiển thị (+)."
                    val_in += line.price_subtotal

            order.summary_goods_in = ", ".join(goods_in_list)
            order.summary_goods_out = ", ".join(goods_out_list)
            order.money_total_in = val_in
            order.money_total_out = val_out

    @api.onchange('order_line', 'order_line_sell', 'order_line_trade_in', 'auto_balance_money')
    def _onchange_balance_money(self):
        """
        Tự động tính toán dòng tiền cân bằng (Fix Phase 13 Issue).
        Logic cập nhật để xử lý: 
        1. Zombie Lines (Dòng đã xóa bị hiện lại).
        2. Stale Money (Tiền không cập nhật khi xóa).
        3. Duplicate Key / Wrong Calc: Loại bỏ dòng tiền ra khỏi danh sách Hàng hóa.
        
        Giải pháp: 
        - Source of Truth: Tab Bán/Mua (đã lọc bỏ dòng tiền).
        - Tính toán: Chỉ sum hằng số Goods.
        - Master Sync: Reconstruct lại list = Goods + 1 Money Line.
        """
        if not self.auto_balance_money:
            return

        company = self.company_id or self.env.company
        money_product = company.money_product_id
        rounding_precision = company.currency_id.rounding or 0.001
        
        # --- 1. Identify Components (Deletion Handling & Clean Separation) ---
        
        # Lists from Tabs (The Authority for their respective domains)
        # CRITICAL FIX: Filter out Auto-Balance lines from Tabs immediately
        # The Tabs might contain the auto-balance line because of domain match (is_trade_in), 
        # but for calculation purposes, we treat them strictly as "Goods".
        tab_sell_lines = self.order_line_sell.filtered(lambda l: not l.is_auto_balance)
        tab_buy_lines = self.order_line_trade_in.filtered(lambda l: not l.is_auto_balance)
        
        # Master List
        master_lines = self.order_line
        
        # Identify Existing Auto-Balance Lines from Master (for updating)
        current_money_lines = master_lines.filtered(lambda l: l.is_auto_balance)
        
        # Identify "Other" lines (Notes, Sections, or lines not covered by Tabs)
        # Strategy: Keep lines from Master ONLY if they don't belong to Sell/Buy domains.
        # If they belong to Sell/Buy domain but are missing from Tabs, they are effectively deleted.
        
        # Note: We already filtered tab_sell/buy to exclude auto_balance.
        # So we just need to ensure we don't accidentally drop valid goods.
        
        preserved_other_lines = self.env['sale.order.line']
        
        # We need a robust way to know if a line "Should belong to Sell Tab".
        # Definition: is_trade_in=False AND is_auto_balance=False.
        
        for line in master_lines:
            if line.is_auto_balance:
                continue # We reconstruct money line later, don't preserve it here
                
            if line.is_trade_in:
                # Should be in Buy Tab
                if line not in tab_buy_lines:
                     continue # Deleted from Buy Tab -> Drop
            else:
                # Should be in Sell Tab
                if line not in tab_sell_lines:
                     continue # Deleted from Sell Tab -> Drop
            
            # If line is in tab lists, it's safe.
            # If line is something else (e.g. unknown domain?), preserve it.
            # But currently our domain covers everything (True/False).
            pass

        # Since tab_sell_lines and tab_buy_lines cover all "Goods" (non-money) scenarios,
        # The Union of them IS the source of truth for Goods.
        
        # CRITICAL FIX (Step 2090): Filter out "Empty/Ghost" lines that have no Name/Product/Type.
        # These lines might be created in UI (NewId) but not filled, causing "Missing Description" error on Confirm.
        all_goods_lines = (tab_sell_lines | tab_buy_lines).filtered(
            lambda l: l.display_type or l.product_id or l.name
        )
        
        # --- 2. Calculate Balance Needed ---
        grand_total_goods = sum(l.price_subtotal for l in all_goods_lines if not l.display_type)
        balance_needed = -grand_total_goods
        
        # --- 3. Manage Money Line ---
        money_vals = {}
        has_money_needed = abs(balance_needed) >= rounding_precision
        
        if has_money_needed:
            # Prepare Values
            money_vals = {
                'product_id': money_product.id if money_product else False,
                'original_product_id': money_product.id if money_product else False,
                'is_auto_balance': True,
                'sequence': 9999, 
                'product_uom': money_product.uom_id.id if money_product else False,
            }
            # Determine Direction
            if balance_needed < 0:
                 # "Thu tiền về"
                 money_vals.update({
                     'is_trade_in': True,
                     'price_unit_base': 1.0, 
                     'product_uom_qty': abs(balance_needed), 
                     'price_unit': -1.0,
                     'name': 'Thu tiền mặt (Tự động)'
                 })
            else:
                 # "Chi tiền ra"
                 money_vals.update({
                     'is_trade_in': False, 
                     'price_unit_base': 1.0, 
                     'product_uom_qty': abs(balance_needed), 
                     'price_unit': 1.0,
                     'name': 'Chi tiền mặt (Tự động)'
                 })

        # --- 4. Apply Updates to Master ---
        
        # Reconstruct Master = All Goods + (Money Line if needed)
        final_lines = all_goods_lines
        
        if not money_product:
             pass
        elif has_money_needed:
             if current_money_lines:
                 # Update existing (Use the first one found)
                 money_line = current_money_lines[0]
                 money_line.update(money_vals)
                 final_lines += money_line
                 
                 # Remove extra duplicate money lines if any existed
                 if len(current_money_lines) > 1:
                     # They are not added to final_lines, so they will be unlinked/removed from relation
                     pass
             else:
                 # Create New
                 new_money = self.env['sale.order.line'].new(money_vals)
                 final_lines += new_money
        
        # CRITICAL ASSIGNMENT & FOCUS OPTIMIZATION
        # Only assign if the Recordset content has changed (e.g. Added/Removed lines).
        # If only values changed (e.g. Qty update), final_lines == self.order_line (Set comparison)
        # This prevents full re-render and preserves Focus.
        if self.order_line != final_lines:
            self.order_line = final_lines
        
        # --- 5. Force UI Refresh ---
        # Similarly, only push to Tabs if Master changed or if we need to sync specific filtered views.
        # But for Tabs, we rely on the filtered set.
        # If self.order_line changed, we MUST update tabs.
        # If self.order_line didn't change (Value update), Tabs usually reflect it auto-magically?
        # To be safe and preserve focus, we also check equality.
        
        new_sell = self.order_line.filtered(lambda l: not l.is_trade_in)
        new_buy = self.order_line.filtered(lambda l: l.is_trade_in)
        
        if self.order_line_sell != new_sell:
            self.order_line_sell = new_sell
            
        if self.order_line_trade_in != new_buy:
             self.order_line_trade_in = new_buy


    @api.depends('partner_id')
    def _compute_pending_order_ids(self):
        for order in self:
            if not order.partner_id:
                order.pending_order_ids = False
                order.pending_pawn_ids = False
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
                ('state', '=', 'sale'),
                ('custom_state', 'in', ('sale', 'partial', 'done_delivery')),
            ]
            
            # Avoid NewId error: Only exclude self if ID is real (integer)
            if isinstance(order.id, int):
                domain.append(('id', '!=', order.id))
                
            order.pending_order_ids = self.search(domain)
            
            # Compute Pawn Orders (Active)
            pawn_domain = [
                ('partner_id', '=', order.partner_id.id),
                ('state', 'in', ('draft', 'confirmed')),
            ]
            order.pending_pawn_ids = self.env['pawn.order'].search(pawn_domain)


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
        # CLEANUP: Remove "Ghost" lines (Empty lines from UI) before Confirming
        # This prevents "Missing Description (name)" error if user added a line but left it empty.
        # We check for lines with no Display Type (Section/Note), No Product, and No Name.
        empty_lines = self.order_line.filtered(lambda l: not l.display_type and not l.product_id and not l.name)
        if empty_lines:
            for line in empty_lines: # Added loop as per instruction
                line.unlink()
            
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
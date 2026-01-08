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
                     # Strict Sanitize: If not a Note/Section, it MUST have a Product.
                     is_section_or_note = v.get('display_type')
                     has_product = v.get('product_id')
                     
                     if not is_section_or_note and not has_product:
                         _logger.warning(f"QLV INFO: Dropped invalid line (No Product) at creation index {i}")
                         continue 
                clean_lines.append(cmd)
            vals['order_line'] = clean_lines

        return super(SaleOrder, self).create(vals)

    def write(self, values):


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
                    # Strict Sanitize: If not a Note/Section, it MUST have a Product.
                    # Otherwise, it's a "ghost" line (e.g. user typed search text "4 số" but didn't pick product).
                    is_section_or_note = vals.get('display_type')
                    has_product = vals.get('product_id')
                    
                    if not is_section_or_note and not has_product:
                         _logger.warning(f"QLV INFO: Dropped invalid line (No Product) in write: {vals}")
                         continue # Skip this invalid line
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
                # Fail-safe: If action_cancel didn't update state (e.g. silent failure), force it.
                if order.state != 'cancel':
                    order.with_context(bypass_lock=True).write({'state': 'cancel'})
            
            # 4. Set to Draft (Reset)
            order.with_context(bypass_lock=True).action_draft()
            
        return True


    pending_order_ids = fields.One2many('sale.order', compute='_compute_pending_order_ids', string='Đơn hàng chưa hoàn thành')
    # pending_pawn_ids = fields.One2many('pawn.order', compute='_compute_pending_order_ids', string='Đơn Cầm cố đang hiệu lực')
    auto_balance_money = fields.Boolean('Tự động thanh toán Tiền mặt', default=True, help="Nếu bật, hệ thống sẽ tự động thêm dòng Tiền mặt để cân bằng đơn hàng về 0.")

    # Status Link to New Order (Forward Link)
    settled_to_order_id = fields.Many2one('sale.order', compute='_compute_settled_to_order', string='Đã thanh toán qua đơn')


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
            # 1. Base State validation
            if order.state in ('draft', 'sent', 'cancel'):
                order.custom_state = order.state
                continue
                
            if order.state == 'done':
                order.custom_state = 'done_delivery' # Treat Locked/Done as "Completed"
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

    # === PHASE 15: LEGACY TRANSACTION LOGIC ===
    
    legacy_type = fields.Selection([
        ('nhap', 'Đơn Nhập'),
        ('xuat', 'Đơn Xuất'),
        ('hdkb', 'HĐKB'), # Hợp đồng Khách Bán
        ('hdkm', 'HĐKM'), # Hợp đồng Khách Mua
        ('mixed', 'Hỗn hợp'),
    ], string='Loại Phiếu (Legacy)', compute='_compute_legacy_type', store=True)

    def action_confirm(self):
        """
        Phase 17 Override: Handle Deferred Debt Settlement.
        Also includes Legacy Trade-in Receipt Logic and Ghost Line Cleanup.
        """
        _logger.warning(f">>> ACTION CONFIRM CALLED for {self.mapped('name')} <<<")

        # 1. CLEANUP: Remove "Ghost" lines (Empty lines from UI)
        empty_lines = self.order_line.filtered(lambda l: not l.display_type and not l.product_id and not l.name)
        if empty_lines:
            empty_lines.unlink()

        # CRASH TEST (Verify this method runs)
        # raise UserError("QLV CRASH TEST: ACTION CONFIRM MERGED!")

        res = super(SaleOrder, self).action_confirm()

        for order in self:
            _logger.warning(f"DEBUG: Processing Settlement for Order {order.name} (ID {order.id})")
            
            # 2. LEGACY: Trade-in Picking Logic (Split by Procurement Group)
            trade_in_moves = order.picking_ids.move_ids_without_package.filtered(
                lambda m: m.sale_line_id and m.sale_line_id.is_trade_in
            )
            
            if trade_in_moves:
                # Group moves by Procurement Group
                grouped_moves = {}
                for move in trade_in_moves:
                    group = move.group_id
                    if group not in grouped_moves:
                        grouped_moves[group] = self.env['stock.move']
                    grouped_moves[group] |= move
                
                # Process each Group
                for group, moves in grouped_moves.items():
                    # Find existing receipt for THIS group
                    # Search criteria: Incoming, Not Done/Cancel, Same Group
                    domain = [
                        ('picking_type_id.code', '=', 'incoming'),
                        ('state', 'not in', ('done', 'cancel')),
                        ('group_id', '=', group.id if group else False),
                        ('origin', '=', order.name) # Ensure it belongs to this order
                    ]
                    # If group is False, we might merge? Or keep distinct?
                    # Safest: Use group_id match.
                    
                    receipt_picking = self.env['stock.picking'].search(domain, limit=1)
                    
                    if not receipt_picking:
                        picking_vals = order._prepare_trade_in_picking()
                        # IMPORTANT: Assign the correct Group to the Picking
                        if group:
                            picking_vals['group_id'] = group.id
                        
                        receipt_picking = self.env['stock.picking'].create(picking_vals)

                    # Assign Moves to this Picking
                    moves.write({
                        'picking_id': receipt_picking.id,
                        'location_id': receipt_picking.location_id.id,
                        'location_dest_id': receipt_picking.location_dest_id.id,
                    })
                    # Explicitly update move lines
                    if moves.move_line_ids:
                        moves.move_line_ids.write({
                            'picking_id': receipt_picking.id,
                            'location_id': receipt_picking.location_id.id,
                            'location_dest_id': receipt_picking.location_dest_id.id,
                        })

                # Cancel empty delivery pickings
                for picking in order.picking_ids:
                    if picking.picking_type_id.code == 'outgoing' and not picking.move_ids_without_package:
                        picking.action_cancel()

            # 3. NEW: Deferred Debt Settlement Lock
            settlement_lines = order.order_line.filtered(lambda l: l.settled_order_id)
            if settlement_lines:
                _logger.info(f"DEBUG: Found {len(settlement_lines)} settlement lines")
                old_orders = settlement_lines.mapped('settled_order_id')
                
                for old_order in old_orders:
                    if old_order.state != 'done':
                        try:
                            # 1. CANCEL PENDING PICKINGS on Old Order
                            # Logic: Obligation transferred to New Order, so Old Order logistics are void.
                            pending_pickings = old_order.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))
                            if pending_pickings:
                                _logger.info(f"DEBUG: Cancelling {len(pending_pickings)} pending pickings for OLD Order {old_order.name}")
                                # Force cancel even if strictly not allowed by standard flow? 
                                # Standard action_cancel() usually works if not done.
                                pending_pickings.action_cancel()
                                old_order.message_post(body=_("Đã hủy phiếu kho treo trước khi khóa đơn (Do chuyển nghĩa vụ sang đơn %s)") % order.name)

                            # 2. LOCK ORDER
                            old_order.action_done() 
                            _logger.info(f"DEBUG: Called action_done() on {old_order.name}")
                            old_order.message_post(body=_("Đơn hàng đã được Khóa tự động do đơn thanh toán bù trừ %s đã được xác nhận.") % order.name)
                            order.message_post(body=_("Đã kích hoạt khóa đơn cũ %s sau khi xác nhận đơn hàng này.") % old_order.name)
                        except Exception as e:
                            _logger.error(f"DEBUG: Failed to Lock {old_order.name}: {e}")
            
        return res



    def action_settle_debt(self):
        """
        Create a Settlement line on the Target Order (New Order).
        Context must contain 'target_order_id'.
        """
        target_order_id = self.env.context.get('target_order_id')
        if not target_order_id:
            return

        target_order = self.env['sale.order'].browse(target_order_id)
        
        for old_order in self:
            # Simplified Logic: Settle Entry Amount
            # In a real scenario, this matches 'amount_residual'.
            amount = old_order.amount_total
            
            # Find a product (Money/Gold)
            product = self.env['product.product'].search([('name', 'ilike', '3 số')], limit=1)
            if not product:
                product = self.env['product.product'].search([], limit=1)
                
    def action_settle_debt(self):
        """
        Phase 19: Full Settlement Transfer (Chuyển Đơn).
        Logic:
        1. Iterate through Old Order lines.
        2. Calculate Net Qty = Delivered - Received (Pending Obligation).
        3. If Net != 0 -> Create lines in New Order to continue the obligation.
           - Net > 0 (Cust owes Goods) -> Trade-in Line (Thu hồi).
           - Net < 0 (Shop owes Goods) -> Sell Line (Bán/Trả).
        4. Financial Offset (Bù trừ tiền):
           - If Old Order has excess payment (Paid > Delivered Value), 
             create an Offset Line (Trade-in Money) in New Order to balance the transferred Goods Value.
        """
        target_order_id = self.env.context.get('target_order_id')
        if not target_order_id:
            return

        target_order = self.env['sale.order'].browse(target_order_id)
        
        # Track Total Transferred Sell Value for Financial Offset Check
        total_transferred_sell_value = 0.0
        
        for old_order in self:
            # GUARD CLAUSE: Strict Settlement Rule
            # Request: Only transfer orders that have NOT executed any Delivery/Receipt.
            # If any picking is Done, we Redirect user to Old Order to handle manually.
            has_done_pickings = old_order.picking_ids.filtered(lambda p: p.state == 'done')
            if has_done_pickings:
                _logger.warning(f"SETTLE: Order {old_order.name} has executed pickings. Redirecting.")
                # Show specific message? Or just redirect.
                # Returning an action from here (inside loop) only works for the first one.
                # Assuming 'self' is usually one order in this context (called via UI).
                message = _("Đơn hàng cũ %s đã có giao dịch kho/tiền. Vui lòng xử lý thủ công trên đơn cũ.") % old_order.name
                
                # We can post a message on Current Order too
                if target_order:
                    target_order.message_post(body=message)

                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'sale.order',
                    'res_id': old_order.id,
                    'view_mode': 'form',
                    'views': [(False, 'form')],
                    'target': 'current',
                }

            _logger.info(f"SETTLE: processing Old Order {old_order.name}")
            
            # --- STOCK OBLIGATION TRANSFER ---
            for line in old_order.order_line:
                if line.display_type: 
                    continue

                # HYBRID LOGIC:
                # 1. Skip "Payment" Lines (Trade-in Money). We handle Payments via Financial Balance.
                # 2. Skip "Auto-Balance" Lines. These are calculation artifacts, not real debts.
                #    If there is a financial imbalance, the Offset Logic will capture it.
                if line.is_auto_balance:
                    continue
                    
                if line.product_id == old_order.company_id.money_product_id and line.is_trade_in:
                    continue
                
                # Check custom "Money" products by name if needed
                # (Assuming 'Tiền' + is_trade_in is the standard Payment line)

                # Calculate Pending Qty based on STOCK MOVES (Physical execution)
                pending_qty = line.product_uom_qty - line.qty_delivered
                
                # Filter small rounding errors
                if abs(pending_qty) < 0.0001:
                    continue
                    
                _logger.info(f"   Line {line.product_id.name}: Ordered {line.product_uom_qty}, Done {line.qty_delivered}, Pending {pending_qty}")

                # Prepare New Line Values
                vals = {
                    'order_id': target_order.id,
                    'product_id': line.product_id.id,
                    'original_product_id': line.original_product_id.id if line.original_product_id else line.product_id.id,
                    'product_uom_qty': abs(pending_qty),
                    'product_uom': line.product_uom.id,
                    'price_unit': line.price_unit, # PRESERVE PRICE
                    'gold_purity': line.gold_purity,
                    'settled_order_id': old_order.id,
                    'sequence': 900, 
                    'is_auto_balance': False, 
                    
                    # Fix 2: Propagate Original UoM & Calculate Pending Original Weight
                    'original_uom_id': line.original_uom_id.id,
                }
                
                # Calculate Proportional Original Weight
                # pending_weight = total_weight * (pending_qty / total_qty)
                if line.product_uom_qty > 0 and line.original_weight > 0:
                     ratio = abs(pending_qty) / line.product_uom_qty
                     vals['original_weight'] = line.original_weight * ratio
                else:
                     vals['original_weight'] = line.original_weight

                # Fix 1: Use Original Product Name in Description
                product_name = line.original_product_id.name if line.original_product_id else line.product_id.name
                
                if not line.is_trade_in:
                    vals.update({
                        'is_trade_in': False,
                        # Use Original Product Name
                        'name': _("Chuyển giao hàng: %s (Từ %s)") % (product_name, old_order.name)
                    })
                    total_transferred_sell_value += (vals['product_uom_qty'] * vals['price_unit'])
                else:
                    vals.update({
                        'is_trade_in': True,
                        # Use Original Product Name
                        'name': _("Chuyển thu hồi: %s (Từ %s)") % (product_name, old_order.name)
                    })
                
                self.env['sale.order.line'].create(vals)

            # --- FINANCIAL OFFSET LOGIC (Bù trừ tiền) ---
            # Calculates the Net Financial Position of the Old Order.
            # Balance = (Money Paid Actual) - (Value of Goods Delivered Actual)
            
            # 1. Money In/Out Actuals
            money_lines = old_order.order_line.filtered(lambda l: l.product_id == old_order.company_id.money_product_id)
            total_paid = sum(abs(l.qty_delivered * l.price_unit) for l in money_lines if l.is_trade_in)
            total_change = sum(abs(l.qty_delivered * l.price_unit) for l in money_lines if not l.is_trade_in)
            net_paid_actual = total_paid - total_change
            
            # 2. Goods Value Actuals
            sell_lines = old_order.order_line.filtered(lambda l: not l.is_trade_in and not l.is_auto_balance and not l.display_type and l.product_id != old_order.company_id.money_product_id)
            # Note: Do we count Trade-in Goods? 
            # If Customer gave us Gold (-100). That is Payment.
            # Currently logic separates "Money" vs "Goods".
            # If Trade-in is Goods, it should convert to Money equivalent? 
            # QLV Standard: Trade-in reduces Total.
            # Balance = (Total Credits) - (Total Debits).
            # Credits = Money In + Trade-in Goods Received.
            # Debits = Money Out + Sell Goods Delivered.
            
            trade_in_goods = old_order.order_line.filtered(lambda l: l.is_trade_in and not l.is_auto_balance and not l.display_type and l.product_id != old_order.company_id.money_product_id)
            value_trade_in_received = sum(abs(l.qty_delivered * l.price_unit) for l in trade_in_goods)
            
            value_delivered_out = sum(l.qty_delivered * l.price_unit for l in sell_lines)
            
            total_credits = net_paid_actual + value_trade_in_received
            total_debits = value_delivered_out
            
            balance = total_credits - total_debits
            
            company = old_order.company_id
            money_prod = company.money_product_id
            
            # Case A: SURPLUS (Excess > 0) -> Customer Paid too much.
            # We credit them on New Order (Trade-in Money).
            # Limit: We can credit up to the amount required to cover the Transfer? 
            # Or just credit the whole balance?
            # User expectation: "Offset corresponding to transferred goods".
            # If Transfer Value = 200. Surplus = 400. Offset = 200? Or 400?
            # Safest: Offset matches the Transfer Obligation first.
            # Actually, standard accounting: Just bring the balance forward.
            # If Balance is +400. New Order gets -400 (Trade-in). Total Reduces.
            if balance > 0.01:
                # Limit offset to transferred value? 
                # If we transfer 200 of goods. Balance 400.
                # New Order: Sell 200. Trade-in 200. (Net 0). Leftover 200?
                # Ideally we transfer FULL Balance.
                offset_amount = balance # Transfer full surplus
                
                offset_vals = {
                    'order_id': target_order.id,
                    'product_id': money_prod.id,
                    'product_uom_qty': 1,
                    'price_unit': -offset_amount,
                    'is_trade_in': True,
                    'settled_order_id': old_order.id,
                    'name': _("Bù trừ dư: Đơn %s") % old_order.name,
                    'is_auto_balance': False,
                    'sequence': 999,
                }
                self.env['sale.order.line'].create(offset_vals)
                old_order.message_post(body=_("Đã chuyển số dư thừa (%s) sang đơn mới") % offset_amount)

            # Case B: DEFICIT (Excess < 0) -> Customer Owes Money.
            # We charge them on New Order (Sell Money).
            # e.g. Balance = -300k. New Order gets +300k (Sell).
            elif balance < -0.01:
                debt_amount = abs(balance)
                
                debt_vals = {
                    'order_id': target_order.id,
                    'product_id': money_prod.id,
                    'product_uom_qty': 1,
                    'price_unit': debt_amount,
                    'is_trade_in': False, # SELL (Charge)
                    'settled_order_id': old_order.id,
                    'name': _("Truy thu nợ cũ: Đơn %s") % old_order.name,
                    'is_auto_balance': False,
                    'sequence': 999,
                }
                self.env['sale.order.line'].create(debt_vals)
                old_order.message_post(body=_("Đã chuyển khoản nợ (%s) sang đơn mới") % debt_amount)

            target_order.message_post(body=_("Đã nhận chuyển giao nghĩa vụ từ đơn cũ %s") % old_order.name)
            
            # FORCE AUTO-BALANCE UPDATE
            # Since lines were created in backend, UI Onchange didn't run.
            target_order.update_auto_balance_money_db()
            
        return True

    def update_auto_balance_money_db(self):
        """
        Calculates and updates the Auto-Balance Money Line directly in the Database.
        Used for backend operations (like Settlement) where Onchange logic is not triggered.
        """
        self.ensure_one()
        if not self.auto_balance_money:
            return

        company = self.company_id or self.env.company
        money_product = company.money_product_id
        rounding_precision = company.currency_id.rounding or 0.001
        
        # 1. Identify Goods Lines (Excluding Auto Balance)
        all_lines = self.order_line
        goods_lines = all_lines.filtered(
            lambda l: not l.is_auto_balance and (l.display_type or l.product_id)
        )
        
        # 2. Calculate Balance
        # Important: Ensure price_subtotal is up-to-date.
        # If this runs in the same transaction as creation, computed fields *should* be available via ORM cache.
        grand_total_goods = sum(l.price_subtotal for l in goods_lines if not l.display_type)
        balance_needed = -grand_total_goods
        
        # 3. Manage Money Line
        current_money_line = all_lines.filtered(lambda l: l.is_auto_balance)
        has_money_needed = abs(balance_needed) >= rounding_precision
        
        if not has_money_needed:
            if current_money_line:
                current_money_line.unlink()
            return

        # Prepare Values
        vals = {
            'product_id': money_product.id,
            'is_auto_balance': True,
            'sequence': 9999,
            'product_uom': money_product.uom_id.id,
        }
        
        if balance_needed < 0:
             # Negative Balance -> Order is Negative Value (Credit/Trade-In Surplus)
             # Need "Thu tiền về" (Trade-In Money with Negative Price? No, Trade-In is Buy).
             # Standard Logic: 
             # Goods subtotal is Negative (Trade In). 
             # Grand Total Goods = -100.
             # Balance Needed = -(-100) = +100.
             # Need +100. 
             # Wait.
             # If Trade-In (Customer gives Goods, Value -100).
             # Payment normally is +100 (Shop Pays Customer).
             # My Logic:
             # balance_needed > 0 -> "Chi tiền ra" (Shop Pays).
             # balance_needed < 0 -> "Thu tiền về" (Customer Pays).
             
             # Re-verify calculation:
             # grand_total_goods = Sum(price_subtotal).
             # Sell (Pos), TradeIn (Neg).
             # If Sell 100. Grand Total = 100. Balance Needed = -100 (Customer Pays).
             # If Balance < 0 -> Customer Pays -> "Thu tiền về".
             vals.update({
                 'is_trade_in': True,
                 'price_unit': -1.0, 
                 'product_uom_qty': abs(balance_needed),
                 'name': 'Thu tiền mặt (Tự động)'
             })
        else:
             # Balance > 0 -> Shop Pays -> "Chi tiền ra".
             vals.update({
                 'is_trade_in': False,
                 'price_unit': 1.0, 
                 'product_uom_qty': abs(balance_needed),
                 'name': 'Chi tiền mặt (Tự động)'
             })

        if current_money_line:
            current_money_line[0].write(vals)
            if len(current_money_line) > 1:
                (current_money_line - current_money_line[0]).unlink()
        else:
            vals['order_id'] = self.id
            self.env['sale.order.line'].create(vals)

    legacy_transaction_status = fields.Selection([
        ('none', '-'),
        ('khach_no', 'Khách Nợ'),
        ('khach_gui', 'Khách Gửi / Dư'),
        ('can_bang', 'Cân bằng'),
    ], string='Trạng thái Nợ (Legacy)', compute='_compute_legacy_transaction_status', store=True)
    
    @api.depends('order_line', 'order_line.price_subtotal', 'order_line.is_trade_in', 'state')
    def _compute_legacy_type(self):
        for order in self:
            # 1. Calculate Dominant Value
            # Sell Value (is_trade_in=False)
            # REVERT: Only exclude strictly Auto-Balance lines. Manual Money lines (Trading Currency) ARE valid goods.
            sell_lines = order.order_line.filtered(lambda l: not l.is_trade_in and not l.is_auto_balance and not l.display_type)
            buy_lines = order.order_line.filtered(lambda l: l.is_trade_in and not l.is_auto_balance and not l.display_type)
            
            # Use count if values are zero (e.g. new lines with no price yet)
            total_sell = sum(sell_lines.mapped('price_subtotal'))
            total_buy = sum(l.price_subtotal for l in buy_lines)
            
            total_buy_abs = abs(total_buy)
            
            # Determine Dominant Side
            # If values distinct, use value. If values both 0, use line count.
            if total_sell == 0 and total_buy_abs == 0:
                 is_sell_dominant = len(sell_lines) >= len(buy_lines)
            else:
                 is_sell_dominant = total_sell >= total_buy_abs
            
            # 2. Determine Prefix based on State
            if order.state in ('draft', 'sent', 'cancel'):
                # Quote Stage
                if not sell_lines and not buy_lines:
                    order.legacy_type = False
                elif is_sell_dominant:
                    order.legacy_type = 'nhap' # Khách mua hàng -> Shop Nhập yêu cầu? No, User said: Sell -> Nhập (Khách thiếu)
                else:
                    order.legacy_type = 'xuat' # Khách bán hàng -> Shop Xuất tiền? User said: Buy -> Xuất (Khách dư)
            else:
                # Contract Stage (sale, done)
                if not sell_lines and not buy_lines:
                    order.legacy_type = False
                elif is_sell_dominant:
                    order.legacy_type = 'hdkb' # Hợp đồng Khách Bán (Khách mua của mình) -> Terminology "Khách Bán" is confusing but User insisted: "Dòng hàng bán -> HĐKB"
                else:
                    order.legacy_type = 'hdkm' # Hợp đồng Khách Mua (Mình mua của khách) -> Terminology "HĐKM"

    @api.depends('order_line.qty_delivered', 'order_line.price_subtotal', 'amount_total', 'state')
    def _compute_legacy_transaction_status(self):
        """
        Khách Nợ: Giá trị Hàng Giao (Delivered Sell) > Giá trị Đã Nhận (Trade-in + Payment)
        Khách Gửi: Giá trị Đã Nhận > Giá trị Hàng Giao
        """
        for order in self:
            # Modified: Allow Draft state to show Projected Status
            # if order.state not in ('sale', 'done'):
            #    order.legacy_transaction_status = 'none'
            #    continue
                
            # 1. Total Value of Goods DELIVERED (Shop gave to Customer)
            # Only count Sell lines.
            sell_lines = order.order_line.filtered(lambda l: not l.is_trade_in and not l.display_type and not l.is_auto_balance)
            
            if order.state in ('draft', 'sent'):
                # Use Ordered Qty for projection
                value_delivered = sum(l.price_unit * l.product_uom_qty for l in sell_lines)
            else:
                # Use Delivered Qty for actual
                value_delivered = sum(l.price_unit * l.qty_delivered for l in sell_lines)
            
            # 2. Total Value RECEIVED (Shop received from Customer)
            # A. Trade-in Lines (Goods received)
            buy_lines = order.order_line.filtered(lambda l: l.is_trade_in and not l.display_type and not l.is_auto_balance)
            
            if order.state in ('draft', 'sent'):
                 value_received_goods = sum(abs(l.price_unit) * l.product_uom_qty for l in buy_lines)
            else:
                 value_received_goods = sum(abs(l.price_unit) * l.qty_delivered for l in buy_lines)

            # B. Money Received/Paid
            money_lines = order.order_line.filtered(lambda l: l.product_id.categ_id.name in ['Tiền', 'Money', 'Ngoại tệ'] or l.is_auto_balance)
            value_received_money = 0.0
            value_paid_money = 0.0
            
            for m in money_lines:
                # Money is always considered "delivered/received" based on Order Qty 
                # (assuming instant exchange, no stock picking for money usually)
                qty = m.product_uom_qty
                
                if m.is_trade_in:
                    # Thu tiền về (Received)
                    value_received_money += abs(m.price_unit) * qty
                else:
                    # Chi tiền ra (Paid)
                    value_paid_money += abs(m.price_unit) * qty

            # Total IN vs OUT
            # IN (Shop received) = Goods Buy + Money Buy (Thu)
            # OUT (Shop gave) = Goods Sell + Money Sell (Chi)
            
            total_shop_gave = value_delivered + value_paid_money
            total_shop_received = value_received_goods + value_received_money
            
            balance = total_shop_received - total_shop_gave
            
            # Formatting
            if abs(balance) < 1000: # Tolerance
                order.legacy_transaction_status = 'can_bang'
            elif balance < 0:
                # Shop gave > Shop received -> Customer owes -> "Khách Nợ"
                order.legacy_transaction_status = 'khach_no'
            else:
                # Shop received > Shop gave -> Customer holds credit -> "Khách Gửi"
                order.legacy_transaction_status = 'khach_gui'


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


    def _compute_settled_to_order(self):
        for order in self:
            # Search for lines in OTHER orders that reference THIS order
            linked_lines = self.env['sale.order.line'].search([('settled_order_id', '=', order.id)], limit=1)
            if linked_lines:
                order.settled_to_order_id = linked_lines.order_id
            else:
                order.settled_to_order_id = False

    @api.depends('partner_id')
    def _compute_pending_order_ids(self):
        for order in self:
            if not order.partner_id:
                order.pending_order_ids = False
                # order.pending_pawn_ids = False
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
            
            # Compute Pawn Orders (Active) -> REMOVED
            # pawn_domain = [
            #     ('partner_id', '=', order.partner_id.id),
            #     ('state', 'in', ('draft', 'confirmed')),
            # ]
            # order.pending_pawn_ids = self.env['pawn.order'].search(pawn_domain)


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
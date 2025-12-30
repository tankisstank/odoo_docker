from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _name = 'sale.order.line'
    _inherit = ['sale.order.line', 'product.conversion.mixin']

    # ... [Keep fields] ...
    # Mixin fields: is_trade_in, price_unit_base, gold_purity, etc. are inherited.
    
    trade_in_price_unit = fields.Float('Trade-in Price (Unit)')
    is_auto_balance = fields.Boolean('Tự động cân bằng', default=False, help="Dòng này được hệ thống tự động tạo ra để cân bằng tiền.")

    # Override for High Precision Display (4 digits)
    product_uom_qty = fields.Float(digits=(16, 4))
    
    # Phase 16: Unique Procurement Group per Line for Granular Pickings
    procurement_group_id = fields.Many2one('procurement.group', 'Lot/Serial Group', copy=False)
    
    # Phase 17: Link to Settled Order (Deferred Locking)
    settled_order_id = fields.Many2one('sale.order', 'Đơn hàng được thanh toán', readonly=True, copy=False)

    @api.onchange('original_product_id')
    def _onchange_original_product(self):
        """Set defaults when Original Product is selected."""
        for line in self:
            if not line.original_product_id:
                continue
            
            # 1. Set Default Purity & UoM
            line.gold_purity = line.original_product_id.gold_purity_standard or 1.0
            line.original_uom_id = line.original_product_id.uom_id
            
            # 2. Set Active Product (Target)
            # USER REQUEST: Default to Conversion Target if available.
            # Stock Logic relies on _prepare_procurement_values overriding this back to Original.
            if line.original_product_id.conversion_target_id:
                line.product_id = line.original_product_id.conversion_target_id
            else:
                line.product_id = line.original_product_id
                
            # 3. Set Default Exchange Rate (from Target Product or Original?)
            # Usually we take the Target Product's price as the base for exchange
            # If target exists, use its price. Else use own.
            target = line.original_product_id.conversion_target_id
            if target:
                line.exchange_rate = target.standard_price if line.is_trade_in else target.list_price
            elif line.product_id:
                line.exchange_rate = line.product_id.standard_price if line.is_trade_in else line.product_id.list_price

            # 4. Set Price Compensation from Variant Extra Price (PHASE 10)
            # Logic: Show UNIT Extra Price.
            # User Request: "ghi ra giá trị bổ sung từ biến thể... cộng vào... nhân tổng trọng lượng"
            price_extra = line.original_product_id.price_extra or 0.0
            line.price_compensation = price_extra


    @api.onchange('product_id', 'is_trade_in')
    def _onchange_product_target_defaults(self):
        """Update Exchange Rate when Target Product changes."""
        for line in self:
            if not line.product_id:
                continue
            # If manually changing Target, update rate if not set or if strictly following target
            # For now, let's just default it if it's 0 or 1
            if line.exchange_rate <= 1.0:
                 line.exchange_rate = line.product_id.standard_price if line.is_trade_in else line.product_id.list_price

    @api.onchange('original_weight', 'loss_weight', 'gold_purity', 'exchange_rate', 'price_compensation', 'product_id', 'is_trade_in')
    def _onchange_calculation_master(self):
        """
        MASTER CALCULATION LOGIC (REFACTORED)
        Triggers: Input Weight, Loss, Purity, Exchange Rate, Compensation, Target Product.
        Output: 
        - product_uom_qty = Net Weight (Original Qty)
        - price_unit = Equivalent Price (Total Value / Net Weight)
        """
        for line in self:
            # 0. Basic Inputs
            net_weight = max(0, line.original_weight - line.loss_weight)
            purity = line.gold_purity or 0.0
            exchange_rate = line.exchange_rate or 0.0
            
            # PHASE 10: Auto-Calculate Compensation from Variant Extra Price
            # Logic: Default to Variant's Extra Price (Unit) if not manually edited?
            # Or just rely on _onchange_original_product to set it once.
            # If we put it here, it enforces the variants price.
            # User wants "system automatically adds...", implying it comes from the product.
            # To allow manual override, we should only set it if it's 0 or matches the product?
            # Better: Rely on _onchange_original_product for initial set. 
            # Remove the auto-overwrite here to allow manual edit.
            
            compensation_unit = line.price_compensation or 0.0
            
            # Detect Mode: Stock vs Money
            is_stock_mode = True
            if line.product_id.categ_id.name in ['Tiền', 'Money', 'Ngoại tệ'] or line.product_id.type == 'service':
                is_stock_mode = False
            
            if is_stock_mode:
                # === STOCK MODE (Gold -> Gold) ===
                
                # 1. Quantity = Converted Weight (Net * Purity)
                converted_qty = net_weight * purity
                line.product_uom_qty = converted_qty
                
                # 2. Calculate Total Target Value
                # Formula: ((Rate * Purity) + Compensation_Unit) * Net_Weight
                # Which equals: (Rate * Converted_Weight) + (Compensation_Unit * Net_Weight)
                
                base_value = converted_qty * exchange_rate
                extra_value = compensation_unit * net_weight
                target_value = base_value + extra_value
                
                # 3. Calculate Equivalent Unit Price
                # Price Unit = Value / Display Qty
                if abs(converted_qty) > 0.000001:
                    new_price_unit = target_value / converted_qty
                else:
                    new_price_unit = 0.0
                
            else:
                # === MONEY MODE (Gold -> Money) ===
                
                # 1. Qty
                line.product_uom_qty = 1.0
                
                # 2. Price
                # Value = ((Rate * Purity) + Compensation) * Net_Weight
                # Note: Exchange Rate here usually is Per-Purity-Unit (like 9999 rate).
                
                total_value = (net_weight * purity * exchange_rate) + (compensation_unit * net_weight)
                new_price_unit = total_value

            # === Final Direction (Buy/Sell) ===
            # If Trade-in (Buying from customer), Price should be Negative?
            if line.is_trade_in:
                line.price_unit = -abs(new_price_unit)
            else:
                line.price_unit = abs(new_price_unit)

            # Update Base Price Display
            line.price_unit_base = exchange_rate

            # Trigger Balancing
            if line.order_id:
                line.order_id._onchange_balance_money()

    @api.onchange('gold_purity')
    def _onchange_gold_purity_switch_variant(self):
        """
        Phase 12: Auto-switch Original Product Variant based on Purity.
        When Purity changes, check if there is a variant of the same template
        that has matching gold_purity_standard.
        """
        for line in self:
            if not line.original_product_id or not line.gold_purity:
                continue
            
            # Avoid loop: If current product already matches, do nothing
            # Note: Float comparison needs epsilon
            if abs(line.original_product_id.gold_purity_standard - line.gold_purity) < 0.00001:
                continue

            # Search for sibling variant
            template = line.original_product_id.product_tmpl_id
            # Find product.product where product_tmpl_id = template and gold_purity_standard matches
            # Limiting to 1 to avoid ambiguity
            matching_variant = self.env['product.product'].search([
                ('product_tmpl_id', '=', template.id),
                ('gold_purity_standard', '=', line.gold_purity)
            ], limit=1)
            
            if matching_variant and matching_variant.id != line.original_product_id.id:
                # Switch!
                # STRICT USER REQUIREMENT: Only change original_product_id.
                # DO NOT change 'product_id' (Converted Product/Target).
                # We simply assign the new variant. 
                # Since this is an onchange, simple assignment won't trigger _onchange_original_product automatically in backend.
                # But to be absolutely safe and clear:
                current_target_product = line.product_id
                line.original_product_id = matching_variant
                # Restore correct target if for some reason it got affected (though it shouldn't)
                if line.product_id != current_target_product:
                    line.product_id = current_target_product
            self._onchange_calculation_master()

    @api.onchange('original_product_id', 'is_trade_in')
    def _onchange_original_product(self):
        """
        Triggered when picking the Original Product (e.g. Old Gold).
        Logic:
        1. Auto-fill Purity from Original Product.
        2. Product Mapping (Phase 15.6 Fix):
           - Previously forced product_id = original_product_id. This broke Pricing (No Rate).
           - NEW: Default 'product_id' to "Standard Gold" (e.g. 9999).
           - This ensures UI shows "Quy đổi: 9999" (with Price) while Stock Move uses Original (via _prepare_procurement).
        """
        for line in self:
            if not line.original_product_id:
                continue
            
            # 1. Purity
            # 1. Purity
            # Logic: Only overwrite Purity if it differs significantly from the Product's Standard.
            # This allows User Input (e.g. 0.9962) to persist even if Product Standard is 0.996.
            # Threshold: 0.001 (Accept variance for specific variants).
            if hasattr(line.original_product_id, 'gold_purity_standard'):
                 standard = line.original_product_id.gold_purity_standard
                 current = line.gold_purity or 0.0
                 if abs(current - standard) > 0.001:
                      line.gold_purity = standard
            elif line.original_product_id.gold_purity_standard:
                 line.gold_purity = line.original_product_id.gold_purity_standard
            
            # 2. Product Mapping (Restored Logic)
            # If product_id is empty OR matching Original (reset state),
            # Try to find the Configured Converted Product (SP Quy đổi Mặc định).
            # If not configured, fallback to 9999 Search.
            
            should_update_target = not line.product_id or line.product_id == line.original_product_id
            
            if should_update_target:
                # A. Check Configuration (High Priority)
                # Note: conversion_target_id is on Product Template, but mapped via product_tmpl_id
                target_product = line.original_product_id.product_tmpl_id.conversion_target_id
                
                # B. Fallback Heuristic
                if not target_product:
                     target_product = self.env['product.product'].search([
                        ('name', 'ilike', '3 số'), # Search for 999 or 3 số
                        ('categ_id.name', '!=', 'Tiền')
                    ], limit=1)
                
                if target_product:
                     line.product_id = target_product
            
                if target_product:
                     line.product_id = target_product
            
            # 3. UOM
            if line.original_product_id.uom_id:
                 line.original_uom_id = line.original_product_id.uom_id

            # 4. Price Compensation (Tiền Công / Variant Extra Price)
            # Auto-fill 'Bù giá' from the Variant's 'price_extra'
            # Note: price_extra is the difference from Template List Price.
            # If user wants absolute value, they should check configuration. 
            # Here we just map it.
            price_extra = line.original_product_id.price_extra or 0.0
            # Cleaned

            line.price_compensation = price_extra
            
            # 5. Trigger Recalculation
            # Ensure any product change immediately updates prices/quantities
            line._onchange_calculation_master()

    @api.onchange('product_id','is_trade_in')
    def _onchange_is_trade_in_trigger_sort(self):
        """Khi thay đổi trạng thái Trade-in, kích hoạt lại logic sắp xếp trên đơn hàng cha."""
        # "Simulated Drag": Force local sequence update.
        if self.is_trade_in:
            pass # self.sequence = 2000 # Move to "Hàng Mua" zone
        else:
            pass # self.sequence = 10   # Move to "Hàng Bán" zone
        
        if self.order_id:
            # Explicit call to parent onchange for full re-balancing and cleanup
            self.order_id._onchange_balance_money()


    @api.depends('product_id', 'is_trade_in')
    def _compute_route_id(self):
        """
        Override: Assign 'Trade-in (Receipt)' Route to Trade-in lines.
        Ensures that 'Buy' lines generate Incoming Pickings (Receipts) 
        instead of Outgoing (Delivery).
        """
        # 1. Standard Logic (Assigns MTO or Deliver rule)
        super(SaleOrderLine, self)._compute_route_id()
        
        # 2. Trade-in Logic
        # Search by name for the route we created in setup script.
        # Ideally we should use External ID but we created it via Python.
        trade_in_route = self.env['stock.route'].search([('name', '=', 'Nhập từ Khách (Trade-in)')], limit=1)
        
        if trade_in_route:
            for line in self:
                if line.is_trade_in:
                    line.route_id = trade_in_route

    @api.depends('move_ids.state', 'move_ids.scrapped', 'move_ids.product_uom_qty', 'move_ids.product_uom')
    def _compute_qty_delivered(self):
        super(SaleOrderLine, self)._compute_qty_delivered()
        for line in self:
            if line.is_trade_in:
                qty = 0.0
                for move in line.move_ids.filtered(lambda r: r.state == 'done' and not r.scrapped):
                    # Count incoming moves as "delivered" (fulfilled) for trade-in
                    if move.picking_code == 'incoming':
                        qty += move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom)
                line.qty_delivered = qty

    def _prepare_invoice_line(self, **optional_values):
        res = super(SaleOrderLine, self)._prepare_invoice_line(**optional_values)
        # Propagate Conversion Data to Invoice Line (Account Move Line)
        res.update({
            'is_trade_in': self.is_trade_in,
            'original_product_id': self.original_product_id.id,
            'original_weight': self.original_weight,
            'original_uom_id': self.original_uom_id.id,
            'loss_weight': self.loss_weight,
            'gold_purity': self.gold_purity,
            'exchange_rate': self.exchange_rate,
            'price_compensation': self.price_compensation,
            'price_unit_base': self.price_unit_base,
        })
        return res

    def _prepare_procurement_values(self, group_id=False):
        """ Prepare specific key for moves or other components that will be created from a procurement rule
        comming from a sale order line. This method populates values for the Stock Move.
        """
        values = super(SaleOrderLine, self)._prepare_procurement_values(group_id)
        
        # PHASE 12 UPDATE: Override Quantity for Stock Move
        # Logic: UI uses Converted Quantity, but Stock must use Physical Weight (Net Weight)
        # Net Weight = Original Weight - Loss Weight
        physical_qty = max(0, self.original_weight - self.loss_weight)
        
        # Only apply override if we are in "Stock Mode" (Gold -> Gold) and strictly using weight logic
        if self.original_uom_id and physical_qty > 0:
             values['product_uom_qty'] = physical_qty
             # CRITICAL: Also override Product to Original Product
             # Because we are using Physical Quantity (of Original), we must use Original Product.
             # Otherwise we have 10 chi (Physical) of Vàng 9999 (Target), which is over-valued.
             values['product_id'] = self.original_product_id.id
        
        # Propagate Conversion Data to Stock Move
        values.update({
            'is_trade_in': self.is_trade_in, 
            'original_product_id': self.original_product_id.id,
            'original_weight': self.original_weight,
            'original_uom_id': self.original_uom_id.id,
            'loss_weight': self.loss_weight,
            'gold_purity': self.gold_purity,
            'exchange_rate': self.exchange_rate,
            'price_compensation': self.price_compensation,
        })
        return values

    def _action_launch_stock_rule(self, previous_product_uom_qty=False):
        """
        Phase 16: Override to Create UNIQUE Procurement Group per Line.
        This forces Odoo to create separate Stock Pickings for each Sale Order Line.
        Original Logic: Uses line.order_id.procurement_group_id (Shared).
        New Logic: Creates new group for each line if not exists.
        """
        """
        Phase 16: Override to Create UNIQUE Procurement Group per Line.
        Force Sequential Execution to prevent Picking Merging.
        """
        procurements = []
        for line in self:
            line = line.with_company(line.company_id)
            if line.state != 'sale' or not line.product_id.type in ('consu', 'product'):
                continue
            
            # Retrieve previous qty
            qty = line.product_uom_qty - (previous_product_uom_qty.get(line.id, 0.0) if previous_product_uom_qty else 0.0)
            
            # Using imported float_compare is cleaner but let's stick to simple
            if line.product_uom.rounding:
                if abs(qty) < line.product_uom.rounding:
                    continue
            else:
                 if qty == 0:
                     continue

            # --- Start Custom Logic ---
            # Create Unique Group ID
            group_id = line.procurement_group_id
            if not group_id:
                # Name pattern: SO/LineSeq-Product
                group_name = u"{} / {} - {}".format(line.order_id.name, line.sequence, line.product_id.name)
                group_vals = {
                    'name': group_name,
                    'move_type': line.order_id.picking_policy,
                    'sale_id': line.order_id.id,
                    'partner_id': line.order_id.partner_shipping_id.id,
                }
                group_id = self.env['procurement.group'].create(group_vals)
                line.procurement_group_id = group_id
            # --- End Custom Logic ---

            values = line._prepare_procurement_values(group_id=group_id)
            product_qty = line.product_uom_qty - (previous_product_uom_qty.get(line.id, 0.0) if previous_product_uom_qty else 0.0)

            line_uom = line.product_uom
            # quant_uom = line.product_id.uom_id
            procurement_uom = line_uom
            
            # Create Procurement
            # Note: We use string references if we don't have direct imports. 
            # But self.env creates objects locally.
            # Force Unique Origin to ensure separation (Include Sequence for Same-Product lines)
            unique_origin = u"{} / {} - {}".format(line.order_id.name, line.sequence, line.product_id.name)
            
            procurements.append(self.env['procurement.group'].Procurement(
                line.product_id, product_qty, procurement_uom,
                line.order_id.partner_shipping_id.property_stock_customer,
                line.name, unique_origin, line.order_id.company_id, values))
        
        if procurements:
            # Force Sequential Execution to prevent Picking Merging
            for proc in procurements:
                 self.env['procurement.group'].run([proc])
            
        return True
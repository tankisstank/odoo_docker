from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _name = 'sale.order.line'
    _inherit = ['sale.order.line', 'product.conversion.mixin']

    # ... [Keep fields] ...
    # Mixin fields: is_trade_in, price_unit_base, gold_purity, etc. are inherited.
    
    trade_in_price_unit = fields.Float('Trade-in Price (Unit)')
    is_auto_balance = fields.Boolean('Tự động cân bằng', default=False, help="Dòng này được hệ thống tự động tạo ra để cân bằng tiền.")

    @api.onchange('original_product_id')
    def _onchange_original_product(self):
        """Set defaults when Original Product is selected."""
        for line in self:
            if not line.original_product_id:
                continue
            
            # 1. Set Default Purity & UoM
            line.gold_purity = line.original_product_id.gold_purity_standard or 1.0
            line.original_uom_id = line.original_product_id.uom_id
            
            # 2. Set Active Product (Same as Original) - CHANGED: Do NOT switch to Target
            # We keep the Original Product as the "Product" of the line for Stock purposes.
            # line.product_id = line.original_product_id.conversion_target_id 
            line.product_id = line.original_product_id
                
            # 3. Set Default Exchange Rate (from Target Product or Original?)
            # Usually we take the Target Product's price as the base for exchange
            # If target exists, use its price. Else use own.
            target = line.original_product_id.conversion_target_id
            if target:
                line.exchange_rate = target.standard_price if line.is_trade_in else target.list_price
            elif line.product_id:
                line.exchange_rate = line.product_id.standard_price if line.is_trade_in else line.product_id.list_price

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
            compensation = line.price_compensation or 0.0
            
            # Detect Mode: Stock vs Money
            is_stock_mode = True
            if line.product_id.categ_id.name in ['Tiền', 'Money', 'Ngoại tệ'] or line.product_id.type == 'service':
                is_stock_mode = False
            
            if is_stock_mode:
                # === STOCK MODE (Gold -> Gold) ===
                # NEW LOGIC: 
                # Qty = Net Weight (Original)
                # Value = (Converted Qty * Rate) + Comp
                # Unit Price = Value / Qty
                
                # 1. Quantity = Actual Weight
                line.product_uom_qty = net_weight
                
                # 2. Calculate Total Target Value
                # Converted Qty (Theoretical 9999) = Net Weight * Purity
                converted_qty = net_weight * purity
                target_value = (converted_qty * exchange_rate) + compensation
                
                # 3. Calculate Equivalent Unit Price
                if abs(net_weight) > 0.000001:
                    new_price_unit = target_value / net_weight
                else:
                    new_price_unit = 0.0
                
            else:
                # === MONEY MODE (Gold -> Money) ===
                # Customer sells Gold for Money.
                # Target Product is likely "VND" or "Cash". Qty usually 1.
                
                # 1. Qty
                line.product_uom_qty = 1.0
                
                # 2. Price
                # Value = (Net Weight * Purity * Exchange Rate) + Compensation
                total_value = (net_weight * purity * exchange_rate) + compensation
                new_price_unit = total_value

            # === Final Direction (Buy/Sell) ===
            # If Trade-in (Buying from customer), Price should be Negative?
            if line.is_trade_in:
                line.price_unit = -abs(new_price_unit)
            else:
                line.price_unit = abs(new_price_unit)

            # Trigger Balancing
            if line.order_id:
                line.order_id._onchange_balance_money()

    @api.onchange('product_id','is_trade_in')
    def _onchange_is_trade_in_trigger_sort(self):
        """Khi thay đổi trạng thái Trade-in, kích hoạt lại logic sắp xếp trên đơn hàng cha."""
        # "Simulated Drag": Force local sequence update.
        if self.is_trade_in:
            self.sequence = 2000 # Move to "Hàng Mua" zone
        else:
            self.sequence = 10   # Move to "Hàng Bán" zone
        
        if self.order_id:
            # Explicit call to parent onchange for full re-balancing and cleanup
            self.order_id._onchange_balance_money()


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
        # Propagate Conversion Data to Stock Move
        values.update({
            'is_trade_in': self.is_trade_in, # While Stock Move doesn't have is_trade_in directly (maybe related?), Mixin has it? 
            # Check StockMove definition. It inherits mixin.
            'original_product_id': self.original_product_id.id,
            'original_weight': self.original_weight,
            'original_uom_id': self.original_uom_id.id,
            'loss_weight': self.loss_weight,
            'gold_purity': self.gold_purity,
            'exchange_rate': self.exchange_rate,
            'price_compensation': self.price_compensation,
            # 'price_unit_base': self.price_unit_base, # Stock move might not need base price effectively, but good to have.
        })
        return values
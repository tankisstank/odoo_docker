from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # ... [Keep fields] ...
    is_trade_in = fields.Boolean('Trade-in Product')
    trade_in_price_unit = fields.Float('Trade-in Price (Unit)')
    price_unit_base = fields.Float('Đơn giá gốc', digits='Product Price')
    gold_purity = fields.Float('Tuổi vàng (Hệ số)', default=1.0, digits=(16, 4), help="Hệ số tuổi vàng thực tế (ví dụ: 0.9953)")
    price_compensation = fields.Monetary('Tiền bù giá', default=0.0, currency_field='currency_id', help="Số tiền khách bù thêm (hoặc nhận thêm) để điều chỉnh giá trị thu mua.")
    is_auto_balance = fields.Boolean('Tự động cân bằng', default=False, help="Dòng này được hệ thống tự động tạo ra để cân bằng tiền.")

    @api.onchange('product_id', 'is_trade_in')
    def _onchange_product_trade_in_base(self):
        """Cập nhật Đơn giá gốc khi thay đổi Sản phẩm hoặc chế độ Trade-in."""
        for line in self:
            if not line.product_id:
                continue
            
            # Luôn cập nhật lại giá gốc khi thay đổi sản phẩm hoặc chế độ
            if line.is_trade_in:
                line.price_unit_base = line.product_id.standard_price
            else:
                line.price_unit_base = line.product_id.list_price

    @api.onchange('product_id', 'is_trade_in', 'price_unit_base', 'gold_purity', 'product_uom_qty', 'price_compensation')
    def _onchange_price_logic(self):
        """Tính toán lại Giá thực tế (price_unit) dựa trên các tham số."""
        for line in self:
            # Logic tính toán giá cuối cùng (price_unit)
            base_price = line.price_unit_base
            purity = line.gold_purity or 1.0
            compensation = line.price_compensation or 0.0
            
            if line.is_trade_in:
                # Giá trị thu mua = (Giá gốc * Tuổi vàng) + Bù giá
                # Vì là trade-in nên giá trị này mang dấu âm
                line.price_unit = -1 * ((base_price * purity) + compensation)
            else:
                # Áp dụng bù giá cho cả hàng bán (nếu có)
                line.price_unit = (base_price * purity) + compensation
            
            # Trigger Parent Logic (Sort & Balance)
            if line.order_id:
                 line.order_id._onchange_balance_money()

    @api.onchange('product_id','is_trade_in')
    def _onchange_is_trade_in_trigger_sort(self):
        """Khi thay đổi trạng thái Trade-in, kích hoạt lại logic sắp xếp trên đơn hàng cha."""
        # "Simulated Drag": Force local sequence update.
        # This acts as a "dirty" signal to the UI to trigger the parent's onchange eventually,
        # or at least visualizes the jump.
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
        res['is_trade_in'] = self.is_trade_in
        res['gold_purity'] = self.gold_purity
        res['trade_in_price_unit'] = self.trade_in_price_unit
        res['price_unit_base'] = self.price_unit_base
        return res
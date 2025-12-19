from odoo import models, fields, api

class ProductConversionMixin(models.AbstractModel):
    _name = 'product.conversion.mixin'
    _description = 'Mixin for Trade-in/Conversion Data Propagation'

    currency_id = fields.Many2one('res.currency', string='Currency')

    # === Transaction Origin Info (Thông tin Giao dịch Gốc) ===
    original_product_id = fields.Many2one('product.product', string='Sản phẩm Gốc', help="Sản phẩm thực tế khách mang đến hoặc mua (trước khi quy đổi).")
    original_weight = fields.Float('Trọng lượng Gốc (TTL)', digits='Product Unit of Measure', help="Trọng lượng/Số lượng thực tế của sản phẩm gốc.")
    original_uom_id = fields.Many2one('uom.uom', string='ĐVT Gốc (1)', help="Đơn vị tính của sản phẩm gốc.")
    
    loss_weight = fields.Float('Hao hụt', digits='Product Unit of Measure', help="Trọng lượng trừ hao (nếu có).")

    # Reuse or New Purity/Exchange fields
    gold_purity = fields.Float('Tuổi vàng (HS1)', default=1.0, digits=(16, 4), help="Hệ số quy đổi chất lượng (Ví dụ: 0.9999).")
    exchange_rate = fields.Float('Giá quy đổi (HS2)', default=1.0, digits=(16, 4), help="Hệ số quy đổi giá trị (Tỷ giá hoặc Đơn giá tham chiếu).")

    # Financial Adjustment
    price_compensation = fields.Monetary('Tiền Bù', currency_field='currency_id', help="Số tiền bù trừ thêm (Công, Chênh lệch...).")
    purity_diff_value = fields.Monetary('Giá trị chênh lệch (Tuổi)', currency_field='currency_id', help="Giá trị chênh lệch do quy đổi tuổi vàng.")

    # Status & Pricing Base (Moved from SaleOrderLine to Mixin for propagation)
    is_trade_in = fields.Boolean('Trade-in Product', default=False, help="Xác định đây là dòng hàng thu mua vào.")
    price_unit_base = fields.Float('Đơn giá gốc', digits='Product Price', help="Đơn giá niêm yết hoặc đơn giá gốc trước khi tính toán.")

    # Computed/Display fields
    converted_value = fields.Float('Giá trị/TL Quy đổi', digits='Product Unit of Measure', help="Kết quả sau quy đổi (TTLQD).", compute='_compute_converted_value', store=True)

    @api.depends('original_weight', 'loss_weight', 'gold_purity')
    def _compute_converted_value(self):
        """
        Đây chỉ là tính toán cơ bản cho Mixin. Logic phức tạp hơn (Money Mode vs Stock Mode) 
        sẽ được override ở từng Model cụ thể nếu cần, hoặc xử lý bằng Onchange. 
        Tại đây ta giữ logic default: Trọng lượng * Tuổi.
        """
        for record in self:
            net_weight = record.original_weight - record.loss_weight
            if net_weight < 0:
                net_weight = 0
            record.converted_value = net_weight * record.gold_purity

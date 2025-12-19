from odoo import models, fields, api

class StockMove(models.Model):
    _name = 'stock.move'
    _inherit = ['stock.move', 'product.conversion.mixin']
    
    # Reporting Fields (Stored for Performance/Analysis)
    price_unit_base = fields.Float('Đơn giá gốc', related='sale_line_id.price_unit_base', readonly=True, store=True)
    is_trade_in = fields.Boolean('Hàng Thu mua', related='sale_line_id.is_trade_in', readonly=True, store=True)
    
    currency_id = fields.Many2one('res.currency', related='sale_line_id.currency_id', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        # Khi tạo move từ SO, copy giá trị purity từ SO line sang
        for vals in vals_list:
            if 'sale_line_id' in vals:
                sale_line = self.env['sale.order.line'].browse(vals['sale_line_id'])
                if sale_line.is_trade_in:
                    vals['gold_purity'] = sale_line.gold_purity
                    vals['price_compensation'] = sale_line.price_compensation
        return super(StockMove, self).create(vals_list)

    def write(self, vals):
        res = super(StockMove, self).write(vals)
        
        # Nếu có thay đổi gold_purity hoặc price_compensation, cập nhật ngược lại SO line
        if 'gold_purity' in vals or 'price_compensation' in vals:
            for move in self:
                if move.sale_line_id and move.sale_line_id.is_trade_in:
                    # Chuẩn bị giá trị update
                    update_vals = {}
                    if 'gold_purity' in vals:
                        update_vals['gold_purity'] = move.gold_purity
                    if 'price_compensation' in vals:
                        update_vals['price_compensation'] = move.price_compensation
                    
                    if update_vals:
                        move.sale_line_id.write(update_vals)
                        # Trigger tính lại giá (vì write không tự gọi onchange)
                        move.sale_line_id._onchange_price_logic()
        return res

from odoo import models, fields, api
from odoo.exceptions import UserError

class ProductPriceHistory(models.Model):
    _name = 'product.price.history'
    _description = 'Lịch sử thay đổi giá sản phẩm'
    _order = 'change_date desc'

    product_template_id = fields.Many2one(
        'product.template',
        string='Sản phẩm',
        required=True,
        ondelete='cascade'
    )
    standard_price = fields.Float('Giá mua', digits='Product Price')
    list_price = fields.Float('Giá bán', digits='Product Price')
    change_date = fields.Datetime('Thời gian thay đổi', readonly=True, default=fields.Datetime.now)
    user_id = fields.Many2one('res.users', string='Người thay đổi', readonly=True, default=lambda self: self.env.user.id)

    def action_rollback(self):
        self.ensure_one()
        if not self.product_template_id:
            raise UserError('Không tìm thấy sản phẩm liên quan đến lịch sử này.')
        
        # Ghi lại giá hiện tại vào lịch sử trước khi rollback
        self.env['product.price.history'].create({
            'product_template_id': self.product_template_id.id,
            'standard_price': self.product_template_id.standard_price,
            'list_price': self.product_template_id.list_price,
        })
        
        # Cập nhật sản phẩm với giá từ lịch sử
        self.product_template_id.write({
            'standard_price': self.standard_price,
            'list_price': self.list_price
        })
        return True
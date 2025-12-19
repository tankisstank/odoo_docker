from odoo import models, fields

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    is_trade_in = fields.Boolean('Trade-in Product')
    trade_in_price_unit = fields.Float('Trade-in Price (Unit)')
    price_unit_base = fields.Float('Đơn giá gốc', digits='Product Price')
    gold_purity = fields.Float('Tuổi vàng (Hệ số)', default=1.0, digits=(16, 4))

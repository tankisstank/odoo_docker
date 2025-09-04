from odoo import models

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    # Không cần thêm trường mới, chỉ kế thừa để custom nếu cần 
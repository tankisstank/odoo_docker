from odoo import fields, models, api

class ResCompany(models.Model):
    _inherit = 'res.company'

    money_product_id = fields.Many2one('product.product', string='Sản phẩm Tiền mặt')

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    money_product_id = fields.Many2one(
        'product.product', 
        string='Sản phẩm Tiền mặt',
        related='company_id.money_product_id', 
        readonly=False,
        help="Sản phẩm được sử dụng để tự động cân bằng tiền trong đơn hàng."
    )

    @api.model
    def default_get(self, fields_list):
        res = super(ResConfigSettings, self).default_get(fields_list)
        # Tự động gợi ý sản phẩm nếu chưa set
        if 'money_product_id' in fields_list and not res.get('money_product_id'):
            company = self.env.company
            if not company.money_product_id:
                # Tìm sản phẩm có tên chứa 'Tiền' hoặc 'Money'
                product = self.env['product.product'].search([
                    '|', ('name', 'ilike', 'Tiền'), ('name', 'ilike', 'Money')
                ], limit=1)
                if product:
                    # Lưu tạm vào company để hiển thị lên form (vì related field cần saved value)
                    # Tuy nhiên default_get chỉ trả về giá trị cho wizard.
                    # Với related field, nó sẽ lấy từ company_id.
                    # Nên ta không can thiệp vào đây được trừ khi set thẳng vào company (side effect).
                    # Tốt hơn là để onchange hoặc user tự chọn.
                    # Nhưng users muốn "suggest để tự động tạo".
                    pass
        return res
    
    @api.onchange('company_id')
    def _onchange_company_id_suggest_money(self):
        if not self.money_product_id:
             product = self.env['product.product'].search([
                '|', ('name', 'ilike', 'Tiền'), ('name', 'ilike', 'Money')
            ], limit=1)
             if product:
                 self.money_product_id = product

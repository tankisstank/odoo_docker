from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    hidden = fields.Boolean('Ẩn sản phẩm', default=False)
    price_ratio = fields.Float('Tỷ lệ', default=1.0, help="Tỷ lệ quy đổi giá. Ví dụ: Giá 1000đ cho 100 sản phẩm thì tỷ lệ là 100.")

    # === Conversion Configuration ===
    gold_purity_standard = fields.Float('Tuổi vàng chuẩn (HS1)', default=1.0, digits=(16, 4), help="Hệ số quy đổi tiêu chuẩn cho sản phẩm này (Ví dụ: 0.9999).")
    conversion_target_id = fields.Many2one('product.product', string='SP Quy đổi Mặc định', help="Sản phẩm đích mặc định khi thực hiện quy đổi (Ví dụ: Vàng 9999).")

    history_ids = fields.One2many(
        'product.price.history',
        'product_template_id',
        string='Lịch sử giá'
    )

    @api.model
    def create(self, vals):
        # Khi tạo mới sản phẩm, cũng tạo một bản ghi lịch sử ban đầu
        product = super(ProductTemplate, self).create(vals)
        self.env['product.price.history'].create({
            'product_template_id': product.id,
            'standard_price': vals.get('standard_price', 0.0),
            'list_price': vals.get('list_price', 0.0),
        })
        return product

    def write(self, vals):
        # Nếu 'standard_price' hoặc 'list_price' thay đổi, tạo bản ghi lịch sử
        if 'standard_price' in vals or 'list_price' in vals:
            for product in self:
                self.env['product.price.history'].create({
                    'product_template_id': product.id,
                    'standard_price': product.standard_price,
                    'list_price': product.list_price,
                })
        return super(ProductTemplate, self).write(vals)

    def action_view_price_history(self):
        self.ensure_one()
        
        # Lấy ID của các view đã định nghĩa trong XML
        graph_view_id = self.env.ref('qlv.view_product_price_history_graph').id
        tree_view_id = self.env.ref('qlv.view_product_price_history_tree').id
        form_view_id = self.env.ref('qlv.view_product_price_history_form').id
        
        
        return {
            'name': 'Lịch sử giá của: %s' % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'product.price.history',
            'view_mode': 'tree,graph,form',
            'domain': [('product_template_id', '=', self.id)],
            'target': 'current',
            'views': [
                (graph_view_id, 'graph'),
                (tree_view_id, 'tree'),
                (form_view_id, 'form'),
            ],
            'view_ids': [graph_view_id, tree_view_id, form_view_id],
        }

    def action_open_product_form(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'product.template',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',  # Mở trong cửa sổ chính, thay thế view hiện tại
        }

import logging
_logger = logging.getLogger(__name__)

class ProductProduct(models.Model):
    _inherit = 'product.product'

    # === Variant Specific Purity ===
    gold_purity_standard = fields.Float('Tuổi vàng (HS1)', default=1.0, digits=(16, 4), help="Hệ số quy đổi chất lượng (Ví dụ: 0.9999) riêng cho biến thể này.")

    @api.model_create_multi
    def create(self, vals_list):
        return super(ProductProduct, self).create(vals_list)

    def action_open_variant_details(self):
        """Open the Product Variant Form View (Renamed to avoid conflict)."""
        self.ensure_one()
        _logger.info("OPENING VARIANT DETAILS FOR ID: %s", self.id)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'product.product',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_price_history(self):
        """Open Price History (Delegates to Template)."""
        self.ensure_one()
        return self.product_tmpl_id.action_view_price_history()
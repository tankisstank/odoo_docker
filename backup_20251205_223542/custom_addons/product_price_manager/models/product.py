from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    hidden = fields.Boolean('Ẩn sản phẩm', default=False)
    price_ratio = fields.Float('Tỷ lệ', default=1.0, help="Tỷ lệ quy đổi giá. Ví dụ: Giá 1000đ cho 100 sản phẩm thì tỷ lệ là 100.")

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
        graph_view_id = self.env.ref('product_price_manager.view_product_price_history_graph').id
        tree_view_id = self.env.ref('product_price_manager.view_product_price_history_tree').id
        form_view_id = self.env.ref('product_price_manager.view_product_price_history_form').id
        
        
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
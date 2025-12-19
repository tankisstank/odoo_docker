# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class PawnOrder(models.Model):
    _name = 'pawn.order'
    _description = 'Phiếu Cầm cố / Vay mượn (Gửi sổ)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char('Mã phiếu', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    partner_id = fields.Many2one('res.partner', string='Khách hàng', required=True, tracking=True)
    date_order = fields.Datetime('Ngày cầm cố', required=True, default=fields.Datetime.now, tracking=True)
    
    # Financials
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    amount_loan = fields.Monetary('Số tiền vay', required=True, tracking=True, help="Số tiền khách hàng vay của cửa hàng.")
    interest_rate = fields.Float('Lãi suất (%)', default=0.0, help="Lãi suất thỏa thuận (nếu có).")
    
    # Lines (Collateral)
    pawn_line_ids = fields.One2many('pawn.order.line', 'pawn_id', string='Tài sản Cầm cố')

    state = fields.Selection([
        ('draft', 'Nháp'),
        ('confirmed', 'Đang cầm cố'),
        ('redeemed', 'Đã chuộc'),
        ('liquidated', 'Đã thanh lý'),
        ('cancel', 'Đã hủy'),
    ], string='Trạng thái', default='draft', tracking=True)

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    note = fields.Text('Ghi chú')

    # Relations
    picking_count = fields.Integer(compute='_compute_moves')
    payment_count = fields.Integer(compute='_compute_moves')
    sale_order_id = fields.Many2one('sale.order', string='Đơn hàng Thanh lý', readonly=True, copy=False)

    def _compute_moves(self):
        for order in self:
            order.picking_count = self.env['stock.picking'].search_count([('origin', 'ilike', order.name)])
            order.payment_count = 0 # Deprecated logic

    def action_view_sale_order(self):
        self.ensure_one()
        if not self.sale_order_id:
            return
        return {
            'name': _('Đơn hàng Thanh lý'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': self.sale_order_id.id,
            'target': 'current',
        }

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('pawn.order') or _('New')
        return super(PawnOrder, self).create(vals)

    def _get_money_product(self):
        # Find product config or search by name/category
        # Priority: Product named "Tiền Việt Nam (VNĐ)" or Category "Tiền"
        domain = [('name', '=', 'Tiền Việt Nam (VNĐ)')]
        product = self.env['product.product'].search(domain, limit=1)
        if not product:
            product = self.env['product.product'].search([('categ_id.name', '=', 'Tiền')], limit=1)
        if not product:
            raise UserError(_("Không tìm thấy sản phẩm 'Tiền Việt Nam (VNĐ)' trong hệ thống."))
        return product

    def action_confirm(self):
        """
        Transition to 'confirmed'.
        1. Stock Receipt (Collateral): Customer -> Shop (Owner=Customer).
        2. Stock Delivery (Money): Shop -> Customer (Out).
        """
        self.ensure_one()
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)], limit=1)
        if not warehouse:
             raise UserError(_("Không tìm thấy kho hàng cho công ty này."))
        
        # 1. Receipt: Collateral (Customer -> Shop)
        picking_in_type = warehouse.in_type_id
        customer_loc = self.partner_id.property_stock_customer.id
        
        # Collateral Moves
        moves_collateral = [(0, 0, {
            'name': line.description or line.product_id.name,
            'product_id': line.product_id.id,
            'product_uom_qty': line.product_uom_qty,
            'product_uom': line.uom_id.id,
            'location_id': customer_loc,
            'location_dest_id': picking_in_type.default_location_dest_id.id,
        }) for line in self.pawn_line_ids]
        
        picking_collateral = self.env['stock.picking'].create({
            'picking_type_id': picking_in_type.id,
            'partner_id': self.partner_id.id,
            'origin': f"Cầm cố {self.name} (Tài sản)",
            'location_id': customer_loc,
            'location_dest_id': picking_in_type.default_location_dest_id.id,
            'owner_id': self.partner_id.id, # Keep Owner
            'move_ids_without_package': moves_collateral
        })
        picking_collateral.action_confirm()

        # 2. Delivery: Money (Shop -> Customer)
        money_product = self._get_money_product()
        picking_out_type = warehouse.out_type_id
        
        if self.amount_loan > 0:
            picking_money = self.env['stock.picking'].create({
                'picking_type_id': picking_out_type.id,
                'partner_id': self.partner_id.id,
                'origin': f"Cầm cố {self.name} (Tiền)",
                'location_id': picking_out_type.default_location_src_id.id,
                'location_dest_id': customer_loc,
                'move_ids_without_package': [(0, 0, {
                    'name': 'Giải ngân tiền vay',
                    'product_id': money_product.id,
                    'product_uom_qty': self.amount_loan,
                    'product_uom': money_product.uom_id.id,
                    'location_id': picking_out_type.default_location_src_id.id,
                    'location_dest_id': customer_loc,
                })]
            })
            picking_money.action_confirm()
        
        self.write({'state': 'confirmed'})

    def action_redeem(self):
        """
        Transition to 'redeemed'.
        1. Stock Receipt (Money): Customer -> Shop (In).
        2. Stock Delivery (Collateral): Shop -> Customer (Return Owner).
        """
        self.ensure_one()
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)], limit=1)
        picking_in_type = warehouse.in_type_id
        picking_out_type = warehouse.out_type_id
        customer_loc = self.partner_id.property_stock_customer.id
        
        # 1. Receipt: Money (Customer pays back)
        money_product = self._get_money_product()
        total_pay = self.amount_loan # + Interest logic here
        
        if total_pay > 0:
            picking_money_in = self.env['stock.picking'].create({
                'picking_type_id': picking_in_type.id,
                'partner_id': self.partner_id.id,
                'origin': f"Chuộc đồ {self.name} (Tiền)",
                'location_id': customer_loc,
                'location_dest_id': picking_in_type.default_location_dest_id.id,
                'move_ids_without_package': [(0, 0, {
                    'name': 'Khách trả tiền chuộc',
                    'product_id': money_product.id,
                    'product_uom_qty': total_pay,
                    'product_uom': money_product.uom_id.id,
                    'location_id': customer_loc,
                    'location_dest_id': picking_in_type.default_location_dest_id.id,
                })]
            })
            picking_money_in.action_confirm()

        # 2. Delivery: Collateral (Return items)
        moves_return = [(0, 0, {
            'name': line.description or line.product_id.name,
            'product_id': line.product_id.id,
            'product_uom_qty': line.product_uom_qty,
            'product_uom': line.uom_id.id,
            'location_id': picking_out_type.default_location_src_id.id,
            'location_dest_id': customer_loc,
        }) for line in self.pawn_line_ids]
        
        if moves_return:
            picking_return = self.env['stock.picking'].create({
                'picking_type_id': picking_out_type.id,
                'partner_id': self.partner_id.id,
                'origin': f"Chuộc đồ {self.name} (Trả hàng)",
                'location_id': picking_out_type.default_location_src_id.id,
                'location_dest_id': customer_loc,
                'owner_id': self.partner_id.id, # Returning owned goods
                'move_ids_without_package': moves_return
            })
            picking_return.action_confirm()

        self.write({'state': 'redeemed'})
        
    def action_liquidate(self):
        """
        Transition to 'liquidated'.
        1. Return Owner Stock (Clear Pawn status).
        2. Create Sale Order (Trade-in).
        3. Confirm SO (State=Sale) to generate Trade-in Receipt.
        4. Unlock SO (Allow Price Edits).
        """
        self.ensure_one()
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)], limit=1)
        picking_out_type = warehouse.out_type_id
        customer_loc = self.partner_id.property_stock_customer.id
        
        # 1. Return Owner Stock (Clear "Held" goods)
        # We auto-return to clear the "Owner: Customer" stock in our warehouse.
        moves_return = [(0, 0, {
            'name': line.description or line.product_id.name,
            'product_id': line.product_id.id,
            'product_uom_qty': line.product_uom_qty,
            'product_uom': line.uom_id.id,
            'location_id': picking_out_type.default_location_src_id.id,
            'location_dest_id': customer_loc,
        }) for line in self.pawn_line_ids]
        
        if moves_return:
            picking_return = self.env['stock.picking'].create({
                'picking_type_id': picking_out_type.id,
                'partner_id': self.partner_id.id,
                'origin': f"Thanh lý {self.name} (Clear Stock)",
                'location_id': picking_out_type.default_location_src_id.id,
                'location_dest_id': customer_loc,
                'owner_id': self.partner_id.id, # Clearing this owner
                'move_ids_without_package': moves_return
            })
            picking_return.action_confirm()
            if picking_return.state != 'done':
                 picking_return.move_ids._action_done()

        # 2. Create Sale Order
        so_vals = {
            'partner_id': self.partner_id.id,
            'date_order': fields.Datetime.now(),
            'origin': f"Thanh lý {self.name}",
            'note': f"Thanh lý phiếu cầm cố {self.name}. {self.note or ''}",
        }
        sale_order = self.env['sale.order'].create(so_vals)
        self.sale_order_id = sale_order.id
        
        for line in self.pawn_line_ids:
            sol_vals = {
                'order_id': sale_order.id,
                'product_id': line.product_id.id,
                'product_uom_qty': line.product_uom_qty,
                'is_trade_in': True,
                'price_unit_base': line.price_valuation, 
            }
            sol = self.env['sale.order.line'].create(sol_vals)
            sol._onchange_product_trade_in_base()
            sol.price_unit_base = line.price_valuation
            sol._onchange_price_logic()

        self.write({'state': 'liquidated'})
        
        # 3. Confirm SO (To generate Trade-in Receipt & Set State 'Sale')
        sale_order.action_confirm()
        
        # 4. Unlock SO (To allow Price Edits as requested)
        sale_order.action_unlock()
        
        return {
            'name': _('Đơn hàng Thanh lý'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': sale_order.id,
            'target': 'current',
        }

    def action_cancel(self):
        self.write({'state': 'cancel'})


class PawnOrderLine(models.Model):
    _name = 'pawn.order.line'
    _description = 'Chi tiết Tài sản Cầm cố'

    pawn_id = fields.Many2one('pawn.order', string='Phiếu Cầm cố', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Tài sản (Vàng)', required=True)
    description = fields.Char('Mô tả', help="Mô tả hiện trạng tài sản")
    
    uom_id = fields.Many2one('uom.uom', string='ĐVT', related='product_id.uom_id')
    product_uom_qty = fields.Float('Số lượng', default=1.0, digits='Product Unit of Measure')
    
    # Valuation for reference (Not affecting accounting directly unless liquidated)
    price_valuation = fields.Monetary('Định giá', currency_field='currency_id', help="Giá trị định giá của tài sản tại thời điểm cầm.")
    currency_id = fields.Many2one(related='pawn_id.currency_id')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.description = self.product_id.name
            self.uom_id = self.product_id.uom_id
            # Default Pawn Value = Product Cost (Purchase Price)
            self.price_valuation = self.product_id.standard_price

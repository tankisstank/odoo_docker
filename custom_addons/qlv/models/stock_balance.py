from odoo import models, fields, api, _
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)

class QlvStockBalance(models.Model):
    _name = 'qlv.stock.balance'
    _description = 'Stock & P&L Balance Report'
    _order = 'create_date desc'

    name = fields.Char(string='Report Ref', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    
    date_from = fields.Date(string='From Date', required=True, default=fields.Date.context_today)
    date_to = fields.Date(string='To Date', required=True, default=fields.Date.context_today)
    
    filter_type = fields.Selection([
        ('all', 'Tất cả'),
        ('shop', 'Trên quầy'),
        ('customer_debt', "K' Nợ"),
        ('customer_pawn', "K' Gửi sổ"),
    ], string='Lọc theo', default='all')
    
    line_ids = fields.One2many('qlv.stock.balance.line', 'report_id', string='Report Lines')
    filtered_line_ids = fields.One2many('qlv.stock.balance.line', compute='_compute_filtered_lines', string='Report Lines')
    summary_line_ids = fields.One2many('qlv.stock.balance.summary', 'report_id', string='Summary Lines')

    user_id = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user, readonly=True)
    
    # P&L Summary Fields
    summary_opening_cash = fields.Float(string='Đầu kỳ (Tiền)', compute='_compute_summary', store=False)
    summary_closing_cash = fields.Float(string='Cuối kỳ (Tiền)', compute='_compute_summary', store=False)
    summary_variance = fields.Float(string='Lệch', compute='_compute_summary', store=False)
    summary_income = fields.Float(string='Tiền thu', compute='_compute_summary', store=False)
    summary_expense = fields.Float(string='Tiền chi', compute='_compute_summary', store=False)
    summary_price_variance = fields.Float(string='Lệch giá', compute='_compute_summary', store=False)
    
    @api.depends('line_ids', 'line_ids.closing_value', 'line_ids.opening_qty', 'line_ids.closing_qty')
    def _compute_summary(self):
        for report in self:
            # Get Money product from company settings (fallback to category-based search)
            money_product = self.env.company.money_product_id
            if money_product:
                vnd_lines = report.line_ids.filtered(lambda l: l.product_id == money_product)
            else:
                # Fallback: filter by category name if money_product_id not configured
                vnd_lines = report.line_ids.filtered(
                    lambda l: l.product_id.categ_id.name in ['Tiền', 'Money', 'Ngoại tệ']
                )
            
            # Opening cash (sum of opening for VND)
            report.summary_opening_cash = sum(vnd_lines.mapped('opening_qty'))
            
            # Closing cash (sum of closing for VND)
            report.summary_closing_cash = sum(vnd_lines.mapped('closing_qty'))
            
            # Variance
            report.summary_variance = report.summary_closing_cash - report.summary_opening_cash
            
            # Income (In transactions for VND)
            report.summary_income = sum(vnd_lines.mapped('in_qty'))
            
            # Expense (Out transactions for VND)
            report.summary_expense = -sum(vnd_lines.mapped('out_qty'))
            
            # Price variance (difference in total value due to price changes)
            # This is closing_value - (closing_qty * old_price)
            # For simplification, we calculate as total value change
            total_opening_value = sum(report.line_ids.mapped(lambda l: l.opening_qty * l.current_price))
            total_closing_value = sum(report.line_ids.mapped('closing_value'))
            report.summary_price_variance = total_closing_value - total_opening_value - report.summary_variance
    
    @api.depends('line_ids', 'filter_type')
    def _compute_filtered_lines(self):
        for report in self:
            if report.filter_type == 'all':
                report.filtered_line_ids = report.line_ids
            else:
                report.filtered_line_ids = report.line_ids.filtered(lambda l: l.ownership_type == report.filter_type)

    def action_compute_report(self):
        self.ensure_one()
        self.line_ids.unlink()

        # 1. Timezone & Date Handling (Vietnam UTC+7)
        # 05:00 AM VN = 22:00 PM Previous Day UTC
        # 04:00 AM VN = 21:00 PM Current Day UTC
        # Report Range: From [Date_From 05:00] To [Date_To+1 04:00]
        
        tz_offset = 7
        start_hour_vn = 5
        end_hour_vn = 4

        # Convert to UTC
        dt_from = fields.Datetime.to_datetime(self.date_from) - timedelta(days=1) + timedelta(hours=24 - tz_offset + start_hour_vn)
        # Fix: 05:00 AM VN is (5 - 7) = -2 (Prev Day 22:00). 
        # So Date_From - 1 Day + (24 + 5 - 7) hours? 
        # Simpler: Date_From (00:00) + 5h - 7h = Date_From - 2h = Date_Prev 22:00. Correct.
        utc_from = fields.Datetime.to_datetime(self.date_from) + timedelta(hours=start_hour_vn - tz_offset)

        # End Date: Date_To + 1 Day (00:00) + 4h - 7h = Date_To + 1 Day - 3h = Date_To 21:00.
        utc_to = fields.Datetime.to_datetime(self.date_to) + timedelta(days=1, hours=end_hour_vn - tz_offset)

        _logger.info(f"Report Computation: {self.name} | UTC Range: {utc_from} to {utc_to}")

        # 2. SQL for Aggregation
        # We need 3 buckets: Opening (< utc_from), In (Range, Dest=Target), Out (Range, Src=Target)
        # Target Locations:
        # - Shop: Internal Locs
        # - Debt: Customer Locs
        
        # Helper to get Internal Locations
        internal_locs = self.env['stock.location'].search([('usage', '=', 'internal')]).ids
        customer_locs = self.env['stock.location'].search([('usage', '=', 'customer')]).ids
        
        if not internal_locs or not customer_locs:
            return

        # Prepare Params
        params = {
            'date_from': utc_from,
            'date_to': utc_to,
            'internal_ids': tuple(internal_locs),
            'customer_ids': tuple(customer_locs),
            'report_id': self.id,
        }

        # --- A. SHOP STOCK (Tồn Quầy) ---
        # Logic: Usage Internal
        # Opening = Sum(Dest=Int) - Sum(Src=Int) where date < from
        # In = Sum(Dest=Int, Src!=Int) where date in range
        # Out = Sum(Src=Int, Dest!=Int) where date in range
        
        # We can implement a unified query or python loop. Given data size, SQL is safer.
        
        query_shop = """
            INSERT INTO qlv_stock_balance_line (
                report_id, product_id, category_id, ownership_type, uom_id,
                opening_qty, in_qty, out_qty, closing_qty, current_price, closing_value,
                create_uid, create_date, write_uid, write_date
            )
            SELECT
                %(report_id)s as report_id,
                m.product_id,
                pt.categ_id,
                'shop' as ownership_type,
                pt.uom_id,
                -- Opening: Moves before From Date
                SUM(CASE 
                    WHEN m.date < %(date_from)s AND m.location_dest_id IN %(internal_ids)s THEN m.product_uom_qty
                    WHEN m.date < %(date_from)s AND m.location_id IN %(internal_ids)s THEN -m.product_uom_qty
                    ELSE 0 
                END) as opening_qty,
                -- In: Moves In Range (Dest=Int, Src!=Int)
                SUM(CASE 
                    WHEN m.date >= %(date_from)s AND m.date <= %(date_to)s 
                         AND m.location_dest_id IN %(internal_ids)s AND m.location_id NOT IN %(internal_ids)s 
                    THEN m.product_uom_qty
                    ELSE 0 
                END) as in_qty,
                -- Out: Moves In Range (Src=Int, Dest!=Int)
                SUM(CASE 
                    WHEN m.date >= %(date_from)s AND m.date <= %(date_to)s 
                         AND m.location_id IN %(internal_ids)s AND m.location_dest_id NOT IN %(internal_ids)s 
                    THEN m.product_uom_qty
                    ELSE 0 
                END) as out_qty,
                -- Closing: All Moves up to To Date
                SUM(CASE 
                    WHEN m.date <= %(date_to)s AND m.location_dest_id IN %(internal_ids)s THEN m.product_uom_qty
                    WHEN m.date <= %(date_to)s AND m.location_id IN %(internal_ids)s THEN -m.product_uom_qty
                    ELSE 0 
                END) as closing_qty,
                -- Price (Max standard_price for simplicity, usually same per product)
                COALESCE(MAX(ip.value_float), 0) as current_price,
                0 as closing_value, -- Computed trigger will handle or SQL update later
                1, NOW(), 1, NOW()
            FROM stock_move m
            JOIN product_product pp ON m.product_id = pp.id
            JOIN product_template pt ON pp.product_tmpl_id = pt.id
            LEFT JOIN ir_property ip ON (ip.name='standard_price' AND ip.res_id = 'product.product,' || pp.id AND ip.company_id = m.company_id)
            WHERE m.state = 'done'
            GROUP BY m.product_id, pt.categ_id, pt.uom_id
            HAVING 
                SUM(CASE WHEN m.date <= %(date_to)s AND (m.location_dest_id IN %(internal_ids)s OR m.location_id IN %(internal_ids)s) THEN 1 ELSE 0 END) > 0
        """
        
        # Note: ir_property join for standard_price is tricky because it might not exist for all products (defaults) or be on template.
        # Fallback to python for price update is safer.
        
        self.env.cr.execute(query_shop, params)

        # --- B. CUSTOMER DEBT/PAWN (Khách Nợ / Gửi) ---
        if customer_locs:
            query_debt = """
                SELECT
                    m.product_id, pt.categ_id, pt.uom_id, m.partner_id,
                    -- Opening
                    SUM(CASE 
                        WHEN m.date < %(date_from)s AND m.location_dest_id IN %(customer_ids)s THEN m.product_uom_qty
                        WHEN m.date < %(date_from)s AND m.location_id IN %(customer_ids)s THEN -m.product_uom_qty
                        ELSE 0 END) as open,
                    -- In (Debt Increase)
                    SUM(CASE 
                        WHEN m.date >= %(date_from)s AND m.date <= %(date_to)s 
                             AND m.location_dest_id IN %(customer_ids)s AND m.location_id NOT IN %(customer_ids)s 
                        THEN m.product_uom_qty ELSE 0 END) as in_q,
                    -- Out (Debt Decrease/Pay)
                    SUM(CASE 
                        WHEN m.date >= %(date_from)s AND m.date <= %(date_to)s 
                             AND m.location_id IN %(customer_ids)s AND m.location_dest_id NOT IN %(customer_ids)s 
                        THEN m.product_uom_qty ELSE 0 END) as out_q
                FROM stock_move m
                JOIN product_product pp ON m.product_id = pp.id
                JOIN product_template pt ON pp.product_tmpl_id = pt.id
                WHERE m.state = 'done' 
                  AND (m.location_dest_id IN %(customer_ids)s OR m.location_id IN %(customer_ids)s)
                GROUP BY m.product_id, m.partner_id, pt.categ_id, pt.uom_id
            """
            self.env.cr.execute(query_debt, params)
            results = self.env.cr.dictfetchall()
            
            debt_map = {} 
            for row in results:
                closing = row['open'] + row['in_q'] - row['out_q']
                balance = round(closing, 4)
                if balance == 0 and row['open'] == 0 and row['in_q'] == 0:
                     continue
                
                # Debt > 0, Pawn < 0
                t_type = 'customer_debt' if balance >= 0 else 'customer_pawn'
                
                key = (row['product_id'], t_type)
                if key not in debt_map:
                    debt_map[key] = {
                        'product_id': row['product_id'],
                        'category_id': row['categ_id'],
                        'uom_id': row['uom_id'],
                        'ownership_type': t_type,
                        'opening_qty': 0.0, 'in_qty': 0.0, 'out_qty': 0.0, 'closing_qty': 0.0
                    }
                
                debt_map[key]['opening_qty'] += row['open']
                debt_map[key]['in_qty'] += row['in_q']
                debt_map[key]['out_qty'] += row['out_q']
                debt_map[key]['closing_qty'] += closing

            if debt_map:
                self.env['qlv.stock.balance.line'].create([
                    dict(val, report_id=self.id) for val in debt_map.values()
                ])
        
        # --- C. UPDATE VALUES (Pricing) ---
        lines = self.line_ids
        for line in lines:
             price = line.product_id.standard_price
             line.write({
                 'current_price': price,
                 'closing_value': line.closing_qty * price
             })

        # --- D. COMPUTE CATEGORY SUMMARY ---
        self.summary_line_ids.unlink()
        
        # Group lines by category
        categories = self.line_ids.mapped('category_id')
        summary_vals = []
        
        for idx, category in enumerate(categories, start=1):
            cat_lines = self.line_ids.filtered(lambda l: l.category_id == category)
            
            summary_vals.append({
                'report_id': self.id,
                'sequence': idx,
                'category_id': category.id,
                'opening_qty': sum(cat_lines.mapped('opening_qty')),
                'in_qty': sum(cat_lines.mapped('in_qty')),
                'out_qty': sum(cat_lines.mapped('out_qty')),
                'closing_qty': sum(cat_lines.mapped('closing_qty')),
                'closing_value': sum(cat_lines.mapped('closing_value')),
            })
        
        if summary_vals:
            self.env['qlv.stock.balance.summary'].create(summary_vals)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

class QlvStockBalanceLine(models.Model):
    _name = 'qlv.stock.balance.line'
    _description = 'Stock Balance Report Line'

    report_id = fields.Many2one('qlv.stock.balance', string='Report Reference', required=True, ondelete='cascade')
    
    product_id = fields.Many2one('product.product', string='Product', required=True)
    category_id = fields.Many2one('product.category', related='product_id.categ_id', string='Category', store=True)
    uom_id = fields.Many2one('uom.uom', related='product_id.uom_id', string='UoM', store=True)
    
    # Ownership Type
    ownership_type = fields.Selection([
        ('shop', 'Tại Quầy'),
        ('customer_debt', "K' Nợ"),
        ('customer_pawn', "K' Gửi"),
    ], string='Ownership', required=True, default='shop')

    # Quantities
    opening_qty = fields.Float(string='Tồn ĐK', digits='Product Unit of Measure')
    in_qty = fields.Float(string='Nhập', digits='Product Unit of Measure')
    out_qty = fields.Float(string='Xuất', digits='Product Unit of Measure')
    closing_qty = fields.Float(string='Tồn CK', digits='Product Unit of Measure')
    
    # Valuation
    current_price = fields.Float(string='Giá Mua', digits='Product Price')
    closing_value = fields.Float(string='Thành tiền', compute='_compute_value', store=True)
    
    @api.depends('closing_qty', 'current_price')
    def _compute_value(self):
        for line in self:
            line.closing_value = line.closing_qty * line.current_price

class QlvStockBalanceSummary(models.Model):
    _name = 'qlv.stock.balance.summary'
    _description = 'Stock Balance Summary by Category'
    _order = 'sequence, category_id'

    report_id = fields.Many2one('qlv.stock.balance', string='Report Reference', required=True, ondelete='cascade')
    sequence = fields.Integer(string='STT', default=10)
    category_id = fields.Many2one('product.category', string='Nhóm SP', required=True)
    
    # Quantities (sum of all products in category)
    opening_qty = fields.Float(string='Tồn ĐK TTL', digits='Product Unit of Measure')
    in_qty = fields.Float(string='Nhập TTL', digits='Product Unit of Measure')
    out_qty = fields.Float(string='Xuất TTL', digits='Product Unit of Measure')
    closing_qty = fields.Float(string='Tồn TTL', digits='Product Unit of Measure')
    
    # Valuation
    closing_value = fields.Float(string='Thành tiền', digits='Product Price')

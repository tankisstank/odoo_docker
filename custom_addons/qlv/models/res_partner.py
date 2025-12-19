# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_gold_partner = fields.Boolean(string="Is Gold Partner", help="Check this box if this partner is a special gold shop partner for debt management.")
    
    # Old Field (Deprecate or Keep as Legacy if needed, but we start fresh)
    # Old Field (Kept for View Compatibility during upgrade, will be removed later)
    current_net_debt = fields.Monetary(string="Net Debt (Legacy)", currency_field='currency_id')
    
    product_debt_summary = fields.Html(string="Tài sản Nợ/Ký gửi", compute='_compute_product_debt', store=False)
    debt_summary_short = fields.Char(string="Tóm tắt Công nợ", compute='_compute_product_debt', store=False)
    
    def _compute_product_debt(self):
        """
        Tính toán công nợ dựa trên sự chênh lệch (Gap) giữa 
        Số lượng Đặt (Cam kết) và Số lượng Thực tế (Kho).
        Optimized for Batch Processing (List View).
        """
        # 1. Initialize logic
        for partner in self:
            partner.product_debt_summary = False
            partner.debt_summary_short = False
            
        partners_to_compute = self.filtered(lambda p: p.is_gold_partner)
        if not partners_to_compute:
            return

        # 2. Bulk Search for all lines of these partners
        domain = [
            ('order_partner_id', 'in', partners_to_compute.ids),
            ('state', 'in', ('sale', 'done')),
        ]
        
        # We need to fetch fields to calculate locally. 
        # Note: Fetching thousands of lines might be heavy, but better than N queries.
        # Ideally use read_group, but we need exact diff per product.
        # read_group doesn't support "Sum(qty_ordered - qty_delivered)" easily without stored field.
        # So we fetch lines.
        
        lines = self.env['sale.order.line'].search(domain)
        
        # 3. Process in Memory
        # Map: {partner_id: {product_name: {'qty': 0.0, 'uom': ''}}}
        partner_debt_map = {}
        
        for line in lines:
            # Optimization: Skip balanced lines immediately
            # Using float compare
            diff = line.product_uom_qty - line.qty_delivered
            if abs(diff) < 0.001:
                continue
                
            pid = line.order_partner_id.id
            if pid not in partner_debt_map:
                partner_debt_map[pid] = {}
            
            p_name = line.product_id.name
            uom_name = line.product_uom.name
            
            if p_name not in partner_debt_map[pid]:
                partner_debt_map[pid][p_name] = {'qty': 0.0, 'uom': uom_name}
            
            # Logic Direction
            if line.is_trade_in or (line.company_id.money_product_id and line.product_id == line.company_id.money_product_id):
                partner_debt_map[pid][p_name]['qty'] += diff
            else:
                partner_debt_map[pid][p_name]['qty'] -= diff

        # 4. Assign Results
        for partner in partners_to_compute:
            if partner.id not in partner_debt_map:
                partner.product_debt_summary = "<span class='text-success'>Không có công nợ</span>"
                partner.debt_summary_short = False # Or ""
                continue
                
            data_map = partner_debt_map[partner.id]
            
            html_rows = ""
            short_texts = []
            
            for name, info in data_map.items():
                qty = info['qty']
                if abs(qty) < 0.001:
                    continue
                    
                # Determine Label
                # Qty > 0: Khách Nợ (Debt)
                # Qty < 0: Shop Nợ (Consignment)
                
                is_debt = qty > 0
                label = "Nợ" if is_debt else "Gửi"
                
                # Format: "Vàng: 1.0 (Gửi)"
                formatted_qty = f"{abs(qty):,.3f}"
                short_texts.append(f"{name}: {formatted_qty} ({label})")
                
                # HTML
                status_html = "Khách nợ" if is_debt else "Ký gửi"
                color = "text-danger" if is_debt else "text-primary"
                html_rows += f"<tr><td>{name}</td><td class='text-right'>{formatted_qty} {info['uom']}</td><td class='{color}'>{status_html}</td></tr>"

            if html_rows:
                partner.product_debt_summary = f"<table class='table table-sm table-borderless'><tbody>{html_rows}</tbody></table>"
                partner.debt_summary_short = " | ".join(short_texts)
            else:
                partner.product_debt_summary = "<span class='text-success'>Cân bằng</span>"
                partner.debt_summary_short = False

    def action_view_debt_details(self):
        """
        Open the detailed list of 'Pending' Order Lines.
        """
        self.ensure_one()
        # Filter Logic in Domain:
        # State in ('sale', 'done') AND Qty != Delivered
        # Odoo Domain doesn't support field comparison (qty != delivered).
        # So we must find IDs in Python.
        
        lines = self.env['sale.order.line'].search([
            ('order_partner_id', '=', self.id),
            ('state', 'in', ('sale', 'done'))
        ])
        
        # Filter for pending
        # Note: Optimization for large datasets is needed, but for now this is fine.
        pending_ids = lines.filtered(lambda l: abs(l.product_uom_qty - l.qty_delivered) > 0.001).ids
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Chi tiết Công nợ (Sản phẩm)',
            'res_model': 'sale.order.line',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', pending_ids)],
            'context': {'create': False, 'edit': False},
        }

    def action_recompute_debt(self):
        """
        Manual/Server Action to force re-calculation of debt.
        """
        for partner in self:
            partner._compute_product_debt()

# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_gold_partner = fields.Boolean(string="Is Gold Partner", help="Check this box if this partner is a special gold shop partner for debt management.")
    
    current_net_debt = fields.Monetary(string="Net Debt", compute='_compute_net_debt', currency_field='currency_id', help="Positive: Customer owes us. Negative: We owe Customer.")
    
    @api.depends('debit', 'credit')
    def _compute_net_debt(self):
        for partner in self:
            # debit: Receivable (Phải thu)
            # credit: Payable (Phải trả)
            partner.current_net_debt = partner.debit - partner.credit

    def action_view_debt_details(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Partner Ledger',
            'res_model': 'account.move.line',
            'view_mode': 'tree',
            'domain': [
                ('partner_id', '=', self.id),
                ('move_id.state', '=', 'posted'),
                ('account_id.account_type', 'in', ('asset_receivable', 'liability_payable')),
                ('reconciled', '=', False)
            ],
            'context': {'search_default_unreconciled': 1},
        }

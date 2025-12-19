# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class DebtReportWizard(models.TransientModel):
    _name = 'gold.debt.report.wizard'
    _description = 'Debt Report Wizard'

    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True, default=fields.Date.context_today)
    partner_ids = fields.Many2many('res.partner', string='Partners', domain="[('is_gold_partner', '=', True)]")
    
    def action_print_summary(self):
        data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'partner_ids': self.partner_ids.ids,
        }
        return self.env.ref('gold_shop_debt.action_report_debt_summary').report_action(self, data=data)

    def action_print_detail(self):
        data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'partner_ids': self.partner_ids.ids,
        }
        return self.env.ref('gold_shop_debt.action_report_debt_detail').report_action(self, data=data)

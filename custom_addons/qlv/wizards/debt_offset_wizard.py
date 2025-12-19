# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class DebtOffsetWizard(models.TransientModel):
    _name = 'gold.debt.offset.wizard'
    _description = 'Debt Offset Wizard'

    partner_id = fields.Many2one('res.partner', string='Partner', required=True)
    date = fields.Date(string='Offset Date', default=fields.Date.context_today, required=True)
    journal_id = fields.Many2one('account.journal', string='Journal', domain=[('type', '=', 'general')], required=True)
    
    receivable_amount = fields.Monetary(string='Total Receivable', compute='_compute_amounts', currency_field='currency_id')
    payable_amount = fields.Monetary(string='Total Payable', compute='_compute_amounts', currency_field='currency_id')
    offset_amount = fields.Monetary(string='Offset Amount', compute='_compute_amounts', currency_field='currency_id', store=True, readonly=False)
    currency_id = fields.Many2one('res.currency', related='partner_id.currency_id')

    @api.depends('partner_id')
    def _compute_amounts(self):
        for wizard in self:
            if not wizard.partner_id:
                wizard.receivable_amount = 0
                wizard.payable_amount = 0
                wizard.offset_amount = 0
                continue
                
            # Get unreconciled lines
            domain = [
                ('partner_id', '=', wizard.partner_id.id),
                ('move_id.state', '=', 'posted'),
                ('reconciled', '=', False),
                ('account_id.reconcile', '=', True),
            ]
            lines = self.env['account.move.line'].search(domain)
            
            receivable = sum(lines.filtered(lambda l: l.account_id.account_type == 'asset_receivable').mapped('amount_residual'))
            payable = sum(lines.filtered(lambda l: l.account_id.account_type == 'liability_payable').mapped('amount_residual'))
            
            # amount_residual is positive for debit (receivable) and negative for credit (payable) usually?
            # Actually amount_residual_currency or amount_residual.
            # For receivable: Debit is positive.
            # For payable: Credit is positive (so amount_residual might be negative).
            
            # Let's check standard Odoo behavior.
            # Receivable: Debit side. Residual > 0.
            # Payable: Credit side. Residual < 0.
            
            wizard.receivable_amount = sum(l.amount_residual for l in lines if l.account_id.account_type == 'asset_receivable')
            wizard.payable_amount = -sum(l.amount_residual for l in lines if l.account_id.account_type == 'liability_payable')
            
            # Offset is the min of the two absolute values
            wizard.offset_amount = min(abs(wizard.receivable_amount), abs(wizard.payable_amount))

    def action_offset_debt(self):
        self.ensure_one()
        if self.offset_amount <= 0:
            raise UserError(_("No amount to offset."))

        # 1. Create Journal Entry to transfer debt
        # Debit Payable Account (Decrease Payable)
        # Credit Receivable Account (Decrease Receivable)
        
        receivable_lines = self.env['account.move.line'].search([
            ('partner_id', '=', self.partner_id.id),
            ('move_id.state', '=', 'posted'),
            ('reconciled', '=', False),
            ('account_id.account_type', '=', 'asset_receivable')
        ])
        payable_lines = self.env['account.move.line'].search([
            ('partner_id', '=', self.partner_id.id),
            ('move_id.state', '=', 'posted'),
            ('reconciled', '=', False),
            ('account_id.account_type', '=', 'liability_payable')
        ])
        
        if not receivable_lines or not payable_lines:
             raise UserError(_("Missing receivable or payable lines to offset."))

        receivable_account = receivable_lines[0].account_id
        payable_account = payable_lines[0].account_id

        move_vals = {
            'journal_id': self.journal_id.id,
            'date': self.date,
            'ref': _('Debt Offset for %s') % self.partner_id.name,
            'line_ids': [
                (0, 0, {
                    'name': _('Debt Offset - Payable'),
                    'account_id': payable_account.id,
                    'partner_id': self.partner_id.id,
                    'debit': self.offset_amount,
                    'credit': 0,
                }),
                (0, 0, {
                    'name': _('Debt Offset - Receivable'),
                    'account_id': receivable_account.id,
                    'partner_id': self.partner_id.id,
                    'debit': 0,
                    'credit': self.offset_amount,
                }),
            ]
        }
        move = self.env['account.move'].create(move_vals)
        move.action_post()

        # 2. Reconcile
        # Match the new Debit line (Payable side) with existing Payable lines (Credit side)
        payable_offset_line = move.line_ids.filtered(lambda l: l.account_id == payable_account)
        (payable_lines + payable_offset_line).reconcile()

        # Match the new Credit line (Receivable side) with existing Receivable lines (Debit side)
        receivable_offset_line = move.line_ids.filtered(lambda l: l.account_id == receivable_account)
        (receivable_lines + receivable_offset_line).reconcile()

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

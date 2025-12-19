# -*- coding: utf-8 -*-
from odoo import models, api

class DebtReportSummary(models.AbstractModel):
    _name = 'report.qlv.report_debt_summary_template'
    _description = 'Debt Summary Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        partner_ids = data.get('partner_ids')
        
        partners = self.env['res.partner'].browse(partner_ids)
        docs = []
        
        for partner in partners:
            # Calculate Opening Balance (Before date_from)
            domain_opening = [
                ('partner_id', '=', partner.id),
                ('move_id.state', '=', 'posted'),
                ('account_id.account_type', 'in', ('asset_receivable', 'liability_payable')),
                ('date', '<', date_from)
            ]
            lines_opening = self.env['account.move.line'].search(domain_opening)
            opening = sum(lines_opening.mapped('debit')) - sum(lines_opening.mapped('credit'))
            
            # Calculate Period Movement
            domain_period = [
                ('partner_id', '=', partner.id),
                ('move_id.state', '=', 'posted'),
                ('account_id.account_type', 'in', ('asset_receivable', 'liability_payable')),
                ('date', '>=', date_from),
                ('date', '<=', date_to)
            ]
            lines_period = self.env['account.move.line'].search(domain_period)
            debit = sum(lines_period.mapped('debit'))
            credit = sum(lines_period.mapped('credit'))
            
            closing = opening + debit - credit
            
            docs.append({
                'name': partner.name,
                'opening': opening,
                'debit': debit,
                'credit': credit,
                'closing': closing,
            })
            
        return {
            'doc_ids': docids,
            'doc_model': 'gold.debt.report.wizard',
            'data': data,
            'docs': docs,
        }

class DebtReportDetail(models.AbstractModel):
    _name = 'report.qlv.report_debt_detail_template'
    _description = 'Debt Detail Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        partner_ids = data.get('partner_ids')
        
        partners = self.env['res.partner'].browse(partner_ids)
        docs = []
        
        for partner in partners:
            # Opening Balance
            domain_opening = [
                ('partner_id', '=', partner.id),
                ('move_id.state', '=', 'posted'),
                ('account_id.account_type', 'in', ('asset_receivable', 'liability_payable')),
                ('date', '<', date_from)
            ]
            lines_opening = self.env['account.move.line'].search(domain_opening)
            opening = sum(lines_opening.mapped('debit')) - sum(lines_opening.mapped('credit'))
            
            # Period Transactions
            domain_period = [
                ('partner_id', '=', partner.id),
                ('move_id.state', '=', 'posted'),
                ('account_id.account_type', 'in', ('asset_receivable', 'liability_payable')),
                ('date', '>=', date_from),
                ('date', '<=', date_to)
            ]
            lines_period = self.env['account.move.line'].search(domain_period, order='date asc, id asc')
            
            lines_data = []
            current_balance = opening
            total_debit = 0
            total_credit = 0
            
            for line in lines_period:
                current_balance += (line.debit - line.credit)
                total_debit += line.debit
                total_credit += line.credit
                
                lines_data.append({
                    'date': line.date,
                    'ref': line.move_id.name,
                    'name': line.name,
                    'product': line.product_id.name if line.product_id else '',
                    'qty': line.quantity if line.product_id else '',
                    'price': line.price_unit if line.product_id else '',
                    'debit': line.debit,
                    'credit': line.credit,
                    'balance': current_balance,
                })
                
            docs.append({
                'name': partner.name,
                'opening': opening,
                'lines': lines_data,
                'total_debit': total_debit,
                'total_credit': total_credit,
                'closing': current_balance,
            })
            
        return {
            'doc_ids': docids,
            'doc_model': 'gold.debt.report.wizard',
            'data': data,
            'docs': docs,
        }

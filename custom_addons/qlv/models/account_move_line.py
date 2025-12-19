from odoo import models, fields

class AccountMoveLine(models.Model):
    _name = 'account.move.line'
    _inherit = ['account.move.line', 'product.conversion.mixin']

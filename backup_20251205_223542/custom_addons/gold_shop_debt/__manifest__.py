# -*- coding: utf-8 -*-
{
    'name': "Gold Shop Debt Management",
    'summary': """
        Manage debt for special partners (customers/vendors) in Gold Shop.
        Includes Net Debt calculation, Debt Offset wizard, and Reports.
    """,
    'description': """
Gold Shop Debt Management
=========================
* Identify Special Partners (Gold Partners).
* Calculate Net Debt (Receivable - Payable).
* Wizard to offset Receivable and Payable amounts.
* Detailed and Summary Debt Reports.
    """,
    'author': "QLV Development Team",
    'website': "https://www.yourgoldshop.com",
    'category': 'Accounting',
    'version': '16.0.1.0.0',
    'depends': ['base', 'account', 'sale_trade_in', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_view.xml',
        'wizards/debt_offset_wizard_view.xml',
        'wizards/debt_report_wizard_view.xml',
        'views/menu_view.xml',
        'reports/debt_report.xml',
    ],
    'license': 'LGPL-3',
}

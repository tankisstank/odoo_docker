# -*- coding: utf-8 -*-
{
    'name': "QLV Addon",
    'post_init_hook': 'post_init_hook',
    'summary': """
        Complete Gold Shop Management: Sales, Trade-in, Pawn, Auto-Balance, and Stock/Debt Control.
    """,
    'description': """
        Core Features:
        - Gold & Money Management
        - Trade-in & Pawn Mechanism
        - Auto-Balance Money (Cash Flow)
        - Locked Orders & Super Cancel
        - Debt Management & Offsetting
    """,
    'author': "QLV Development Team",
    'website': "https://www.yourgoldshop.com",
    'category': 'Customization',
    'version': '16.0.2.0.0',
    'depends': ['base', 'web', 'mail', 'portal', 'website', 'sale', 'website_payment', 'account', 'stock', 'sale_stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_price_view.xml',
        'views/res_config_settings_view.xml',
        'views/sale_order_view.xml',
        'views/sale_order_line_view.xml',
        'views/account_move_view.xml',
        'views/stock_picking_view.xml',
        'views/res_partner_view.xml',
        'wizards/debt_offset_wizard_view.xml',
        'wizards/debt_report_wizard_view.xml',
        'reports/debt_report.xml',
        'views/pawn_order_view.xml',
        'views/menu_view.xml',
        'views/report_sale_order.xml',
        'views/sale_order_report_templates.xml',
        'views/invoice_report_templates.xml',
        'views/portal_templates.xml',
        'views/website_templates.xml',
        'views/web_client_templates.xml',
        'views/product_hide_tax_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'qlv/static/src/js/web_client_patch.js',
            # 'qlv/static/src/js/force_sort_patch.js',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}

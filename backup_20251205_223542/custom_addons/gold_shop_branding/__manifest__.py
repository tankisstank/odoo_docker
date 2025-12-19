# -*- coding: utf-8 -*-
{
    'name': "Gold Shop Branding",
    'summary': """
        Custom branding for Gold Shop: Remove Odoo branding, add Store info.
    """,
    'description': """
        This module removes "Powered by Odoo" links and replaces them with Store branding.
        - Removes Odoo branding from Emails.
        - Removes Odoo branding from Website Footer.
        - Removes Odoo branding from Portal.
        - Replaces Odoo Favicon.
    """,
    'author': "Gold Shop",
    'website': "https://www.yourgoldshop.com",
    'category': 'Customization',
    'version': '16.0.1.0.0',
    'depends': ['base', 'web', 'mail', 'portal', 'website', 'sale', 'website_payment'],
    'data': [
        'views/portal_templates.xml',
        'views/website_templates.xml',
        'views/web_client_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'gold_shop_branding/static/src/js/web_client_patch.js',
        ],
        'web.assets_frontend': [
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

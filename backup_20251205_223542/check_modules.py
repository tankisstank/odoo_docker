import xmlrpc.client

ODOO_CONFIG = {
    'url': 'http://mdl.tail986a43.ts.net:8069',
    'db': 'odoo_test',
    'username': 'c0508g@gmail.com',
    'password': 'abc123'
}

def check_modules():
    common = xmlrpc.client.ServerProxy(f'{ODOO_CONFIG["url"]}/xmlrpc/2/common')
    uid = common.authenticate(ODOO_CONFIG['db'], ODOO_CONFIG['username'], ODOO_CONFIG['password'], {})
    models = xmlrpc.client.ServerProxy(f'{ODOO_CONFIG["url"]}/xmlrpc/2/object')

    modules = models.execute_kw(ODOO_CONFIG['db'], uid, ODOO_CONFIG['password'],
        'ir.module.module', 'search_read', [[['name', '=', 'product_price_manager']]], {'fields': ['name', 'state']})
    print(modules)

if __name__ == '__main__':
    check_modules()

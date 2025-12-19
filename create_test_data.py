import xmlrpc.client

ODOO_CONFIG = {
    'url': 'http://localhost:8069',
    'db': 'qlv_new',
    'username': 'c0508g@gmail.com',
    'password': 'abc123',
}

def create_partner():
    common = xmlrpc.client.ServerProxy(f"{ODOO_CONFIG['url']}/xmlrpc/2/common")
    uid = common.authenticate(ODOO_CONFIG['db'], ODOO_CONFIG['username'], ODOO_CONFIG['password'], {})
    models = xmlrpc.client.ServerProxy(f"{ODOO_CONFIG['url']}/xmlrpc/2/object")
    
    # Check if exists
    ids = models.execute_kw(ODOO_CONFIG['db'], uid, ODOO_CONFIG['password'], 'res.partner', 'search', [[['name', '=', 'Nguyễn Văn Dũng']]])
    if not ids:
        models.execute_kw(ODOO_CONFIG['db'], uid, ODOO_CONFIG['password'], 'res.partner', 'create', [{'name': 'Nguyễn Văn Dũng'}])
        print("Created 'Nguyễn Văn Dũng'")
    else:
        print("'Nguyễn Văn Dũng' already exists")

if __name__ == '__main__':
    create_partner()

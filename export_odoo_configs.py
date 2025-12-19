import xmlrpc.client
import json
import os
import datetime

ODOO_CONFIG = {
    'url': 'http://mdl.tail986a43.ts.net:8069',
    'db': 'odoo_test',
    'username': 'c0508g@gmail.com',
    'password': 'abc123'
}

def export_configs():
    print(f"Connecting to Odoo at {ODOO_CONFIG['url']}...")
    try:
        common = xmlrpc.client.ServerProxy(f'{ODOO_CONFIG["url"]}/xmlrpc/2/common')
        uid = common.authenticate(ODOO_CONFIG['db'], ODOO_CONFIG['username'], ODOO_CONFIG['password'], {})
    except Exception as e:
        print(f"Connection error: {e}")
        return

    if not uid:
        print("Authentication failed. Please check username/password.")
        return

    print(f"Authenticated successfully with UID: {uid}")
    models = xmlrpc.client.ServerProxy(f'{ODOO_CONFIG["url"]}/xmlrpc/2/object')
    
    export_data = {}

    # 1. Export System Parameters (ir.config_parameter)
    print("Exporting ir.config_parameter...")
    try:
        config_params = models.execute_kw(ODOO_CONFIG['db'], uid, ODOO_CONFIG['password'],
            'ir.config_parameter', 'search_read', [[]], {'fields': ['key', 'value']})
        export_data['ir.config_parameter'] = config_params
    except Exception as e:
        print(f"Error exporting ir.config_parameter: {e}")

    # 2. Export Company Settings (res.company)
    print("Exporting res.company...")
    try:
        # Fetch all fields for company to get full settings
        companies = models.execute_kw(ODOO_CONFIG['db'], uid, ODOO_CONFIG['password'],
            'res.company', 'search_read', [[]])
        export_data['res.company'] = companies
    except Exception as e:
        print(f"Error exporting res.company: {e}")
        
    # 3. Export Installed Modules (ir.module.module)
    print("Exporting installed modules...")
    try:
        modules = models.execute_kw(ODOO_CONFIG['db'], uid, ODOO_CONFIG['password'],
            'ir.module.module', 'search_read', [[['state', '=', 'installed']]], 
            {'fields': ['name', 'shortdesc', 'state', 'installed_version']})
        export_data['installed_modules'] = modules
    except Exception as e:
        print(f"Error exporting installed modules: {e}")

    # 4. Export Res Config Settings (This is tricky as it's a transient model, but we can try to see if there are defaults)
    # Actually, ir.values was used in older versions. In newer versions, it's mostly ir.config_parameter.
    # We can check for 'ir.default' (User-defined defaults)
    print("Exporting ir.default...")
    try:
        ir_defaults = models.execute_kw(ODOO_CONFIG['db'], uid, ODOO_CONFIG['password'],
            'ir.default', 'search_read', [[]])
        export_data['ir.default'] = ir_defaults
    except Exception as e:
        print(f"Error exporting ir.default: {e}")

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f'odoo_configs_backup_{timestamp}.json'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=4, ensure_ascii=False, default=str)
        
    print(f"Backup saved to {output_file}")

if __name__ == '__main__':
    export_configs()

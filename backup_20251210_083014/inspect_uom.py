import xmlrpc.client
import sys

ODOO_URL = 'http://localhost:8069'
DB_NAME = 'qlv_new'
USERNAME = 'c0508g@gmail.com'
PASSWORD = 'abc123'

def inspect_model_fields(model_name):
    try:
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
        uid = common.authenticate(DB_NAME, USERNAME, PASSWORD, {})
        if not uid:
            print("Auth failed")
            return

        models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
        fields = models.execute_kw(DB_NAME, uid, PASSWORD,
                                   model_name, 'fields_get',
                                   [], {'attributes': ['string', 'type', 'help']})
        
        print(f"Fields for {model_name}:")
        for field, props in fields.items():
            print(f"- {field}: {props}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_model_fields('uom.category')

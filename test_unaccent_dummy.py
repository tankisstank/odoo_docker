import xmlrpc.client

ODOO_CONFIG = {
    'url': 'http://localhost:8069',
    'db': 'qlv_new',
    'username': 'c0508g@gmail.com',
    'password': 'abc123',
}

def test_unaccent():
    # We can't run SELECT directly via ORM, but we can search.
    # We can try to search where unaccent(name) = '...'? No.
    # BUT, we can use 'execute_kw' on a model that allows executing arbitrary SQL? No.
    # However, 'res.partner' usually has name_search.
    # Let's try to infer unaccent behavior.
    # If we search for 'Dung' and find 'Dũng', unaccent works.
    # Logic:
    # 1. Search [('name', 'ilike', 'Dũng')] -> Should find Dũng.
    # 2. Search [('name', 'ilike', 'dung')] -> Should find Dũng IF unaccent works.
    
    # Check if unaccent is actually enabled in the query.
    # We can check logs if log level is debug.
    pass

# Direct SQL via psycopg2 if possible?
# But we need to install psycopg2. It is usually available in Odoo environment.
# Let's try to use the Odoo shell via docker exec.
print("Use execution via docker exec to check unaccent")

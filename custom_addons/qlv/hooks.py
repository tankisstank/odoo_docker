# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID

def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    # Enable unaccent extension
    env.cr.execute("CREATE EXTENSION IF NOT EXISTS unaccent;")
    # Enable pg_trgm extension for fuzzy search
    env.cr.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    # Create trigram index for res.partner display_name for faster fuzzy search
    env.cr.execute("""
        CREATE INDEX IF NOT EXISTS res_partner_display_name_trgm_gin 
        ON res_partner USING gin (display_name gin_trgm_ops);
    """)
    print("QLV: Enabled unaccent and pg_trgm extensions, and created trigram index on res.partner")

# Script to activate custom addons
$addons = "gold_shop_branding,gold_shop_debt,product_price_manager,sale_trade_in"
Write-Host "Activating addons: $addons"
docker exec -it odoo_server odoo -c /etc/odoo/odoo.conf -d odoo -u $addons --stop-after-init --db_host=db --db_user=odoo --db_password=odoo
Write-Host "Restarting Odoo server..."
docker restart odoo_server
Write-Host "Done."

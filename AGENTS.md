# AGENTS.md - QLV (Quản lý Vàng) - Hệ thống Kinh doanh Vàng & Cầm đồ

## Quick Commands
- **Start:** `docker-compose up -d` | **Stop:** `docker-compose down` | **Logs:** `docker logs odoo_server -f`
- **Backup/Restore:** `.\backup_odoo.ps1` / `.\restore_odoo.ps1`
- **Migration (SQL Server → Odoo):** `python migrate_data.py`
- **Test P&L Report:** `python test_pnl_report.py` | **Test Transactions:** `python test_daily_transactions.py`

## Architecture
- **Odoo 16** + PostgreSQL 13 via Docker (`localhost:8069`, db: `odoo/odoo/odoo`)
- **Module `qlv`** (`custom_addons/qlv/`): Extends `sale.order`, `product.product`, `stock.*`
- **Docs:** `docs/technical_architecture.md` (flow diagrams), `docs/functional_requirements.md`

## Business Logic (QLV Module)
- **Tiền là Hàng:** Cash managed as storable product in inventory (Thu/Chi → Receipt/Delivery)
- **Auto-Balance:** Auto-generates money line to balance order total to 0
- **Trade-in:** `is_trade_in=True` → negative price, routed to Receipt instead of Delivery
- **Conversion Mixin:** Gold purity conversion (e.g., Vàng Tây 60% → Vàng 9999)
- **Order Locking:** `write()` blocks edits on `invoiced`/`done` orders; use `action_super_cancel()` to revert
- **Settle Debt:** `action_settle_debt()` transfers pending items from old order to new, cancels old pickings
- **Daily P&L Report:** `qlv.stock.balance` model - tính Lãi/Lỗ = (Tồn CK + Tiền CK) - (Tồn ĐK + Tiền ĐK)

## Code Style
- Header: `# -*- coding: utf-8 -*-` | Imports: `from odoo import models, fields, api, _`
- Logging: `_logger = logging.getLogger(__name__)` | Errors: `raise UserError(_("Vietnamese msg"))`
- Inherit: `_inherit = 'model.name'` | New model: `_name = 'model.name'`
- Vietnamese comments/UI strings are standard; wrap user-facing text with `_()`

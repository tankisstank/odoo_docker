# -*- coding: utf-8 -*-
import logging

def migrate_debts(self):
    """
    Di chuyển công nợ cũ từ tb_CTNo thành các bút toán nhật ký (account.move).
    - 'N' (Nợ) được chuyển thành Hóa đơn khách hàng (Customer Invoice).
    - 'C' (Có) được chuyển thành Hóa đơn trả hàng (Credit Note).
    """
    logging.info("Bắt đầu di chuyển Công nợ (Debts)...")
    
    # 1. Thiết lập ban đầu: Lấy các tài khoản và nhật ký cần thiết
    try:
        # Lấy nhật ký bán hàng
        sale_journal_ids = self.execute_odoo_kw('account.journal', 'search', args_list=[[('type', '=', 'sale')]], kw_dict={'limit': 1})
        if not sale_journal_ids:
            logging.error("Không tìm thấy nhật ký bán hàng (Sales Journal). Dừng di chuyển công nợ.")
            return
        sale_journal_id = sale_journal_ids[0]

        # Lấy tài khoản phải thu và tài khoản doanh thu mặc định
        user_company = self.execute_odoo_kw('res.users', 'read', args_list=[[self.uid]], kw_dict={'fields': ['company_id']})[0]
        company_id = user_company['company_id'][0]
        
        # Thay thế ir.property.get bằng search trên account.account
        receivable_accounts = self.execute_odoo_kw('account.account', 'search', 
            args_list=[[('account_type', '=', 'asset_receivable'), ('company_id', '=', company_id), ('deprecated', '=', False)]], 
            kw_dict={'limit': 1})
        
        if not receivable_accounts:
            logging.error("Không tìm thấy tài khoản phải thu (Receivable Account). Dừng di chuyển công nợ.")
            return
        receivable_account_id = receivable_accounts[0]

        income_account_ids = self.execute_odoo_kw('account.account', 'search', 
            args_list=[[('account_type', '=', 'income'), ('company_id', '=', company_id), ('deprecated', '=', False)]], 
            kw_dict={'limit': 1})
        if not income_account_ids:
            logging.error("Không tìm thấy tài khoản doanh thu. Dừng di chuyển công nợ.")
            return
        income_account_id = income_account_ids[0]

        logging.info(f"Sử dụng Nhật ký ID: {sale_journal_id}, TK Phải thu ID: {receivable_account_id}, TK Doanh thu ID: {income_account_id}")

    except Exception as e:
        logging.error(f"Lỗi khi thiết lập ban đầu cho di chuyển công nợ: {e}")
        return

    # 2. Lấy dữ liệu công nợ
    cursor = self.sql_conn.cursor()
    # Cập nhật tên cột chính xác theo schema thực tế
    cursor.execute("SELECT MaNghoeo, MaBH, ThoiGian, TTL, HinhThucNo FROM tb_CTNo ORDER BY ThoiGian ASC")
    debt_transactions = cursor.fetchall()
    total_debts = len(debt_transactions)
    logging.info(f"Tìm thấy {total_debts} giao dịch công nợ trong tb_CTNo.")

    if 'debt' not in self.mapping:
        self.mapping['debt'] = set()

    for i, (ma_nghoeo, ma_bh, thoi_gian, ttl, hinh_thuc_no) in enumerate(debt_transactions):
        ma_bh_str = str(ma_bh) if ma_bh is not None else None
        hinh_thuc = str(hinh_thuc_no).strip()
        amount = float(ttl or 0.0)

        # Idempotency check: Tạo một key duy nhất cho mỗi giao dịch
        idempotency_key = f"{ma_nghoeo}-{ma_bh_str}-{thoi_gian}-{amount}-{hinh_thuc}"
        if idempotency_key in self.mapping['debt']:
            logging.info(f"[{i+1}/{total_debts}] Giao dịch công nợ '{idempotency_key}' đã được di chuyển. Bỏ qua.")
            continue

        # Tìm đối tác Odoo tương ứng bằng 'ref'
        partner_id = None
        if ma_bh_str:
            partner_ids = self.execute_odoo_kw('res.partner', 'search', args_list=[[('ref', '=', ma_bh_str)]], kw_dict={'limit': 1})
            if partner_ids:
                partner_id = partner_ids[0]

        if not partner_id:
            logging.warning(f"[{i+1}/{total_debts}] Không tìm thấy đối tác cho MaBH '{ma_bh_str}'. Bỏ qua giao dịch công nợ.")
            continue
        
        # Xác định loại bút toán
        # HinhThucNo = 1: Tăng nợ/Nhận (Hóa đơn)
        # HinhThucNo = -1: Giảm nợ/Trả (Hoàn tiền)
        if hinh_thuc == '1':
            move_type = 'out_invoice' # Hóa đơn khách hàng
            log_msg = "Hóa đơn"
        elif hinh_thuc == '-1':
            move_type = 'out_refund' # Hóa đơn trả hàng
            log_msg = "Hóa đơn trả"
        else:
            logging.warning(f"[{i+1}/{total_debts}] Loại công nợ '{hinh_thuc}' không xác định. Bỏ qua.")
            continue

        # 3. Tạo bút toán (account.move)
        move_data = {
            'move_type': move_type,
            'partner_id': partner_id,
            'journal_id': sale_journal_id,
            'date': thoi_gian.strftime('%Y-%m-%d'),
            'ref': str(ma_nghoeo).strip() if ma_nghoeo else None,
            'invoice_line_ids': [(0, 0, {
                'name': f"Di chuyển công nợ cũ (Ref: {str(ma_nghoeo).strip() if ma_nghoeo else 'N/A'})",
                'account_id': income_account_id,
                'price_unit': amount,
                'quantity': 1,
            })]
        }

        try:
            logging.info(f"[{i+1}/{total_debts}] Tạo {log_msg} cho đối tác '{ma_bh_str}' với số tiền {amount}")
            new_move_id = self.execute_odoo_kw('account.move', 'create', args_list=[move_data])
            
            # Xác nhận bút toán
            if new_move_id:
                self.execute_odoo_kw('account.move', 'action_post', args_list=[[new_move_id]])
                logging.info(f"Đã tạo và xác nhận thành công Bút toán ID: {new_move_id} (từ MaNghoeo: {ma_nghoeo})")
                self.mapping['debt'].add(idempotency_key)

        except Exception as e:
            logging.error(f"Lỗi khi di chuyển công nợ cho MaBH '{ma_bh_str}', Ref '{ma_nghoeo}': {e}")

    logging.info("Di chuyển Công nợ (Debts) hoàn tất.")
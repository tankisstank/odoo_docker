# -*- coding: utf-8 -*-
import logging

def migrate_sale_orders(self):
    """Di chuyển các đơn hàng cũ từ tb_GD và tb_CTGD."""
    logging.info("Bắt đầu di chuyển Đơn hàng (Sales Orders)...")
    cursor = self.sql_conn.cursor()

    cursor.execute("SELECT MaGD, MaBH, ThoiGian, MaND, LoaiPhieu, TinhTrang FROM tb_GD ORDER BY ThoiGian ASC")
    sales_transactions = cursor.fetchall()
    logging.info(f"Tìm thấy {len(sales_transactions)} giao dịch trong tb_GD.")

    for i, (ma_gd, ma_bh, thoi_gian, ma_nd, loai_phieu, tinh_trang) in enumerate(sales_transactions):
        ma_gd_str = str(ma_gd).strip()
        
        if loai_phieu not in (1, 14):
            continue

        if ma_gd_str in self.mapping['order']:
            logging.info(f"[{i+1}/{len(sales_transactions)}] Đơn hàng với MaGD '{ma_gd_str}' đã được di chuyển. Bỏ qua.")
            continue

        partner_id = None
        if ma_bh:
            partner_ids = self.execute_odoo_kw('res.partner', 'search', args_list=[[('ref', '=', str(ma_bh))]], kw_dict={'limit': 1})
            if partner_ids:
                partner_id = partner_ids[0]

        if not partner_id:
            logging.warning(f"[{i+1}/{len(sales_transactions)}] Không tìm thấy đối tác cho MaBH '{ma_bh}' của đơn hàng '{ma_gd_str}'. Bỏ qua đơn hàng.")
            continue
        
        user_id = self.mapping['user'].get(str(ma_nd) if ma_nd else None, self.uid)

        order_data = {
            'partner_id': partner_id,
            'state': 'draft', 
            'date_order': thoi_gian.strftime('%Y-%m-%d %H:%M:%S'),
            'user_id': user_id,
            'name': f"QTU/{ma_gd_str}"
        }
        
        try:
            logging.info(f"[{i+1}/{len(sales_transactions)}] Đang tạo đơn hàng cho MaGD: {ma_gd_str} (Loại: {loai_phieu})")
            new_order_id = self.execute_odoo_kw('sale.order', 'create', args_list=[order_data])
            self.mapping['order'][ma_gd_str] = new_order_id 
            
            line_cursor = self.sql_conn.cursor()
            line_query = """
                SELECT 
                    MaGD, MaSP, MaNhomSP, MaNhomCon, MaKho, TTL, TTLThuc, TTLNhap, TTLDa, 
                    TTLHao, TTLVang, DVT, NhanChia1, HeSoQD1, HeSoQD1Thuc, HeSoQD1Nhap, 
                    NhanChia2, HeSoQD2, HeSoQD2Thuc, HeSoQD2Nhap, TTLQD, DVTQD, DVTThuc, 
                    LoaiCTGD, ThoiGian 
                FROM tb_CTGD WHERE MaGD = ?
            """
            line_cursor.execute(line_query, ma_gd)
            
            lines_created = 0
            for line_idx, row_data in enumerate(line_cursor.fetchall()):
                (ma_gd_line, old_masp, ma_nhom_sp, ma_nhom_con, ma_kho, ttl, ttl_thuc, 
                 ttl_nhap, ttl_da, ttl_hao, ttl_vang, dvt, nhan_chia1, he_so_qd1, 
                 he_so_qd1_thuc, he_so_qd1_nhap, nhan_chia2, he_so_qd2, 
                 he_so_qd2_thuc, he_so_qd2_nhap, ttlqd, dvtqd, dvt_thuc, loai_ctgd, thoi_gian_line) = row_data

                if not old_masp: 
                    continue

                old_masp_str = str(old_masp).strip()
                
                product_uom_qty = float(ttl_thuc or ttl or 0.0)
                if product_uom_qty == 0:
                    continue

                base_price = float(he_so_qd2 or 0.0)
                gold_purity = float(he_so_qd1 or 1.0)
                
                is_trade_in = False
                trade_in_price_unit = 0.0
                price_unit = base_price

                if loai_ctgd == -1: 
                    is_trade_in = True
                    trade_in_price_unit = base_price
                    price_unit = -1 * base_price * gold_purity
                else: 
                    is_trade_in = False
                    price_unit = base_price

                # Xác định UoM dựa trên Nhóm Con
                group_name = self.mapping['group_info'].get(ma_nhom_con, "").lower()
                is_non_gold = False
                for keyword in ['tiền', 'ngoại tệ', 'tài khoản', 'usd', 'vnd']:
                    if keyword in group_name:
                        is_non_gold = True
                        break
                
                if is_non_gold:
                    product_uom_id = 1 # Units
                    gold_purity = 1.0 
                else:
                    product_uom_id = self.mapping['uom'].get('chỉ', 1) 

                product_tmpl_id = self.mapping['product'].get(old_masp_str)
                if not product_tmpl_id:
                    logging.warning(f"[{i+1}/{len(sales_transactions)}] Không tìm thấy SP '{old_masp_str}'. Bỏ qua.")
                    continue
                
                product_ids = self.execute_odoo_kw('product.product', 'search', args_list=[[('product_tmpl_id', '=', product_tmpl_id)]])
                if not product_ids: 
                    continue
                product_id = product_ids[0]

                line_vals = {
                    'order_id': new_order_id, 
                    'product_id': product_id, 
                    'product_uom_qty': product_uom_qty, 
                    'product_uom': product_uom_id,
                    'price_unit': price_unit,
                    'is_trade_in': is_trade_in,
                    'gold_purity': gold_purity,
                    'name': f"[{old_masp_str}] {str(dvt)}"
                }
                
                if is_trade_in:
                    line_vals['trade_in_price_unit'] = trade_in_price_unit

                self.execute_odoo_kw('sale.order.line', 'create', args_list=[line_vals])
                lines_created += 1
            
            if lines_created > 0 and tinh_trang == 1:
                logging.info(f"[{i+1}/{len(sales_transactions)}] Xác nhận đơn hàng Odoo ID: {new_order_id} (MaGD: {ma_gd_str})")
                self.execute_odoo_kw('sale.order', 'action_confirm', args_list=[[new_order_id]])
            elif lines_created == 0:
                logging.warning(f"[{i+1}/{len(sales_transactions)}] Đơn hàng {ma_gd_str} rỗng. Xóa.")
                self.execute_odoo_kw('sale.order', 'unlink', args_list=[[new_order_id]])
                del self.mapping['order'][ma_gd_str]

        except Exception as e:
            logging.error(f"Lỗi khi di chuyển đơn hàng '{ma_gd_str}': {e}")
    logging.info("Di chuyển Đơn hàng (Sales Orders) hoàn tất.")
# -*- coding: utf-8 -*-
import logging

def migrate_products_from_sp(self):
    """Di chuyển sản phẩm từ tb_SP."""
    logging.info("Bắt đầu di chuyển Sản phẩm từ tb_SP...")
    cursor = self.sql_conn.cursor()
    
    query = "SELECT MaSP, TenSP, MaNhomSP, MaNhomCon, DVTNhap, DVTXuat FROM tb_SP WHERE TinhTrang = 1"
    cursor.execute(query)
    
    for row in cursor.fetchall():
        old_masp, tensp, old_nhom_sp, old_nhom_con, dvt_nhap, dvt_xuat = row
        old_masp_str = str(old_masp)
        tensp = tensp.strip() if tensp else f"Sản phẩm {old_masp_str}"
        
        existing = self.execute_odoo_kw('product.product', 'search', args_list=[[('default_code', '=', old_masp_str)]], kw_dict={'limit': 1})
        
        # Xử lý UoM dựa trên Nhóm Con
        group_name = self.mapping['group_info'].get(old_nhom_con, "").lower()
        
        is_non_gold = False
        for keyword in ['tiền', 'ngoại tệ', 'tài khoản', 'usd', 'vnd']:
            if keyword in group_name:
                is_non_gold = True
                break
        
        if is_non_gold:
            uom_id = 1 # Units
        else:
            # Mặc định là Vàng -> UoM Chỉ
            uom_id = self.mapping['uom'].get('chỉ', 1)

        uom_po_id = uom_id
        
        # Xử lý Category
        categ_id = self.mapping['category'].get(f'child_{old_nhom_con}')
        if not categ_id:
             categ_id = self.mapping['category'].get(f'parent_{old_nhom_sp}', 1)

        product_vals = {
            'uom_id': uom_id,
            'uom_po_id': uom_po_id,
            'categ_id': categ_id,
        }

        if existing:
            # Sản phẩm đã tồn tại, cập nhật UoM
            prod_id = existing[0]
            prod_info = self.execute_odoo_kw('product.product', 'read', args_list=[prod_id], kw_dict={'fields': ['product_tmpl_id']})
            tmpl_id = prod_info[0]['product_tmpl_id'][0]
            
            try:
                self.execute_odoo_kw('product.template', 'write', args_list=[[tmpl_id], product_vals])
                self.mapping['product'][old_masp_str] = tmpl_id
            except Exception as e:
                logging.error(f"Lỗi cập nhật SP '{tensp}' (Mã: {old_masp_str}): {e}")
            continue

        # Tạo mới
        product_vals.update({
            'name': tensp, 
            'default_code': old_masp_str, 
            'type': 'product',
            'sale_ok': True, 
            'purchase_ok': True, 
        })
        
        try:
            new_tmpl_id = self.execute_odoo_kw('product.template', 'create', args_list=[product_vals])
            self.mapping['product'][old_masp_str] = new_tmpl_id
            logging.info(f"Tạo SP: '{tensp}' (Mã: {old_masp_str}, UoM ID: {uom_id})")
        except Exception as e:
            logging.error(f"Lỗi tạo SP '{tensp}' (Mã: {old_masp_str}): {e}")
            
    logging.info("Di chuyển sản phẩm từ tb_SP hoàn tất.")
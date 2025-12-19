# -*- coding: utf-8 -*-
import logging

def migrate_product_categories(self):
    """Di chuyển danh mục sản phẩm từ tb_NhomSP và tb_NhomCon."""
    logging.info("Bắt đầu di chuyển Danh mục sản phẩm...")
    cursor = self.sql_conn.cursor()
    cursor.execute("SELECT MaNhomSP, TenNhomSP FROM tb_NhomSP WHERE TinhTrang = 1")
    for old_id, name in cursor.fetchall():
        existing_cat = self.execute_odoo_kw('product.category', 'search', args_list=[[('name', '=', name), ('parent_id', '=', False)]])
        if not existing_cat:
            new_id = self.execute_odoo_kw('product.category', 'create', args_list=[{'name': name}])
            logging.info(f"Tạo danh mục cha: {name} (Odoo ID: {new_id})")
            self.mapping['category'][f'parent_{old_id}'] = new_id
        else:
            new_id = existing_cat[0]
            logging.info(f"Danh mục cha '{name}' đã tồn tại (Odoo ID: {new_id}).")
            self.mapping['category'][f'parent_{old_id}'] = new_id

    cursor.execute("SELECT MaNhomCon, MaNhomSP, TenNhomCon FROM tb_NhomCon WHERE TinhTrang = 1")
    for old_id, parent_old_id, name in cursor.fetchall():
        # Lưu thông tin nhóm để dùng cho logic UoM
        self.mapping['group_info'][old_id] = name
        
        parent_new_id = self.mapping['category'].get(f'parent_{parent_old_id}')
        cat_data = {'name': name}
        if parent_new_id:
            cat_data['parent_id'] = parent_new_id

        existing_cat = self.execute_odoo_kw('product.category', 'search', args_list=[[('name', '=', name), ('parent_id', '=', parent_new_id)]])
        if not existing_cat:
            new_id = self.execute_odoo_kw('product.category', 'create', args_list=[cat_data])
            logging.info(f"Tạo danh mục con: {name} (Odoo ID: {new_id})")
            self.mapping['category'][f'child_{old_id}'] = new_id
        else:
            new_id = existing_cat[0]
            logging.info(f"Danh mục con '{name}' đã tồn tại (Odoo ID: {new_id}).")
            self.mapping['category'][f'child_{old_id}'] = new_id
    logging.info("Di chuyển Danh mục sản phẩm hoàn tất.")
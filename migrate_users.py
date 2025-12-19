# -*- coding: utf-8 -*-
import logging

def migrate_users(self):
    """Di chuyển người dùng từ tb_TK."""
    logging.info("Bắt đầu di chuyển Người dùng (Users)...")
    cursor = self.sql_conn.cursor()
    cursor.execute("SELECT MaTK, TenTK FROM tb_TK WHERE TinhTrang = 1")
    
    # Lấy ID của group "Sales / User: All Documents"
    sales_group_ids = self.execute_odoo_kw('res.groups', 'search', args_list=[[('name', 'ilike', 'Sales')]])
    sales_group_id = None
    if sales_group_ids:
        groups_data = self.execute_odoo_kw('res.groups', 'read', args_list=[sales_group_ids], kw_dict={'fields': ['name', 'full_name']})
        for group in groups_data:
            if 'Sales / User: All Documents' in group['full_name']:
                sales_group_id = group['id']
                break

    for old_id, name in cursor.fetchall():
        old_id_str = str(old_id)
        login_email = f"user_{old_id_str}@example.com".lower()
        existing_ids = self.execute_odoo_kw('res.users', 'search', args_list=[[('login', '=', login_email)]])
        if existing_ids:
            self.mapping['user'][old_id_str] = existing_ids[0]
            logging.info(f"Người dùng '{name}' với login '{login_email}' đã tồn tại (Odoo ID: {existing_ids[0]}). Bỏ qua tạo mới.")
            continue
        
        user_data = {'name': name.strip(), 'login': login_email}
        if sales_group_id:
            user_data['groups_id'] = [(4, sales_group_id)]
        try:
            new_user_id = self.execute_odoo_kw('res.users', 'create', args_list=[user_data])
            self.mapping['user'][old_id_str] = new_user_id
            logging.info(f"Đã tạo thành công người dùng: '{name}' (Odoo ID: {new_user_id}).")
        except Exception as e:
            logging.error(f"Lỗi khi tạo người dùng '{name}': {e}")
    logging.info("Di chuyển Người dùng hoàn tất.")
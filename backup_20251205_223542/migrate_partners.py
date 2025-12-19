# -*- coding: utf-8 -*-
import logging

def migrate_partners(self):
    """Di chuyển đối tác từ tb_BH."""
    logging.info("Bắt đầu di chuyển Đối tác...")
    cursor = self.sql_conn.cursor()
    
    partner_details = {} 
    logging.info("Tải thông tin chi tiết đối tác từ tb_BH...")
    cursor.execute("SELECT MaBH, TenBH, DienThoai, DiaChi FROM tb_BH WHERE TinhTrang = 1")
    for old_id, name, phone, address in cursor.fetchall():
        partner_details[str(old_id)] = {
            'name': name.strip() if name else '',
            'phone': phone.strip() if phone else None,
            'street': address.strip() if address else None,
        }
    logging.info(f"Đã tải {len(partner_details)} chi tiết đối tác từ tb_BH.")

    unique_partner_ids = set()
    logging.info("Thu thập ID đối tác từ các bảng giao dịch...")
    cursor.execute("SELECT DISTINCT MaBH FROM tb_GD WHERE MaBH IS NOT NULL")
    unique_partner_ids.update({str(row[0]) for row in cursor.fetchall()})
    cursor.execute("SELECT DISTINCT MaBH FROM tb_CTNo WHERE MaBH IS NOT NULL")
    unique_partner_ids.update({str(row[0]) for row in cursor.fetchall()})
    cursor.execute("SELECT DISTINCT MaTK FROM tb_CTGD WHERE MaTK IS NOT NULL")
    unique_partner_ids.update({str(row[0]) for row in cursor.fetchall()})
    logging.info(f"Tìm thấy tổng cộng {len(unique_partner_ids)} đối tác duy nhất từ các giao dịch.")

    for old_id in unique_partner_ids:
        search_domain = [('ref', '=', old_id)]
        existing_partner_ids = self.execute_odoo_kw('res.partner', 'search', args_list=[search_domain], kw_dict={'limit': 1})

        details = partner_details.get(old_id)
        if not details:
            logging.warning(f"Không tìm thấy chi tiết đối tác trong tb_BH cho MaBH '{old_id}'. Tạo đối tác chung.")
            partner_name = f"Khách hàng {old_id}"
            phone = None
            street = None
        else:
            partner_name = details['name'] or f"Khách hàng {old_id}"
            phone = details['phone']
            street = details['street']

        partner_data = {
            'name': partner_name,
            'ref': old_id,
            'phone': phone,
            'street': street,
            'is_company': False,
            'is_gold_partner': True,
        }

        if not existing_partner_ids:
            logging.info(f"Tạo đối tác mới: {partner_name} (MaBH gốc: {old_id})")
            try:
                new_id = self.execute_odoo_kw('res.partner', 'create', args_list=[partner_data])
                self.mapping['partner'][old_id] = new_id
            except Exception as e:
                logging.error(f"Lỗi khi tạo đối tác với MaBH gốc '{old_id}': {e}")
        else:
            partner_id = existing_partner_ids[0]
            logging.info(f"Tìm thấy đối tác hiện có: {partner_name} (MaBH gốc: {old_id}, Odoo ID: {partner_id}). Cập nhật.")
            try:
                update_payload = partner_data.copy()
                del update_payload['ref']
                self.execute_odoo_kw('res.partner', 'write', args_list=[[partner_id], update_payload])
                self.mapping['partner'][old_id] = partner_id
            except Exception as e:
                logging.error(f"Lỗi khi cập nhật đối tác với MaBH gốc '{old_id}': {e}")
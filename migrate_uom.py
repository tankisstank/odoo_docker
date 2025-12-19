# -*- coding: utf-8 -*-
import logging

def migrate_uom(self):
    """Di chuyển Đơn vị tính từ tb_DVT và thiết lập các đơn vị chuẩn."""
    logging.info("Bắt đầu di chuyển Đơn vị tính (UoM)...")
    
    # 1. Tạo Category
    uom_categ_name = 'Trọng lượng Vàng'
    categ_ids = self.execute_odoo_kw('uom.category', 'search', args_list=[[('name', '=', uom_categ_name)]])
    if categ_ids:
        uom_categ_id = categ_ids[0]
    else:
        uom_categ_id = self.execute_odoo_kw('uom.category', 'create', args_list=[{'name': uom_categ_name}])
    
    # 2. Xác định UoM Chuẩn (Reference)
    # Tìm xem đã có UoM nào là reference trong category này chưa
    existing_ref_uoms = self.execute_odoo_kw('uom.uom', 'search_read', 
                                             args_list=[[('category_id', '=', uom_categ_id), ('uom_type', '=', 'reference')]], 
                                             kw_dict={'fields': ['id', 'name'], 'limit': 1})
    
    if existing_ref_uoms:
        reference_uom_id = existing_ref_uoms[0]['id']
        ref_name = existing_ref_uoms[0]['name']
        logging.info(f"Đã tìm thấy UoM tham chiếu hiện tại: '{ref_name}' (ID: {reference_uom_id}). Sử dụng làm chuẩn.")
        
        # Nếu tên khác 'Chỉ', ta có thể đổi tên hoặc giữ nguyên. 
        # Ở đây ta giữ nguyên ID và map 'chỉ' vào ID này để logic sau này hoạt động.
        self.mapping['uom']['chỉ'] = reference_uom_id
        self.mapping['uom']['999'] = reference_uom_id
        
        # Nếu tên không phải là 'Chỉ', kiểm tra xem 'Chỉ' có tồn tại dưới dạng non-reference không để tránh trùng lặp tên sau này
        if ref_name.lower() != 'chỉ':
             # Logic xử lý thêm nếu cần, hiện tại chấp nhận reference khác tên
             pass
    else:
        # Chưa có reference, tạo mới 'Chỉ'
        logging.info("Chưa có UoM tham chiếu. Tạo mới 'Chỉ'.")
        reference_uom_name = 'Chỉ'
        # Kiểm tra xem tên 'Chỉ' đã bị dùng bởi UoM non-reference chưa (trường hợp hiếm nhưng có thể)
        chk_chi = self.execute_odoo_kw('uom.uom', 'search', args_list=[[('name', '=', reference_uom_name), ('category_id', '=', uom_categ_id)]])
        if chk_chi:
             # Đã có 'Chỉ' nhưng không phải reference? Điều này gây lỗi logic Odoo.
             # Ta sẽ set nó thành reference.
             logging.warning(f"UoM '{reference_uom_name}' đã tồn tại nhưng không phải Reference. Cập nhật thành Reference.")
             reference_uom_id = chk_chi[0]
             self.execute_odoo_kw('uom.uom', 'write', args_list=[[reference_uom_id], {'uom_type': 'reference', 'ratio': 1.0}])
        else:
            reference_uom_id = self.execute_odoo_kw('uom.uom', 'create', args_list=[{
                'name': reference_uom_name,
                'category_id': uom_categ_id,
                'uom_type': 'reference',
                'ratio': 1.0,
                'rounding': 0.001
            }])
        
        self.mapping['uom']['chỉ'] = reference_uom_id
        self.mapping['uom']['999'] = reference_uom_id 

    # 3. Tạo các đơn vị tiêu chuẩn: Lượng, Gram
    std_uoms = {
        'Lượng': {'type': 'bigger', 'ratio': 10.0},
        'Gram': {'type': 'smaller', 'ratio': 1/3.75}
    }
    
    for name, specs in std_uoms.items():
        uom_ids = self.execute_odoo_kw('uom.uom', 'search', args_list=[[('name', '=', name), ('category_id', '=', uom_categ_id)]])
        if uom_ids:
            self.mapping['uom'][name.lower()] = uom_ids[0]
        else:
            new_id = self.execute_odoo_kw('uom.uom', 'create', args_list=[{
                'name': name,
                'category_id': uom_categ_id,
                'uom_type': specs['type'],
                'ratio': specs['ratio'],
                'rounding': 0.001
            }])
            self.mapping['uom'][name.lower()] = new_id

    # 4. Di chuyển UoM từ tb_DVT (Tuổi vàng)
    cursor = self.sql_conn.cursor()
    cursor.execute("SELECT DVT, HeSoQD FROM tb_DVT")
    
    for row in cursor.fetchall():
        dvt_code = row.DVT.strip()
        he_so = float(row.HeSoQD or 0.0)
        
        if dvt_code.upper() == 'VND' or he_so <= 0:
            continue
            
        if dvt_code.lower() in self.mapping['uom']:
            continue

        # Logic ratio (so với Reference vừa tìm được)
        if he_so == 1.0:
            uom_type = 'bigger' 
            ratio = 1.0
        elif he_so > 1.0:
            uom_type = 'bigger'
            ratio = he_so
        else: 
            uom_type = 'smaller'
            ratio = 1.0 / he_so

        uom_name = dvt_code
        
        exist_ids = self.execute_odoo_kw('uom.uom', 'search', args_list=[[('name', '=', uom_name), ('category_id', '=', uom_categ_id)]])
        if exist_ids:
            self.mapping['uom'][dvt_code.lower()] = exist_ids[0]
            # logging.info(f"UoM '{uom_name}' đã tồn tại.")
        else:
            try:
                new_id = self.execute_odoo_kw('uom.uom', 'create', args_list=[{
                    'name': uom_name,
                    'category_id': uom_categ_id,
                    'uom_type': uom_type,
                    'ratio': ratio,
                    'rounding': 0.001
                }])
                self.mapping['uom'][dvt_code.lower()] = new_id
                logging.info(f"Tạo UoM mới: {uom_name} (Type: {uom_type}, Ratio: {ratio:.4f})")
            except Exception as e:
                logging.error(f"Lỗi khi tạo UoM '{uom_name}': {e}")

    logging.info("Di chuyển Đơn vị tính hoàn tất.")
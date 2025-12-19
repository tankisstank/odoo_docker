#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script cấu hình Odoo cho cửa hàng vàng và ngoại tệ
Chạy sau khi cài đặt Odoo thành công
"""

import xmlrpc.client
import sys

# Cấu hình kết nối
ODOO_URL = 'http://localhost:8069'
DB_NAME = 'qlv_new'
USERNAME = 'c0508g@gmail.com'
PASSWORD = 'abc123'  # Thay đổi sau khi tạo database


def connect_odoo():
    """Kết nối đến Odoo"""
    try:
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
        uid = common.authenticate(DB_NAME, USERNAME, PASSWORD, {})
        if not uid:
            print("Không thể kết nối đến Odoo. Kiểm tra thông tin đăng nhập.")
            sys.exit(1)

        models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
        return uid, models
    except Exception as e:
        print(f"Lỗi kết nối: {e}")
        sys.exit(1)


def check_and_confirm(current_val, target_val, item_name):
    """
    Kiểm tra và xác nhận hành động khi có xung đột dữ liệu
    Return: 'overwrite', 'new', 'skip'
    """
    if current_val == target_val:
        return 'skip'

    print(f"\n[!] Xung đột cấu hình cho '{item_name}':")
    print(f"    - Giá trị hiện tại: {current_val}")
    print(f"    - Giá trị mong muốn: {target_val}")
    
    while True:
        choice = input("    => Bạn muốn làm gì? [O]verwrite (Ghi đè) / [N]ew (Tạo mới) / [S]kip (Bỏ qua): ").lower()
        if choice in ['o', 'overwrite']:
            return 'overwrite'
        elif choice in ['n', 'new']:
            return 'new'
        elif choice in ['s', 'skip']:
            return 'skip'


def install_modules(uid, models):
    """Cài đặt các module cần thiết"""
    modules_to_install = [
        'sale_management',
        'stock',
        'account',
        'purchase',
        'qlv',  # Addon quản lý vàng
        # 'multi_currency' # Đã tắt theo yêu cầu
    ]

    print("\n=== Cài đặt Modules ===")
    for module in modules_to_install:
        try:
            # Check if installed
            module_info = models.execute_kw(DB_NAME, uid, PASSWORD,
                                           'ir.module.module', 'search_read',
                                           [[['name', '=', module]]],
                                           {'fields': ['state']})
            
            # Upgrade 'qlv' even if installed to apply XML changes
            if module == 'qlv' and module_info and module_info[0]['state'] == 'installed':
                 print(f"... Đang nâng cấp module: {module}")
                 models.execute_kw(DB_NAME, uid, PASSWORD,
                                   'ir.module.module', 'button_immediate_upgrade',
                                   [[module_info[0]['id']]])
                 print(f"✓ Đã nâng cấp module: {module}")
                 continue

            if module_info and module_info[0]['state'] == 'installed':
                print(f"✓ Module đã cài đặt: {module}")
                continue

            print(f"... Đang cài đặt module: {module}")
            module_ids = models.execute_kw(DB_NAME, uid, PASSWORD,
                                           'ir.module.module', 'search',
                                           [[['name', '=', module]]])

            if module_ids:
                # Force install/upgrade
                models.execute_kw(DB_NAME, uid, PASSWORD,
                                  'ir.module.module', 'button_immediate_upgrade',
                                  [module_ids])
                print(f"✓ Đã cài đặt/nâng cấp module: {module}")
            else:
                print(f"✗ Không tìm thấy module: {module}")
        except Exception as e:
            print(f"✗ Lỗi cài đặt module {module}: {e}")


def configure_general_settings(uid, models):
    """Cấu hình chung: Thuế, Định dạng số, Sequence"""
    print("\n=== Cấu hình chung ===")

    # 1. Tắt/Ẩn thuế (Tax)
    try:
        # Cách đơn giản nhất là tắt hiển thị thuế ở dòng phụ (Subtotals Tax Excluded)
        # Tuy nhiên, để "tắt" hẳn, ta cần can thiệp vào settings
        # Ở đây ta set group_show_line_subtotals_tax_excluded = False (Hiển thị Tax Included mặc định hoặc tắt cột thuế nếu có option)
        # Thực tế Odoo quản lý việc hiển thị thuế qua Group 'account.group_show_line_subtotals_tax_excluded' vs '_included'
        # Để "ẩn", ta có thể remove user khỏi các group này hoặc tắt tax display trong Sales Settings.
        
        # update res.config.settings
        # sale_tax_id = False (Default tax)
        
        print("... Đang tắt hiển thị thuế")
        # Tìm các thuế đang active và archive chúng nếu cần thiết, hoặc set default tax = None
        # Đơn giản nhất: Set default sale tax của company về rỗng
        company_ids = models.execute_kw(DB_NAME, uid, PASSWORD, 'res.company', 'search', [[]])
        if company_ids:
            models.execute_kw(DB_NAME, uid, PASSWORD, 'res.company', 'write', [company_ids, {
                'account_sale_tax_id': False,
                'account_purchase_tax_id': False
            }])
            print("✓ Đã bỏ thuế mặc định cho Company")

        # Clean taxes from existing products
        print("... Đang xóa thuế khỏi các sản phẩm hiện có")
        prod_ids = models.execute_kw(DB_NAME, uid, PASSWORD, 'product.template', 'search', [[]])
        if prod_ids:
             # (5, 0, 0) removes all links (Many2many)
             models.execute_kw(DB_NAME, uid, PASSWORD, 'product.template', 'write', 
                               [prod_ids, {'taxes_id': [(5, 0, 0)], 'supplier_taxes_id': [(5, 0, 0)]}])
             print(f"✓ Đã xóa thuế khỏi {len(prod_ids)} sản phẩm")

        # Archive Taxes (Optional, but ensures they don't appear in dropdowns)
        # Only archive taxes that are not used in valid posted entries? 
        # For safely, just archive all. User said "tắt, ẩn, ko dùng".
        tax_ids = models.execute_kw(DB_NAME, uid, PASSWORD, 'account.tax', 'search', [[['active', '=', True]]])
        if tax_ids:
            models.execute_kw(DB_NAME, uid, PASSWORD, 'account.tax', 'write', [tax_ids, {'active': False}])
            print(f"✓ Đã lưu trữ {len(tax_ids)} loại thuế")
            
    except Exception as e:
        print(f"✗ Lỗi tắt thuế: {e}")

    # 2. Định dạng số: Thập phân (.) và Phân cách hàng nghìn (,)
    try:
        lang_ids = models.execute_kw(DB_NAME, uid, PASSWORD,
                                     'res.lang', 'search_read',
                                     [[['code', '=', 'vi_VN']]], # Ưu tiên cấu hình cho tiếng Việt
                                     {'fields': ['decimal_point', 'thousands_sep', 'name']})
        
        if not lang_ids:
             # Fallback to en_US if vi_VN not active
             lang_ids = models.execute_kw(DB_NAME, uid, PASSWORD,
                                     'res.lang', 'search_read',
                                     [[['code', '=', 'en_US']]],
                                     {'fields': ['decimal_point', 'thousands_sep', 'name']})

        if lang_ids:
            lang = lang_ids[0]
            current_dec = lang['decimal_point']
            current_sep = lang['thousands_sep']
            
            target_dec = '.'
            target_sep = "'"

            if current_dec != target_dec or current_sep != target_sep:
                action = check_and_confirm(f"Dec: '{current_dec}', Sep: '{current_sep}'", 
                                         f"Dec: '{target_dec}', Sep: '{target_sep}'", 
                                         f"Định dạng số ({lang['name']})")
                
                if action == 'overwrite':
                    models.execute_kw(DB_NAME, uid, PASSWORD, 'res.lang', 'write', 
                                      [[lang['id']], {'decimal_point': target_dec, 'thousands_sep': target_sep}])
                    print("✓ Đã cập nhật định dạng số")
                else:
                    print("- Bỏ qua cập nhật định dạng số")
            else:
                print("✓ Định dạng số đã chuẩn")

    except Exception as e:
        print(f"✗ Lỗi cấu hình định dạng số: {e}")

    # 3. Sequence: QTU/[mã đơn hàng]
    try:
        seq_ids = models.execute_kw(DB_NAME, uid, PASSWORD,
                                    'ir.sequence', 'search_read',
                                    [[['code', '=', 'sale.order']]],
                                    {'fields': ['prefix', 'name']})
        
        target_prefix = 'QTU/'
        
        if seq_ids:
            seq = seq_ids[0]
            if seq['prefix'] != target_prefix:
                action = check_and_confirm(seq['prefix'], target_prefix, f"Mã đơn hàng ({seq['name']})")
                
                if action == 'overwrite':
                    models.execute_kw(DB_NAME, uid, PASSWORD, 'ir.sequence', 'write',
                                      [[seq['id']], {'prefix': target_prefix}])
                    print(f"✓ Đã cập nhật prefix sequence thành {target_prefix}")
                elif action == 'new':
                     # Tạo sequence mới (Lưu ý: Sale Order mặc định dùng code 'sale.order', tạo mới cần đổi code hoặc thay thế logic,
                     # Tuy nhiên ở đây user yêu cầu đơn giản, ta sẽ tạo bản ghi mới nhưng cùng code (có thể gây conflict logic Odoo chọn cái nào)
                     # Hoặc tốt hơn là đổi code cái cũ đi và tạo cái mới với code 'sale.order'
                     
                     # Rename old code to avoid conflict
                     models.execute_kw(DB_NAME, uid, PASSWORD, 'ir.sequence', 'write',
                                      [[seq['id']], {'code': 'sale.order.old'}])
                     
                     new_seq = seq.copy()
                     del new_seq['id']
                     new_seq['prefix'] = target_prefix
                     new_seq['code'] = 'sale.order'
                     new_seq['name'] = 'Sales Order (Gold Shop)'
                     models.execute_kw(DB_NAME, uid, PASSWORD, 'ir.sequence', 'create', [new_seq])
                     print(f"✓ Đã tạo sequence mới {target_prefix}")
                else:
                    print("- Bỏ qua cập nhật sequence")
            else:
                print("✓ Sequence đã chuẩn")
                
    except Exception as e:
        print(f"✗ Lỗi cấu hình sequence: {e}")


def create_uom_categories(uid, models):
    """Tạo danh mục đơn vị tính cho vàng"""
    print("\n=== Cấu hình Đơn vị tính ===")
    
    # 1. Danh mục
    cat_name = 'Trọng lượng vàng'
    cat_ids = models.execute_kw(DB_NAME, uid, PASSWORD, 'uom.category', 'search', [[['name', '=', cat_name]]])
    
    cat_id = None
    if cat_ids:
        cat_id = cat_ids[0]
        print(f"✓ Danh mục '{cat_name}' đã tồn tại")
    else:
        try:
            cat_id = models.execute_kw(DB_NAME, uid, PASSWORD, 'uom.category', 'create', [{
                'name': cat_name,
            }])
            print(f"✓ Đã tạo danh mục: {cat_name}")
        except Exception as e:
            print(f"✗ Lỗi tạo danh mục đơn vị: {e}")
            return None

    return cat_id


def create_gold_uoms(uid, models, category_id):
    """
    Cấu hình UoM:
    - Lượng (Reference, precision 4)
    - Chỉ (1 Lượng = 10 Chỉ) -> Type: Bigger? No.
      Nếu Lượng là Ref (1.0).
      1 Lượng = 10 Chỉ. => 1 Chỉ = 0.1 Lượng.
      Odoo:
      - Bigger than ref: 1 This = X Ref. (Ví dụ kg vs g. 1kg = 1000g).
      - Smaller than ref: 1 Ref = Y This. (Ví dụ g vs mg. 1g = 1000mg).
      
      Ở đây:
      1 Lượng (Ref) = 10 Chỉ. => Chỉ nhỏ hơn Lượng.
      => Chỉ type là 'smaller', factor = 10.0 (1 Ref = 10 This).
      
      1 Lượng (Ref) = 37.5 Gram. => Gram nhỏ hơn Lượng.
      => Gram type là 'smaller', factor = 37.5.
    """
    if not category_id:
        return

    # Định nghĩa các unit mong muốn
    # name: (type, factor, rounding)
    # type: 'reference', 'bigger', 'smaller'
    desired_uoms = {
        'Lượng': {'uom_type': 'reference', 'factor': 1.0, 'rounding': 0.0001, 'active': True},
        'Cây':   {'uom_type': 'reference', 'factor': 1.0, 'rounding': 0.0001, 'active': False}, # Lượng còn gọi là Cây -> Có thể user muốn tên là "Lượng" hoặc "Cây". Tạo 1 cái chính.
        # Ở đây user bảo "Lượng (tên gọi khác là cây)". Ta dùng "Lượng" làm chính.
        
        'Chỉ':   {'uom_type': 'smaller', 'factor': 10.0, 'rounding': 0.0001, 'active': True},
        'Gram':  {'uom_type': 'smaller', 'factor': 37.5, 'rounding': 0.0001, 'active': True},
    }

    # Xử lý "Lượng" trước (Reference)
    luong_uom = desired_uoms['Lượng']
    
    # Tìm xem đã có đơn vị nào là Reference trong category này chưa?
    # Nếu category mới tinh thì chưa. Nếu cũ thì có thể 'kg' hoặc 'gram' đang là ref.
    # Ta phải cẩn thận. Odoo quy định 1 category chỉ có 1 Reference Unit.
    
    existing_ref_ids = models.execute_kw(DB_NAME, uid, PASSWORD, 'uom.uom', 'search_read',
                                         [[['category_id', '=', category_id], ['uom_type', '=', 'reference']]],
                                         {'fields': ['name', 'id']})
    
    ref_id = None
    if existing_ref_ids:
        ref = existing_ref_ids[0]
        ref_id = ref['id']
        # Nếu đã có ref unit nhưng tên không phải Lượng
        if ref['name'] != 'Lượng':
            action = check_and_confirm(ref['name'], 'Lượng', "Đơn vị chuẩn (Reference UoM)")
            if action == 'overwrite':
                # Đổi tên unit hiện tại thành Lượng và sửa thông số
                models.execute_kw(DB_NAME, uid, PASSWORD, 'uom.uom', 'write',
                                  [[ref_id], {'name': 'Lượng', 'rounding': 0.0001}])
                print("✓ Đã cập nhật Reference Unit thành 'Lượng'")
            elif action == 'new':
                 # Không thể tạo 2 Reference Unit cùng category.
                 # Phải biến ông kia thành non-ref trước? Rất phức tạp.
                 # Giả sử user chọn New -> Ta tạo category mới cho lành?
                 # Ở đây đơn giản hóa: Force user Overwrite hoặc Skip.
                 print("! Không thể tạo mới Reference Unit trong cùng danh mục. Vui lòng chọn Overwrite để sửa.")
                 return
            else:
                print("- Giữ nguyên Reference Unit cũ")
        else:
            # Tên đã là Lượng, check rounding
            # (Thực ra cần check sâu hơn nhưng tạm tin tưởng)
             models.execute_kw(DB_NAME, uid, PASSWORD, 'uom.uom', 'write',
                                  [[ref_id], {'rounding': 0.0001}])
             print("✓ Đơn vị 'Lượng' đã tồn tại và cập nhật độ chính xác")
    else:
        # Chưa có ref unit (lạ, thường tạo category xong phải tạo ngay ref)
        # Tạo mới
         try:
            ref_id = models.execute_kw(DB_NAME, uid, PASSWORD, 'uom.uom', 'create', [{
                'name': 'Lượng',
                'category_id': category_id,
                'uom_type': 'reference',
                'factor_inv': 1.0, # reference
                'rounding': 0.0001
            }])
            print("✓ Đã tạo đơn vị: Lượng")
         except Exception as e:
             print(f"✗ Lỗi tạo Ref unit: {e}")

    # Tạo/Update các đơn vị con (Chỉ, Gram)
    for name, data in desired_uoms.items():
        if name == 'Lượng' or name == 'Cây': continue 

        uom_ids = models.execute_kw(DB_NAME, uid, PASSWORD, 'uom.uom', 'search_read',
                                     [[['category_id', '=', category_id], ['name', '=', name]]],
                                     {'fields': ['factor', 'uom_type']})
        
        target_factor = data['factor']
        
        if uom_ids:
             # Đã tồn tại -> Check
             uom = uom_ids[0]
             # Check sai số factor
             current_factor = uom['factor']
             if abs(current_factor - target_factor) > 0.001:
                 action = check_and_confirm(f"{current_factor}", f"{target_factor}", f"Tỷ lệ quy đổi {name}")
                 if action == 'overwrite':
                     models.execute_kw(DB_NAME, uid, PASSWORD, 'uom.uom', 'write',
                                      [[uom['id']], {'factor': target_factor, 'uom_type': data['uom_type'], 'rounding': 0.0001}])
                     print(f"✓ Đã cập nhật {name}")
                 elif action == 'new':
                     models.execute_kw(DB_NAME, uid, PASSWORD, 'uom.uom', 'create', [{
                        'name': name + " (Mới)",
                        'category_id': category_id,
                        'uom_type': data['uom_type'],
                        'factor': target_factor,
                        'rounding': 0.0001
                    }])
                     print(f"✓ Đã tạo {name} (Mới)")
             else:
                 print(f"✓ Đơn vị {name} đã chuẩn")
        else:
             # Chưa tồn tại -> Tạo
             models.execute_kw(DB_NAME, uid, PASSWORD, 'uom.uom', 'create', [{
                'name': name,
                'category_id': category_id,
                'uom_type': data['uom_type'],
                'factor': target_factor,
                'rounding': 0.0001
            }])
             print(f"✓ Đã tạo đơn vị: {name}")


def create_product_categories(uid, models):
    """Tạo danh mục sản phẩm: Vàng, Ngoại tệ, Tiền, Bạc"""
    print("\n=== Cấu hình Danh mục sản phẩm ===")
    
    target_categories = ['Vàng', 'Ngoại tệ', 'Tiền', 'Bạc']
    
    for cat_name in target_categories:
        cat_ids = models.execute_kw(DB_NAME, uid, PASSWORD, 'product.category', 'search', [[['name', '=', cat_name]]])
        
        if cat_ids:
            print(f"✓ Danh mục '{cat_name}' đã tồn tại")
        else:
            try:
                models.execute_kw(DB_NAME, uid, PASSWORD, 'product.category', 'create', [{'name': cat_name}])
                print(f"✓ Đã tạo danh mục: {cat_name}")
            except Exception as e:
                print(f"✗ Lỗi tạo danh mục {cat_name}: {e}")


def create_money_product(uid, models):
    """Tạo sản phẩm Tiền VNĐ để giao dịch"""
    print("\n=== Cấu hình Sản phẩm Tiền ===")
    
    product_name = "Tiền Việt Nam (VNĐ)"
    cat_name = "Tiền"
    
    # Tìm category ID
    cat_ids = models.execute_kw(DB_NAME, uid, PASSWORD, 'product.category', 'search', [[['name', '=', cat_name]]])
    if not cat_ids:
        print(f"✗ Không tìm thấy danh mục '{cat_name}'. Vui lòng chạy tạo danh mục trước.")
        return

    cat_id = cat_ids[0]

    # Tìm sản phẩm
    prod_ids = models.execute_kw(DB_NAME, uid, PASSWORD, 'product.template', 'search', [[['name', '=', product_name]]])
    
    if prod_ids:
        print(f"✓ Sản phẩm '{product_name}' đã tồn tại")
    else:
        try:
            models.execute_kw(DB_NAME, uid, PASSWORD, 'product.template', 'create', [{
                'name': product_name,
                'detailed_type': 'product', # Storable Product
                'categ_id': cat_id,
                'list_price': 1.0,
                'standard_price': 1.0,
                'uom_id': 1, # Đơn vị gốc (thường là Unit), hoặc có thể tìm đơn vị VNĐ nếu có. Tạm dùng mặc định.
                'uom_po_id': 1,
                'taxes_id': [(5, 0, 0)], # Không thuế
                'supplier_taxes_id': [(5, 0, 0)],
            }])
            print(f"✓ Đã tạo sản phẩm: {product_name}")
        except Exception as e:
            print(f"✗ Lỗi tạo sản phẩm {product_name}: {e}")


def _configure_currency_vnd(uid, models):
    """Cấu hình tiền tệ VND (Làm tròn 3 số thập phân)"""
    print("\n=== Cấu hình Tiền tệ VND ===")
    
    try:
        # Tìm currency VND
        vnd_ids = models.execute_kw(DB_NAME, uid, PASSWORD, 
                                   'res.currency', 'search_read', 
                                   [[['name', '=', 'VND']]],
                                   {'fields': ['rounding', 'decimal_places', 'name']})
        
        if not vnd_ids:
            print("✗ Không tìm thấy tiền tệ VND")
            return

        vnd = vnd_ids[0]
        current_rounding = vnd['rounding']
        current_places = vnd['decimal_places']
        
        target_rounding = 0.001
        target_places = 3
        
        # Check logic: Rounding usually matches places (3 places -> 0.001).
        # Float comparison needs tolerance
        if abs(current_rounding - target_rounding) > 0.00001 or current_places != target_places:
            action = check_and_confirm(
                f"Rounding: {current_rounding}, Places: {current_places}",
                f"Rounding: {target_rounding}, Places: {target_places}",
                f"Cấu hình tiền tệ {vnd['name']}"
            )
            
            if action == 'overwrite':
                models.execute_kw(DB_NAME, uid, PASSWORD, 'res.currency', 'write',
                                  [[vnd['id']], {
                                      'rounding': target_rounding,
                                      'decimal_places': target_places
                                  }])
                print("✓ Đã cập nhật tiền tệ VND (3 số thập phân)")
            else:
                print("- Bỏ qua cập nhật tiền tệ VND")
        else:
            print("✓ Tiền tệ VND đã chuẩn")
            
    except Exception as e:
        print(f"✗ Lỗi cấu hình tiền tệ VND: {e}")
        
def _configure_decimal_precision(uid, models):
    """
    Cập nhật Decimal Precision cho 'Product Unit of Measure' lên 3 chữ số.
    """
    print("\n=== Cấu hình Độ chính xác thập phân (Precision) ===")
    try:
        precision_ids = models.execute_kw(DB_NAME, uid, PASSWORD, 
                                        'decimal.precision', 'search_read', 
                                        [[['name', '=', 'Product Unit of Measure']]],
                                        {'fields': ['digits']})
        if precision_ids:
            prec = precision_ids[0]
            current_digits = prec['digits']
            target_digits = 3
            
            if current_digits != target_digits:
                # Odoo returns digits as integer for 'digits' field usually? Or float? 
                # decimal.precision model has 'digits' as integer.
                print(f"... Cập nhật Precision từ {current_digits} lên {target_digits}")
                models.execute_kw(DB_NAME, uid, PASSWORD, 'decimal.precision', 'write',
                                  [[prec['id']], {'digits': target_digits}])
                print("✓ Đã cập nhật Product Unit of Measure precision")
            else:
                 print("✓ Precision đã chuẩn (3)")
        else:
            print("✗ Không tìm thấy cấu hình 'Product Unit of Measure'")
    except Exception as e:
        print(f"✗ Lỗi cấu hình Precision: {e}")


def main():
    """Hàm chính"""
    print("=== BẮT ĐẦU CẤU HÌNH ODOO CHO CỬA HÀNG VÀNG ===")

    uid, models = connect_odoo()

    # 1. Cài đặt modules (bao gồm qlv)
    install_modules(uid, models)

    # 2. Cấu hình chung (Thuế, Format, Sequence)
    configure_general_settings(uid, models)

    # 3. Tạo UoM
    category_id = create_uom_categories(uid, models)
    if category_id:
        create_gold_uoms(uid, models, category_id)

    # 4. Danh mục sản phẩm
    create_product_categories(uid, models)

    # 5. Tạo sản phẩm Tiền
    create_money_product(uid, models)

    # 6. Cấu hình Tiền tệ VND
    _configure_currency_vnd(uid, models)
    
    # 7. Cấu hình Precision
    _configure_decimal_precision(uid, models)

    print("\n=== CẤU HÌNH HOÀN TẤT ===")
    print("Hệ thống đã sẵn sàng!")


if __name__ == "__main__":
    main()

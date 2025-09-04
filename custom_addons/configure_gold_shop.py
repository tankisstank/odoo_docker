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
DB_NAME = 'gold_shop_db'
USERNAME = 'admin'
PASSWORD = 'admin'  # Thay đổi sau khi tạo database


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


def install_modules(uid, models):
    """Cài đặt các module cần thiết"""
    modules_to_install = [
        'sale_management',
        'stock',
        'account',
        'purchase',
        'crm',
        'multi_currency'
    ]

    print("Cài đặt modules...")
    for module in modules_to_install:
        try:
            module_ids = models.execute_kw(DB_NAME, uid, PASSWORD,
                                           'ir.module.module', 'search',
                                           [[['name', '=', module]]])

            if module_ids:
                models.execute_kw(DB_NAME, uid, PASSWORD,
                                  'ir.module.module', 'button_immediate_install',
                                  [module_ids])
                print(f"✓ Đã cài đặt module: {module}")
        except Exception as e:
            print(f"✗ Lỗi cài đặt module {module}: {e}")


def setup_currencies(uid, models):
    """Cấu hình đa tiền tệ"""
    currencies = [
        'USD', 'EUR', 'JPY', 'TWD', 'CNY',
        'KRW', 'GBP', 'THB', 'CAD', 'AUD',
        'SGD', 'MYR', 'HKD'
    ]

    print("Cấu hình tiền tệ...")
    for currency in currencies:
        try:
            # Kích hoạt tiền tệ
            currency_ids = models.execute_kw(DB_NAME, uid, PASSWORD,
                                             'res.currency', 'search',
                                             [[['name', '=', currency]]])

            if currency_ids:
                models.execute_kw(DB_NAME, uid, PASSWORD,
                                  'res.currency', 'write',
                                  [currency_ids, {'active': True}])
                print(f"✓ Đã kích hoạt tiền tệ: {currency}")
        except Exception as e:
            print(f"✗ Lỗi cấu hình tiền tệ {currency}: {e}")


def create_uom_categories(uid, models):
    """Tạo danh mục đơn vị tính cho vàng"""
    # Tạo danh mục đơn vị cho vàng
    uom_category_data = {
        'name': 'Trọng lượng vàng',
        'measure_type': 'weight'
    }

    try:
        category_id = models.execute_kw(DB_NAME, uid, PASSWORD,
                                        'uom.category', 'create', [uom_category_data])
        print(f"✓ Đã tạo danh mục đơn vị: Trọng lượng vàng")
        return category_id
    except Exception as e:
        print(f"✗ Lỗi tạo danh mục đơn vị: {e}")
        return None


def create_gold_uoms(uid, models, category_id):
    """Tạo các đơn vị tính cho vàng"""
    if not category_id:
        return

    # Đơn vị cơ bản: gram
    gram_data = {
        'name': 'Gram',
        'category_id': category_id,
        'uom_type': 'reference',
        'factor': 1.0,
        'rounding': 0.01,
        'active': True
    }

    try:
        gram_id = models.execute_kw(DB_NAME, uid, PASSWORD,
                                    'uom.uom', 'create', [gram_data])
        print("✓ Đã tạo đơn vị: Gram")
    except Exception as e:
        print(f"✗ Lỗi tạo đơn vị Gram: {e}")
        return

    # Các đơn vị khác
    uoms = [
        {'name': 'Chỉ', 'factor': 0.266667, 'type': 'smaller'},  # 1 gram = 3.75 chỉ
        {'name': 'Lượng', 'factor': 10.666667, 'type': 'bigger'},  # 1 lượng = 10 chỉ = 37.5 gram
    ]

    for uom in uoms:
        uom_data = {
            'name': uom['name'],
            'category_id': category_id,
            'uom_type': uom['type'],
            'factor': uom['factor'],
            'rounding': 0.01,
            'active': True
        }

        try:
            models.execute_kw(DB_NAME, uid, PASSWORD,
                              'uom.uom', 'create', [uom_data])
            print(f"✓ Đã tạo đơn vị: {uom['name']}")
        except Exception as e:
            print(f"✗ Lỗi tạo đơn vị {uom['name']}: {e}")


def create_product_categories(uid, models):
    """Tạo danh mục sản phẩm"""
    categories = [
        {'name': 'Vàng miếng', 'parent': None},
        {'name': 'Vàng 4 số (9999)', 'parent': 'Vàng miếng'},
        {'name': 'Vàng 3 số (999)', 'parent': 'Vàng miếng'},
        {'name': 'Vàng thấp tuổi', 'parent': 'Vàng miếng'},
        {'name': 'Vàng Doji', 'parent': 'Vàng miếng'},
        {'name': 'Vàng SJC', 'parent': 'Vàng miếng'},
        {'name': 'Bạc phân kim', 'parent': None},
        {'name': 'Ngoại tệ', 'parent': None},
    ]

    created_categories = {}

    for category in categories:
        parent_id = None
        if category['parent']:
            parent_id = created_categories.get(category['parent'])

        category_data = {
            'name': category['name'],
            'parent_id': parent_id
        }

        try:
            cat_id = models.execute_kw(DB_NAME, uid, PASSWORD,
                                       'product.category', 'create', [category_data])
            created_categories[category['name']] = cat_id
            print(f"✓ Đã tạo danh mục: {category['name']}")
        except Exception as e:
            print(f"✗ Lỗi tạo danh mục {category['name']}: {e}")

    return created_categories


def setup_accounting(uid, models):
    """Cấu hình kế toán cơ bản"""
    print("Cấu hình kế toán...")

    # Kích hoạt đa tiền tệ trong kế toán
    try:
        company_ids = models.execute_kw(DB_NAME, uid, PASSWORD,
                                        'res.company', 'search', [[]])

        if company_ids:
            models.execute_kw(DB_NAME, uid, PASSWORD,
                              'res.company', 'write',
                              [company_ids, {'currency_exchange_journal_id': 1}])
            print("✓ Đã cấu hình đa tiền tệ cho kế toán")
    except Exception as e:
        print(f"✗ Lỗi cấu hình kế toán: {e}")


def create_sample_products(uid, models, categories):
    """Tạo sản phẩm mẫu"""
    # Lấy đơn vị tính
    gram_ids = models.execute_kw(DB_NAME, uid, PASSWORD,
                                 'uom.uom', 'search', [[['name', '=', 'Gram']]])
    chi_ids = models.execute_kw(DB_NAME, uid, PASSWORD,
                                'uom.uom', 'search', [[['name', '=', 'Chỉ']]])

    gram_id = gram_ids[0] if gram_ids else 1
    chi_id = chi_ids[0] if chi_ids else 1

    # Sản phẩm mẫu
    products = [
        {
            'name': 'Vàng miếng 4 số 1 chỉ',
            'categ_id': categories.get('Vàng 4 số (9999)', 1),
            'type': 'product',
            'uom_id': chi_id,
            'uom_po_id': chi_id,
            'list_price': 7500000,  # Giá mẫu
            'standard_price': 7400000,
            'tracking': 'none'
        },
        {
            'name': 'Vàng miếng SJC 1 lượng',
            'categ_id': categories.get('Vàng SJC', 1),
            'type': 'product',
            'uom_id': gram_id,
            'uom_po_id': gram_id,
            'list_price': 75000000,
            'standard_price': 74000000,
            'tracking': 'none'
        },
        {
            'name': 'Bạc phân kim 1 chỉ',
            'categ_id': categories.get('Bạc phân kim', 1),
            'type': 'product',
            'uom_id': chi_id,
            'uom_po_id': chi_id,
            'list_price': 150000,
            'standard_price': 145000,
            'tracking': 'none'
        }
    ]

    for product in products:
        try:
            models.execute_kw(DB_NAME, uid, PASSWORD,
                              'product.product', 'create', [product])
            print(f"✓ Đã tạo sản phẩm: {product['name']}")
        except Exception as e:
            print(f"✗ Lỗi tạo sản phẩm {product['name']}: {e}")


def main():
    """Hàm chính"""
    print("=== BẮT ĐẦU CẤU HÌNH ODOO CHO CỬA HÀNG VÀNG ===")

    uid, models = connect_odoo()

    # Cài đặt modules
    install_modules(uid, models)

    # Cấu hình tiền tệ
    setup_currencies(uid, models)

    # Tạo đơn vị tính
    category_id = create_uom_categories(uid, models)
    create_gold_uoms(uid, models, category_id)

    # Tạo danh mục sản phẩm
    categories = create_product_categories(uid, models)

    # Cấu hình kế toán
    setup_accounting(uid, models)

    # Tạo sản phẩm mẫu
    create_sample_products(uid, models, categories)

    print("=== CẤU HÌNH HOÀN TẤT ===")
    print("Hệ thống đã sẵn sàng cho cửa hàng vàng và ngoại tệ!")


if __name__ == "__main__":
    main()

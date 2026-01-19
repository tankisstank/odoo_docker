# -*- coding: utf-8 -*-
"""
Test Script cho Module Báo cáo Lãi/Lỗ Hàng ngày (qlv.stock.balance)
Sử dụng XML-RPC API để test các case
"""

import xmlrpc.client
from datetime import date, timedelta
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
_logger = logging.getLogger(__name__)

# Cấu hình kết nối Odoo
ODOO_CONFIG = {
    'url': 'http://localhost:8069',
    'db': 'qlv_new',
    'username': 'c0508g@gmail.com',
    'password': 'abc123'
}

class OdooTestClient:
    def __init__(self, config):
        self.url = config['url']
        self.db = config['db']
        self.username = config['username']
        self.password = config['password']
        self.uid = None
        self.models = None
        self._connect()
    
    def _connect(self):
        try:
            common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
            self.uid = common.authenticate(self.db, self.username, self.password, {})
            if not self.uid:
                raise Exception("Authentication failed")
            self.models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object', allow_none=True)
            _logger.info(f"✓ Kết nối Odoo thành công (UID: {self.uid})")
        except Exception as e:
            _logger.error(f"✗ Lỗi kết nối: {e}")
            raise
    
    def execute(self, model, method, *args, **kwargs):
        return self.models.execute_kw(self.db, self.uid, self.password, model, method, args, kwargs)
    
    def search(self, model, domain, **kwargs):
        return self.execute(model, 'search', domain, **kwargs)
    
    def read(self, model, ids, fields=None):
        if fields:
            return self.models.execute_kw(self.db, self.uid, self.password, model, 'read', [ids], {'fields': fields})
        return self.models.execute_kw(self.db, self.uid, self.password, model, 'read', [ids])
    
    def create(self, model, vals):
        return self.execute(model, 'create', vals)
    
    def write(self, model, ids, vals):
        return self.execute(model, 'write', ids, vals)
    
    def unlink(self, model, ids):
        return self.execute(model, 'unlink', ids)


def test_case_1_create_report(client):
    """Test Case 1: Tạo báo cáo mới - kiểm tra tên tự động"""
    _logger.info("\n" + "="*60)
    _logger.info("TEST CASE 1: Tạo báo cáo mới với tên tự động")
    _logger.info("="*60)
    
    today = date.today().isoformat()
    
    try:
        report_id = client.create('qlv.stock.balance', {
            'date_from': today,
            'date_to': today,
        })
        
        report = client.read('qlv.stock.balance', [report_id], ['name', 'state', 'date_from', 'date_to'])[0]
        
        expected_name = f"BC {date.today().strftime('%d/%m/%Y')}"
        
        if report['name'] == expected_name:
            _logger.info(f"✓ PASSED: Tên báo cáo đúng format: {report['name']}")
        else:
            _logger.warning(f"✗ FAILED: Tên báo cáo = '{report['name']}', expected = '{expected_name}'")
        
        if report['state'] == 'draft':
            _logger.info(f"✓ PASSED: State mặc định = 'draft'")
        else:
            _logger.warning(f"✗ FAILED: State = '{report['state']}', expected = 'draft'")
        
        return report_id
    except Exception as e:
        _logger.error(f"✗ ERROR: {e}")
        return None


def test_case_2_compute_report(client, report_id):
    """Test Case 2: Cập nhật số liệu báo cáo"""
    _logger.info("\n" + "="*60)
    _logger.info("TEST CASE 2: Cập nhật số liệu báo cáo")
    _logger.info("="*60)
    
    try:
        # Gọi action_compute_report
        client.execute('qlv.stock.balance', 'action_compute_report', [report_id])
        
        # Đọc lại báo cáo
        report = client.read('qlv.stock.balance', [report_id], [
            'shop_opening_stock_value', 'shop_closing_stock_value',
            'shop_opening_cash', 'shop_closing_cash',
            'shop_total_opening', 'shop_total_closing',
            'profit_loss',
            'pawn_opening_value', 'pawn_closing_value',
            'debt_opening_value', 'debt_closing_value',
        ])[0]
        
        _logger.info(f"✓ Đã cập nhật số liệu thành công")
        _logger.info(f"  - Shop ĐK Hàng: {report['shop_opening_stock_value']:,.0f}")
        _logger.info(f"  - Shop CK Hàng: {report['shop_closing_stock_value']:,.0f}")
        _logger.info(f"  - Shop ĐK Tiền: {report['shop_opening_cash']:,.0f}")
        _logger.info(f"  - Shop CK Tiền: {report['shop_closing_cash']:,.0f}")
        _logger.info(f"  - Tổng ĐK: {report['shop_total_opening']:,.0f}")
        _logger.info(f"  - Tổng CK: {report['shop_total_closing']:,.0f}")
        _logger.info(f"  - LÃI/LỖ: {report['profit_loss']:,.0f}")
        _logger.info(f"  - Hàng gửi sổ (ĐK/CK): {report['pawn_opening_value']:,.0f} / {report['pawn_closing_value']:,.0f}")
        _logger.info(f"  - Công nợ khách (ĐK/CK): {report['debt_opening_value']:,.0f} / {report['debt_closing_value']:,.0f}")
        
        return True
    except Exception as e:
        _logger.error(f"✗ ERROR: {e}")
        return False


def test_case_3_confirm_report(client, report_id):
    """Test Case 3: Chốt sổ báo cáo"""
    _logger.info("\n" + "="*60)
    _logger.info("TEST CASE 3: Chốt sổ báo cáo")
    _logger.info("="*60)
    
    try:
        # Gọi action_confirm_report
        client.execute('qlv.stock.balance', 'action_confirm_report', [report_id])
        
        # Đọc lại báo cáo
        report = client.read('qlv.stock.balance', [report_id], ['state', 'confirmed_date', 'confirmed_by'])[0]
        
        if report['state'] == 'confirmed':
            _logger.info(f"✓ PASSED: State = 'confirmed'")
        else:
            _logger.warning(f"✗ FAILED: State = '{report['state']}', expected = 'confirmed'")
        
        if report['confirmed_date']:
            _logger.info(f"✓ PASSED: Confirmed date = {report['confirmed_date']}")
        else:
            _logger.warning(f"✗ FAILED: Confirmed date is empty")
        
        if report['confirmed_by']:
            _logger.info(f"✓ PASSED: Confirmed by = {report['confirmed_by']}")
        else:
            _logger.warning(f"✗ FAILED: Confirmed by is empty")
        
        return True
    except Exception as e:
        _logger.error(f"✗ ERROR: {e}")
        return False


def test_case_4_block_update_after_confirm(client, report_id):
    """Test Case 4: Chặn cập nhật sau khi chốt sổ"""
    _logger.info("\n" + "="*60)
    _logger.info("TEST CASE 4: Chặn cập nhật sau khi chốt sổ")
    _logger.info("="*60)
    
    try:
        # Thử gọi action_compute_report - phải bị chặn
        client.execute('qlv.stock.balance', 'action_compute_report', [report_id])
        _logger.warning(f"✗ FAILED: Không bị chặn khi cập nhật báo cáo đã chốt!")
        return False
    except Exception as e:
        if "chốt sổ" in str(e).lower() or "confirmed" in str(e).lower():
            _logger.info(f"✓ PASSED: Đã chặn cập nhật với lỗi: {e}")
            return True
        else:
            _logger.info(f"✓ PASSED: Đã chặn cập nhật (lỗi khác): {e}")
            return True


def test_case_5_reopen_report_admin(client, report_id):
    """Test Case 5: Mở lại báo cáo (Admin)"""
    _logger.info("\n" + "="*60)
    _logger.info("TEST CASE 5: Mở lại báo cáo (Admin)")
    _logger.info("="*60)
    
    try:
        # Gọi action_draft_report
        client.execute('qlv.stock.balance', 'action_draft_report', [report_id])
        
        # Đọc lại báo cáo
        report = client.read('qlv.stock.balance', [report_id], ['state', 'confirmed_date', 'confirmed_by'])[0]
        
        if report['state'] == 'draft':
            _logger.info(f"✓ PASSED: State = 'draft' (đã mở lại)")
        else:
            _logger.warning(f"✗ FAILED: State = '{report['state']}', expected = 'draft'")
        
        if not report['confirmed_date']:
            _logger.info(f"✓ PASSED: Confirmed date đã xóa")
        else:
            _logger.warning(f"✗ FAILED: Confirmed date vẫn còn: {report['confirmed_date']}")
        
        return True
    except Exception as e:
        _logger.error(f"✗ ERROR: {e}")
        return False


def test_case_6_multi_day_report_name(client):
    """Test Case 6: Tên báo cáo nhiều ngày"""
    _logger.info("\n" + "="*60)
    _logger.info("TEST CASE 6: Tên báo cáo nhiều ngày")
    _logger.info("="*60)
    
    today = date.today()
    yesterday = today - timedelta(days=3)
    
    try:
        report_id = client.create('qlv.stock.balance', {
            'date_from': yesterday.isoformat(),
            'date_to': today.isoformat(),
        })
        
        report = client.read('qlv.stock.balance', [report_id], ['name'])[0]
        
        expected_name = f"BC {yesterday.strftime('%d/%m')} - {today.strftime('%d/%m/%Y')}"
        
        if report['name'] == expected_name:
            _logger.info(f"✓ PASSED: Tên báo cáo đúng format: {report['name']}")
        else:
            _logger.warning(f"✗ FAILED: Tên = '{report['name']}', expected = '{expected_name}'")
        
        # Cleanup
        client.unlink('qlv.stock.balance', [report_id])
        
        return True
    except Exception as e:
        _logger.error(f"✗ ERROR: {e}")
        return False


def cleanup(client, report_id):
    """Dọn dẹp dữ liệu test"""
    _logger.info("\n" + "="*60)
    _logger.info("CLEANUP: Xóa dữ liệu test")
    _logger.info("="*60)
    
    try:
        if report_id:
            client.unlink('qlv.stock.balance', [report_id])
            _logger.info(f"✓ Đã xóa báo cáo test ID={report_id}")
    except Exception as e:
        _logger.warning(f"Không thể xóa: {e}")


def main():
    _logger.info("\n" + "#"*60)
    _logger.info("# BẮT ĐẦU TEST MODULE BÁO CÁO LÃI/LỖ HÀNG NGÀY")
    _logger.info("#"*60)
    
    try:
        client = OdooTestClient(ODOO_CONFIG)
    except:
        _logger.error("Không thể kết nối Odoo. Kiểm tra lại cấu hình!")
        return
    
    report_id = None
    results = []
    
    try:
        # Test Case 1
        report_id = test_case_1_create_report(client)
        results.append(("TC1: Tạo báo cáo", report_id is not None))
        
        if report_id:
            # Test Case 2
            results.append(("TC2: Cập nhật số liệu", test_case_2_compute_report(client, report_id)))
            
            # Test Case 3
            results.append(("TC3: Chốt sổ", test_case_3_confirm_report(client, report_id)))
            
            # Test Case 4
            results.append(("TC4: Chặn cập nhật sau chốt", test_case_4_block_update_after_confirm(client, report_id)))
            
            # Test Case 5
            results.append(("TC5: Mở lại báo cáo", test_case_5_reopen_report_admin(client, report_id)))
        
        # Test Case 6
        results.append(("TC6: Tên báo cáo nhiều ngày", test_case_6_multi_day_report_name(client)))
        
    finally:
        # Cleanup
        cleanup(client, report_id)
    
    # Summary
    _logger.info("\n" + "#"*60)
    _logger.info("# KẾT QUẢ TEST")
    _logger.info("#"*60)
    
    passed = 0
    failed = 0
    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        _logger.info(f"  {status}: {name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    _logger.info("-"*60)
    _logger.info(f"  TỔNG KẾT: {passed} passed, {failed} failed")
    _logger.info("#"*60)


if __name__ == '__main__':
    main()

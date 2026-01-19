# -*- coding: utf-8 -*-
"""
Test Script Giả lập Giao dịch Hàng ngày & Kiểm tra Báo cáo Lãi/Lỗ
=================================================================

LUỒNG NGHIỆP VỤ (theo docs):
1. Tạo Sale Order → Chọn Partner
2. Thêm dòng Hàng Bán (is_trade_in=False) hoặc Hàng Mua (is_trade_in=True)
3. Hệ thống tự động tính Auto-Balance (dòng Tiền mặt)
4. Confirm Order → Sinh Phiếu Xuất (Delivery) và Phiếu Nhập (Receipt)
5. Validate Pickings → Cập nhật Tồn kho
6. Báo cáo P&L = (Tồn CK + Tiền CK) - (Tồn ĐK + Tiền ĐK)

KỊCH BẢN TEST:
- GD1: Bán 0.5 chỉ Vàng 9999, giá 8,500,000 → Xuất hàng, Thu tiền
- GD2: Mua (Trade-in) 0.3 chỉ Vàng 9999, giá 8,200,000 → Nhập hàng, Chi tiền
- GD3: Đổi cũ lấy mới: Khách đưa 0.2 chỉ, lấy 0.3 chỉ, trả thêm tiền
- Chốt sổ và verify P&L
"""

import xmlrpc.client
from datetime import date, datetime, timedelta
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
_logger = logging.getLogger(__name__)

# Cấu hình
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
        common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
        self.uid = common.authenticate(self.db, self.username, self.password, {})
        if not self.uid:
            raise Exception("Authentication failed")
        self.models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object', allow_none=True)
        _logger.info(f"✓ Kết nối Odoo thành công (UID: {self.uid})")
    
    def execute(self, model, method, *args, **kwargs):
        return self.models.execute_kw(self.db, self.uid, self.password, model, method, list(args), kwargs)
    
    def search(self, model, domain, **kwargs):
        return self.models.execute_kw(self.db, self.uid, self.password, model, 'search', [domain], kwargs)
    
    def read(self, model, ids, fields=None):
        if fields:
            return self.models.execute_kw(self.db, self.uid, self.password, model, 'read', [ids], {'fields': fields})
        return self.models.execute_kw(self.db, self.uid, self.password, model, 'read', [ids])
    
    def create(self, model, vals):
        return self.models.execute_kw(self.db, self.uid, self.password, model, 'create', [vals])
    
    def write(self, model, ids, vals):
        return self.models.execute_kw(self.db, self.uid, self.password, model, 'write', [ids, vals])
    
    def search_read(self, model, domain, fields=None, limit=None):
        kwargs = {}
        if fields:
            kwargs['fields'] = fields
        if limit:
            kwargs['limit'] = limit
        return self.models.execute_kw(self.db, self.uid, self.password, model, 'search_read', [domain], kwargs)


class TransactionSimulator:
    """Giả lập các giao dịch mua bán vàng"""
    
    def __init__(self, client):
        self.client = client
        self.created_orders = []
        self.test_partner_id = None
        self.gold_product_id = None
        self.money_product_id = None
        self.initial_stock = {}
        self.initial_cash = 0
        
    def setup(self):
        """Chuẩn bị dữ liệu test"""
        _logger.info("\n" + "="*60)
        _logger.info("SETUP: Chuẩn bị dữ liệu test")
        _logger.info("="*60)
        
        # 1. Tìm hoặc tạo Partner test
        partners = self.client.search_read('res.partner', 
            [('name', 'ilike', 'Khách Test')], 
            ['id', 'name'], limit=1)
        
        if partners:
            self.test_partner_id = partners[0]['id']
            _logger.info(f"  → Sử dụng Partner: {partners[0]['name']} (ID: {self.test_partner_id})")
        else:
            self.test_partner_id = self.client.create('res.partner', {
                'name': 'Khách Test P&L',
                'phone': '0901234567'
            })
            _logger.info(f"  → Tạo Partner mới: Khách Test P&L (ID: {self.test_partner_id})")
        
        # 2. Tìm sản phẩm Vàng (4 số / 9999)
        gold_products = self.client.search_read('product.product',
            ['|', '|', ('name', 'ilike', '4 số'), ('name', 'ilike', '9999'), ('name', 'ilike', 'vàng')],
            ['id', 'name', 'list_price', 'standard_price'], limit=1)
        
        if not gold_products:
            # Thử tìm bất kỳ sản phẩm storable nào
            gold_products = self.client.search_read('product.product',
                [('type', '=', 'product'), ('name', 'not ilike', 'Tiền')],
                ['id', 'name', 'list_price', 'standard_price'], limit=1)
        
        if gold_products:
            self.gold_product_id = gold_products[0]['id']
            _logger.info(f"  → Sản phẩm Vàng: {gold_products[0]['name']}")
            _logger.info(f"    Giá bán: {gold_products[0]['list_price']:,.0f} | Giá mua: {gold_products[0]['standard_price']:,.0f}")
        else:
            _logger.error("  ✗ Không tìm thấy sản phẩm Vàng 9999!")
            return False
        
        # 3. Tìm sản phẩm Tiền mặt (Money Product)
        money_products = self.client.search_read('product.product',
            ['|', ('name', 'ilike', 'VND'), ('name', 'ilike', 'Tiền')],
            ['id', 'name'], limit=1)
        
        if money_products:
            self.money_product_id = money_products[0]['id']
            _logger.info(f"  → Sản phẩm Tiền: {money_products[0]['name']} (ID: {self.money_product_id})")
        else:
            _logger.warning("  ! Không tìm thấy sản phẩm Tiền mặt")
        
        # 4. Ghi nhận tồn kho ban đầu
        self._record_initial_stock()
        
        return True
    
    def _record_initial_stock(self):
        """Ghi nhận tồn kho ban đầu"""
        _logger.info("\n  [Tồn kho ban đầu]")
        
        # Tồn Vàng
        if self.gold_product_id:
            gold_quant = self.client.search_read('stock.quant',
                [('product_id', '=', self.gold_product_id), ('location_id.usage', '=', 'internal')],
                ['quantity', 'location_id'], limit=10)
            total_gold = sum(q['quantity'] for q in gold_quant)
            self.initial_stock['gold'] = total_gold
            _logger.info(f"    Vàng 9999: {total_gold:.4f} lượng")
        
        # Tồn Tiền
        if self.money_product_id:
            money_quant = self.client.search_read('stock.quant',
                [('product_id', '=', self.money_product_id), ('location_id.usage', '=', 'internal')],
                ['quantity'], limit=10)
            total_money = sum(q['quantity'] for q in money_quant)
            self.initial_cash = total_money
            _logger.info(f"    Tiền mặt: {total_money:,.0f} VND")
    
    def create_sale_order(self, order_lines, note=""):
        """
        Tạo đơn hàng với các dòng sản phẩm
        
        order_lines: list of dict với keys:
            - product_id: ID sản phẩm
            - product_uom_qty: Số lượng
            - price_unit: Đơn giá
            - is_trade_in: True nếu là hàng mua vào
        """
        order_vals = {
            'partner_id': self.test_partner_id,
            'note': note,
        }
        
        order_id = self.client.create('sale.order', order_vals)
        _logger.info(f"  → Tạo đơn hàng ID: {order_id}")
        
        # Thêm các dòng sản phẩm
        for line in order_lines:
            line_vals = {
                'order_id': order_id,
                'product_id': line['product_id'],
                'product_uom_qty': line.get('product_uom_qty', 1),
                'price_unit': line.get('price_unit', 0),
                'is_trade_in': line.get('is_trade_in', False),
                'sequence': 110 if line.get('is_trade_in') else 10,
            }
            self.client.create('sale.order.line', line_vals)
        
        self.created_orders.append(order_id)
        return order_id
    
    def confirm_order(self, order_id):
        """Xác nhận đơn hàng → Sinh phiếu kho"""
        _logger.info(f"  → Confirm đơn hàng ID: {order_id}")
        self.client.execute('sale.order', 'action_confirm', [order_id])
        
        # Đọc lại thông tin đơn hàng
        order = self.client.read('sale.order', [order_id], ['name', 'state', 'picking_ids'])[0]
        _logger.info(f"    State: {order['state']} | Pickings: {order['picking_ids']}")
        return order
    
    def validate_pickings(self, order_id):
        """Xác nhận tất cả phiếu kho của đơn hàng"""
        order = self.client.read('sale.order', [order_id], ['picking_ids'])[0]
        
        for picking_id in order['picking_ids']:
            picking = self.client.read('stock.picking', [picking_id], ['name', 'state', 'picking_type_id'])[0]
            
            if picking['state'] == 'done':
                _logger.info(f"    Picking {picking['name']} đã done, bỏ qua")
                continue
            
            if picking['state'] == 'cancel':
                _logger.info(f"    Picking {picking['name']} đã cancel, bỏ qua")
                continue
            
            _logger.info(f"    Validating Picking: {picking['name']} (state: {picking['state']})")
            
            try:
                # Đặt qty_done cho các move lines
                moves = self.client.search_read('stock.move',
                    [('picking_id', '=', picking_id)],
                    ['id', 'product_uom_qty', 'quantity_done'])
                
                for move in moves:
                    if move['quantity_done'] == 0:
                        self.client.write('stock.move', [move['id']], {
                            'quantity_done': move['product_uom_qty']
                        })
                
                # Validate picking
                self.client.execute('stock.picking', 'button_validate', [picking_id])
                _logger.info(f"    ✓ Đã validate {picking['name']}")
                
            except Exception as e:
                _logger.warning(f"    ! Lỗi validate {picking['name']}: {e}")
    
    def run_scenario_1_sell_gold(self):
        """
        Kịch bản 1: BÁN VÀNG
        - Bán 0.05 chỉ Vàng 9999, giá 8,500,000/lượng
        - Kỳ vọng: Xuất 0.05 chỉ vàng, Thu tiền (0.05 * 8,500,000 = 425,000)
        """
        _logger.info("\n" + "="*60)
        _logger.info("KỊCH BẢN 1: BÁN VÀNG")
        _logger.info("="*60)
        
        qty = 0.05  # 0.05 chỉ
        price = 8500000  # 8.5 triệu/lượng
        
        order_id = self.create_sale_order([
            {
                'product_id': self.gold_product_id,
                'product_uom_qty': qty,
                'price_unit': price,
                'is_trade_in': False,  # Hàng BÁN
            }
        ], note="Test Bán vàng")
        
        self.confirm_order(order_id)
        self.validate_pickings(order_id)
        
        expected_revenue = qty * price
        _logger.info(f"  → Doanh thu kỳ vọng: {expected_revenue:,.0f} VND")
        _logger.info(f"  → Tồn vàng giảm: {qty} chỉ")
        
        return order_id, {'revenue': expected_revenue, 'gold_out': qty}
    
    def run_scenario_2_buy_gold(self):
        """
        Kịch bản 2: MUA VÀNG (Trade-in)
        - Mua 0.03 chỉ Vàng 9999, giá 8,200,000/lượng
        - Kỳ vọng: Nhập 0.03 chỉ vàng, Chi tiền (0.03 * 8,200,000 = 246,000)
        """
        _logger.info("\n" + "="*60)
        _logger.info("KỊCH BẢN 2: MUA VÀNG (Trade-in)")
        _logger.info("="*60)
        
        qty = 0.03
        price = 8200000
        
        order_id = self.create_sale_order([
            {
                'product_id': self.gold_product_id,
                'product_uom_qty': qty,
                'price_unit': -price,  # Giá âm vì là Trade-in
                'is_trade_in': True,   # Hàng MUA
            }
        ], note="Test Mua vàng")
        
        self.confirm_order(order_id)
        self.validate_pickings(order_id)
        
        expected_cost = qty * price
        _logger.info(f"  → Chi phí mua: {expected_cost:,.0f} VND")
        _logger.info(f"  → Tồn vàng tăng: {qty} chỉ")
        
        return order_id, {'cost': expected_cost, 'gold_in': qty}
    
    def run_scenario_3_trade_in_exchange(self):
        """
        Kịch bản 3: ĐỔI CŨ LẤY MỚI
        - Khách đưa 0.02 chỉ vàng cũ (mua vào 8,200,000)
        - Khách lấy 0.03 chỉ vàng mới (bán ra 8,500,000)
        - Chênh lệch: Khách trả thêm (0.03*8.5M - 0.02*8.2M) = 255,000 - 164,000 = 91,000
        """
        _logger.info("\n" + "="*60)
        _logger.info("KỊCH BẢN 3: ĐỔI CŨ LẤY MỚI")
        _logger.info("="*60)
        
        sell_qty = 0.03
        sell_price = 8500000
        buy_qty = 0.02
        buy_price = 8200000
        
        order_id = self.create_sale_order([
            # Dòng BÁN (Khách lấy)
            {
                'product_id': self.gold_product_id,
                'product_uom_qty': sell_qty,
                'price_unit': sell_price,
                'is_trade_in': False,
            },
            # Dòng MUA (Khách đưa)
            {
                'product_id': self.gold_product_id,
                'product_uom_qty': buy_qty,
                'price_unit': -buy_price,  # Giá âm
                'is_trade_in': True,
            }
        ], note="Test Đổi cũ lấy mới")
        
        self.confirm_order(order_id)
        self.validate_pickings(order_id)
        
        revenue = sell_qty * sell_price
        cost = buy_qty * buy_price
        net = revenue - cost
        
        _logger.info(f"  → Bán: {sell_qty} x {sell_price:,.0f} = {revenue:,.0f}")
        _logger.info(f"  → Mua: {buy_qty} x {buy_price:,.0f} = {cost:,.0f}")
        _logger.info(f"  → Khách trả thêm: {net:,.0f} VND")
        _logger.info(f"  → Tồn vàng thay đổi: +{buy_qty} -{sell_qty} = {buy_qty - sell_qty}")
        
        return order_id, {
            'revenue': revenue,
            'cost': cost,
            'gold_in': buy_qty,
            'gold_out': sell_qty
        }
    
    def verify_pnl_report(self, expected_results):
        """Tạo và kiểm tra báo cáo P&L"""
        _logger.info("\n" + "="*60)
        _logger.info("KIỂM TRA BÁO CÁO LÃI/LỖ")
        _logger.info("="*60)
        
        today = date.today().isoformat()
        
        # Tạo báo cáo
        report_id = self.client.create('qlv.stock.balance', {
            'date_from': today,
            'date_to': today,
        })
        _logger.info(f"  → Tạo báo cáo ID: {report_id}")
        
        # Cập nhật số liệu
        self.client.execute('qlv.stock.balance', 'action_compute_report', [report_id])
        _logger.info(f"  → Đã cập nhật số liệu")
        
        # Đọc kết quả
        report = self.client.read('qlv.stock.balance', [report_id], [
            'name', 'shop_opening_stock_value', 'shop_closing_stock_value',
            'shop_opening_cash', 'shop_closing_cash',
            'shop_total_opening', 'shop_total_closing',
            'profit_loss'
        ])[0]
        
        _logger.info(f"\n  [KẾT QUẢ BÁO CÁO: {report['name']}]")
        _logger.info(f"  ┌──────────────────────────────────────────────")
        _logger.info(f"  │ Hàng hóa ĐK: {report['shop_opening_stock_value']:>20,.0f}")
        _logger.info(f"  │ Hàng hóa CK: {report['shop_closing_stock_value']:>20,.0f}")
        _logger.info(f"  │ Tiền mặt ĐK: {report['shop_opening_cash']:>20,.0f}")
        _logger.info(f"  │ Tiền mặt CK: {report['shop_closing_cash']:>20,.0f}")
        _logger.info(f"  ├──────────────────────────────────────────────")
        _logger.info(f"  │ TỔNG ĐẦU KỲ: {report['shop_total_opening']:>20,.0f}")
        _logger.info(f"  │ TỔNG CUỐI KỲ:{report['shop_total_closing']:>20,.0f}")
        _logger.info(f"  ├──────────────────────────────────────────────")
        _logger.info(f"  │ LÃI / LỖ:   {report['profit_loss']:>20,.0f}")
        _logger.info(f"  └──────────────────────────────────────────────")
        
        # Phân tích kỳ vọng
        total_revenue = sum(r.get('revenue', 0) for r in expected_results)
        total_cost = sum(r.get('cost', 0) for r in expected_results)
        expected_pnl = total_revenue - total_cost
        
        _logger.info(f"\n  [PHÂN TÍCH KỲ VỌNG]")
        _logger.info(f"  Tổng doanh thu:  {total_revenue:>15,.0f}")
        _logger.info(f"  Tổng chi phí:    {total_cost:>15,.0f}")
        _logger.info(f"  Lãi/Lỗ kỳ vọng:  {expected_pnl:>15,.0f}")
        
        # So sánh
        diff = report['profit_loss'] - expected_pnl
        if abs(diff) < 1000:  # Sai số cho phép 1000 VND
            _logger.info(f"\n  ✓ PASSED: P&L khớp với giao dịch (sai số: {diff:,.0f})")
        else:
            _logger.warning(f"\n  ! CHÊNH LỆCH: {diff:,.0f} VND")
            _logger.warning(f"    (Có thể do giá vàng thay đổi hoặc tồn kho trước đó)")
        
        # Chốt sổ
        self.client.execute('qlv.stock.balance', 'action_confirm_report', [report_id])
        _logger.info(f"\n  ✓ Đã chốt sổ báo cáo")
        
        return report_id, report
    
    def cleanup(self):
        """Dọn dẹp dữ liệu test"""
        _logger.info("\n" + "="*60)
        _logger.info("CLEANUP")
        _logger.info("="*60)
        
        for order_id in self.created_orders:
            try:
                # Không xóa đơn hàng đã confirm, chỉ log
                order = self.client.read('sale.order', [order_id], ['name', 'state'])[0]
                _logger.info(f"  → Đơn hàng {order['name']} (state: {order['state']}) - Giữ lại để kiểm tra")
            except Exception as e:
                _logger.warning(f"  ! Lỗi đọc đơn hàng {order_id}: {e}")


def main():
    _logger.info("\n" + "#"*70)
    _logger.info("#  GIẢN LẬP GIAO DỊCH HÀNG NGÀY & KIỂM TRA BÁO CÁO LÃI/LỖ")
    _logger.info("#"*70)
    
    try:
        client = OdooTestClient(ODOO_CONFIG)
    except Exception as e:
        _logger.error(f"Không thể kết nối Odoo: {e}")
        return
    
    simulator = TransactionSimulator(client)
    
    # Setup
    if not simulator.setup():
        _logger.error("Setup thất bại!")
        return
    
    expected_results = []
    
    try:
        # Kịch bản 1: Bán vàng
        _, result1 = simulator.run_scenario_1_sell_gold()
        expected_results.append(result1)
        
        time.sleep(1)  # Đợi xử lý
        
        # Kịch bản 2: Mua vàng
        _, result2 = simulator.run_scenario_2_buy_gold()
        expected_results.append(result2)
        
        time.sleep(1)
        
        # Kịch bản 3: Đổi cũ lấy mới
        _, result3 = simulator.run_scenario_3_trade_in_exchange()
        expected_results.append(result3)
        
        time.sleep(1)
        
        # Kiểm tra báo cáo P&L
        simulator.verify_pnl_report(expected_results)
        
    except Exception as e:
        _logger.error(f"Lỗi trong quá trình test: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        simulator.cleanup()
    
    _logger.info("\n" + "#"*70)
    _logger.info("#  HOÀN TẤT")
    _logger.info("#"*70)


if __name__ == '__main__':
    main()

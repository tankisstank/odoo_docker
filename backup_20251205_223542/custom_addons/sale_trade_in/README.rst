=============
Sale Trade-In
=============

Module này hỗ trợ nghiệp vụ "Đổi cũ lấy mới" (Trade-in) đặc thù của ngành kinh doanh vàng, cho phép thực hiện mua và bán trên cùng một đơn hàng.

Tính năng chính
===============

1. **Đơn hàng hỗn hợp (Mua & Bán):**
   * Cho phép thêm dòng sản phẩm "Trade-in" (khách bán lại) vào đơn bán hàng (`Sale Order`).
   * Tự động lấy giá mua vào (`standard_price`) làm giá trade-in.

2. **Tính toán Tổng tiền thông minh:**
   * Tự động tính toán lại tổng giá trị đơn hàng:
     ``Tổng thanh toán = (Tổng tiền hàng bán ra) - (Tổng tiền hàng mua lại)``
   * Hiển thị rõ ràng tổng giá trị Trade-in trên giao diện đơn hàng và phiếu in.

3. **Tự động xử lý Kho:**
   * Khi xác nhận đơn hàng, hệ thống tự động tách thành 2 phiếu kho:
     * **Delivery Order (Xuất kho):** Cho các sản phẩm bán ra.
     * **Receipt (Nhập kho):** Cho các sản phẩm khách bán lại (Trade-in).
   * Đảm bảo quy trình kho vận hành chính xác theo chiều hàng đi và về.

Sử dụng
=======

1. **Tạo đơn Trade-in:**
   * Tạo Báo giá (`Quotation`) như bình thường.
   * Thêm sản phẩm khách muốn bán lại.
   * Tích vào ô **Trade-in Product** trên dòng sản phẩm đó.
   * Giá sẽ tự động chuyển sang giá mua vào và số tiền sẽ được trừ vào tổng đơn hàng.

2. **Xử lý đơn hàng:**
   * Nhấn **Confirm** để chốt đơn.
   * Vào nút **Smart Button** (Delivery/Transfers) để xem và xử lý các phiếu xuất/nhập kho tương ứng.

Chi tiết Kỹ thuật
=================

* **Model:**
  * ``sale.order``: Thêm trường ``trade_in_total`` và logic tính lại ``amount_total``.
  * ``sale.order.line``: Thêm cờ ``is_trade_in`` và giá ``trade_in_price_unit``.

* **Logic Kho:**
  * Can thiệp vào quy trình ``action_confirm`` của đơn hàng để tạo và điều hướng các `stock.move` sang đúng loại phiếu kho (Incoming/Outgoing).

Phụ thuộc
=========

* ``sale_management``
* ``stock``
* ``product_price_manager`` (Khuyến nghị, để đồng bộ giá mua)

Tác giả
=======

* QLV Development Team

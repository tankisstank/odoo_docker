=====================
Product Price Manager
=====================

Module này cung cấp giải pháp quản lý giá vàng tập trung, cho phép cập nhật nhanh giá mua/bán và theo dõi lịch sử biến động giá.

Tính năng chính
===============

1. **Quản lý Giá tập trung:**
   * Hiển thị đồng thời **Giá Mua** (`standard_price`) và **Giá Bán** (`list_price`) trên giao diện danh sách sản phẩm.
   * Cho phép sửa nhanh giá trực tiếp trên Tree View mà không cần mở từng sản phẩm.

2. **Lịch sử Giá (Price History):**
   * Tự động ghi lại mọi lần thay đổi giá của sản phẩm.
   * Lưu trữ thông tin: Giá cũ, Giá mới, Người thay đổi, Thời gian thay đổi.
   * **Biểu đồ:** Cung cấp biểu đồ đường (Line Chart) để trực quan hóa xu hướng biến động giá theo thời gian.

3. **Khôi phục Giá (Rollback):**
   * Tính năng cho phép quay lại mức giá tại một thời điểm trong quá khứ từ lịch sử.

Sử dụng
=======

1. **Cập nhật giá hàng ngày:**
   * Truy cập menu **Quản lý giá sản phẩm**.
   * Nhập giá mới vào cột "Giá Mua" hoặc "Giá Bán".
   * Hệ thống tự động lưu và ghi lịch sử.

2. **Xem lịch sử:**
   * Mở chi tiết một sản phẩm.
   * Chuyển sang tab **Lịch sử giá** để xem danh sách các lần thay đổi.
   * Nhấn nút **Rollback** trên một dòng lịch sử để khôi phục lại mức giá đó.

Chi tiết Kỹ thuật
=================

* **Model:**
  * ``product.template``: Kế thừa để thêm quan hệ với lịch sử giá.
  * ``product.price.history``: Model mới lưu trữ dữ liệu lịch sử.

* **Views:**
  * Tree View tùy chỉnh cho ``product.template``.
  * Graph View và Tree View cho ``product.price.history``.

Phụ thuộc
=========

* ``product``

Tác giả
=======

* QLV Development Team

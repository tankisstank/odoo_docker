# Mô tả dự án: Hệ thống quản lý kinh doanh vàng

Đây là một dự án Odoo 16 được thiết lập để quản lý hoạt động kinh doanh của một doanh nghiệp chuyên về vàng miếng và vàng nguyên liệu.

## Mục tiêu

Xây dựng một hệ thống ERP (Enterprise Resource Planning) tùy chỉnh trên nền tảng Odoo Community để số hóa và tối ưu hóa các quy trình nghiệp vụ cốt lõi, bao gồm:
- Quản lý sản phẩm vàng theo loại và trọng lượng.
- Cập nhật và quản lý giá mua vào, bán ra hàng ngày.
- Xử lý đơn hàng mua, bán và đặc biệt là các đơn hàng phức hợp (trade-in), nơi khách hàng vừa bán sản phẩm cũ vừa mua sản phẩm mới trong cùng một giao dịch.
- Phân chia quy trình làm việc rõ ràng cho các bộ phận: Kinh doanh, Kế toán, và Kho/Thủ quỹ.

## Công nghệ sử dụng

- **Nền tảng:** Odoo 16 Community Edition.
- **Triển khai:** Docker và Docker Compose.
- **Cơ sở dữ liệu:** PostgreSQL 13.

## Các module tùy chỉnh chính

Dự án đã được phát triển với 2 module tùy chỉnh quan trọng:

1.  **`product_price_manager`**: Một module hỗ trợ việc hiển thị và quản lý giá sản phẩm. Module này tận dụng các trường có sẵn của Odoo (`list_price` cho giá bán và `standard_price` cho giá mua) để bộ phận kinh doanh có thể cập nhật hàng ngày.
2.  **`sale_trade_in`**: Module này mở rộng chức năng của đơn bán hàng (`Sale Order`) để xử lý nghiệp vụ "trade-in". Nó cho phép thêm các sản phẩm mà khách hàng bán lại cho công ty vào cùng một đơn hàng, và tự động tính toán số tiền chênh lệch mà khách hàng phải trả hoặc được nhận lại.

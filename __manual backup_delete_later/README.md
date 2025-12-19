# Hệ thống Quản lý Kinh doanh Vàng (Odoo Gold Business)

Dự án xây dựng hệ thống ERP trên nền tảng Odoo 16 Community để quản lý hoạt động kinh doanh vàng, bao gồm các nghiệp vụ đặc thù như quản lý trọng lượng (chỉ, lượng), cập nhật giá hàng ngày và đổi hàng (trade-in).

## Tài liệu Dự án

Hệ thống tài liệu chi tiết được lưu trữ trong thư mục `docs/`:

-   **[Yêu cầu Chức năng](docs/functional_requirements.md):** Mô tả chi tiết các nghiệp vụ vàng, đơn vị tính và quy trình.
-   **[Hướng dẫn Sử dụng](docs/user_manual.md):** Cách cài đặt, cấu hình và thao tác vận hành hàng ngày.
-   **[Kiến trúc Kỹ thuật](docs/technical_architecture.md):** Chi tiết về các module tùy chỉnh (`product_price_manager`, `sale_trade_in`) và cấu trúc hệ thống.
-   **[Lộ trình Phát triển](docs/roadmap.md):** Các tính năng đã hoàn thành và kế hoạch sắp tới.

## Bắt đầu nhanh (Quick Start)

### 1. Khởi động hệ thống
Yêu cầu: Đã cài đặt Docker và Docker Compose.

```bash
docker-compose up -d
```

Truy cập Odoo tại: `http://localhost:8069`

### 2. Cấu hình môi trường
Sử dụng script tự động để cài đặt module và tạo dữ liệu mẫu:

```bash
python custom_addons/configure_gold_shop.py
```

## Các tính năng chính

1.  **Quản lý Giá:** Cập nhật giá Mua/Bán tập trung, xem lịch sử biến động giá.
2.  **Trade-in (Đổi cũ lấy mới):** Hỗ trợ khách hàng vừa mua vừa bán trên cùng một đơn hàng. Hệ thống tự động tính toán chênh lệch và xử lý kho (Xuất hàng mới, Nhập hàng cũ).
3.  **Đơn vị tính đặc thù:** Hỗ trợ đơn vị "Chỉ", "Lượng" và quy đổi chuẩn.

---
*Dự án được phát triển trên Odoo 16.*

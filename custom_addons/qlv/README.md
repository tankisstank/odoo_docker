# QLV - Hệ thống Quản lý Vàng & Cầm đồ

Module Odoo tùy chỉnh dành riêng cho nghiệp vụ kinh doanh vàng bạc đá quý và cầm đồ.

## Tính năng chính

### 1. Quản lý Giá & Sản phẩm
- Cập nhật giá Mua/Bán hàng ngày (Vàng 9999, 999...).
- Theo dõi lịch sử biến động giá.

### 2. Bán hàng & Đổi cũ lấy mới (Trade-in)
- **Giao diện tối ưu:** Tự động sắp xếp hàng Mua/Bán/Tiền.
- **Auto-Balance:** Tự động tính toán số tiền khách cần trả/nhận lại.
- **Trade-in:** Hỗ trợ thu mua sản phẩm cũ ngay trên đơn bán hàng mới.

### 3. Nghiệp vụ Cầm cố / Gửi sổ
- **Quy trình chuẩn:** Tạo phiếu -> Xác nhận (Nhập kho/Xuất tiền) -> Chuộc lại (Xuất kho/Thu tiền).
- **Thanh lý:** Chuyển đổi phiếu cầm cố quá hạn thành Đơn bán hàng (Mua lại) để thanh lý.
- **Liên kết:** Tự động hiển thị các phiếu cầm cố đang vay của khách hàng ngay trên giao diện Bán hàng.

### 4. Quản lý Kho & Tiền
- **Tiền là Hàng:** Quản lý tiền mặt như một loại hàng hóa tồn kho đặc biệt để kiểm soát chặt chẽ thu chi tại quầy.
- **Giao diện Kho:** Phân biệt rõ phiếu Nhập/Xuất bằng màu sắc trực quan.

## Cài đặt
Module này yêu cầu các dependencies tiêu chuẩn của Odoo: `sale_management`, `stock`, `account`.

## Cấu trúc
Xem chi tiết tại `docs/technical_architecture.md`.

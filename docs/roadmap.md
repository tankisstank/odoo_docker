# Lộ trình Phát triển (Roadmap)

## Các tính năng đã hoàn thành
- [x] Quản lý giá tập trung (Mua/Bán).
- [x] Lịch sử giá và Rollback.
- [x] Nghiệp vụ Trade-in (Tính toán giá, Tách phiếu kho).
- [x] Script cấu hình tự động ban đầu.

## Kế hoạch phát triển tiếp theo

### 1. Quản lý Giá (Product Price Manager)
- [x] **Ràng buộc giá:**
    - Đảm bảo giá không âm.
    - Cảnh báo nếu Giá Bán < Giá Mua (trừ trường hợp khuyến mãi đặc biệt).
- [ ] **Import/Export:**
    - Xây dựng Wizard để cập nhật giá hàng loạt từ file Excel/CSV.

### 2. Báo cáo và In ấn
- [x] **Tùy chỉnh mẫu in:**
    - Thiết kế lại mẫu Báo giá/Hóa đơn theo đặc thù cửa hàng vàng (khổ giấy in nhiệt hoặc A5).
    - Hiển thị rõ ràng phần "Hàng đổi" trên phiếu in.
- [x] **Giao diện Kho:**
    - Hiển thị màu sắc (Xanh/Cam) cho phiếu Nhập/Xuất.
    - Sắp xếp phẳng (Flat List) để dễ quan sát.
- [ ] **Báo cáo doanh thu:**
    - Báo cáo riêng biệt doanh thu bán hàng và chi phí mua lại hàng cũ.

### 3. Quản lý Kho và Tem nhãn
- [ ] **In tem nhãn:** Tích hợp in tem mã vạch cho sản phẩm vàng (bao gồm trọng lượng, hàm lượng).
- [ ] **Kiểm kê:** Quy trình kiểm kê kho vàng cuối ngày.


### 4. Phân quyền và Bảo mật
- [ ] Thiết lập nhóm quyền chi tiết cho: Nhân viên bán hàng, Kế toán, Thủ quỹ, Quản lý cửa hàng.

### 5. Xóa/ ẩn thông tin branding của odoo, thay thế bằng logo của cửa hàng, thay favicon bằng icon của cửa hàng
- [x] Xóa thông tin branding của odoo, thay thế bằng logo của cửa hàng, thay favicon bằng icon của cửa hàng
- [x] Thêm thông tin của cửa hàng vào footer của trang web
- [x] Thêm thông tin của cửa hàng vào header của trang web
- [x] Thêm thông tin của cửa hàng vào footer của các email, pdf mẫu

### 6. Quản lý công nợ
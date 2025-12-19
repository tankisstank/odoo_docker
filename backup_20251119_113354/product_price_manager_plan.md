# Kế hoạch Phát triển Addon: Product Price Manager

**Mục đích:** Addon này nhằm mục đích cung cấp một giao diện người dùng hiệu quả trong Odoo để quản lý (xem, chỉnh sửa, cập nhật) giá mua (`standard_price`) và giá bán (`list_price`) của sản phẩm, đồng thời theo dõi lịch sử thay đổi giá một cách chi tiết.

---

## 1. Trạng thái hiện tại: Các tính năng đã hoàn thành

*   **Giao diện quản lý giá tập trung:**
    *   Một Tree View cho phép xem và chỉnh sửa nhanh giá mua, giá bán của sản phẩm.
    *   Tích hợp Search View cho phép tìm kiếm động theo tên, mã sản phẩm và lọc theo danh mục.

*   **Truy cập nhanh và tiện ích:**
    *   Nút "Mở chi tiết sản phẩm" trên mỗi dòng để truy cập nhanh vào Form View của sản phẩm.
    *   Nút "Xem lịch sử giá" trên mỗi dòng để mở cửa sổ lịch sử giá của sản phẩm đó.

*   **Quản lý lịch sử giá chi tiết:**
    *   Tự động ghi lại mọi thay đổi về giá (người thay đổi, thời gian, giá trị cũ) vào một model riêng (`product.price.history`).
    *   Hiển thị lịch sử giá trong một tab riêng trên Form View của sản phẩm.

*   **Trực quan hóa dữ liệu và Rollback:**
    *   Cửa sổ lịch sử giá có nhiều chế độ xem: Biểu đồ đường (Line Chart) để xem biến động giá, và Danh sách (List View).
    *   Tính năng "Rollback" cho phép khôi phục lại một phiên bản giá cũ trực tiếp từ danh sách lịch sử.

*   **Nền tảng kỹ thuật:**
    *   Đã thống nhất sử dụng model `product.template` cho toàn bộ module.
    *   Đã thiết lập quyền truy cập cơ bản qua file `ir.model.access.csv`.

---

## 2. Checklist các hạng mục cần làm tiếp theo

#### 1. Kiểm tra ràng buộc giá
*   **Trạng thái:** `[Chưa bắt đầu]`
*   **Mục tiêu:** Thêm các ràng buộc (`constraints`) trong Python để đảm bảo dữ liệu giá luôn hợp lệ.
*   **Yêu cầu:**
    *   Giá mua (`standard_price`) và giá bán (`list_price`) không được là số âm.
    *   (Tùy chọn) Giá bán phải luôn lớn hơn hoặc bằng giá mua.

#### 2. Chức năng Nhập/Xuất dữ liệu
*   **Trạng thái:** `[Chưa bắt đầu]`
*   **Mục tiêu:** Cho phép người dùng cập nhật giá hàng loạt thông qua file Excel/CSV.
*   **Yêu cầu:**
    *   Tạo wizard cho phép tải lên file.
    *   Xử lý logic đọc file và cập nhật giá sản phẩm tương ứng.
    *   Cung cấp thông báo kết quả sau khi nhập (số sản phẩm được cập nhật, lỗi nếu có).

#### 3. Cải thiện giao diện UI/UX
#### 4. Tài liệu hóa
*   **Trạng thái:** `[Chưa bắt đầu]`
*   **Mục tiêu:** Tạo file `README.md` mô tả chức năng, cách cài đặt và sử dụng module.

---

## 3. Scripts cập nhật module

### 3.1. Khi có thay đổi trong file Python (.py)
*Bắt buộc phải khởi động lại server Odoo trước khi nâng cấp.*
```bash
docker-compose restart odoo
```

### 3.2. Lệnh nâng cấp module
*Sử dụng sau khi khởi động lại (nếu cần) hoặc khi chỉ thay đổi file XML.*
```bash
docker-compose exec odoo odoo -d odoo_test -u product_price_manager --db_host=db --db_user=odoo --db_password=odoo --stop-after-init
```

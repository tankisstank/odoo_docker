# Kịch Bản Giới Thiệu Giải Pháp Phần Mềm Quản Lý Vàng (QLV)

## 1. Giới thiệu chung (Overview)
**Tiêu đề:** QLV - Giải pháp quản lý kinh doanh Vàng & Cầm đồ chuyên sâu.
**Mục tiêu:** Giới thiệu một hệ thống quản lý hiện đại, giải quyết triệt để các nghiệp vụ đặc thù của ngành vàng mà các phần mềm kế toán thông thường không đáp ứng được.
**Đối tượng:** Chủ tiệm vàng, Quản lý cửa hàng, Kế toán, Nhân viên bán hàng.

---

## 2. Các vấn đề cốt lõi & Giải pháp (Pain Points & Solutions)

### Vấn đề 1: Biến động giá và Đơn vị tính phức tạp
*   **Thực trạng:** Giá vàng thay đổi theo giờ. Vàng có nhiều đơn vị (Lượng, Chỉ, Gram, Ly).
*   **Giải pháp QLV:**
    *   **Quản lý giá tập trung:** Cập nhật giá Mua/Bán tại một màn hình duy nhất đầu ngày.
    *   **Đa đơn vị tính:** Hỗ trợ quy đổi tự động giữa Lượng, Chỉ, Phân.
    *   **Lịch sử giá:** Lưu vết toàn bộ biến động giá để đối chiếu sau này.

### Vấn đề 2: Nghiệp vụ "Đổi cũ lấy mới" (Trade-in)
*   **Thực trạng:** Khách mua hàng mới, trả bằng hàng cũ + tiền mặt. Việc tính toán thủ công dễ nhầm lẫn, khó tách bạch doanh thu và chi phí mua lại.
*   **Giải pháp QLV:**
    *   **Giao diện thông minh (Auto-Sort):** Tự động phân chia dòng hàng Bán (Khách lấy) và hàng Mua (Khách trả).
    *   **Tự động cân bằng (Auto-Balance):** Hệ thống tự tính toán chênh lệch (Tiền hàng - Tiền đổi) để ra số tiền khách cần trả.
    *   **Xử lý kho tự động:** Một đơn hàng tự động tách thành 2 phiếu kho: Phiếu Xuất (hàng bán) và Phiếu Nhập (hàng thu lại).

### Vấn đề 3: Quản lý Tiền mặt & Công nợ
*   **Thực trạng:** Khó kiểm soát tồn quỹ tiền mặt thực tế tại quầy. Công nợ khách hàng và nhà cung cấp lẫn lộn.
*   **Giải pháp QLV:**
    *   **Tiền là Hàng hóa (Money as Product):** Tiền mặt được quản lý như một sản phẩm lưu kho. Thu/Chi tiền chính là Nhập/Xuất kho tiền.
    *   **Đối tác hợp nhất:** Không phân biệt Khách hàng/Nhà cung cấp. Công nợ được tính toán bù trừ tự động (Net Debt).

### Vấn đề 4: Nghiệp vụ Cầm đồ (Pawn)
*   **Thực trạng:** Quản lý sổ sách rời rạc, khó theo dõi hạn lãi, khó xử lý khi khách bỏ đồ (thanh lý).
*   **Giải pháp QLV:**
    *   **Quy trình khép kín:** Tạo phiếu -> Duyệt (Tiền ra/Vàng vào) -> Chuộc (Tiền vào/Vàng ra).
    *   **Thanh lý tự động:** Chuyển đổi phiếu cầm đồ quá hạn thành Đơn bán hàng (Trade-in) chỉ với 1 click chuột.

---

## 3. Thiết lập & Cài đặt ban đầu (Installation & Setup)

Hệ thống được thiết kế để triển khai nhanh chóng thông qua công nghệ Container (Docker).

**Bước 1: Khởi tạo hệ thống**
*   Sử dụng `docker-compose up -d` để dựng server Odoo và Database.
*   Hệ thống sẵn sàng tại `http://localhost:8069`.

**Bước 2: Cấu hình tự động (One-click Config)**
*   Chạy script `configure_gold_shop.py`.
*   **Hệ thống tự động thực hiện:**
    *   Cài đặt các module nghiệp vụ (Sales, Stock, Accounting, QLV Core).
    *   Thiết lập Đơn vị tính (Chỉ, Lượng).
    *   Tạo dữ liệu mẫu: Danh mục vàng (9999, 999), Sản phẩm mẫu.
    *   Cấu hình sổ nhật ký và tài khoản kế toán cơ bản.

---

## 4. Hướng dẫn Luồng quy trình (User Workflow)

### Kịch bản 1: Đầu ngày làm việc
1.  Quản lý truy cập menu **Quản lý giá sản phẩm**.
2.  Cập nhật **Giá Mua vào** và **Giá Bán ra** cho các loại vàng (9999, SJC, Vàng trang sức).
3.  Hệ thống áp dụng giá mới cho toàn bộ các giao dịch phát sinh sau đó.

### Kịch bản 2: Bán hàng & Đổi vàng (Tại quầy)
1.  Nhân viên tạo Báo giá mới.
2.  **Chọn hàng bán:** Nhẫn vàng 2 chỉ (Giá bán tự động load).
3.  **Chọn hàng khách trả (Trade-in):** Dây chuyền cũ 1 chỉ. Tích chọn "Trade-in". Giá mua lại tự động load.
4.  **Thanh toán:** Hệ thống hiển thị số tiền khách cần bù. Xác nhận đơn.
5.  **Kết quả:**
    *   In hóa đơn cho khách.
    *   Kho tự động trừ: 1 Nhẫn 2 chỉ.
    *   Kho tự động cộng: 1 Dây chuyền cũ.
    *   Quỹ tự động cộng: Số tiền khách bù.

### Kịch bản 3: Cầm đồ & Thanh lý
1.  Tạo phiếu Cầm cố: Nhập thông tin khách, Tài sản cầm, Số tiền vay, Lãi suất.
2.  **Xác nhận:** Kho Tiền giảm, Kho Hàng Cầm (tài sản khách) tăng.
3.  **Trường hợp Thanh lý (Khách bỏ đồ):**
    *   Bấm nút "Thanh lý".
    *   Hệ thống tự động tạo Đơn bán hàng Trade-in (Shop mua đứt tài sản này từ khách để cấn trừ nợ gốc).

---

## 5. Giao diện & Trải nghiệm (UI/UX)
*   **Trực quan:** Phiếu kho sử dụng màu sắc phân biệt (Xanh: Nhập / Cam: Xuất).
*   **Thương hiệu riêng:** Logo, Favicon, Header/Footer báo cáo được tùy chỉnh theo cửa hàng, loại bỏ branding của Odoo.
*   **Thông minh:** Cảnh báo khi Giá bán < Giá mua. Hiển thị danh sách tài sản đang cầm cố ngay trên màn hình bán hàng.

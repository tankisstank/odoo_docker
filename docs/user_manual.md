# Hướng dẫn Sử dụng và Cấu hình

## 1. Cài đặt và Khởi động

### Yêu cầu
- Docker và Docker Compose đã được cài đặt.

### Các bước thực hiện
1.  Mở terminal tại thư mục dự án.
2.  Chạy lệnh khởi động:
    ```bash
    docker-compose up -d
    ```
3.  Truy cập `http://localhost:8069`.
4.  Tạo database mới (ví dụ: `gold_business`) với thông tin đăng nhập Admin.

## 2. Cấu hình Ban đầu (Tự động)

Dự án cung cấp một script Python để tự động cấu hình các thông số cơ bản cho cửa hàng vàng.

1.  Đảm bảo Odoo đang chạy và bạn đã tạo database.
2.  Mở file `custom_addons/configure_gold_shop.py` và cập nhật thông tin kết nối nếu cần (URL, DB Name, User, Password).
3.  Chạy script:
    ```bash
    python custom_addons/configure_gold_shop.py
    ```
    Script này sẽ:
    - Cài đặt các module cần thiết (`sale`, `stock`, `account`, ...).
    - Cấu hình đa tiền tệ.
    - Tạo đơn vị tính: `Chỉ`, `Lượng`, `Gram`.
    - Tạo danh mục sản phẩm và một số sản phẩm mẫu.

## 3. Cấu hình Thủ công (Nếu cần)

Nếu không dùng script, bạn cần thực hiện các bước sau:

1.  **Cài đặt Module:** Vào Apps, tìm và cài `product_price_manager` và `sale_trade_in`.
2.  **Đơn vị tính:** Vào Inventory -> Configuration -> UoM, tạo `Chỉ` và `Lượng` (1 Lượng = 10 Chỉ).
3.  **Sản phẩm:** Tạo sản phẩm với thuộc tính Trọng lượng (0.5 chỉ, 1 chỉ, ...).

## 4. Hướng dẫn Vận hành Hàng ngày

### a. Cập nhật Giá vàng
1.  Vào menu **Quản lý giá sản phẩm**.
2.  Tại danh sách sản phẩm, bạn có thể sửa trực tiếp **Giá Mua** (`standard_price`) và **Giá Bán** (`list_price`).
3.  Lịch sử thay đổi sẽ được lưu lại tự động.

### b. Tạo đơn hàng Trade-in (Đổi vàng)
1.  Vào **Sales -> Quotations -> Create**.
2.  **Thêm dòng bán:** Chọn sản phẩm khách mua (ví dụ: Nhẫn 2 chỉ). Giá bán tự động lấy từ hệ thống.
3.  **Thêm dòng mua lại (Trade-in):**
    - Chọn sản phẩm khách bán lại (ví dụ: Nhẫn 1 chỉ cũ).
    - Tích vào ô **Trade-in Product**.
    - Giá mua lại sẽ tự động lấy từ giá Cost của sản phẩm (có thể sửa nếu cần).
4.  **Kiểm tra tổng tiền:** Hệ thống sẽ tự động trừ tiền hàng khách bán lại khỏi tổng tiền khách phải trả.
5.  **Confirm:** Xác nhận đơn hàng. Hệ thống sẽ tạo 1 phiếu xuất kho (giao hàng mới) và 1 phiếu nhập kho (nhận hàng cũ).

## 5. Hướng dẫn Nghiệp vụ Cầm cố (Pawn)

### a. Tạo phiếu Cầm cố
1.  Truy cập menu **Cầm cố / Vay mượn**.
2.  Tạo mới phiếu, chọn Khách hàng, Nhập số tiền vay và Lãi suất (nếu có).
3.  Thêm tài sản cầm cố (Vàng) và định giá.
4.  Bấm **Xác nhận**: Hệ thống tự động tạo phiếu nhập kho tài sản và xuất tiền.

### b. Chuộc đồ
1.  Mở phiếu đang ở trạng thái "Đang cầm cố".
2.  Bấm **Khách chuộc lại**.
3.  Hệ thống xác nhận khách đã trả tiền và tạo phiếu trả lại tài sản.

### c. Thanh lý (Khách bỏ đồ)
1.  Mở phiếu Cầm cố cần thanh lý.
2.  Bấm **Chuyển sang Mua bán (Thanh lý)**.
3.  Hệ thống sẽ:
    -   Kết thúc phiếu cầm cố.
    -   Tự động tạo một **Đơn bán hàng** mới cho khách này.
    -   Đưa tài sản vào đơn hàng dưới dạng **Trade-in** (Mua lại).
4.  Bạn có thể bấm vào nút **"Đơn Thanh lý"** trên phiếu để chuyển sang đơn bán và thương lượng giá thêm với khách.

### d. Theo dõi khi Bán hàng
-   Tại giao diện **Đơn bán hàng**, khi chọn Khách hàng, hệ thống sẽ tự động hiển thị danh sách **"Đơn Cầm cố đang hiệu lực"** của khách đó ngay bên dưới, giúp bạn nắm bắt tổng quan tình hình nợ/tài sản của khách.

## 6. Hướng dẫn Quản lý Công nợ (Module `qlv`)

### a. Thiết lập Đối tác Công nợ
1.  Vào menu **Công nợ -> Đối tác Công nợ**.
2.  Chọn hoặc tạo mới một khách hàng.
3.  Tích vào ô **Is Gold Partner** (Là đối tác vàng).
4.  Lưu lại. Bạn sẽ thấy ô **Net Debt** xuất hiện để theo dõi công nợ ròng.

### b. Quy trình Mua/Bán ghi nợ
*   **Bán hàng ghi nợ:**
    1.  Tạo đơn bán hàng (Sale Order) -> Confirm.
    2.  Tạo Invoice -> Confirm.
    3.  **Quan trọng:** Không bấm "Register Payment" ngay. Khoản tiền này sẽ được treo vào công nợ Phải thu (Receivable).
*   **Mua hàng/Trade-in ghi nợ:**
    1.  Tạo Vendor Bill (hoặc từ đơn Trade-in) -> Confirm.
    2.  Không thanh toán ngay. Khoản tiền này treo vào công nợ Phải trả (Payable).

### c. Cấn trừ Công nợ
Khi đối tác vừa có khoản nợ phải thu và phải trả, bạn dùng tính năng này để bù trừ:
1.  Vào menu **Công nợ -> Cấn trừ Công nợ**.
2.  Chọn **Partner** (Đối tác).
3.  Hệ thống tự động tính toán:
    *   *Total Receivable:* Tổng tiền khách nợ mình.
    *   *Total Payable:* Tổng tiền mình nợ khách.
    *   *Offset Amount:* Số tiền có thể cấn trừ (là số nhỏ nhất trong 2 số trên).
4.  Bấm **Confirm Offset**. Hệ thống sẽ tự động tạo bút toán để khớp 2 khoản nợ này với nhau.

    -   **Destination Location:** Kho đích (ví dụ: WH/Safe hoặc Partner Location).

### d. Hủy Đơn hàng đã Hoàn tất (Super Cancel)
Trong trường hợp cần hủy đơn hàng đã chốt (Invoiced/Done) vì sai sót:
1.  Mở đơn hàng cần hủy.
2.  Bấm nút **"Hủy đơn hàng"** trên thanh trạng thái (Header).
3.  Xác nhận thông báo. Hệ thống sẽ tự động:
    -   Hủy các hóa đơn liên quan.
    -   Tạo phiếu **Trả hàng (Return)** cho các phiếu xuất kho đã xong.
    -   Tự động xác nhận phiếu trả để nhập lại kho.
    -   Đưa đơn hàng về trạng thái "Đã hủy" (Cancelled).

### e. Lưu ý về Tiền mặt và Số Âm
-   **Hàng Trade-in (Mua lại):** Hệ thống hiển thị số tiền là **Âm (-)** để biểu thị việc trừ tiền thanh toán.
-   **Tiền VNĐ (Nhập tay):** Bạn có thể nhập sản phẩm "Tiền VNĐ" (ví dụ khách trả trước 1 phần tiền mặt). Dòng này sẽ hiển thị như hàng hóa thông thường.
-   **Dòng Cân bằng (Tự động):** Hệ thống tự sinh dòng "Thu tiền mặt" hoặc "Chi tiền mặt" để chốt số tiền cuối cùng cần giao dịch. Dòng này lấy `Tổng Hàng - Tổng Tiền đã đưa`.

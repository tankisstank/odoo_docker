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
    -   *Lưu ý:* Hệ thống sẽ tự động hiển thị nhãn **"Đơn Nhập" (nhap)** nếu giá trị mua lớn hơn giá trị bán, và nược lại là **"Đơn Xuất" (xuat)**.


## 5. Hướng dẫn Nghiệp vụ Cầm cố / Gửi sổ (Tích hợp)
*Lưu ý: Tính năng này hiện được thực hiện trực tiếp trên giao diện Đơn bán hàng.*

### a. Tạo phiếu Cầm cố (Khách gửi vàng lấy tiền)
1.  Tạo **Đơn bán hàng** mới.
2.  Chọn **Khách hàng**.
3.  Thêm dòng sản phẩm khách đưa (Trade-in):
    - Tích chọn `Hàng mua vào (Trade-in)`.
    - Nhập số lượng và định giá.
4.  Tại dòng tiền (Auto Balance), hệ thống sẽ hiển thị "Chi tiền mặt" (Số tiền Shop đưa cho khách).
5.  **Ghi chú:** Có thể nhập vào ô Ghi chú là "Cầm cố 1 tháng...".
6.  **Confirm:** Xác nhận đơn. Hàng vào kho, tiền ra khỏi quỹ. Đơn hàng ở trạng thái đang giao dịch.

### b. Chuộc đồ (Khách trả tiền lấy vàng)
1.  Nếu khách muốn chuộc lại đúng món đồ đó:
    - Tạo Đơn bán hàng mới.
    - Tìm lại đơn cũ trong danh sách **"Đơn hàng chưa hoàn thành"**.
    - Sử dụng tính năng **Thanh toán (Settlement)** (xem mục dưới).
2.  Hoặc tạo đơn bán hàng mới, bán lại sản phẩm tương đương.

### c. Chuyển Đơn / Thanh toán Bù trừ (Settlement)
Khi khách muốn tất toán một đơn hàng cũ (đang nợ/cầm cố) để chuyển sang giao dịch mới:

1.  Tạo **Đơn hàng mới**.
2.  Chọn Khách hàng. Danh sách **"Đơn hàng chưa hoàn thành"** sẽ hiện ra bên dưới.
3.  Tại dòng đơn cũ cần xử lý, bấm nút **Thanh toán** (biểu tượng tiền).
4.  Hệ thống sẽ:
    -   Tự động khóa đơn cũ (Trạng thái chuyển sang "ĐÃ CHUYỂN ĐƠN").
    -   Đưa toàn bộ hàng hóa của đơn cũ sang đơn mới.
    -   *Lưu ý:* Các dòng hàng chuyển sang sẽ hiển thị **Tên hàng gốc** trong phần mô tả (ví dụ "Chuyển thu hồi: Vàng ta 777...") để dễ đối chiếu.
5.  Trên đơn mới, bạn tiếp tục thêm/bớt các sản phẩm mua bán khác.
6.  Số tiền chênh lệch cuối cùng sẽ được tính toán tự động.
7.  **Lưu và Xác nhận** đơn mới để hoàn tất giao dịch.






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

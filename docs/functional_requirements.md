# Yêu cầu chức năng dự án

Dưới đây là danh sách các yêu cầu chức năng chi tiết cho hệ thống quản lý kinh doanh vàng.

## 1. Quản lý Sản phẩm (Product Management)

-   **Phân loại sản phẩm:**
    -   Vàng 4 số (9999)
    -   Vàng 3 số (999)
    -   Vàng X (loại khác)
    -   Vàng thương hiệu (ví dụ: Vàng Bảo Tín Minh Châu)
-   **Đơn vị tính (UoM):**
    -   Hệ thống phải hỗ trợ quản lý theo các đơn vị trọng lượng vàng.
    -   Các đơn vị cơ bản: `lượng`, cho  các sản phẩm thuộc loại vàng 4 số, vàng 3 số, vàng X, BTMC, vàng non tuổi
    -   Đơn vị tính: "ĐV" cho các sản phẩm thuộc loại Ngoại tệ, Tiền tệ
-   **Sản phẩm Tiền tệ (ĐẶC BIỆT):**
    -   Hệ thống quản lý "Tiền mặt" là dạng **Sản phẩm lưu kho (Storable Product)**.
    -   **Cơ chế:** Khi thực hiện giao dịch thu/chi trên đơn hàng, hế thống sẽ sinh ra các phiếu nhập/xuất kho tiền mặt tương ứng (như một hàng hóa đặc biệt).
    -   **Quản lý:** Số lượng tồn kho của sản phẩm này chính là số tiền mặt thực tế tại quầy/két.

## 2. Quản lý Giá (Price Management)

-   **Cập nhật giá hàng ngày:**
    -   Bộ phận kinh doanh phải có giao diện để cập nhật **Giá Mua Vào** và **Giá Bán Ra** cho từng loại sản phẩm.
    -   Việc cập nhật cần được thực hiện dễ dàng vào đầu ngày hoặc đầu phiên giao dịch.
-   **Áp dụng giá:**
    -   Giá bán ra được tự động áp dụng khi tạo đơn hàng bán.
    -   Giá mua vào được tự động áp dụng cho các sản phẩm trong nghiệp vụ "trade-in".

## 3. Quản lý Đối tác (Partner Management)

-   **Đối tác hợp nhất:**
    -   Không phân biệt Khách hàng và Nhà cung cấp (`res.partner`).

## 4. Quản lý Cầm đồ / Vay Mượn (Pawn & Loan) - Đã tích hợp
-   **Tích hợp hoàn toàn vào Đơn bán hàng (`sale.order`):**
    -   Không còn module riêng biệt `pawn.order`. Mọi nghiệp vụ Cầm cố/Gửi sổ được xử lý trực tiếp trên Đơn hàng.
    -   **Cầm đồ:** Tạo đơn Trade-in (Mua vào). Khách bán tạm cho Shop.
    -   **Chuộc đồ:** Tạo đơn Bán ra (Shop bán lại cho Khách).
    -   **Ghi chú:** Sử dụng trường `note` hoặc Sequence riêng để phân biệt.
-   **Đơn hàng treo (Pending Orders):**
    -   Tại giao diện Đơn hàng bán, danh sách "Đơn hàng chưa hoàn thành" sẽ hiển thị toàn bộ các giao dịch cũ (bao gồm cả Cầm cố cũ) của khách hàng để nhân viên dễ dàng thao tác thanh toán/tất toán.


## 5. Quy trình bán hàng (Sales Workflow)

-   **Tự động sắp xếp (Smart Auto-Sort):**
    -   Quy tắc Sequence: Hàng Bán (10), Hàng Mua (110), Header (0, 100), Tiền Tự động (9998).
    -   Hệ thống tự động sắp xếp lại khi lưu hoặc tính toán, nhưng **đảm bảo giữ Focus** con trỏ chuột tại dòng đang nhập liệu.
-   **Cân bằng tiền tự động (Dynamic Auto-Balance):**
    -   Hệ thống tự động sinh dòng "Tiền mặt" cuối cùng để cân bằng đơn hàng.
    -   **Tách biệt:** Tiền nhập tay (Manual VND) được coi là hàng hóa/trade-in bình thường.
    -   **Đặt tên thông minh:** "Thu tiền mặt (Tự động)" (Nếu khách trả thêm) hoặc "Chi tiền mặt (Tự động)" (Nếu shop trả lại khách).
-   **Kiểm soát Trạng thái & Hủy đơn (Locking & Super Cancel):**
    -   **Khóa đơn (Locking):** Đơn hàng ở trạng thái "Đã giao dịch" (Done/Invoiced) sẽ bị khóa chỉnh sửa (Readonly) để bảo toàn dữ liệu.
    -   **Hủy đơn siêu cấp (Super Cancel):**
        -   Cho phép quản lý hủy đơn hàng đã hoàn tất.
        -   **Tự động hoàn kho:** Hệ thống tự động tạo và xác nhận phiếu trả hàng (Return Picking) để bù lại kho.
        -   **Hủy hóa đơn:** Tự động hủy/reset các hóa đơn liên quan.
-   **Chốt đơn hàng:**
    -   Khi Confirm, hệ thống tự động tách các dòng hàng thành các phiếu kho riêng biệt:
        -   Hàng Bán -> Phiếu Xuất (Delivery Order).
        -   Hàng Mua/Trade-in -> Phiếu Nhập (Receipt).
-   **Thanh toán Bù trừ / Tất toán đơn cũ (Order Settlement):**
    -   **Mục đích:** Khi khách hàng muốn tất toán một đơn hàng cũ (đang treo, đang cầm cố) để chuyển sang đơn hàng mới hoặc trả tiền.
    -   **Cơ chế "Chuyển Đơn" (Order Transfer):**
        -   Từ Đơn Mới, nhân viên chọn đơn cũ cần tất toán trong danh sách "Đơn hàng chưa hoàn thành".
        -   Bấm nút **Thanh toán**.
        -   Hệ thống tự động:
            1.  **Hủy phiếu kho treo** của đơn cũ (nếu chưa hoàn thành).
            2.  **Khóa đơn cũ** (chuyển trạng thái "Đã giao dịch/Completed").
            3.  **Chuyển toàn bộ hàng hóa & nghĩa vụ tài chính** dở dang sang Đơn Mới.
            4.  Tại Đơn Mới, các dòng này xuất hiện dưới dạng Trade-in (Thu về) hoặc Bán ra.
            5.  Dòng tiền cân bằng được tính toán lại để chốt số tiền cuối cùng khách cần trả/nhận.


## 5. Quy trình Kế toán (Accounting Workflow)

-   **Xử lý đơn hàng:**
    -   Kế toán tiếp nhận các đơn hàng đã "chốt" từ bộ phận Kinh doanh.
    -   Kiểm tra thông tin đơn hàng, công nợ của khách.
-   **Duyệt và tạo hóa đơn:**
    -   Sau khi kiểm tra, kế toán duyệt đơn hàng và tạo hóa đơn (`Invoice`).
-   **In phiếu:**
    -   Hệ thống cho phép in phiếu hóa đơn/giao nhận để chuyển cho bộ phận Kho/Thủ quỹ.

## 6. Quy trình Kho và Quỹ (Inventory & Treasury)

-   **Quản lý phiếu kho (Enhanced UI):**
    -   Danh sách phiếu kho hiển thị trực quan với **Màu sắc phân biệt** (Xanh: Nhập, Cam: Xuất).
    -   Hiển thị đầy đủ thông tin chi tiết (Nguồn, Đích, Ngày dự kiến) ngay trên danh sách.
-   **Xuất/Nhập kho:**
    -   Dựa trên phiếu từ kế toán, bộ phận kho thực hiện xuất vàng cho khách (đối với hàng bán ra) hoặc nhập vàng từ khách (đối với hàng trade-in).
-   **Thu/Chi tiền:**
    -   Thủ quỹ thực hiện xác nhận trên phiếu nhập/xuất kho của sản phẩm "Tiền mặt".

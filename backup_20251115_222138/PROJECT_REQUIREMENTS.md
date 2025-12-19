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
    -   Các đơn vị cơ bản: `chỉ`, `lượng`.
    -   Mối quan hệ: `1 lượng = 10 chỉ`.
-   **Biến thể sản phẩm (Product Variants):**
    -   Hệ thống cần quản lý sản phẩm theo các trọng lượng khác nhau: 0.5 chỉ, 1 chỉ, 2 chỉ, 5 chỉ, 1 lượng, 5 lượng.

## 2. Quản lý Giá (Price Management)

-   **Cập nhật giá hàng ngày:**
    -   Bộ phận kinh doanh phải có giao diện để cập nhật **Giá Mua Vào** và **Giá Bán Ra** cho từng loại sản phẩm.
    -   Việc cập nhật cần được thực hiện dễ dàng vào đầu ngày hoặc đầu phiên giao dịch.
-   **Áp dụng giá:**
    -   Giá bán ra được tự động áp dụng khi tạo đơn hàng bán.
    -   Giá mua vào được tự động áp dụng cho các sản phẩm trong nghiệp vụ "trade-in".

## 3. Quản lý Đối tác (Partner Management)

-   **Đối tác hợp nhất:**
    -   Không phân biệt Khách hàng và Nhà cung cấp.
    -   Một đối tác (`res.partner`) có thể vừa là người mua hàng, vừa là người bán hàng cho công ty.

## 4. Quy trình bán hàng (Sales Workflow)

-   **Tạo và báo giá:**
    -   Bộ phận kinh doanh tiếp nhận yêu cầu, tạo báo giá (`Quotation`).
-   **Nghiệp vụ Trade-in:**
    -   Trên cùng một đơn hàng, hệ thống phải hỗ trợ thêm dòng sản phẩm khách hàng bán lại (trade-in).
    -   Các dòng trade-in phải có giá mua vào riêng.
    -   Tổng giá trị đơn hàng phải được tính bằng: `(Tổng tiền hàng bán ra) - (Tổng tiền hàng mua vào/trade-in)`.
-   **Chốt đơn hàng:**
    -   Khi khách hàng đồng ý, nhân viên kinh doanh "chốt" đơn hàng (chuyển từ `Quotation` thành `Sale Order`).
    -   Đơn hàng sau khi chốt sẽ được chuyển cho bộ phận Kế toán.

## 5. Quy trình Kế toán (Accounting Workflow)

-   **Xử lý đơn hàng:**
    -   Kế toán tiếp nhận các đơn hàng đã "chốt" từ bộ phận Kinh doanh.
    -   Kiểm tra thông tin đơn hàng, công nợ của khách.
-   **Duyệt và tạo hóa đơn:**
    -   Sau khi kiểm tra, kế toán duyệt đơn hàng và tạo hóa đơn (`Invoice`).
-   **In phiếu:**
    -   Hệ thống cho phép in phiếu hóa đơn/giao nhận để chuyển cho bộ phận Kho/Thủ quỹ.

## 6. Quy trình Kho và Quỹ (Inventory & Treasury)

-   **Xuất/Nhập kho:**
    -   Dựa trên phiếu từ kế toán, bộ phận kho thực hiện xuất vàng cho khách (đối với hàng bán ra) hoặc nhập vàng từ khách (đối với hàng trade-in).
-   **Thu/Chi tiền:**
    -   Thủ quỹ thực hiện thu tiền chênh lệch từ khách hoặc chi trả lại cho khách dựa trên tổng giá trị cuối cùng của đơn hàng.

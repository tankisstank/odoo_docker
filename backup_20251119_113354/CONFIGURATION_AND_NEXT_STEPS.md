# Hướng dẫn Cấu hình và Các bước Tiếp theo

Hệ thống đã có nền tảng vững chắc với các module tùy chỉnh. Bây giờ, bạn cần thực hiện các bước cấu hình sau trực tiếp trên giao diện Odoo để hệ thống có thể đi vào hoạt động.

## 1. Khởi động hệ thống

Trước tiên, hãy đảm bảo hệ thống Odoo của bạn đang chạy. Mở terminal trong thư mục `E:\repo\odoo_docker` và chạy lệnh:

```bash
docker-compose up -d
```

Sau đó, truy cập Odoo qua địa chỉ `http://localhost:8069`. Bạn sẽ cần tạo một database mới (ví dụ `gold_business`) và đăng nhập với tài khoản admin.

## 2. Cài đặt các module

1.  Vào menu **Apps**.
2.  Xóa bộ lọc "Apps" mặc định trên thanh tìm kiếm.
3.  Tìm và cài đặt lần lượt 2 module sau:
    -   `Product Price Manager` (tên kỹ thuật: `product_price_manager`)
    -   `Sale Trade-In` (tên kỹ thuật: `sale_trade_in`)
    *(Lưu ý: Cài đặt `product_price_manager` trước nếu có thể, dù chúng không phụ thuộc trực tiếp vào nhau)*

## 3. Cấu hình Đơn vị tính (Units of Measure)

Đây là bước quan trọng để quản lý trọng lượng vàng.

1.  Kích hoạt chế độ nhà phát triển (Developer Mode).
2.  Vào menu **Inventory -> Configuration -> UoM Categories**.
    -   Tạo một danh mục mới tên là `Trọng lượng Vàng`.
3.  Vào menu **Inventory -> Configuration -> Units of Measure**.
    -   Tạo đơn vị `chỉ`:
        -   **Unit of Measure:** `chỉ`
        -   **Category:** `Trọng lượng Vàng`
        -   **Type:** `Reference Unit for this category`
    -   Tạo đơn vị `lượng`:
        -   **Unit of Measure:** `lượng`
        -   **Category:** `Trọng lượng Vàng`
        -   **Type:** `Bigger than the Reference Unit`
        -   **Ratio:** `10` (Vì 1 lượng = 10 chỉ)

## 4. Cấu hình Sản phẩm

### a. Product Categories

Vào **Inventory -> Configuration -> Product Categories**, tạo các danh mục để phân loại vàng, ví dụ:
-   Vàng 9999
-   Vàng 999
-   Vàng BTMC

### b. Product Attributes

Vào **Inventory -> Configuration -> Attributes**, tạo thuộc tính `Trọng lượng`:
-   **Attribute Name:** `Trọng lượng`
-   **Display Type:** `Radio`
-   **Values:** `0.5 chỉ`, `1 chỉ`, `2 chỉ`, `5 chỉ`, `1 lượng`, `5 lượng`

### c. Tạo sản phẩm mẫu

Bây giờ, hãy tạo một sản phẩm có biến thể:
1.  Vào **Sales -> Products -> Products**.
2.  Nhấn **Create**.
3.  **Product Name:** `Vàng nhẫn 9999`
4.  Chuyển qua tab **Attributes & Variants**:
    -   Thêm thuộc tính `Trọng lượng` và chọn tất cả các giá trị bạn đã tạo.
5.  Lưu lại. Odoo sẽ tự động tạo ra các biến thể sản phẩm (ví dụ: Vàng nhẫn 9999 (1 chỉ), Vàng nhẫn 9999 (2 chỉ),...).
6.  **Cập nhật giá:**
    -   Vào từng biến thể sản phẩm (tab **Variants** trên form sản phẩm gốc).
    -   Tại tab **General Information** của mỗi biến thể:
        -   **Sales Price:** Nhập giá bán ra cho 1 đơn vị UoM (ví dụ: giá cho 1 chỉ).
        -   **Cost:** Nhập giá mua vào cho 1 đơn vị UoM.
    -   **Unit of Measure:** Chọn `chỉ` hoặc `lượng` cho phù hợp.

## 5. Thử nghiệm quy trình Trade-in

1.  Vào **Sales -> Orders -> Quotations** và tạo một báo giá mới.
2.  **Thêm dòng bán:**
    -   Thêm sản phẩm bạn muốn bán cho khách, ví dụ `Vàng nhẫn 9999 (1 lượng)`.
    -   Số lượng: 1. Đơn giá sẽ được tự động điền.
3.  **Thêm dòng mua (trade-in):**
    -   Thêm sản phẩm khách hàng bán lại, ví dụ `Vàng nhẫn 999 (8 chỉ)`.
    -   Tích vào ô **"Trade-in Product"**.
    -   Giá **"Trade-in Price (Unit)"** sẽ được tự động điền bằng giá "Cost" của sản phẩm đó.
4.  **Kiểm tra kết quả:**
    -   Quan sát trường **"Total Trade-in"** ở cuối đơn hàng.
    -   Kiểm tra **"Total"** cuối cùng, nó sẽ được tính bằng `(Tổng bán) - (Tổng trade-in)`.

## 6. Các bước tiếp theo

-   **Phân quyền người dùng:** Tạo các nhóm người dùng (Kinh doanh, Kế toán, Kho) và gán quyền truy cập phù hợp cho từng nhóm để họ chỉ thấy các menu và chức năng liên quan đến công việc của mình.
-   **Tùy chỉnh báo cáo/in ấn:** Tùy chỉnh lại mẫu báo giá, hóa đơn, phiếu giao hàng để có định dạng chuyên nghiệp và phù hợp với thông tin của công ty.
-   **Phát triển module quản lý giá:** Để chuyên nghiệp hơn, có thể phát triển module `product_price_manager` thêm một bước nữa: tạo một giao diện riêng để cập nhật giá hàng loạt cho tất cả sản phẩm thay vì phải vào từng sản phẩm để sửa.

==================
Gold Shop Branding
==================

Module này cung cấp giải pháp xây dựng thương hiệu (Branding) và loại bỏ thương hiệu mặc định (Debranding) cho hệ thống Odoo, được thiết kế riêng cho Cửa hàng Vàng.

Tính năng chính
===============

1. **Loại bỏ thương hiệu Odoo (Debranding):**
   * **Email:** Tự động xóa dòng chữ "Powered by Odoo" và các liên kết trỏ về odoo.com trong tất cả các email gửi đi từ hệ thống.
   * **Website Footer:** Ẩn dòng "Create a free website with Odoo" và "Powered by Odoo" ở chân trang web.
   * **Portal:** Ẩn các thông tin quảng cáo Odoo trong giao diện Portal (trang dành cho khách hàng).
   * **Login Page:** Thay thế dòng "Powered by Odoo" bằng tên Công ty.

2. **Xây dựng thương hiệu Cửa hàng (Branding):**
   * **Favicon:** Thay thế biểu tượng Odoo mặc định trên tab trình duyệt bằng biểu tượng đồng tiền vàng (hoặc logo tùy chỉnh của cửa hàng).
   * **Website Footer:** Tự động hiển thị thông tin bản quyền (Copyright), Tên công ty và Địa chỉ ở chân trang web.

Cấu hình
========

Module này hoạt động chủ yếu dựa trên cấu hình **Công ty (Company)** của Odoo.

1. **Thông tin Công ty:**
   * Truy cập vào **Settings -> Users & Companies -> Companies**.
   * Cập nhật đầy đủ: Tên công ty, Địa chỉ, Số điện thoại, Email.
   * Các thông tin này sẽ được tự động lấy để hiển thị trên Website Footer và trang Login.

2. **Favicon:**
   * Module đi kèm với một favicon mặc định (hình đồng tiền vàng).
   * Để thay đổi favicon: Thay thế file ``static/src/img/favicon.ico`` trong thư mục module bằng file icon của bạn (định dạng .ico).

Chi tiết Kỹ thuật
=================

Module này can thiệp vào các thành phần sau:

* **Mail Render Mixin (`mail.render.mixin`):**
  * Ghi đè hàm ``_render_template`` và ``_replace_local_links`` để xử lý nội dung HTML của email trước khi gửi.
  * Sử dụng biểu thức chính quy (Regex) để tìm và loại bỏ các thẻ ``<a>`` chứa liên kết đến odoo.com.

* **Web Layout (`web.layout`):**
  * Thay thế thẻ ``<link rel="shortcut icon">`` để đổi Favicon.

* **Website & Portal Templates:**
  * Kế thừa và ẩn (d-none) các thành phần ``o_brand_promotion`` và ``o_footer`` mặc định của Odoo.
  * Inject (chèn) thông tin công ty vào footer thông qua XPath.

Phụ thuộc
=========

* ``base``
* ``web``
* ``mail``
* ``portal``
* ``website``
* ``sale``
* ``website_payment``

Tác giả
=======

* QLV Development Team

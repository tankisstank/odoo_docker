# Hướng Dẫn Restore Odoo trên Máy Mới

## 📋 Checklist Trước Khi Restore

- [ ] Docker Desktop đã được cài đặt
- [ ] Docker Compose đã được cài đặt
- [ ] Đã copy toàn bộ thư mục backup sang máy mới
- [ ] Đã giải nén backup (nếu có)

---

## 🔧 Bước 1: Kiểm Tra và Chỉnh Sửa docker-compose.yml

### Vấn đề thường gặp:
File `docker-compose.yml` trong backup có thể chứa đường dẫn tuyệt đối của máy cũ.

### Cách sửa:

1. **Mở file `docker-compose.yml`** trong thư mục restore

2. **Kiểm tra phần volumes:**

```yaml
volumes:
  - "E:\\repo\\odoo_docker\\postgres_data:/var/lib/postgresql/data"  # ❌ Đường dẫn cũ
  - "./odoo_data:/var/lib/odoo"  # ✅ Đường dẫn tương đối (OK)
```

3. **Sửa đường dẫn volumes:**

**Cách 1: Dùng đường dẫn tương đối (Khuyến nghị)**
```yaml
volumes:
  - "./postgres_data:/var/lib/postgresql/data"  # ✅ Tương đối
  - "./odoo_data:/var/lib/odoo"  # ✅ Tương đối
```

**Cách 2: Dùng đường dẫn tuyệt đối mới**
```yaml
volumes:
  - "C:\\QLV\\qlv_docker\\postgres_data:/var/lib/postgresql/data"  # ✅ Đường dẫn mới
  - "C:\\QLV\\qlv_docker\\odoo_data:/var/lib/odoo"  # ✅ Đường dẫn mới
```

**Lưu ý:** Thay `C:\\QLV\\qlv_docker` bằng đường dẫn thực tế trên máy mới của bạn.

---

## 🚀 Bước 2: Chạy Script Restore

### Cách 1: Sử dụng file .bat (Dễ nhất)
```batch
restore.bat backup_20241114_112749
```

### Cách 2: Chạy PowerShell
```powershell
# Mở PowerShell trong thư mục restore
powershell -ExecutionPolicy Bypass -File .\restore_odoo.ps1 -BackupPath ".\backup_20241114_112749"
```

### Cách 3: Nếu đã set Execution Policy
```powershell
.\restore_odoo.ps1 -BackupPath ".\backup_20241114_112749"
```

---

## 🐳 Bước 3: Khởi Động Containers

Sau khi restore xong, khởi động containers:

```powershell
# Di chuyển đến thư mục dự án
cd C:\QLV\qlv_docker  # (hoặc đường dẫn của bạn)

# Khởi động containers
docker compose up -d
```

**Kết quả mong đợi:**
```
[+] Running 2/2
 ✔ Container odoo_db      Started
 ✔ Container odoo_server  Started
```

---

## ✅ Bước 4: Kiểm Tra Containers

### Kiểm tra containers đã chạy:
```powershell
docker ps
```

**Kết quả mong đợi:**
```
NAMES         STATUS        PORTS
odoo_server   Up X minutes  0.0.0.0:8069->8069/tcp
odoo_db       Up X minutes  5432/tcp
```

### Kiểm tra logs:
```powershell
# Xem logs Odoo
docker compose logs -f odoo

# Xem logs Database
docker compose logs -f db
```

**Dấu hiệu Odoo đã sẵn sàng:**
- Logs hiển thị: `INFO odoo odoo.service.server: HTTP service (werkzeug) running on 0.0.0.0:8069`
- Không có lỗi ERROR nghiêm trọng

---

## 🌐 Bước 5: Truy Cập Odoo

1. **Mở trình duyệt:**
   ```
   http://localhost:8069
   ```

2. **Chọn database:**
   - Database name: `odoo_test` (hoặc tên database trong backup)
   - Language: Tiếng Việt / English
   - Country: Vietnam

3. **Đăng nhập:**
   - Username: `admin` (hoặc username bạn đã cấu hình)
   - Password: (password bạn đã cấu hình)

---

## 🔍 Bước 6: Kiểm Tra Custom Modules

1. **Vào Apps:**
   - Menu: Apps → Apps

2. **Update Apps List:**
   - Click nút "Update Apps List" (hoặc F5)

3. **Kiểm tra modules:**
   - Tìm: `Sale Trade-In`
   - Tìm: `Product Price Manager`
   - Đảm bảo chúng đã được cài đặt

4. **Nếu module chưa cài:**
   - Click vào module
   - Click "Install"

---

## ⚠️ Xử Lý Các Vấn Đề Thường Gặp

### Vấn đề 1: Containers không khởi động được

**Nguyên nhân:** Đường dẫn volumes sai

**Giải pháp:**
```powershell
# 1. Kiểm tra đường dẫn trong docker-compose.yml
# 2. Đảm bảo thư mục postgres_data và odoo_data tồn tại
# 3. Sửa đường dẫn nếu cần
# 4. Khởi động lại:
docker compose down
docker compose up -d
```

---

### Vấn đề 2: Port 8069 đã được sử dụng

**Lỗi:**
```
Error: bind: address already in use
```

**Giải pháp:**

**Cách 1: Thay đổi port trong docker-compose.yml**
```yaml
ports:
  - "8070:8069"  # Thay đổi port bên ngoài
```

**Cách 2: Tìm và dừng process đang dùng port 8069**
```powershell
# Tìm process
netstat -ano | findstr :8069

# Dừng process (thay PID bằng số thực tế)
taskkill /PID <PID> /F
```

---

### Vấn đề 3: Database không restore được

**Lỗi:**
```
ERROR: Failed to restore database!
```

**Giải pháp:**

1. **Kiểm tra container database đang chạy:**
```powershell
docker ps | findstr odoo_db
```

2. **Restore thủ công:**
```powershell
# Khởi động database container trước
docker compose up -d db

# Đợi 10 giây để database sẵn sàng
Start-Sleep -Seconds 10

# Restore database
Get-Content .\backup_20241114_112749\database_backup.sql | docker exec -i odoo_db psql -U odoo odoo
```

3. **Kiểm tra database đã restore:**
```powershell
docker exec -it odoo_db psql -U odoo -d odoo -c "\dt"
```

---

### Vấn đề 4: Odoo không tìm thấy custom modules

**Nguyên nhân:** Đường dẫn custom_addons không đúng

**Giải pháp:**

1. **Kiểm tra volume mount:**
```yaml
volumes:
  - "./custom_addons:/mnt/extra-addons"  # Đảm bảo đường dẫn đúng
```

2. **Kiểm tra trong container:**
```powershell
docker exec -it odoo_server ls -la /mnt/extra-addons
```

3. **Restart Odoo:**
```powershell
docker compose restart odoo
```

---

### Vấn đề 5: Lỗi "Database does not exist"

**Giải pháp:**

1. **Tạo database mới:**
```powershell
docker exec -it odoo_db psql -U odoo -c "CREATE DATABASE odoo_test;"
```

2. **Restore lại database:**
```powershell
Get-Content .\backup_20241114_112749\database_backup.sql | docker exec -i odoo_db psql -U odoo odoo_test
```

---

## 📝 Checklist Sau Khi Restore

- [ ] Containers đã chạy (`docker ps`)
- [ ] Odoo truy cập được (`http://localhost:8069`)
- [ ] Đăng nhập thành công
- [ ] Custom modules hiển thị trong Apps
- [ ] Dữ liệu đã được restore (Sales Orders, Products, etc.)
- [ ] Module Sale Trade-In hoạt động đúng
- [ ] PDF quotation hiển thị đúng

---

## 🎯 Quick Start Commands

```powershell
# 1. Restore
.\restore_odoo.ps1 -BackupPath ".\backup_20241114_112749"

# 2. Sửa docker-compose.yml (nếu cần)

# 3. Khởi động
docker compose up -d

# 4. Kiểm tra
docker ps
docker compose logs -f odoo

# 5. Truy cập
# http://localhost:8069
```

---

## 📞 Hỗ Trợ

Nếu gặp vấn đề:
1. Kiểm tra logs: `docker compose logs`
2. Kiểm tra file `BACKUP_INFO.txt` trong thư mục backup
3. Xem file `FIX_EXECUTION_POLICY.md` nếu gặp lỗi Execution Policy


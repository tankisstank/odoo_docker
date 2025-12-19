# Hướng Dẫn Backup và Restore Odoo Docker Environment

## 📋 Mục Lục
1. [Tổng Quan](#tổng-quan)
2. [Backup](#backup)
3. [Restore](#restore)
4. [Các Tùy Chọn Nâng Cao](#các-tùy-chọn-nâng-cao)
5. [Troubleshooting](#troubleshooting)

---

## 📦 Tổng Quan

Script backup này sẽ sao lưu toàn bộ:
- ✅ Cấu hình Docker (`docker-compose.yml`, `Dockerfile`)
- ✅ Custom modules (`custom_addons/`)
- ✅ Database (PostgreSQL dump)
- ✅ Odoo data (filestore, sessions)
- ✅ Các file cấu hình khác

---

## 💾 Backup

### Cách 1: Sử dụng Script Tự Động (Khuyến nghị)

#### Bước 1: Mở PowerShell
```powershell
# Di chuyển đến thư mục dự án
cd E:\repo\odoo_docker
```

#### Bước 2: Chạy script backup
```powershell
# Backup đầy đủ (bao gồm database và data)
.\backup_odoo.ps1

# Backup không bao gồm database (nhanh hơn)
.\backup_odoo.ps1 -IncludeDatabase:$false

# Backup không bao gồm data (chỉ code và config)
.\backup_odoo.ps1 -IncludeData:$false

# Chỉ định thư mục backup tùy chỉnh
.\backup_odoo.ps1 -BackupPath ".\my_backup_2024"
```

#### Bước 3: Kiểm tra kết quả
Script sẽ tạo thư mục backup với tên: `backup_YYYYMMDD_HHMMSS`

Ví dụ: `backup_20241113_143022`

### Cách 2: Backup Thủ Công

#### 1. Backup Cấu Hình Docker
```powershell
# Copy các file cấu hình
Copy-Item docker-compose.yml backup_folder\
Copy-Item Dockerfile backup_folder\
```

#### 2. Backup Custom Modules
```powershell
# Copy toàn bộ custom_addons (loại bỏ __pycache__)
robocopy custom_addons backup_folder\custom_addons /E /XD __pycache__
```

#### 3. Backup Database
```powershell
# Tạo database dump
docker exec odoo_db pg_dump -U odoo odoo > backup_folder\database_backup.sql
```

#### 4. Backup Odoo Data
```powershell
# Backup filestore
robocopy odoo_data\filestore backup_folder\odoo_data\filestore /E

# Backup sessions
robocopy odoo_data\sessions backup_folder\odoo_data\sessions /E
```

---

## 🔄 Restore

### Cách 1: Sử dụng Script Tự Động (Khuyến nghị)

#### Bước 1: Đảm bảo containers đã dừng
```powershell
docker compose down
```

#### Bước 2: Chạy script restore
```powershell
# Restore đầy đủ
.\restore_odoo.ps1 -BackupPath ".\backup_20241113_143022"

# Restore không bao gồm database
.\restore_odoo.ps1 -BackupPath ".\backup_20241113_143022" -RestoreDatabase:$false

# Restore không bao gồm data
.\restore_odoo.ps1 -BackupPath ".\backup_20241113_143022" -RestoreData:$false
```

#### Bước 3: Khởi động lại containers
```powershell
docker compose up -d
```

#### Bước 4: Kiểm tra logs
```powershell
docker compose logs -f odoo
```

### Cách 2: Restore Thủ Công

#### 1. Restore Cấu Hình Docker
```powershell
Copy-Item backup_folder\docker-compose.yml .
Copy-Item backup_folder\Dockerfile .
```

#### 2. Restore Custom Modules
```powershell
# Xóa custom_addons cũ (nếu có)
Remove-Item custom_addons -Recurse -Force

# Copy từ backup
Copy-Item backup_folder\custom_addons -Destination . -Recurse
```

#### 3. Restore Database
```powershell
# Khởi động database container trước
docker compose up -d db

# Đợi database sẵn sàng (khoảng 10 giây)
Start-Sleep -Seconds 10

# Restore database
Get-Content backup_folder\database_backup.sql | docker exec -i odoo_db psql -U odoo odoo
```

#### 4. Restore Odoo Data
```powershell
# Restore filestore
robocopy backup_folder\odoo_data\filestore odoo_data\filestore /E

# Restore sessions
robocopy backup_folder\odoo_data\sessions odoo_data\sessions /E
```

#### 5. Khởi Động Lại
```powershell
docker compose up -d
```

---

## ⚙️ Các Tùy Chọn Nâng Cao

### Backup Chỉ Custom Modules
```powershell
.\backup_odoo.ps1 -IncludeDatabase:$false -IncludeData:$false
```

### Backup Chỉ Database
```powershell
# Tạo thư mục backup
$BackupPath = ".\backup_db_only"
New-Item -ItemType Directory -Force -Path $BackupPath

# Backup database
docker exec odoo_db pg_dump -U odoo odoo > "$BackupPath\database_backup.sql"
```

### Backup Định Kỳ (Scheduled Task)

#### Tạo Task Scheduler trên Windows:

1. Mở **Task Scheduler** (Win + R → `taskschd.msc`)
2. Tạo **Basic Task**
3. Đặt tên: "Odoo Daily Backup"
4. Trigger: Daily, 2:00 AM
5. Action: Start a program
   - Program: `powershell.exe`
   - Arguments: `-ExecutionPolicy Bypass -File "E:\repo\odoo_docker\backup_odoo.ps1"`
   - Start in: `E:\repo\odoo_docker`

### Backup Lên Cloud

#### Sử dụng rclone (nếu có cấu hình):
```powershell
# Backup local trước
.\backup_odoo.ps1

# Upload lên cloud
$LatestBackup = Get-ChildItem -Directory -Filter "backup_*" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
rclone copy $LatestBackup.FullName remote:odoo_backups/$($LatestBackup.Name)
```

---

## 🔧 Troubleshooting

### Lỗi: "Container không chạy"
**Giải pháp:**
```powershell
# Kiểm tra containers
docker ps -a

# Khởi động containers
docker compose up -d
```

### Lỗi: "Permission denied" khi restore database
**Giải pháp:**
```powershell
# Đảm bảo database container đang chạy
docker compose up -d db

# Kiểm tra quyền truy cập
docker exec odoo_db psql -U odoo -c "SELECT version();"
```

### Lỗi: "Port already in use"
**Giải pháp:**
```powershell
# Kiểm tra port đang sử dụng
netstat -ano | findstr :8069

# Dừng container cũ
docker compose down

# Hoặc thay đổi port trong docker-compose.yml
```

### Lỗi: "Out of disk space"
**Giải pháp:**
```powershell
# Backup không bao gồm data (tiết kiệm dung lượng)
.\backup_odoo.ps1 -IncludeData:$false

# Hoặc xóa các backup cũ
Get-ChildItem -Directory -Filter "backup_*" | Sort-Object LastWriteTime | Select-Object -SkipLast 5 | Remove-Item -Recurse -Force
```

### Database quá lớn
**Giải pháp:**
```powershell
# Backup database với compression
docker exec odoo_db pg_dump -U odoo odoo | gzip > backup_folder\database_backup.sql.gz

# Restore từ file nén
gunzip -c backup_folder\database_backup.sql.gz | docker exec -i odoo_db psql -U odoo odoo
```

---

## 📝 Checklist Backup

Trước khi backup, đảm bảo:
- [ ] Containers đang chạy ổn định
- [ ] Không có thay đổi đang pending
- [ ] Đủ dung lượng ổ đĩa
- [ ] Đã test restore trên môi trường test (nếu có)

Sau khi backup:
- [ ] Kiểm tra kích thước backup hợp lý
- [ ] Kiểm tra file BACKUP_INFO.txt
- [ ] Test restore trên môi trường test
- [ ] Lưu backup ở nơi an toàn (cloud, external drive)

---

## 🚀 Chuyển Sang Môi Trường Mới

### Trên Máy Mới:

1. **Cài đặt Docker và Docker Compose**
   ```powershell
   # Kiểm tra Docker
   docker --version
   docker compose version
   ```

2. **Copy toàn bộ thư mục backup sang máy mới**

3. **Chạy restore**
   ```powershell
   cd <thư_mục_backup>
   ..\restore_odoo.ps1 -BackupPath .
   ```

4. **Chỉnh sửa docker-compose.yml** (nếu cần)
   - Kiểm tra đường dẫn volumes
   - Kiểm tra ports
   - Kiểm tra environment variables

5. **Khởi động**
   ```powershell
   docker compose up -d
   ```

6. **Kiểm tra**
   ```powershell
   # Xem logs
   docker compose logs -f

   # Kiểm tra web interface
   # Mở browser: http://localhost:8069
   ```

---

## 📞 Hỗ Trợ

Nếu gặp vấn đề:
1. Kiểm tra file `BACKUP_INFO.txt` trong thư mục backup
2. Xem logs: `docker compose logs`
3. Kiểm tra file hướng dẫn này

---

**Lưu ý quan trọng:**
- ⚠️ Backup database có thể mất thời gian nếu database lớn
- ⚠️ Luôn test restore trên môi trường test trước
- ⚠️ Giữ nhiều bản backup (ít nhất 3 bản gần nhất)
- ⚠️ Backup định kỳ (hàng ngày hoặc hàng tuần)


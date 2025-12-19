# Cập Nhật Backup và Restore - Hỗ Trợ Tất Cả Databases

## 🔄 Thay Đổi Chính

### **Trước đây:**
- ❌ Chỉ backup 1 database: `odoo`
- ❌ Chỉ restore 1 database: `odoo`
- ❌ Mất dữ liệu các database khác khi restore

### **Bây giờ:**
- ✅ Backup **TẤT CẢ** databases trong PostgreSQL
- ✅ Backup **globals** (roles, users, permissions)
- ✅ Restore **TẤT CẢ** databases
- ✅ Tự động tạo database nếu chưa có
- ✅ Hỗ trợ cả format mới và format cũ

---

## 📁 Cấu Trúc Backup Mới

```
backup_YYYYMMDD_HHMMSS/
├── docker-compose.yml
├── Dockerfile
├── custom_addons/
│   ├── sale_trade_in/
│   └── product_price_manager/
├── databases/                    ← THƯ MỤC MỚI
│   ├── globals.sql              ← Roles, users
│   ├── databases_list.txt       ← Danh sách databases
│   ├── odoo.sql                 ← Database odoo
│   ├── odoo_test.sql            ← Database odoo_test
│   └── odoo_qlv.sql             ← Database odoo_qlv (nếu có)
├── odoo_data/
│   ├── filestore/
│   └── sessions/
└── BACKUP_INFO.txt
```

---

## 🚀 Cách Sử Dụng

### **1. Backup (Tự động backup tất cả databases)**

```powershell
# Backup đầy đủ
.\backup_odoo.ps1

# Hoặc dùng file .bat
backup.bat
```

**Script sẽ tự động:**
- Tìm tất cả databases (trừ system databases)
- Backup từng database vào file riêng
- Backup globals (roles, users)
- Tạo file danh sách databases

---

### **2. Restore (Tự động restore tất cả databases)**

```powershell
# Restore đầy đủ (tất cả databases + config + data)
.\restore_odoo.ps1 -BackupPath ".\backup_20241114_112749"

# Hoặc chỉ restore databases
.\restore_database_only.ps1 -BackupPath ".\backup_20241114_112749"
```

**Script sẽ tự động:**
- Restore globals trước (roles, users)
- Restore từng database
- Tạo database nếu chưa có
- Xác minh restore thành công

---

## 🔍 Kiểm Tra Databases

### **Xem danh sách databases trong backup:**

```powershell
# Xem file danh sách
Get-Content .\backup_20241114_112749\databases\databases_list.txt

# Hoặc xem các file .sql
Get-ChildItem .\backup_20241114_112749\databases\*.sql
```

### **Kiểm tra databases trên server:**

```powershell
# Xem tất cả databases
docker exec odoo_db psql -U odoo -l

# Hoặc dùng script
.\check_database.ps1
```

---

## ⚠️ Lưu Ý Quan Trọng

### **1. Format tương thích ngược:**
- Script restore vẫn hỗ trợ format cũ (`database_backup.sql`)
- Nếu tìm thấy thư mục `databases/` → dùng format mới
- Nếu chỉ có `database_backup.sql` → dùng format cũ

### **2. Khi restore:**
- Script sẽ **DROP và RECREATE** database trước khi restore
- ⚠️ **Dữ liệu hiện tại sẽ bị mất!**
- Đảm bảo đã backup trước khi restore

### **3. Thứ tự restore:**
1. Globals (roles, users) ← Restore trước
2. Databases ← Restore sau

---

## 📋 Checklist Sau Khi Restore

- [ ] Tất cả databases đã được restore
- [ ] Kiểm tra số lượng databases: `docker exec odoo_db psql -U odoo -l`
- [ ] Kiểm tra bảng `ir_module_module` trong mỗi database
- [ ] Odoo truy cập được: `http://localhost:8069`
- [ ] Có thể chọn database khi đăng nhập
- [ ] Dữ liệu trong mỗi database đã đầy đủ

---

## 🛠️ Troubleshooting

### **Vấn đề: Một số databases không được restore**

**Giải pháp:**
```powershell
# Kiểm tra file backup có tồn tại không
Get-ChildItem .\backup_20241114_112749\databases\*.sql

# Restore thủ công từng database
Get-Content .\backup_20241114_112749\databases\odoo_test.sql | docker exec -i odoo_db psql -U odoo -d odoo_test
```

### **Vấn đề: Lỗi "database already exists"**

**Giải pháp:**
Script sẽ tự động DROP và RECREATE, nhưng nếu vẫn lỗi:
```powershell
# Drop database thủ công
docker exec odoo_db psql -U odoo -d postgres -c "DROP DATABASE IF EXISTS odoo_test;"

# Sau đó restore lại
.\restore_database_only.ps1 -BackupPath ".\backup_20241114_112749"
```

---

## 📊 So Sánh Format

| Tính năng | Format Cũ | Format Mới |
|-----------|-----------|------------|
| Số lượng databases | 1 (odoo) | Tất cả |
| Backup globals | ❌ | ✅ |
| File backup | `database_backup.sql` | `databases/<name>.sql` |
| Danh sách databases | ❌ | ✅ (`databases_list.txt`) |
| Tương thích ngược | - | ✅ |

---

## 🎯 Khuyến Nghị

1. **Backup định kỳ:** Chạy backup hàng ngày/tuần
2. **Kiểm tra backup:** Đảm bảo tất cả databases đã được backup
3. **Test restore:** Thử restore trên môi trường test trước
4. **Giữ nhiều bản backup:** Ít nhất 3 bản gần nhất

---

**Lưu ý:** Script mới sẽ tự động phát hiện và backup/restore tất cả databases. Không cần cấu hình thêm!


# Hướng Dẫn Xử Lý Lỗi Execution Policy

## 🔴 Lỗi Thường Gặp

```
.\restore_odoo.ps1 : File cannot be loaded because running scripts is disabled on this system.
```

## ✅ Các Cách Xử Lý

### **Cách 1: Bypass cho lần chạy hiện tại (Khuyến nghị - An toàn nhất)**

Chạy script với tham số `-ExecutionPolicy Bypass`:

```powershell
# Mở PowerShell và chạy:
powershell -ExecutionPolicy Bypass -File .\restore_odoo.ps1 -BackupPath ".\backup_20241114_112749"

# Hoặc với backup_odoo.ps1:
powershell -ExecutionPolicy Bypass -File .\backup_odoo.ps1
```

**Ưu điểm:** 
- ✅ Không thay đổi cài đặt hệ thống
- ✅ Chỉ áp dụng cho lần chạy này
- ✅ An toàn nhất

---

### **Cách 2: Thay đổi Execution Policy cho CurrentUser (Khuyến nghị cho thường xuyên sử dụng)**

Chỉ thay đổi cho user hiện tại, không ảnh hưởng toàn hệ thống:

```powershell
# Mở PowerShell với quyền Administrator
# Kiểm tra policy hiện tại:
Get-ExecutionPolicy -List

# Thay đổi policy cho CurrentUser:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Xác nhận: Nhấn Y
```

**Sau đó có thể chạy script bình thường:**
```powershell
.\restore_odoo.ps1 -BackupPath ".\backup_20241114_112749"
.\backup_odoo.ps1
```

**Ưu điểm:**
- ✅ Áp dụng cho tất cả script của user này
- ✅ Không cần gõ lại `-ExecutionPolicy Bypass`
- ✅ An toàn (chỉ ảnh hưởng user hiện tại)

---

### **Cách 3: Thay đổi Execution Policy cho Process (Tạm thời)**

Chỉ áp dụng cho session PowerShell hiện tại:

```powershell
# Mở PowerShell và chạy:
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process

# Sau đó chạy script bình thường:
.\restore_odoo.ps1 -BackupPath ".\backup_20241114_112749"
```

**Ưu điểm:**
- ✅ Chỉ áp dụng cho session hiện tại
- ✅ Tự động reset khi đóng PowerShell

**Nhược điểm:**
- ⚠️ Phải chạy lại mỗi lần mở PowerShell mới

---

### **Cách 4: Unblock file (Nếu file bị block do download từ internet)**

Nếu file bị đánh dấu là "downloaded from internet":

```powershell
# Unblock file:
Unblock-File -Path .\restore_odoo.ps1
Unblock-File -Path .\backup_odoo.ps1

# Sau đó chạy bình thường:
.\restore_odoo.ps1 -BackupPath ".\backup_20241114_112749"
```

---

## 📋 Các Loại Execution Policy

| Policy | Mô tả | Mức độ an toàn |
|--------|-------|----------------|
| **Restricted** | Không cho chạy script nào (mặc định) | ⚠️ Rất an toàn |
| **RemoteSigned** | Cho chạy script local, script từ internet cần signature | ✅ An toàn (Khuyến nghị) |
| **AllSigned** | Tất cả script đều cần signature | ✅ Rất an toàn |
| **Unrestricted** | Cho chạy tất cả script | ⚠️ Không an toàn |
| **Bypass** | Bỏ qua tất cả kiểm tra | ⚠️ Không an toàn |

---

## 🎯 Khuyến Nghị

### **Cho người dùng thông thường:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### **Cho lần chạy đơn lẻ:**
```powershell
powershell -ExecutionPolicy Bypass -File .\restore_odoo.ps1 -BackupPath ".\backup_20241114_112749"
```

---

## 🔍 Kiểm Tra Execution Policy Hiện Tại

```powershell
# Xem policy hiện tại:
Get-ExecutionPolicy

# Xem tất cả policy:
Get-ExecutionPolicy -List
```

**Kết quả mẫu:**
```
        Scope ExecutionPolicy
        ----- ---------------
MachinePolicy       Undefined
   UserPolicy       Undefined
      Process       Undefined
  CurrentUser       RemoteSigned
 LocalMachine       Restricted
```

---

## ⚠️ Lưu Ý Quan Trọng

1. **Không nên** set `Unrestricted` hoặc `Bypass` cho `LocalMachine` (toàn hệ thống)
2. **Nên** sử dụng `RemoteSigned` cho `CurrentUser` nếu thường xuyên chạy script
3. **Luôn** kiểm tra nguồn gốc script trước khi chạy
4. **Nên** unblock file nếu download từ internet

---

## 🚀 Quick Fix (Copy và chạy)

```powershell
# Fix nhanh cho user hiện tại:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Sau đó chạy script:
.\restore_odoo.ps1 -BackupPath ".\backup_20241114_112749"
```

---

## 📞 Troubleshooting

### **Lỗi: "Access Denied"**
**Giải pháp:** Mở PowerShell với quyền Administrator

### **Lỗi: "Cannot change policy"**
**Giải pháp:** 
```powershell
# Thử với scope CurrentUser thay vì LocalMachine
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
```

### **Muốn reset về mặc định:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy Restricted -Scope CurrentUser
```


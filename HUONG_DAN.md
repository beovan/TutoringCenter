# 📚 Hướng Dẫn Cài Đặt & Chạy App

## Lần đầu tiên dùng (Option A — Chạy trên máy tính)

### Bước 1: Cài Python
- Tải tại: https://www.python.org/downloads/
- ⚠️ **QUAN TRỌNG**: Tick vào **"Add Python to PATH"** khi cài

### Bước 2: Chạy file cài đặt
Double-click vào file: **`CAI_DAT_VA_CHAY.bat`**

App sẽ tự động mở trong trình duyệt tại địa chỉ: http://localhost:8501

- Tài khoản mặc định lần đầu: **`admin`** / **`admin123`** *(hãy đổi mật khẩu trong Quản lý tài khoản)*

---

## Từ lần sau
- Mở app: Double-click **`CHAY_APP.bat`**
- Sao lưu nhanh ra `data/backups/` + Google Drive: Double-click **`SAO_LUU_DATA.bat`**

---

## Cấu trúc thư mục
```
TutoringCenter/
├── app.py                       ← App chính (Dashboard + Biểu đồ học phí)
├── pages/
│   ├── 1_Lop_Hoc.py             ← Quản lý lớp học
│   ├── 2_Hoc_Sinh.py            ← Quản lý học sinh + hồ sơ + tính cách
│   ├── 3_Lich_Hoc.py            ← Lịch học trong tuần + số tiết
│   ├── 4_Diem_Danh.py           ← Điểm danh hàng ngày + pivot tháng
│   ├── 5_Hoc_Phi.py             ← Học phí + biểu đồ cột
│   ├── 6_Bai_Tap_Kiem_Tra.py   ← Bài tập, kiểm tra, chấm điểm
│   ├── 7_Ghi_Chu.py             ← Ghi chú học sinh
│   ├── 8_Admin_Panel.py         ← Quản lý tài khoản giáo viên / Admin
│   └── 9_Sao_Luu_Data.py        ← Sao lưu Google Drive, xuất Excel/JSON, chuyển lên Neon
├── utils/
│   ├── database.py              ← Hỗ trợ song song SQLite (Option A) & Neon PostgreSQL (Option B)
│   ├── auth.py                  ← Đăng nhập, phân quyền Admin / Giáo viên
│   ├── backup.py                ← Sao lưu an toàn + đồng bộ Google Drive
│   └── helpers.py               ← Hàm tiện ích
├── data/
│   ├── tutoring.db              ← Database SQLite local (tự tạo khi chạy Option A)
│   └── backups/                 ← Các bản sao lưu tự động/thủ công
├── requirements.txt
├── CAI_DAT_VA_CHAY.bat          ← Cài đặt & chạy lần đầu
├── CHAY_APP.bat                 ← Chạy app từ lần sau
├── SAO_LUU_DATA.bat             ← Sao lưu nhanh (+ đồng bộ Google Drive)
└── DEPLOY_CLOUD.md              ← Hướng dẫn Option A (Google Drive) & Option B (Neon + Render)
```

---

## ☁️ Đưa lên Web miễn phí (Option B — Neon + Render)
Xem chi tiết từng bước trong file **[DEPLOY_CLOUD.md](DEPLOY_CLOUD.md)**.

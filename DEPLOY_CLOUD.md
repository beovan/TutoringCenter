# ☁️ Hướng Dẫn Sao Lưu Google Drive (Option A) & Deploy Neon Cloud (Option B)

App đã được thiết kế để hỗ trợ **cả 2 chế độ tự động**:
- **Không có `DATABASE_URL`** → Tự chạy **Option A (SQLite Local)** tại `data/tutoring.db`
- **Có `DATABASE_URL`** → Tự chuyển sang **Option B (Neon PostgreSQL Cloud)**, mọi máy đều dùng chung dữ liệu real-time!

---

## 💾 OPTION A — Chạy Local + Tự Sao Lưu Lên Google Drive (0đ mãi mãi)

Phù hợp khi chạy trên 1 máy tính trung tâm, không lo mất dữ liệu nếu hỏng ổ cứng.

### Bước 1 — Cài Google Drive trên máy tính
1. Tải **Google Drive for Desktop** từ [google.com/drive/download](https://www.google.com/drive/download/)
2. Đăng nhập tài khoản Google → Máy sẽ có thêm ổ `G:\My Drive` (hoặc thư mục `Google Drive`)

### Bước 2 — Bật đồng bộ trong App
1. Mở app → đăng nhập `admin` → vào **💾 Sao lưu & Cloud** trên thanh menu trái
2. Vào tab **☁️ Đồng bộ Google Drive (Option A)**
3. Bấm nút chọn thư mục Google Drive phát hiện sẵn (hoặc nhập `G:\My Drive\TutoringCenter_Backup`)
4. Tick **🔄 Tự sao lưu mỗi ngày khi mở app** → bấm **🚀 Lưu & Sao lưu ngay**

### Bước 3 — (Tùy chọn) Đặt lịch tự backup mỗi tuần bằng Windows Task Scheduler
1. Mở **Task Scheduler** (`Win + R` → gõ `taskschd.msc`)
2. Chọn **Create Basic Task...** → đặt tên `Backup TutoringCenter`
3. Chọn lịch **Weekly** (VD: Chủ nhật 21:00)
4. Action: **Start a program** → chọn file **`SAO_LUU_DATA.bat`** (kèm argument `--nopause` nếu muốn tự đóng)

> 💡 Mỗi lần chạy `SAO_LUU_DATA.bat`, app tự chụp an toàn file `.db` + xuất file `TutoringCenter_MoiNhat.xlsx` và copy vào Google Drive.

---

## ☁️ OPTION B — Neon.tech + Render.com / Streamlit Cloud (0đ mãi, Không lo Pause 7 ngày)

Khác với Supabase (tạm dừng project sau 7 ngày không hoạt động), **Neon.tech** cung cấp PostgreSQL **miễn phí vĩnh viễn** không bị pause xóa trạng thái!

### Bước 1 — Tạo Database miễn phí trên Neon.tech
1. Vào [neon.tech](https://neon.tech) → Đăng ký miễn phí (có thể đăng nhập bằng GitHub)
2. Tạo **New Project**:
   - Tên: `tutoring-center`
   - Region: `AWS Asia Pacific (Singapore)` (gần Việt Nam, nhanh nhất)
   - Postgres version: `16` (mặc định)
3. Sau khi tạo xong, bấm **Connect** → copy chuỗi **Connection string**:
   ```text
   postgresql://neondb_owner:npg_xxxxx@ep-xxxx-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require
   ```
4. **Không cần chạy SQL thủ công!** Khi app khởi động lần đầu với `DATABASE_URL`, `init_db()` tự tạo toàn bộ 9 bảng và tài khoản `admin` (`admin123`) trên Neon.

### Bước 2 — (Nếu đã có dữ liệu cũ ở máy) Chuẩn bị chuyển lên Neon
1. Ở app chạy trên máy (Option A), vào **💾 Sao lưu & Cloud** → bấm **🔄 Tải file JSON đầy đủ (.json)**
2. Giữ file `.json` này để nhập lên Neon ở Bước 4.

### Bước 3 — Push code lên GitHub & Deploy Web

#### Cách 3A: Deploy lên Render.com (khuyên dùng nếu muốn app bảo mật riêng tư)
1. Push code lên GitHub:
   ```cmd
   cd "d:\Video Youtube\TutoringCenter"
   git init
   git branch -M main
   git add .
   git commit -m "Ready for Option A + Option B (Neon)"
   git remote add origin https://github.com/YOUR_USERNAME/TutoringCenter.git
   git push -u origin main
   ```
2. Vào [render.com](https://render.com) → **New +** → **Web Service** → chọn repo GitHub
3. Điền cấu hình:
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true`
   - **Instance Type:** `Free`
4. Vào mục **Environment Variables** → thêm:
   - Key: `DATABASE_URL`
   - Value: *(dán Connection String của Neon ở Bước 1)*
5. Bấm **Create Web Service** → Chờ 3–5 phút sẽ có link `https://ten-app.onrender.com`

#### Cách 3B: Deploy lên Streamlit Community Cloud (rất nhanh)
1. Vào [share.streamlit.io](https://share.streamlit.io) → **Create app** → chọn repo GitHub, main file `app.py`
2. Bấm **Advanced settings... → Secrets** → dán:
   ```toml
   DATABASE_URL = "postgresql://neondb_owner:npg_xxxxx@ep-xxxx-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
   ```
3. Bấm **Deploy**!

### Bước 4 — Đưa dữ liệu từ máy lên Neon & đổi mật khẩu
1. Mở link web vừa deploy → đăng nhập `admin` / `admin123`
2. Vào **⚙️ Quản lý tài khoản → 🔑 Đổi mật khẩu** để đổi mật khẩu admin ngay!
3. Nếu có dữ liệu cũ từ Bước 2: vào **💾 Sao lưu & Cloud → tab Khôi phục / Chuyển lên Neon** → upload file `.json` → xác nhận nhập dữ liệu.

---

## 💡 Muốn chạy app trên máy tính nhưng kết nối thẳng Neon?
1. Copy file `.env.example` thành `.env`
2. Thay `DATABASE_URL=...` bằng chuỗi kết nối Neon của bạn
3. Mở app như bình thường bằng `CHAY_APP.bat` → Sidebar sẽ hiện **☁️ Neon Cloud**!
4. Muốn quay lại chạy offline trên máy? Chỉ cần xóa hoặc đổi tên file `.env`.

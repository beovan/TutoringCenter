"""
Trang Sao Lưu & Cloud – Option A (Local + Google Drive) & Option B (Neon PostgreSQL)
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime
import pandas as pd
import streamlit as st

from utils.auth import check_auth, is_admin, render_sidebar
from utils.backup import (
    BACKUP_DIR,
    create_backup,
    detect_cloud_folders,
    export_all_to_excel_bytes,
    export_all_to_json_bytes,
    import_from_json_bytes,
    list_local_backups,
    load_backup_config,
    restore_sqlite_bytes,
    save_backup_config,
)
from utils.database import DB_PATH, get_db_info, init_db, is_postgres

init_db()
st.set_page_config(page_title="Sao lưu & Cloud", page_icon="💾", layout="wide")

user = check_auth()
render_sidebar()

if not is_admin():
    st.error("⛔ Chỉ Admin mới được phép sao lưu / khôi phục toàn bộ dữ liệu!")
    st.stop()

st.title("💾 Sao Lưu & Đồng Bộ Dữ Liệu")

db_info = get_db_info()
if db_info["mode"] == "postgres":
    st.success(f"☁️ Đang kết nối **{db_info['provider']}** (`{db_info['target']}`) — dữ liệu tự động lưu online.")
else:
    st.info(f"💾 Đang chạy **Option A — SQLite Local** (`{db_info['target']}`)")

tab_backup, tab_gdrive, tab_restore = st.tabs([
    "📦 Sao lưu & Tải về",
    "☁️ Đồng bộ Google Drive (Option A)",
    "📥 Khôi phục / Chuyển lên Neon (Option B)",
])

# ─── TAB 1: SAO LƯU & TẢI VỀ ────────────────────────────────────────────────────
with tab_backup:
    st.subheader("📥 Tải bản sao lưu về máy")
    col1, col2, col3 = st.columns(3)

    with col1:
        try:
            excel_bytes = export_all_to_excel_bytes()
            st.download_button(
                "📊 Tải toàn bộ Excel (.xlsx)",
                data=excel_bytes,
                file_name=f"TrungTam_DayThem_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
            st.caption("Gồm tất cả sheet: Lớp, Học sinh, Điểm danh, Học phí, Điểm thi...")
        except ImportError:
            st.warning("⚠️ Chưa cài `openpyxl`. Chạy `pip install -r requirements.txt` để xuất Excel.")

    with col2:
        st.download_button(
            "🔄 Tải file JSON đầy đủ (.json)",
            data=export_all_to_json_bytes(),
            file_name=f"tutoring_backup_{datetime.now().strftime('%Y-%m-%d_%H%M')}.json",
            mime="application/json",
            use_container_width=True,
        )
        st.caption("Dùng để khôi phục hoặc chuyển dữ liệu từ SQLite lên Neon Cloud.")

    with col3:
        if not is_postgres() and os.path.exists(DB_PATH):
            with open(DB_PATH, "rb") as f:
                db_bytes = f.read()
            st.download_button(
                "🗄️ Tải file SQLite gốc (.db)",
                data=db_bytes,
                file_name=f"tutoring_{datetime.now().strftime('%Y-%m-%d')}.db",
                mime="application/octet-stream",
                use_container_width=True,
            )
            st.caption("Copy file này sang máy khác là dùng lại ngay.")
        else:
            st.info("☁️ Đang dùng Neon Cloud — hãy dùng file **JSON** hoặc **Excel**.")

    st.markdown("---")
    st.subheader("🗂️ Lịch sử sao lưu trong máy (`data/backups/`)")

    if st.button("⚡ Tạo bản sao lưu ngay bây giờ", type="primary"):
        res = create_backup(tag="manual", sync_to_cloud=True, also_excel=True)
        st.success(f"✅ Đã tạo {len(res['local_files'])} file sao lưu tại `data/backups/`!")
        if res["cloud_files"]:
            st.success(f"☁️ Đã đồng bộ sang thư mục Google Drive / OneDrive ({len(res['cloud_files'])} file).")
        elif res.get("cloud_error"):
            st.warning(f"⚠️ Không thể ghi vào thư mục đồng bộ: {res['cloud_error']}")

    backups = list_local_backups()
    if not backups:
        st.info(f"Chưa có bản sao lưu nào trong `{BACKUP_DIR}`.")
    else:
        df_bk = pd.DataFrame(backups)[["name", "size_kb", "modified_at"]]
        df_bk.columns = ["Tên file", "Dung lượng (KB)", "Thời gian tạo"]
        st.dataframe(df_bk, use_container_width=True, hide_index=True)

# ─── TAB 2: GOOGLE DRIVE SYNC (OPTION A) ────────────────────────────────────────
with tab_gdrive:
    st.subheader("☁️ Tự động sao lưu vào Google Drive / OneDrive trên máy")
    st.markdown(
        "Cài **Google Drive for Desktop** (hoặc dùng OneDrive có sẵn trên Windows), "
        "chọn thư mục nằm trong Drive → mỗi lần sao lưu, file sẽ tự động bay lên Google Drive của bạn."
    )

    cfg = load_backup_config()
    detected = detect_cloud_folders()

    if detected:
        st.markdown("**🔍 Đã tìm thấy thư mục đồng bộ trên máy:**")
        d_cols = st.columns(min(len(detected), 3))
        for idx, item in enumerate(detected):
            with d_cols[idx % 3]:
                if st.button(f"📁 Dùng {item['label']}", key=f"pick_cloud_{idx}", use_container_width=True):
                    cfg["cloud_sync_dir"] = item["suggested"]
                    save_backup_config(cfg)
                    st.success(f"✅ Đã chọn: `{item['suggested']}`")
                    st.rerun()
    else:
        st.warning("Chưa tự động phát hiện Google Drive / OneDrive. Bạn có thể tự nhập đường dẫn bên dưới.")

    with st.form("gdrive_config_form"):
        cloud_dir = st.text_input(
            "📂 Đường dẫn thư mục sao lưu (Google Drive / OneDrive / USB)",
            value=cfg.get("cloud_sync_dir", ""),
            placeholder=r"VD: G:\My Drive\TutoringCenter_Backup",
        )
        c1, c2, c3 = st.columns(3)
        auto_start = c1.checkbox(
            "🔄 Tự sao lưu mỗi ngày khi mở app",
            value=bool(cfg.get("auto_backup_on_start", True)),
        )
        keep_local = c2.number_input(
            "Giữ tối đa (bản local)", min_value=5, max_value=200,
            value=int(cfg.get("keep_local_count", 30)), step=5,
        )
        keep_cloud = c3.number_input(
            "Giữ tối đa (bản trên Drive)", min_value=5, max_value=200,
            value=int(cfg.get("keep_cloud_count", 30)), step=5,
        )

        col_save, col_run = st.columns(2)
        btn_save = col_save.form_submit_button("💾 Lưu cấu hình", use_container_width=True)
        btn_run  = col_run.form_submit_button("🚀 Lưu & Sao lưu ngay", type="primary", use_container_width=True)

    if btn_save or btn_run:
        cfg["cloud_sync_dir"] = cloud_dir.strip()
        cfg["auto_backup_on_start"] = auto_start
        cfg["keep_local_count"] = int(keep_local)
        cfg["keep_cloud_count"] = int(keep_cloud)
        save_backup_config(cfg)
        st.success("✅ Đã lưu cấu hình!")

        if btn_run:
            res = create_backup(tag="manual", sync_to_cloud=True, also_excel=True)
            if res["cloud_files"]:
                st.success(f"☁️ Đã sao lưu và đồng bộ {len(res['cloud_files'])} file sang `{cloud_dir}`!")
            elif res.get("cloud_error"):
                st.error(f"❌ Lỗi đồng bộ thư mục `{cloud_dir}`: {res['cloud_error']}")
            else:
                st.info("✅ Đã sao lưu vào máy (`data/backups/`). Nhập đường dẫn Drive nếu muốn đồng bộ thêm.")

    st.markdown("---")
    with st.expander("📖 Cách đặt lịch tự backup hàng tuần trên Windows (không cần mở app)"):
        st.markdown("""
        1. Nhấn **Win + R**, gõ `taskschd.msc` → Enter để mở **Task Scheduler**
        2. Chọn **Create Basic Task...** → Đặt tên `Backup Trung Tam Day Them`
        3. Trigger: chọn **Weekly** (Chủ nhật hàng tuần, VD: 21:00)
        4. Action: **Start a program** → Browse tới file `SAO_LUU_DATA.bat` trong thư mục dự án
        5. Hoàn tất! Mỗi tuần máy sẽ tự backup DB + Excel và đẩy vào Google Drive.
        """)

# ─── TAB 3: KHÔI PHỤC / CHUYỂN LÊN NEON ────────────────────────────────────────
with tab_restore:
    st.subheader("🔄 Khôi phục hoặc Di chuyển dữ liệu sang Neon Cloud")
    st.warning(
        "⚠️ **Lưu ý:** Thao tác này sẽ **ghi đè toàn bộ dữ liệu hiện tại** bằng dữ liệu từ file tải lên. "
        "Hãy tải 1 bản backup hiện tại trước khi thực hiện."
    )

    col_json, col_db = st.columns(2)

    with col_json:
        st.markdown("### 1️⃣ Khôi phục / Đẩy lên Neon bằng file `.json`")
        st.caption("Hoạt động cho cả **SQLite Local** và **Neon PostgreSQL**. Dùng khi chuyển dữ liệu từ máy lên Cloud.")
        up_json = st.file_uploader("Chọn file `.json` backup", type=["json"], key="up_json")
        confirm_json = st.checkbox("Tôi hiểu dữ liệu hiện tại sẽ bị thay thế", key="cf_json")
        if st.button("📥 Nhập dữ liệu JSON", type="primary", disabled=not (up_json and confirm_json)):
            try:
                counts = import_from_json_bytes(up_json.getvalue())
                total_rows = sum(counts.values())
                st.success(f"✅ Đã khôi phục thành công **{total_rows} dòng** dữ liệu!")
                st.json(counts)
                st.balloons()
            except Exception as exc:
                st.error(f"❌ Lỗi khôi phục JSON: {exc}")

    with col_db:
        st.markdown("### 2️⃣ Khôi phục trực tiếp file `.db` (chỉ SQLite Local)")
        st.caption("Dùng khi chuyển máy tính chạy Option A hoặc khôi phục từ Google Drive.")
        if is_postgres():
            st.info("☁️ App đang kết nối **Neon Cloud** nên chỉ hỗ trợ nhập bằng file **`.json`** ở cột bên trái.")
        else:
            up_db = st.file_uploader("Chọn file `.db` backup", type=["db"], key="up_db")
            confirm_db = st.checkbox("Tôi hiểu file tutoring.db hiện tại sẽ bị thay thế", key="cf_db")
            if st.button("🗄️ Khôi phục file .db", type="primary", disabled=not (up_db and confirm_db)):
                try:
                    safety = restore_sqlite_bytes(up_db.getvalue())
                    msg = "✅ Đã khôi phục database `.db` thành công!"
                    if safety:
                        msg += f" (Đã tự lưu bản cũ tại `{os.path.basename(safety)}`)"
                    st.success(msg)
                    st.balloons()
                except Exception as exc:
                    st.error(f"❌ Lỗi khôi phục file .db: {exc}")

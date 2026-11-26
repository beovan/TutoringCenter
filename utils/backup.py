"""
utils/backup.py – Sao lưu, đồng bộ Google Drive / OneDrive và khôi phục dữ liệu
Hỗ trợ:
  - Option A: SQLite local snapshot an toàn (sqlite3.backup) + copy vào thư mục Google Drive / OneDrive
  - Option B: Export / Import JSON & Excel để backup Neon Cloud hoặc đẩy dữ liệu từ máy lên Neon
Chạy độc lập: python utils/backup.py
"""
import io
import json
import os
import shutil
import sqlite3
import string
import sys
from datetime import datetime

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from utils import database as _db
from utils.database import (  # noqa: E402
    TABLE_EXPORT_ORDER,
    export_all_tables,
    get_db_info,
    init_db,
    is_postgres,
    replace_all_tables,
    reset_db_init_cache,
)

BACKUP_DIR = os.path.join(_db.DATA_DIR, "backups")
CONFIG_PATH = os.path.join(_db.DATA_DIR, "backup_config.json")

DEFAULT_CONFIG = {
    "cloud_sync_dir": "",
    "auto_backup_on_start": True,
    "keep_local_count": 30,
    "keep_cloud_count": 30,
    "last_auto_backup_date": "",
}

SHEET_NAMES = {
    "users": "Tai_Khoan",
    "classes": "Lop_Hoc",
    "students": "Hoc_Sinh",
    "schedules": "Lich_Hoc",
    "attendance": "Diem_Danh",
    "fees": "Hoc_Phi",
    "assignments": "Bai_Tap_Kiem_Tra",
    "assignment_results": "Ket_Qua_Diem",
    "student_notes": "Ghi_Chu",
}


def load_backup_config() -> dict:
    os.makedirs(_db.DATA_DIR, exist_ok=True)
    cfg = dict(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                cfg.update(loaded)
        except Exception:
            pass
    return cfg


def save_backup_config(cfg: dict):
    os.makedirs(_db.DATA_DIR, exist_ok=True)
    merged = dict(DEFAULT_CONFIG)
    merged.update(cfg)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)


def detect_cloud_folders() -> list[dict]:
    """Tự tìm thư mục Google Drive / OneDrive / Dropbox trên Windows."""
    found = []
    seen = set()

    def _add(label: str, base_path: str):
        norm = os.path.normpath(base_path)
        key = norm.lower()
        if os.path.isdir(norm) and key not in seen:
            seen.add(key)
            suggested = os.path.join(norm, "TutoringCenter_Backup")
            found.append({
                "label": label,
                "root": norm,
                "suggested": suggested,
            })

    home = os.path.expanduser("~")
    # Kiểm tra các ổ đĩa ảo Google Drive for Desktop (G:\My Drive, H:\Drive của tôi, ...)
    for letter in string.ascii_uppercase:
        if letter in ("A", "B", "C"):
            continue
        for sub in ("My Drive", "Drive của tôi"):
            _add(f"Google Drive ({letter}:\\{sub})", f"{letter}:\\{sub}")

    # Kiểm tra trong thư mục User
    for sub, label in [
        ("Google Drive", "Google Drive"),
        ("My Drive", "Google Drive (My Drive)"),
        ("OneDrive", "OneDrive"),
        ("Dropbox", "Dropbox"),
    ]:
        _add(label, os.path.join(home, sub))

    # Một số máy đặt Google Drive trực tiếp ở D:\ hoặc E:\
    for letter in ("D", "E", "F"):
        for sub in ("Google Drive", "OneDrive"):
            _add(f"{sub} ({letter}:\\)", f"{letter}:\\{sub}")

    return found


def _prune_old_files(folder: str, prefix: str, suffix: str, keep_count: int):
    if keep_count <= 0 or not os.path.isdir(folder):
        return
    files = []
    for name in os.listdir(folder):
        if name.startswith(prefix) and name.endswith(suffix):
            full = os.path.join(folder, name)
            if os.path.isfile(full):
                files.append((os.path.getmtime(full), full))
    files.sort(reverse=True)
    for _, old_path in files[keep_count:]:
        try:
            os.remove(old_path)
        except Exception:
            pass


def export_all_to_json_bytes() -> bytes:
    """Xuất toàn bộ dữ liệu tất cả bảng sang JSON (dùng được cho cả SQLite và Neon)."""
    init_db()
    tables = export_all_tables()
    payload = {
        "version": 2,
        "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "db_mode": get_db_info()["mode"],
        "tables": tables,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str).encode("utf-8")


def export_all_to_excel_bytes() -> bytes:
    """Xuất toàn bộ dữ liệu ra file Excel nhiều sheet (ẩn password_hash)."""
    import pandas as pd

    init_db()
    tables = export_all_tables()
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for table in TABLE_EXPORT_ORDER:
            rows = tables.get(table, [])
            if table == "users":
                rows = [{k: v for k, v in r.items() if k != "password_hash"} for r in rows]
            df = pd.DataFrame(rows)
            sheet = SHEET_NAMES.get(table, table)[:31]
            df.to_excel(writer, index=False, sheet_name=sheet)
    return buf.getvalue()


def import_from_json_bytes(raw_bytes: bytes) -> dict:
    """Khôi phục / di chuyển toàn bộ dữ liệu từ file JSON backup vào DB hiện tại."""
    payload = json.loads(raw_bytes.decode("utf-8"))
    if not isinstance(payload, dict) or "tables" not in payload or not isinstance(payload["tables"], dict):
        raise ValueError("File JSON không đúng định dạng backup của TutoringCenter!")

    tables = payload["tables"]
    if not any(k in tables for k in TABLE_EXPORT_ORDER):
        raise ValueError("File JSON không chứa bảng dữ liệu hợp lệ!")

    replace_all_tables(tables)
    return {t: len(tables.get(t, [])) for t in TABLE_EXPORT_ORDER}


def restore_sqlite_bytes(raw_bytes: bytes) -> str:
    """Khôi phục file .db vào SQLite local (có kiểm tra hợp lệ và tự backup bản cũ trước)."""
    if is_postgres():
        raise RuntimeError("Đang kết nối Neon PostgreSQL. Hãy dùng tính năng khôi phục bằng file .json.")
    if len(raw_bytes) < 100 or not raw_bytes.startswith(b"SQLite format 3\x00"):
        raise ValueError("File tải lên không phải file SQLite (.db) hợp lệ!")

    os.makedirs(_db.DATA_DIR, exist_ok=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)
    tmp_path = os.path.join(_db.DATA_DIR, "_restore_check.tmp")

    with open(tmp_path, "wb") as f:
        f.write(raw_bytes)

    try:
        test_conn = sqlite3.connect(tmp_path)
        check = test_conn.execute("PRAGMA integrity_check").fetchone()
        if not check or check[0] != "ok":
            raise ValueError("File SQLite bị lỗi toàn vẹn (corrupted).")
        tables = {
            r[0]
            for r in test_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        test_conn.close()
        if not {"classes", "students"}.issubset(tables):
            raise ValueError("File .db không đúng cấu trúc dữ liệu của ứng dụng.")

        # Backup bản hiện tại trước khi ghi đè
        safety_path = ""
        if os.path.exists(_db.DB_PATH):
            ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            safety_path = os.path.join(BACKUP_DIR, f"tutoring_{ts}_pre_restore.db")
            src = sqlite3.connect(_db.DB_PATH)
            dst = sqlite3.connect(safety_path)
            src.backup(dst)
            dst.close()
            src.close()

        os.replace(tmp_path, _db.DB_PATH)
        reset_db_init_cache()
        init_db(force=True)
        return safety_path
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def create_backup(tag: str = "manual", sync_to_cloud: bool = True, also_excel: bool = True) -> dict:
    """
    Tạo bản sao lưu vào data/backups/ và đồng bộ sang thư mục cloud (Google Drive / OneDrive) nếu có.
    Hoạt động tốt cho cả SQLite local lẫn Neon Cloud.
    """
    init_db()
    os.makedirs(BACKUP_DIR, exist_ok=True)
    cfg = load_backup_config()
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")

    result = {
        "ok": True,
        "mode": get_db_info()["mode"],
        "local_files": [],
        "cloud_files": [],
        "cloud_error": "",
    }

    if not is_postgres() and os.path.exists(_db.DB_PATH):
        db_backup_name = f"tutoring_{ts}_{tag}.db"
        local_db_path = os.path.join(BACKUP_DIR, db_backup_name)
        src = sqlite3.connect(_db.DB_PATH)
        dst = sqlite3.connect(local_db_path)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()
        result["local_files"].append(local_db_path)
        _prune_old_files(BACKUP_DIR, "tutoring_", ".db", int(cfg.get("keep_local_count", 30)))

    # Luôn lưu thêm bản JSON nếu đang dùng Neon Cloud (hoặc khi backup thủ công / scheduled)
    if is_postgres() or tag != "auto":
        json_name = f"tutoring_{ts}_{tag}.json"
        local_json_path = os.path.join(BACKUP_DIR, json_name)
        with open(local_json_path, "wb") as f:
            f.write(export_all_to_json_bytes())
        result["local_files"].append(local_json_path)
        _prune_old_files(BACKUP_DIR, "tutoring_", ".json", int(cfg.get("keep_local_count", 30)))

    excel_bytes = None
    if also_excel:
        try:
            excel_bytes = export_all_to_excel_bytes()
            local_xlsx_path = os.path.join(BACKUP_DIR, "TutoringCenter_MoiNhat.xlsx")
            with open(local_xlsx_path, "wb") as f:
                f.write(excel_bytes)
            result["local_files"].append(local_xlsx_path)
        except Exception as exc:
            result["excel_error"] = str(exc)

    cloud_dir = (cfg.get("cloud_sync_dir") or "").strip()
    if sync_to_cloud and cloud_dir:
        try:
            os.makedirs(cloud_dir, exist_ok=True)
            for src_path in result["local_files"]:
                dest_path = os.path.join(cloud_dir, os.path.basename(src_path))
                shutil.copy2(src_path, dest_path)
                result["cloud_files"].append(dest_path)
            keep_cloud = int(cfg.get("keep_cloud_count", 30))
            _prune_old_files(cloud_dir, "tutoring_", ".db", keep_cloud)
            _prune_old_files(cloud_dir, "tutoring_", ".json", keep_cloud)
        except Exception as exc:
            result["cloud_error"] = str(exc)

    return result


def auto_backup_if_needed():
    """Tự động backup mỗi ngày 1 lần khi mở app (chỉ chạy ở SQLite local)."""
    if is_postgres() or not os.path.exists(_db.DB_PATH):
        return
    try:
        cfg = load_backup_config()
        if not cfg.get("auto_backup_on_start", True):
            return
        today = datetime.now().strftime("%Y-%m-%d")
        if cfg.get("last_auto_backup_date") == today:
            return
        create_backup(tag="auto", sync_to_cloud=True, also_excel=False)
        cfg["last_auto_backup_date"] = today
        save_backup_config(cfg)
    except Exception:
        # Không làm gián đoạn quá trình mở app nếu ổ đồng bộ tạm thời không khả dụng
        pass


def list_local_backups() -> list[dict]:
    if not os.path.isdir(BACKUP_DIR):
        return []
    items = []
    for name in os.listdir(BACKUP_DIR):
        if not (name.endswith(".db") or name.endswith(".json") or name.endswith(".xlsx")):
            continue
        full = os.path.join(BACKUP_DIR, name)
        if not os.path.isfile(full):
            continue
        stat = os.stat(full)
        items.append({
            "name": name,
            "path": full,
            "size_kb": round(stat.st_size / 1024, 1),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        })
    items.sort(key=lambda x: x["modified_at"], reverse=True)
    return items


if __name__ == "__main__":
    tag_arg = "scheduled"
    if len(sys.argv) > 1 and sys.argv[1].strip():
        tag_arg = sys.argv[1].strip()

    info = get_db_info()
    print(f"[INFO] Che do DB: {info['provider']} ({info['target']})")
    res = create_backup(tag=tag_arg, sync_to_cloud=True, also_excel=True)
    print("[OK] Da luu cac file local:")
    for p in res["local_files"]:
        print(f"  - {p}")
    if res["cloud_files"]:
        print("[OK] Da dong bo sang thu muc Cloud:")
        for p in res["cloud_files"]:
            print(f"  - {p}")
    elif res.get("cloud_error"):
        print(f"[CANH BAO] Chua dong bo duoc Cloud: {res['cloud_error']}")
    else:
        print("[GOI Y] Chua chon thu muc Google Drive/OneDrive. Mo app -> Sao luu & Cloud de cau hinh.")

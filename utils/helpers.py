"""
Các hàm tiện ích dùng chung
"""
import pandas as pd
import io
from datetime import datetime

DAYS_VI = {
    "Monday": "Thứ 2",
    "Tuesday": "Thứ 3",
    "Wednesday": "Thứ 4",
    "Thursday": "Thứ 5",
    "Friday": "Thứ 6",
    "Saturday": "Thứ 7",
    "Sunday": "Chủ nhật",
}

DAYS_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

STATUS_LABEL = {
    "present": "✅ Có mặt",
    "absent":  "❌ Vắng",
    "late":    "⏰ Trễ",
    "excuse":  "📋 Có phép",
}

FEE_STATUS_LABEL = {
    "paid":    "✅ Đã đóng",
    "partial": "⚠️ Đóng thiếu",
    "unpaid":  "❌ Chưa đóng",
}

ASSIGNMENT_TYPE_LABEL = {
    "homework": "📝 Bài tập",
    "test":     "📄 Kiểm tra",
    "exam":     "🎓 Thi",
}

GRADES = ["Lớp 6", "Lớp 7", "Lớp 8", "Lớp 9", "Lớp 10", "Lớp 11", "Lớp 12"]

SUBJECTS = [
    "Toán", "Ngữ Văn", "Tiếng Anh", "Vật Lý", "Hóa Học",
    "Sinh Học", "Lịch Sử", "Địa Lý", "GDCD", "Tin Học", "Khác"
]

MONTHS_VI = [
    "", "Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4",
    "Tháng 5", "Tháng 6", "Tháng 7", "Tháng 8",
    "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12"
]


def fmt_currency(value):
    if value is None:
        return "0 ₫"
    return f"{value:,.0f} ₫"


def fmt_date(date_str):
    if not date_str:
        return ""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        return date_str


def fmt_datetime(dt_str):
    if not dt_str:
        return ""
    try:
        return datetime.strptime(dt_str[:19], "%Y-%m-%dT%H:%M:%S").strftime("%d/%m/%Y %H:%M")
    except Exception:
        return dt_str


def to_excel(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Data")
    return buf.getvalue()


def classes_to_options(classes):
    """Trả về dict {display_name: id} cho selectbox"""
    return {f"{c['name']} ({c['subject']})": c["id"] for c in classes}

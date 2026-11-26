"""
app.py – Dashboard chính (Phase 2 – có auth)
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

from utils.database import init_db, get_dashboard_stats, get_fee_summary_by_month, get_all_classes
from utils.auth import check_auth, render_sidebar, is_admin, get_teacher_id
from utils.helpers import fmt_currency, MONTHS_VI

# ── Cấu hình trang ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="📚 Trung Tâm Dạy Thêm",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ─────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1A1A2E 0%, #16213E 100%);
}
[data-testid="stSidebar"] * { color: #E0E0E0 !important; }

div[data-testid="metric-container"] {
    background: white;
    border: 1px solid #E8ECF4;
    border-radius: 12px;
    padding: 16px;
    box-shadow: 0 2px 8px rgba(79,142,247,0.08);
}
div[data-testid="metric-container"] label { color: #666 !important; font-size: 13px; }
div[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-size: 28px !important; font-weight: 700; color: #1A1A2E !important;
}
h1 { color: #1A1A2E; font-weight: 800; }
h2 { color: #2D3561; font-weight: 700; }
h3 { color: #4F8EF7; }
.stButton > button { border-radius: 8px; font-weight: 600; transition: all 0.2s; }
.stButton > button:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(79,142,247,0.3); }
</style>
""", unsafe_allow_html=True)

# ── Auth + DB ────────────────────────────────────────────────────────────────────
init_db()
user = check_auth()
render_sidebar()

teacher_id = get_teacher_id()   # None = admin
now = datetime.now()

# ── Header ───────────────────────────────────────────────────────────────────────
col_title, col_badge = st.columns([4, 1])
col_title.title("🏠 Tổng Quan Trung Tâm")
role_color = "#FF6B6B" if is_admin() else "#4F8EF7"
role_text  = "🔑 Admin" if is_admin() else "👩‍🏫 Giáo viên"
col_badge.markdown(f"""
<div style="background:{role_color};color:white;border-radius:20px;padding:6px 16px;
     text-align:center;font-weight:700;margin-top:12px">{role_text}</div>
""", unsafe_allow_html=True)

# ── Metrics ───────────────────────────────────────────────────────────────────────
stats = get_dashboard_stats(teacher_id=teacher_id)
cols = st.columns(5 if is_admin() else 4)
cols[0].metric("👨‍🎓 Học sinh", stats["total_students"])
cols[1].metric("📖 Số lớp", stats["total_classes"])
if is_admin():
    cols[2].metric("👩‍🏫 Giáo viên", stats["total_teachers"])
    cols[3].metric(f"💰 Đã thu T{stats['month']}", fmt_currency(stats["month_paid"]))
    cols[4].metric("⚠️ Còn nợ", fmt_currency(stats["month_debt"]),
                   delta=f"-{fmt_currency(stats['month_debt'])}" if stats["month_debt"] > 0 else None,
                   delta_color="inverse")
else:
    cols[2].metric(f"💰 Đã thu T{stats['month']}", fmt_currency(stats["month_paid"]))
    cols[3].metric("⚠️ Còn nợ", fmt_currency(stats["month_debt"]),
                   delta=f"-{fmt_currency(stats['month_debt'])}" if stats["month_debt"] > 0 else None,
                   delta_color="inverse")

st.markdown("---")

# ── Biểu đồ học phí ─────────────────────────────────────────────────────────────
st.subheader("📊 Thống Kê Học Phí Theo Tháng")
year_sel = st.selectbox("Năm", list(range(now.year, now.year - 4, -1)),
                        key="dash_year", label_visibility="collapsed")
fee_data = get_fee_summary_by_month(year_sel, teacher_id=teacher_id)

if fee_data:
    df_fee = pd.DataFrame(fee_data)
    df_fee["month_label"] = df_fee["month"].apply(lambda m: MONTHS_VI[m])
    fig = go.Figure()
    fig.add_trace(go.Bar(name="✅ Đã thu", x=df_fee["month_label"], y=df_fee["total_paid"],
                          marker_color="#4CAF50",
                          text=df_fee["total_paid"].apply(lambda v: f"{v/1e6:.1f}M"),
                          textposition="auto"))
    fig.add_trace(go.Bar(name="❌ Còn nợ", x=df_fee["month_label"], y=df_fee["total_debt"],
                          marker_color="#F44336",
                          text=df_fee["total_debt"].apply(lambda v: f"{v/1e6:.1f}M"),
                          textposition="auto"))
    fig.update_layout(barmode="group", plot_bgcolor="white", paper_bgcolor="white",
                      height=380,
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                      yaxis=dict(tickformat=",.0f", title="VNĐ"),
                      margin=dict(t=40, b=40, l=60, r=20))
    st.plotly_chart(fig, use_container_width=True)
    df_show = df_fee[["month_label","student_count","total_amount","total_paid","total_debt"]].copy()
    df_show.columns = ["Tháng","Số HS","Tổng học phí","Đã thu","Còn nợ"]
    for c in ["Tổng học phí","Đã thu","Còn nợ"]:
        df_show[c] = df_show[c].apply(fmt_currency)
    st.dataframe(df_show, use_container_width=True, hide_index=True)
else:
    st.info("📌 Chưa có dữ liệu học phí. Vào **Học phí** để nhập liệu.")

# ── Danh sách lớp ────────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("📖 Danh Sách Lớp Hiện Tại")
classes = get_all_classes(teacher_id=teacher_id)
if classes:
    df_cls = pd.DataFrame(classes)
    show_cols = ["name", "subject", "grade", "teacher_name", "student_count", "tuition_fee"]
    labels    = ["Tên lớp", "Môn", "Khối", "Giáo viên", "Học sinh", "Học phí/tháng"]
    if not is_admin():
        show_cols.remove("teacher_name")
        labels.remove("Giáo viên")
    df_show = df_cls[show_cols].copy()
    df_show.columns = labels
    if "Học phí/tháng" in df_show.columns:
        df_show["Học phí/tháng"] = df_show["Học phí/tháng"].apply(fmt_currency)
    st.dataframe(df_show, use_container_width=True, hide_index=True)
else:
    st.info("📌 Chưa có lớp nào.")

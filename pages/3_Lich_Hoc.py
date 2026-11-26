"""Lịch học – Phase 2"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import streamlit as st
import pandas as pd
from utils.database import init_db, get_all_classes, get_schedules, add_schedule, delete_schedule
from utils.auth import check_auth, render_sidebar, get_teacher_id
from utils.helpers import DAYS_VI, DAYS_ORDER

init_db()
st.set_page_config(page_title="Lịch học", page_icon="📅", layout="wide")
user = check_auth(); render_sidebar()
teacher_id = get_teacher_id()

st.title("📅 Quản Lý Lịch Học Trong Tuần")
classes = get_all_classes(teacher_id=teacher_id)
if not classes:
    st.warning("⚠️ Chưa có lớp."); st.stop()

cls_opts = {f"{c['name']} ({c['subject']})": c["id"] for c in classes}
sel_cls  = st.selectbox("📖 Chọn lớp", list(cls_opts.keys()))
cid      = cls_opts[sel_cls]
schedules = get_schedules(cid)

st.subheader("🗓️ Lịch học hiện tại")
if schedules:
    df = pd.DataFrame(schedules)
    df["Thứ"]   = df["day_of_week"].map(DAYS_VI)
    df["Tiết"]  = df.apply(lambda r: f"{r['start_time']} – {r['end_time']} ({r['lessons_per_session']} tiết)", axis=1)
    df["Phòng"] = df["room"].fillna("—")
    day_order = {v: i for i, v in enumerate(DAYS_VI.values())}
    df_show = df[["Thứ","Tiết","Phòng"]].sort_values("Thứ", key=lambda s: s.map(day_order))
    st.dataframe(df_show, use_container_width=True, hide_index=True)
    total = sum(s["lessons_per_session"] for s in schedules)
    st.metric("📊 Tổng số tiết / tuần", f"{total} tiết")
    st.markdown("---")
    st.subheader("🗑️ Xóa buổi học")
    sched_opts = {f"{DAYS_VI[s['day_of_week']]} | {s['start_time']}–{s['end_time']}": s["id"] for s in schedules}
    sel_del = st.selectbox("Chọn buổi xóa", list(sched_opts.keys()))
    if st.button("🗑️ Xóa", type="secondary"):
        delete_schedule(sched_opts[sel_del]); st.success("✅ Đã xóa!"); st.rerun()
else:
    st.info("Chưa có lịch học.")

st.markdown("---")
st.subheader("➕ Thêm buổi học mới")
with st.form("add_schedule_form", clear_on_submit=True):
    c1, c2, c3 = st.columns(3)
    day     = c1.selectbox("Thứ", DAYS_ORDER, format_func=lambda d: DAYS_VI[d])
    start   = c2.time_input("Giờ bắt đầu")
    end     = c3.time_input("Giờ kết thúc")
    c4, c5  = st.columns(2)
    lessons = c4.number_input("Số tiết / buổi", min_value=1, max_value=10, value=2, step=1)
    room    = c5.text_input("Phòng học", placeholder="Phòng 101")
    submitted = st.form_submit_button("➕ Thêm lịch", type="primary", use_container_width=True)

if submitted:
    if str(start) >= str(end):
        st.error("⚠️ Giờ bắt đầu phải trước giờ kết thúc!")
    else:
        add_schedule(cid, day, str(start)[:5], str(end)[:5], lessons, room)
        st.success(f"✅ Đã thêm: {DAYS_VI[day]} | {str(start)[:5]}–{str(end)[:5]} | {lessons} tiết")
        st.rerun()

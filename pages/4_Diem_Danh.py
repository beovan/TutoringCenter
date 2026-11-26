"""Điểm danh – Phase 2"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import streamlit as st
import pandas as pd
from datetime import date, datetime
from utils.database import (
    init_db, get_all_classes, get_all_students,
    get_attendance, save_attendance, get_attendance_by_month
)
from utils.auth import check_auth, render_sidebar, get_teacher_id
from utils.helpers import STATUS_LABEL, MONTHS_VI

init_db()
st.set_page_config(page_title="Điểm danh", page_icon="✅", layout="wide")
user = check_auth(); render_sidebar()
teacher_id = get_teacher_id()

st.title("✅ Điểm Danh Học Sinh")
classes = get_all_classes(teacher_id=teacher_id)
if not classes:
    st.warning("⚠️ Chưa có lớp."); st.stop()

cls_opts = {f"{c['name']} ({c['subject']})": c["id"] for c in classes}
tab_today, tab_history = st.tabs(["📋 Điểm danh hôm nay", "📊 Lịch sử theo tháng"])

with tab_today:
    c1, c2 = st.columns([2,1])
    sel_cls  = c1.selectbox("📖 Lớp", list(cls_opts.keys()), key="att_cls")
    att_date = c2.date_input("📅 Ngày", value=date.today(), key="att_date")
    cid = cls_opts[sel_cls]
    students = get_all_students(class_id=cid)
    if not students:
        st.info("Lớp này chưa có học sinh.")
    else:
        existing = {a["student_id"]: a for a in get_attendance(cid, str(att_date))}
        st.markdown(f"**{sel_cls}** | {att_date.strftime('%d/%m/%Y')} | Sĩ số: **{len(students)}**")
        st.markdown("---")
        with st.form("attendance_form"):
            rows_data = []
            for stu in students:
                sid  = stu["id"]
                prev = existing.get(sid, {})
                col_name, col_status, col_note = st.columns([3,2,3])
                col_name.markdown(f"**{stu['full_name']}**")
                status = col_status.radio(
                    f"s_{sid}", list(STATUS_LABEL.keys()),
                    format_func=lambda x: STATUS_LABEL[x],
                    index=list(STATUS_LABEL.keys()).index(prev.get("status","present")),
                    horizontal=True, label_visibility="collapsed", key=f"att_s_{sid}")
                note = col_note.text_input(f"n_{sid}", value=prev.get("note",""),
                                            placeholder="Ghi chú", label_visibility="collapsed",
                                            key=f"att_n_{sid}")
                rows_data.append((sid, status, note))
            st.markdown("---")
            submitted = st.form_submit_button("💾 Lưu điểm danh", type="primary", use_container_width=True)
        if submitted:
            for sid, status, note in rows_data:
                save_attendance(sid, cid, str(att_date), status, note)
            counts = {}
            for _, s, _ in rows_data: counts[s] = counts.get(s,0)+1
            st.success("✅ Đã lưu! " + " | ".join(f"{STATUS_LABEL[k]}: **{v}**" for k,v in counts.items()))
            st.rerun()

with tab_history:
    c1, c2, c3 = st.columns(3)
    sel_cls2  = c1.selectbox("📖 Lớp", list(cls_opts.keys()), key="att_hist_cls")
    cid2      = cls_opts[sel_cls2]
    now       = datetime.now()
    sel_month = c2.selectbox("Tháng", range(1,13), index=now.month-1,
                              format_func=lambda m: MONTHS_VI[m])
    sel_year  = c3.selectbox("Năm", list(range(now.year, now.year-4, -1)))
    hist = get_attendance_by_month(cid2, sel_month, sel_year)
    if not hist:
        st.info("Không có dữ liệu.")
    else:
        df_hist = pd.DataFrame(hist)
        df_hist["Ngày"]     = pd.to_datetime(df_hist["date"]).dt.strftime("%d/%m")
        df_hist["Trạng thái"] = df_hist["status"].map(STATUS_LABEL)
        df_show = df_hist[["full_name","Ngày","Trạng thái","note"]].copy()
        df_show.columns = ["Học sinh","Ngày","Trạng thái","Ghi chú"]
        st.dataframe(df_show, use_container_width=True, hide_index=True)
        st.markdown("---")
        st.subheader("📊 Bảng tổng hợp")
        pivot = df_hist.pivot_table(index="full_name", columns="Ngày",
                                     values="status", aggfunc="first").fillna("—")
        pivot = pivot.replace({"present":"✅","absent":"❌","late":"⏰","excuse":"📋"})
        st.dataframe(pivot, use_container_width=True)
        absent = df_hist[df_hist["status"]=="absent"].groupby("full_name").size().reset_index()
        absent.columns = ["Học sinh","Số buổi vắng"]
        if not absent.empty:
            st.markdown("---"); st.subheader("⚠️ Học sinh vắng nhiều")
            st.dataframe(absent.sort_values("Số buổi vắng", ascending=False),
                         use_container_width=True, hide_index=True)
        st.download_button("📥 Xuất CSV",
                           data=df_show.to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"diem_danh_{sel_month}_{sel_year}.csv", mime="text/csv")

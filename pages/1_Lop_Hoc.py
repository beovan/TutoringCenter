"""
Trang quản lý lớp học – Phase 2 (auth + teacher filter)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
from utils.database import (
    init_db, get_all_classes, get_class, add_class, update_class, delete_class,
    get_teacher_options
)
from utils.auth import check_auth, render_sidebar, is_admin, get_teacher_id
from utils.helpers import GRADES, SUBJECTS, fmt_currency

init_db()
st.set_page_config(page_title="Lớp học", page_icon="📖", layout="wide")
user = check_auth()
render_sidebar()
teacher_id = get_teacher_id()

st.title("📖 Quản Lý Lớp Học")

tab_list, tab_add = st.tabs(["📋 Danh sách lớp", "➕ Thêm lớp mới"])

with tab_list:
    classes = get_all_classes(teacher_id=teacher_id)
    if not classes:
        st.info("Chưa có lớp. Chuyển sang tab **Thêm lớp mới**.")
    else:
        df = pd.DataFrame(classes)
        show = ["name","subject","grade","teacher_name","student_count","tuition_fee","note"]
        labs = ["Tên lớp","Môn","Khối","Giáo viên","Học sinh","Học phí/tháng","Ghi chú"]
        if not is_admin():
            show.remove("teacher_name"); labs.remove("Giáo viên")
        df_show = df[show].copy(); df_show.columns = labs
        df_show["Học phí/tháng"] = df_show["Học phí/tháng"].apply(fmt_currency)
        st.dataframe(df_show, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("✏️ Sửa / Xóa lớp")
        cls_names = {f"{c['name']} ({c['subject']})": c["id"] for c in classes}
        sel = st.selectbox("Chọn lớp", list(cls_names.keys()))
        if sel:
            cid = cls_names[sel]
            cls = get_class(cid)
            teachers = get_teacher_options()
            t_opts = {t["full_name"]: t["id"] for t in teachers}

            with st.form("edit_class_form"):
                c1, c2 = st.columns(2)
                name    = c1.text_input("Tên lớp *", cls["name"])
                subject = c2.selectbox("Môn *", SUBJECTS,
                                       index=SUBJECTS.index(cls["subject"]) if cls["subject"] in SUBJECTS else 0)
                grade   = c1.selectbox("Khối *", GRADES,
                                       index=GRADES.index(cls["grade"]) if cls["grade"] in GRADES else 0)
                fee     = c2.number_input("Học phí/tháng (₫)", value=float(cls["tuition_fee"]),
                                          min_value=0.0, step=100000.0, format="%.0f")
                if is_admin():
                    cur_tid = cls.get("teacher_id")
                    cur_tname = next((t["full_name"] for t in teachers if t["id"]==cur_tid), list(t_opts.keys())[0] if t_opts else None)
                    sel_teacher = st.selectbox("Giáo viên phụ trách", list(t_opts.keys()),
                                               index=list(t_opts.keys()).index(cur_tname) if cur_tname in t_opts else 0)
                note = st.text_area("Ghi chú", cls["note"] or "")
                col_s, col_d = st.columns(2)
                save = col_s.form_submit_button("💾 Lưu", type="primary", use_container_width=True)
                dele = col_d.form_submit_button("🗑️ Xóa lớp", use_container_width=True)

            if save:
                tid = t_opts[sel_teacher] if is_admin() else teacher_id
                update_class(cid, name.strip(), subject, grade, fee, tid, note)
                st.success(f"✅ Đã cập nhật lớp **{name}**")
                st.rerun()
            if dele:
                delete_class(cid)
                st.success(f"✅ Đã xóa lớp **{cls['name']}**")
                st.rerun()

with tab_add:
    teachers = get_teacher_options()
    t_opts = {t["full_name"]: t["id"] for t in teachers}

    with st.form("add_class_form", clear_on_submit=True):
        st.subheader("Thông tin lớp mới")
        c1, c2 = st.columns(2)
        name    = c1.text_input("Tên lớp *", placeholder="Toán 9A")
        subject = c2.selectbox("Môn *", SUBJECTS)
        grade   = c1.selectbox("Khối *", GRADES)
        fee     = c2.number_input("Học phí/tháng (₫)", min_value=0.0, value=500000.0,
                                   step=100000.0, format="%.0f")
        if is_admin() and t_opts:
            sel_teacher = st.selectbox("Giáo viên phụ trách", list(t_opts.keys()))
        note = st.text_area("Ghi chú")
        submitted = st.form_submit_button("➕ Tạo lớp", type="primary", use_container_width=True)

    if submitted:
        if not name.strip():
            st.error("⚠️ Nhập tên lớp!")
        else:
            tid = t_opts.get(sel_teacher) if (is_admin() and t_opts) else teacher_id
            add_class(name.strip(), subject, grade, fee, tid, note)
            st.success(f"✅ Đã tạo lớp **{name}**!")
            st.balloons()
            st.rerun()

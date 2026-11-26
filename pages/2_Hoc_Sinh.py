"""
Trang quản lý học sinh – Phase 2
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
from datetime import date
import plotly.graph_objects as go
from utils.database import (
    init_db, get_all_classes, get_all_students, get_student,
    add_student, update_student, delete_student,
    get_attendance_summary, get_notes, add_note, delete_note, get_fees
)
from utils.auth import check_auth, render_sidebar, is_admin, get_teacher_id
from utils.helpers import GRADES, fmt_currency, fmt_date, FEE_STATUS_LABEL

init_db()
st.set_page_config(page_title="Học sinh", page_icon="👨‍🎓", layout="wide")
user = check_auth()
render_sidebar()
teacher_id = get_teacher_id()

st.title("👨‍🎓 Quản Lý Học Sinh")

classes = get_all_classes(teacher_id=teacher_id)
cls_opts = {"-- Tất cả lớp --": None}
cls_opts.update({f"{c['name']} ({c['subject']})": c["id"] for c in classes})

tab_list, tab_add, tab_profile = st.tabs(["📋 Danh sách", "➕ Thêm học sinh", "🧑 Hồ sơ chi tiết"])

with tab_list:
    col_f1, col_f2 = st.columns([2, 1])
    sel_cls  = col_f1.selectbox("Lọc theo lớp", list(cls_opts.keys()), key="filter_cls")
    sel_stat = col_f2.selectbox("Trạng thái", ["Đang học", "Đã nghỉ"], key="filter_stat")
    cid      = cls_opts[sel_cls]
    status   = "active" if sel_stat == "Đang học" else "inactive"
    students = get_all_students(class_id=cid, status=status, teacher_id=teacher_id)

    if not students:
        st.info("Chưa có học sinh. Chuyển sang tab **Thêm học sinh**.")
    else:
        df = pd.DataFrame(students)
        df_show = df[["full_name","gender","grade","school","phone","parent_phone","class_name"]].copy()
        df_show.columns = ["Họ tên","GT","Khối","Trường","SĐT HS","SĐT PH","Lớp"]
        st.dataframe(df_show, use_container_width=True, hide_index=True)
        st.download_button("📥 Xuất CSV",
                           data=df_show.to_csv(index=False).encode("utf-8-sig"),
                           file_name="hoc_sinh.csv", mime="text/csv")

with tab_add:
    cls_add_opts = {f"{c['name']} ({c['subject']})": c["id"] for c in classes}
    with st.form("add_student_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        full_name    = c1.text_input("Họ và tên *", placeholder="Nguyễn Văn A")
        dob          = c2.date_input("Ngày sinh", value=date(2010, 1, 1),
                                      min_value=date(1990,1,1), max_value=date.today())
        gender       = c1.radio("Giới tính", ["Nam","Nữ"], horizontal=True)
        grade        = c2.selectbox("Khối *", GRADES)
        school       = c1.text_input("Trường đang học")
        class_sel    = c2.selectbox("Lớp học thêm *",
                                     list(cls_add_opts.keys()) if cls_add_opts else ["(Chưa có lớp)"])
        phone        = c1.text_input("SĐT học sinh")
        parent_name  = c2.text_input("Tên phụ huynh")
        parent_phone = c1.text_input("SĐT phụ huynh")
        address      = c2.text_input("Địa chỉ")
        personality  = st.text_area("🌟 Tính cách nổi trội / Ghi chú",
                                     placeholder="VD: Nhanh hiểu bài, hay mất tập trung...")
        submitted = st.form_submit_button("➕ Thêm học sinh", type="primary", use_container_width=True)

    if submitted:
        if not full_name.strip():
            st.error("⚠️ Nhập họ tên!")
        elif not cls_add_opts:
            st.error("⚠️ Tạo lớp trước!")
        else:
            add_student(full_name.strip(), str(dob), gender, grade, school,
                        phone, parent_name, parent_phone, address, personality,
                        cls_add_opts[class_sel])
            st.success(f"✅ Đã thêm **{full_name}**!")
            st.balloons(); st.rerun()

with tab_profile:
    all_students = get_all_students(teacher_id=teacher_id)
    if not all_students:
        st.info("Chưa có học sinh.")
    else:
        stu_opts = {f"{s['full_name']} – {s['class_name'] or 'Chưa xếp lớp'}": s["id"] for s in all_students}
        sel_stu  = st.selectbox("Chọn học sinh", list(stu_opts.keys()), key="profile_sel")
        sid = stu_opts[sel_stu]
        stu = get_student(sid)

        col_info, col_stats = st.columns([2, 1])
        with col_info:
            st.subheader(f"🧑 {stu['full_name']}")
            for label, val in [
                ("📅 Ngày sinh",   fmt_date(stu["dob"])),
                ("⚧ Giới tính",   stu["gender"]),
                ("📚 Khối",        stu["grade"]),
                ("🏫 Trường",      stu["school"] or "—"),
                ("📱 SĐT HS",      stu["phone"] or "—"),
                ("👨‍👩‍👧 Phụ huynh", f"{stu['parent_name']} – {stu['parent_phone']}" if stu["parent_name"] else "—"),
                ("🏠 Địa chỉ",    stu["address"] or "—"),
                ("📖 Lớp",         stu["class_name"] or "Chưa xếp lớp"),
                ("💰 Học phí",     fmt_currency(stu["tuition_fee"])),
            ]:
                st.markdown(f"**{label}:** {val}")
            if stu["personality"]:
                st.markdown("---")
                st.markdown("**🌟 Tính cách:**")
                st.info(stu["personality"])

        with col_stats:
            att = get_attendance_summary(sid)
            total_att = sum(att.values())
            st.subheader("📊 Điểm danh")
            if total_att:
                fig = go.Figure(go.Pie(
                    labels=["Có mặt","Vắng","Trễ","Có phép"],
                    values=[att.get("present",0), att.get("absent",0),
                            att.get("late",0), att.get("excuse",0)],
                    marker_colors=["#4CAF50","#F44336","#FF9800","#2196F3"], hole=0.5,
                ))
                fig.update_layout(height=250, margin=dict(t=20,b=0,l=0,r=0),
                                  legend=dict(orientation="h"))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Chưa có dữ liệu điểm danh")
            fees = get_fees(student_id=sid)
            if fees:
                lf = fees[0]
                st.markdown(f"**Học phí T{lf['month']}/{lf['year']}:** {FEE_STATUS_LABEL.get(lf['status'],lf['status'])}")

        st.markdown("---")
        with st.expander("✏️ Chỉnh sửa thông tin"):
            with st.form("edit_student_form"):
                c1, c2 = st.columns(2)
                u_name  = c1.text_input("Họ tên *", stu["full_name"])
                u_dob   = c2.date_input("Ngày sinh",
                                         value=pd.to_datetime(stu["dob"]).date() if stu["dob"] else date(2010,1,1))
                u_gender= c1.radio("Giới tính",["Nam","Nữ"], index=0 if stu["gender"]=="Nam" else 1, horizontal=True)
                u_grade = c2.selectbox("Khối", GRADES,
                                        index=GRADES.index(stu["grade"]) if stu["grade"] in GRADES else 0)
                u_school= c1.text_input("Trường", stu["school"] or "")
                cls_up  = {f"{c['name']} ({c['subject']})": c["id"] for c in classes}
                cur_key = next((k for k,v in cls_up.items() if v==stu["class_id"]), None)
                u_cls   = c2.selectbox("Lớp", list(cls_up.keys()),
                                        index=list(cls_up.keys()).index(cur_key) if cur_key else 0)
                u_phone = c1.text_input("SĐT HS", stu["phone"] or "")
                u_pname = c2.text_input("Tên PH", stu["parent_name"] or "")
                u_pphone= c1.text_input("SĐT PH", stu["parent_phone"] or "")
                u_addr  = c2.text_input("Địa chỉ", stu["address"] or "")
                u_pers  = st.text_area("Tính cách", stu["personality"] or "")
                cs, cd  = st.columns(2)
                sv = cs.form_submit_button("💾 Lưu", type="primary", use_container_width=True)
                dl = cd.form_submit_button("🗑️ Nghỉ học", use_container_width=True)
            if sv:
                update_student(sid, u_name, str(u_dob), u_gender, u_grade, u_school,
                               u_phone, u_pname, u_pphone, u_addr, u_pers, cls_up[u_cls])
                st.success("✅ Đã cập nhật!"); st.rerun()
            if dl:
                delete_student(sid); st.success(f"✅ Đã đánh dấu {stu['full_name']} nghỉ học."); st.rerun()

        st.markdown("---")
        st.subheader("🗒️ Ghi chú nhanh")
        notes = get_notes(sid)
        with st.form("add_note_form", clear_on_submit=True):
            new_note = st.text_area("Nội dung", placeholder="Hôm nay làm bài tốt...")
            if st.form_submit_button("➕ Thêm", type="primary"):
                if new_note.strip():
                    add_note(sid, new_note.strip()); st.rerun()
        for note in notes:
            c1, c2 = st.columns([6,1])
            c1.markdown(f"🗒️ **{note['created_at'][:16]}** — {note['content']}")
            if c2.button("🗑️", key=f"del_note_{note['id']}"):
                delete_note(note["id"]); st.rerun()

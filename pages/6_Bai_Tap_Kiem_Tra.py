"""Bài tập & Kiểm tra – Phase 2"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import streamlit as st
import pandas as pd
from datetime import datetime, date
import plotly.express as px
from utils.database import (
    init_db, get_all_classes, get_all_students,
    get_assignments, add_assignment, get_results, save_result
)
from utils.auth import check_auth, render_sidebar, get_teacher_id
from utils.helpers import ASSIGNMENT_TYPE_LABEL, fmt_datetime

init_db()
st.set_page_config(page_title="Bài tập & Kiểm tra", page_icon="📝", layout="wide")
user = check_auth(); render_sidebar()
teacher_id = get_teacher_id()

st.title("📝 Bài Tập & Kiểm Tra")
classes = get_all_classes(teacher_id=teacher_id)
if not classes:
    st.warning("⚠️ Chưa có lớp."); st.stop()

cls_opts = {f"{c['name']} ({c['subject']})": c["id"] for c in classes}
tab_new, tab_list, tab_scores = st.tabs(["➕ Tạo bài mới","📋 Danh sách","📊 Nhập & Xem điểm"])
now = datetime.now()

with tab_new:
    sel_cls = st.selectbox("📖 Lớp", list(cls_opts.keys()), key="asgn_cls_new")
    cid = cls_opts[sel_cls]
    with st.form("add_assignment_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        title = c1.text_input("Tiêu đề *", placeholder="Kiểm tra 15p – Đạo hàm")
        atype = c2.selectbox("Loại", list(ASSIGNMENT_TYPE_LABEL.keys()),
                              format_func=lambda x: ASSIGNMENT_TYPE_LABEL[x])
        description = st.text_area("Nội dung / đề bài")
        st.markdown("**⏱️ Thời gian**")
        c3, c4, c5 = st.columns(3)
        start_date = c3.date_input("Ngày bắt đầu", value=date.today())
        start_time = c4.time_input("Giờ bắt đầu", value=now.time())
        max_score  = c5.number_input("Điểm tối đa", min_value=1.0, max_value=100.0, value=10.0, step=0.5)
        c6, c7 = st.columns(2)
        end_date = c6.date_input("Ngày kết thúc", value=date.today())
        end_time = c7.time_input("Giờ kết thúc")
        submitted = st.form_submit_button("➕ Tạo bài", type="primary", use_container_width=True)
    if submitted:
        if not title.strip():
            st.error("⚠️ Nhập tiêu đề!")
        else:
            aid = add_assignment(cid, title.strip(), atype, description,
                                 f"{start_date}T{start_time}", f"{end_date}T{end_time}", max_score)
            st.success(f"✅ Đã tạo: **{title}**"); st.balloons(); st.rerun()

with tab_list:
    sel_cls2 = st.selectbox("📖 Lớp", list(cls_opts.keys()), key="asgn_cls_list")
    cid2 = cls_opts[sel_cls2]; assignments = get_assignments(cid2)
    if not assignments:
        st.info("Chưa có bài tập / kiểm tra.")
    else:
        for asgn in assignments:
            with st.expander(f"{ASSIGNMENT_TYPE_LABEL[asgn['type']]} – {asgn['title']}"):
                c1, c2 = st.columns([2,1])
                c1.markdown(f"**📝 Mô tả:** {asgn['description'] or '—'}")
                c2.markdown(f"**⏱️ Bắt đầu:** {fmt_datetime(asgn['started_at'])}")
                c2.markdown(f"**⏱️ Kết thúc:** {fmt_datetime(asgn['ended_at'])}")
                c2.markdown(f"**🏆 Điểm tối đa:** {asgn['max_score']}")
                results = get_results(asgn["id"])
                scores = [r["score"] for r in results if r["score"] is not None]
                if scores:
                    c1.markdown(f"**📊 TB:** {sum(scores)/len(scores):.1f} | **Cao:** {max(scores)} | **Thấp:** {min(scores)}")
                c1.markdown(f"**👥 Đã có điểm:** {len(results)}")

with tab_scores:
    sel_cls3 = st.selectbox("📖 Lớp", list(cls_opts.keys()), key="asgn_cls_score")
    cid3 = cls_opts[sel_cls3]; assignments3 = get_assignments(cid3)
    if not assignments3:
        st.info("Chưa có bài tập / kiểm tra.")
    else:
        asgn_opts = {f"{ASSIGNMENT_TYPE_LABEL[a['type']]} – {a['title']}": a for a in assignments3}
        sel_asgn_key = st.selectbox("Chọn bài", list(asgn_opts.keys()))
        asgn = asgn_opts[sel_asgn_key]; aid = asgn["id"]
        st.markdown(f"""
        **{asgn['title']}** | ⏱️ `{fmt_datetime(asgn['started_at'])}` → `{fmt_datetime(asgn['ended_at'])}`  
        🏆 Điểm tối đa: **{asgn['max_score']}**
        """)
        st.markdown("---")
        students3 = get_all_students(class_id=cid3)
        existing  = {r["student_id"]: r for r in get_results(aid)}
        with st.form("score_form"):
            hdr = st.columns([3,2,3])
            hdr[0].markdown("**Học sinh**"); hdr[1].markdown("**Điểm**"); hdr[2].markdown("**Nhận xét**")
            rows = []
            for stu in students3:
                sid = stu["id"]; prev = existing.get(sid,{})
                cols = st.columns([3,2,3])
                cols[0].markdown(f"**{stu['full_name']}**")
                score = cols[1].number_input(f"sc{sid}", label_visibility="collapsed",
                    value=float(prev.get("score") or 0),
                    min_value=0.0, max_value=float(asgn["max_score"]), step=0.5, key=f"sc{sid}")
                note = cols[2].text_input(f"nt{sid}", label_visibility="collapsed",
                    value=prev.get("note") or "", placeholder="Làm tốt / cần xem lại...", key=f"nt{sid}")
                rows.append((sid, score, note))
            submitted3 = st.form_submit_button("💾 Lưu điểm", type="primary", use_container_width=True)
        if submitted3:
            for sid, score, note in rows:
                save_result(aid, sid, score, note, str(now)[:19])
            st.success("✅ Đã lưu điểm!"); st.rerun()
        results_all = get_results(aid)
        if results_all:
            scores = [r["score"] for r in results_all if r["score"] is not None]
            if scores:
                st.markdown("---"); st.subheader("📊 Phân phối điểm")
                df_s = pd.DataFrame({"Học sinh":[r["full_name"] for r in results_all if r["score"] is not None],"Điểm":scores})
                fig = px.bar(df_s.sort_values("Điểm", ascending=False), x="Học sinh", y="Điểm",
                              color="Điểm", color_continuous_scale="RdYlGn",
                              range_color=[0, asgn["max_score"]])
                fig.add_hline(y=sum(scores)/len(scores), line_dash="dash", line_color="blue",
                               annotation_text=f"TB: {sum(scores)/len(scores):.1f}")
                fig.update_layout(plot_bgcolor="white", paper_bgcolor="white")
                st.plotly_chart(fig, use_container_width=True)

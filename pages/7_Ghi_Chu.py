"""Ghi chú học sinh – Phase 2"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import streamlit as st
from utils.database import (
    init_db, get_all_students, get_all_classes,
    get_notes, add_note, delete_note
)
from utils.auth import check_auth, render_sidebar, get_teacher_id

init_db()
st.set_page_config(page_title="Ghi chú", page_icon="🗒️", layout="wide")
user = check_auth(); render_sidebar()
teacher_id = get_teacher_id()

st.title("🗒️ Ghi Chú Học Sinh")
classes  = get_all_classes(teacher_id=teacher_id)
cls_opts = {"-- Tất cả lớp --": None}
cls_opts.update({f"{c['name']} ({c['subject']})": c["id"] for c in classes})

col1, col2 = st.columns([2,1])
sel_cls    = col1.selectbox("📖 Lọc theo lớp", list(cls_opts.keys()))
cid_filter = cls_opts[sel_cls]
students   = get_all_students(class_id=cid_filter, teacher_id=teacher_id)

if not students:
    st.info("Chưa có học sinh."); st.stop()

stu_opts = {f"{s['full_name']} – {s['class_name'] or 'Chưa xếp lớp'}": s["id"] for s in students}
sel_stu  = col2.selectbox("👨‍🎓 Học sinh", list(stu_opts.keys()))
sid      = stu_opts[sel_stu]
stu_name = sel_stu.split(" – ")[0]

st.subheader(f"🗒️ Ghi chú của {stu_name}")
with st.form("note_form", clear_on_submit=True):
    content = st.text_area("✍️ Nội dung ghi chú mới",
                            placeholder="VD: Hôm nay làm bài đầy đủ, cần ôn lại phương trình bậc 2...",
                            height=120)
    if st.form_submit_button("➕ Thêm ghi chú", type="primary", use_container_width=True):
        if content.strip():
            add_note(sid, content.strip()); st.success("✅ Đã thêm!"); st.rerun()
        else:
            st.error("⚠️ Nội dung không được trống!")

st.markdown("---")
notes = get_notes(sid)
if not notes:
    st.info(f"Chưa có ghi chú nào cho **{stu_name}**.")
else:
    st.markdown(f"**📊 Tổng: {len(notes)} ghi chú**\n")
    for note in notes:
        c1, c2 = st.columns([10,1])
        with c1:
            st.markdown(f"""
<div style="background:#FAFAFA;border-left:4px solid #4F8EF7;border-radius:8px;
     padding:12px 16px;margin-bottom:8px">
<small style="color:#888">📅 {note['created_at'][:16]}</small><br>
{note['content'].replace(chr(10),'<br>')}
</div>""", unsafe_allow_html=True)
        if c2.button("🗑️", key=f"del_{note['id']}", help="Xóa"):
            delete_note(note["id"]); st.rerun()

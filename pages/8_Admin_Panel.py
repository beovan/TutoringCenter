"""
Trang Admin – Quản lý tài khoản giáo viên (chỉ Admin mới vào được)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
from utils.database import init_db, get_all_users, add_user, update_user, change_password, delete_user
from utils.auth import check_auth, render_sidebar, is_admin

init_db()
st.set_page_config(page_title="Admin Panel", page_icon="⚙️", layout="wide")

user = check_auth()
render_sidebar()

# Chặn giáo viên vào trang này
if not is_admin():
    st.error("⛔ Bạn không có quyền truy cập trang này!")
    st.stop()

st.title("⚙️ Quản Lý Tài Khoản")

tab_list, tab_add, tab_edit, tab_pwd = st.tabs([
    "👥 Danh sách tài khoản",
    "➕ Tạo tài khoản mới",
    "✏️ Sửa thông tin",
    "🔑 Đổi mật khẩu",
])

# ─── DANH SÁCH ──────────────────────────────────────────────────────────────────
with tab_list:
    users = get_all_users()
    if users:
        df = pd.DataFrame(users)
        df["role"]      = df["role"].map({"admin": "🔑 Admin", "teacher": "👩‍🏫 Giáo viên"})
        df["is_active"] = df["is_active"].map({1: "✅ Đang hoạt động", 0: "🔴 Đã khóa"})
        df["created_at"]= df["created_at"].apply(lambda d: d[:10] if d else "")
        df_show = df[["username","full_name","role","is_active","created_at"]]
        df_show.columns = ["Tên đăng nhập","Họ tên","Vai trò","Trạng thái","Ngày tạo"]
        st.dataframe(df_show, use_container_width=True, hide_index=True)
        st.caption(f"Tổng: **{len(users)}** tài khoản")
    else:
        st.info("Không có tài khoản nào.")

# ─── TẠO ACCOUNT ─────────────────────────────────────────────────────────────────
with tab_add:
    with st.form("add_user_form", clear_on_submit=True):
        st.subheader("Thông tin tài khoản mới")
        c1, c2 = st.columns(2)
        new_username  = c1.text_input("Tên đăng nhập *", placeholder="gv_nguyen")
        new_fullname  = c2.text_input("Họ và tên *", placeholder="Nguyễn Thị Hoa")
        new_role      = c1.selectbox("Vai trò", ["teacher", "admin"],
                                      format_func=lambda x: "👩‍🏫 Giáo viên" if x=="teacher" else "🔑 Admin")
        new_pass      = c2.text_input("Mật khẩu *", type="password", placeholder="Tối thiểu 6 ký tự")
        new_pass2     = st.text_input("Nhập lại mật khẩu *", type="password")
        submitted = st.form_submit_button("➕ Tạo tài khoản", type="primary", use_container_width=True)

    if submitted:
        if not new_username or not new_fullname or not new_pass:
            st.error("⚠️ Điền đầy đủ thông tin!")
        elif len(new_pass) < 6:
            st.error("⚠️ Mật khẩu tối thiểu 6 ký tự!")
        elif new_pass != new_pass2:
            st.error("⚠️ Mật khẩu nhập lại không khớp!")
        else:
            ok, msg = add_user(new_username, new_fullname, new_pass, new_role)
            if ok:
                st.success(f"✅ Đã tạo tài khoản **{new_fullname}** (`{new_username}`)")
                st.balloons()
                st.rerun()
            else:
                st.error(f"❌ {msg}")

# ─── SỬA THÔNG TIN ───────────────────────────────────────────────────────────────
with tab_edit:
    users = get_all_users()
    if not users:
        st.info("Không có tài khoản.")
    else:
        u_opts = {f"{u['full_name']} ({u['username']})": u for u in users}
        sel_u = st.selectbox("Chọn tài khoản", list(u_opts.keys()), key="edit_user_sel")
        u_data = u_opts[sel_u]

        with st.form("edit_user_form"):
            c1, c2 = st.columns(2)
            e_name   = c1.text_input("Họ tên", u_data["full_name"])
            e_role   = c2.selectbox("Vai trò", ["teacher","admin"],
                                     index=0 if u_data["role"]=="teacher" else 1,
                                     format_func=lambda x: "👩‍🏫 Giáo viên" if x=="teacher" else "🔑 Admin")
            e_active = st.checkbox("✅ Đang hoạt động", value=bool(u_data["is_active"]))

            col_save, col_del = st.columns(2)
            save_btn = col_save.form_submit_button("💾 Lưu", type="primary", use_container_width=True)
            del_btn  = col_del.form_submit_button("🔴 Khóa tài khoản", use_container_width=True)

        if save_btn:
            # Không cho xóa quyền admin của chính mình
            if u_data["id"] == user["id"] and e_role != "admin":
                st.error("⚠️ Không thể tự hạ quyền của mình!")
            else:
                update_user(u_data["id"], e_name, e_role, e_active)
                st.success("✅ Đã cập nhật!")
                st.rerun()
        if del_btn:
            if u_data["id"] == user["id"]:
                st.error("⚠️ Không thể khóa tài khoản đang đăng nhập!")
            else:
                delete_user(u_data["id"])
                st.success(f"✅ Đã khóa tài khoản **{u_data['full_name']}**")
                st.rerun()

# ─── ĐỔI MẬT KHẨU ────────────────────────────────────────────────────────────────
with tab_pwd:
    st.info("💡 Admin có thể đổi mật khẩu cho bất kỳ tài khoản nào. Giáo viên chỉ đổi của mình (ở phần cài đặt cá nhân).")
    users2 = get_all_users()
    if users2:
        u_opts2 = {f"{u['full_name']} ({u['username']})": u["id"] for u in users2}
        sel_u2  = st.selectbox("Chọn tài khoản", list(u_opts2.keys()), key="pwd_user_sel")
        uid2    = u_opts2[sel_u2]

        with st.form("change_pwd_form", clear_on_submit=True):
            p1 = st.text_input("Mật khẩu mới *", type="password", placeholder="Tối thiểu 6 ký tự")
            p2 = st.text_input("Nhập lại *", type="password")
            if st.form_submit_button("🔑 Đổi mật khẩu", type="primary", use_container_width=True):
                if len(p1) < 6:
                    st.error("Mật khẩu tối thiểu 6 ký tự!")
                elif p1 != p2:
                    st.error("Mật khẩu nhập lại không khớp!")
                else:
                    change_password(uid2, p1)
                    st.success("✅ Đã đổi mật khẩu thành công!")

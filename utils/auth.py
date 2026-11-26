"""
utils/auth.py – Xác thực & phân quyền cho toàn bộ app
"""
import streamlit as st
from utils.database import verify_login, get_db_info
from utils.backup import auto_backup_if_needed


# ══════════════════════════════════════════════════════════════════════════════
# CORE AUTH
# ══════════════════════════════════════════════════════════════════════════════

def check_auth() -> dict:
    """
    Gọi đầu mỗi page. Trả về user dict nếu đã đăng nhập.
    Nếu chưa → hiện form đăng nhập rồi st.stop().
    """
    if "user" not in st.session_state:
        _show_login_page()
        st.stop()
    auto_backup_if_needed()
    return st.session_state["user"]


def is_admin() -> bool:
    user = st.session_state.get("user", {})
    return user.get("role") == "admin"


def get_teacher_id():
    """Trả về None nếu admin (xem tất cả), id nếu là giáo viên"""
    user = st.session_state.get("user", {})
    if user.get("role") == "admin":
        return None
    return user.get("id")


def logout():
    st.session_state.clear()
    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# LOGIN PAGE
# ══════════════════════════════════════════════════════════════════════════════

def _show_login_page():
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] > .main {
        background: linear-gradient(135deg, #1A1A2E 0%, #16213E 50%, #0F3460 100%);
    }
    .login-box {
        background: white;
        border-radius: 20px;
        padding: 48px 40px;
        max-width: 420px;
        margin: 60px auto 0 auto;
        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
    }
    .login-title {
        text-align: center;
        color: #1A1A2E;
        font-size: 28px;
        font-weight: 800;
        margin-bottom: 4px;
    }
    .login-sub {
        text-align: center;
        color: #888;
        font-size: 14px;
        margin-bottom: 32px;
    }
    </style>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.markdown('<div class="login-title">📚 Trung Tâm Dạy Thêm</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-sub">Hệ thống quản lý học sinh</div>', unsafe_allow_html=True)

        with st.form("login_form"):
            username = st.text_input("👤 Tên đăng nhập", placeholder="admin")
            password = st.text_input("🔒 Mật khẩu", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("🚀 Đăng nhập", type="primary", use_container_width=True)

        if submitted:
            if not username or not password:
                st.error("⚠️ Vui lòng nhập đầy đủ thông tin!")
            else:
                user = verify_login(username.strip(), password)
                if user:
                    st.session_state["user"] = user
                    st.success(f"✅ Chào mừng **{user['full_name']}**!")
                    st.rerun()
                else:
                    st.error("❌ Sai tên đăng nhập hoặc mật khẩu!")

        st.markdown("---")
        st.caption("💡 Lần đầu dùng: `admin` / `admin123`")
        st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR CHUNG (gọi ở mỗi page)
# ══════════════════════════════════════════════════════════════════════════════

def render_sidebar():
    """Render sidebar với thông tin user và điều hướng"""
    user = st.session_state.get("user", {})
    role = user.get("role", "teacher")
    name = user.get("full_name", "")
    db_info = get_db_info()

    with st.sidebar:
        st.markdown("## 📚 Trung Tâm Dạy Thêm")
        st.markdown("---")

        role_icon = "🔑" if role == "admin" else "👩‍🏫"
        role_label = "Admin" if role == "admin" else "Giáo viên"
        st.markdown(f"""
        <div style="background:#2D3561;border-radius:10px;padding:12px 14px;margin-bottom:12px">
        <div style="color:#A0C4FF;font-size:12px">{role_icon} {role_label} • {db_info['badge']}</div>
        <div style="color:white;font-weight:700;font-size:15px">{name}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("### 📋 Menu")
        st.page_link("app.py",                         label="🏠 Tổng quan")
        st.page_link("pages/1_Lop_Hoc.py",             label="📖 Lớp học")
        st.page_link("pages/2_Hoc_Sinh.py",            label="👨‍🎓 Học sinh")
        st.page_link("pages/3_Lich_Hoc.py",            label="📅 Lịch học")
        st.page_link("pages/4_Diem_Danh.py",           label="✅ Điểm danh")
        st.page_link("pages/5_Hoc_Phi.py",             label="💰 Học phí")
        st.page_link("pages/6_Bai_Tap_Kiem_Tra.py",   label="📝 Bài tập / Kiểm tra")
        st.page_link("pages/7_Ghi_Chu.py",             label="🗒️ Ghi chú học sinh")

        if role == "admin":
            st.markdown("---")
            st.markdown("### 🔑 Quản trị")
            st.page_link("pages/8_Admin_Panel.py",   label="⚙️ Quản lý tài khoản")
            st.page_link("pages/9_Sao_Luu_Data.py",  label="💾 Sao lưu & Cloud")

        st.markdown("---")
        if st.button("🚪 Đăng xuất", use_container_width=True, type="secondary"):
            logout()

        st.caption(f"🕐 {__import__('datetime').datetime.now().strftime('%d/%m/%Y %H:%M')}")

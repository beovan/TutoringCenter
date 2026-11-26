"""
utils/auth.py – Xác thực & phân quyền cho toàn bộ app
"""
from datetime import datetime
import streamlit as st
from utils.database import verify_login, get_db_info
from utils.backup import auto_backup_if_needed


# ══════════════════════════════════════════════════════════════════════════════
# SHARED UI CSS
# ══════════════════════════════════════════════════════════════════════════════

_APP_CSS = """
<style>
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1A1A2E 0%, #16213E 100%);
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
    color: #E6ECFF !important;
}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] {
    border-radius: 8px;
    padding: 4px 8px;
}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover {
    background: rgba(79, 142, 247, 0.22);
}
[data-testid="stSidebar"] .stButton > button {
    background-color: #2D3561 !important;
    color: #FFFFFF !important;
    border: 1px solid #4F8EF7 !important;
    border-radius: 8px;
    font-weight: 600;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background-color: #4F8EF7 !important;
    color: #FFFFFF !important;
}

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
.stButton > button:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(79,142,247,0.25); }
</style>
"""


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
    [data-testid="stSidebar"],
    [data-testid="collapsedControl"] {
        display: none !important;
    }
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #1A1A2E 0%, #16213E 55%, #0F3460 100%);
    }
    [data-testid="stHeader"] {
        background: transparent;
    }
    .login-header {
        text-align: center;
        padding: 24px 0 12px 0;
    }
    .login-title {
        color: #FFFFFF;
        font-size: 32px;
        font-weight: 800;
        margin-bottom: 6px;
    }
    .login-sub {
        color: #B8C7E0;
        font-size: 15px;
    }
    [data-testid="stForm"] {
        background: #FFFFFF;
        border-radius: 18px;
        padding: 32px 28px 24px 28px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.35);
        border: none;
    }
    [data-testid="stForm"] label,
    [data-testid="stForm"] p {
        color: #1A1A2E !important;
    }
    .login-hint {
        text-align: center;
        color: #C9D6EA;
        font-size: 13px;
        margin-top: 10px;
    }
    .login-hint code {
        background: rgba(255,255,255,0.14);
        color: #FFFFFF;
        padding: 2px 6px;
        border-radius: 4px;
    }
    </style>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        st.markdown(
            """
            <div class="login-header">
                <div class="login-title">📚 Trung Tâm Dạy Thêm</div>
                <div class="login-sub">Hệ thống quản lý học sinh &amp; học phí</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

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

        st.markdown(
            '<div class="login-hint">💡 Tài khoản mặc định: <code>admin</code> / <code>admin123</code></div>',
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR CHUNG (gọi ở mỗi page)
# ══════════════════════════════════════════════════════════════════════════════

def render_sidebar():
    """Render CSS chung, sidebar với thông tin user và điều hướng."""
    st.markdown(_APP_CSS, unsafe_allow_html=True)

    user = st.session_state.get("user", {})
    role = user.get("role", "teacher")
    name = user.get("full_name", "")
    db_info = get_db_info()

    with st.sidebar:
        st.markdown("## 📚 Trung Tâm Dạy Thêm")
        st.markdown("---")

        role_icon = "🔑" if role == "admin" else "👩‍🏫"
        role_label = "Admin" if role == "admin" else "Giáo viên"
        st.markdown(
            f"""
            <div style="background:#2D3561;border-radius:10px;padding:12px 14px;margin-bottom:12px">
                <div style="color:#A0C4FF;font-size:12px">{role_icon} {role_label} • {db_info['badge']}</div>
                <div style="color:white;font-weight:700;font-size:15px">{name}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

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
        if st.button("🚪 Đăng xuất", use_container_width=True):
            logout()

        st.caption(f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M')}")

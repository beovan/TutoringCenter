"""
Database layer – Hỗ trợ song song:
  - Option A: SQLite local (data/tutoring.db)
  - Option B: PostgreSQL Cloud (Neon.tech / Supabase qua DATABASE_URL)
"""
import hashlib
import os
import sqlite3
from datetime import datetime
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(ROOT_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "tutoring.db")

_INIT_DONE_FOR = None

# Thứ tự bảng an toàn cho export / import (tôn trọng khóa ngoại)
TABLE_EXPORT_ORDER = [
    "users",
    "classes",
    "students",
    "schedules",
    "attendance",
    "fees",
    "assignments",
    "assignment_results",
    "student_notes",
]

TABLE_COLUMNS = {
    "users": ["id", "username", "full_name", "password_hash", "role", "is_active", "created_at"],
    "classes": ["id", "name", "subject", "grade", "tuition_fee", "teacher_id", "note", "created_at"],
    "students": [
        "id", "full_name", "dob", "gender", "grade", "school", "phone",
        "parent_name", "parent_phone", "address", "personality", "class_id", "status", "created_at",
    ],
    "schedules": ["id", "class_id", "day_of_week", "start_time", "end_time", "lessons_per_session", "room"],
    "attendance": ["id", "student_id", "class_id", "date", "status", "note", "created_at"],
    "fees": ["id", "student_id", "class_id", "month", "year", "amount", "paid_amount", "paid_date", "status", "note", "created_at"],
    "assignments": ["id", "class_id", "title", "type", "description", "started_at", "ended_at", "max_score", "created_at"],
    "assignment_results": ["id", "assignment_id", "student_id", "score", "note", "submitted_at"],
    "student_notes": ["id", "student_id", "content", "created_at"],
}


def get_database_url() -> str:
    """Lấy DATABASE_URL từ biến môi trường (.env / Render) hoặc Streamlit secrets."""
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        try:
            import streamlit as st
            has_secrets = (
                st.secrets.load_if_toml_exists()
                if hasattr(st.secrets, "load_if_toml_exists")
                else any(os.path.exists(p) for p in (st.config.get_option("secrets.files") or []))
            )
            if has_secrets and "DATABASE_URL" in st.secrets:
                url = str(st.secrets["DATABASE_URL"]).strip()
        except Exception:
            pass

    if not url:
        return ""

    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]

    # Neon và các cloud Postgres yêu cầu sslmode=require
    if url.startswith("postgresql://"):
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        if "sslmode" not in qs and parsed.hostname not in (None, "localhost", "127.0.0.1"):
            qs["sslmode"] = ["require"]
            new_query = urlencode(qs, doseq=True)
            url = urlunparse(parsed._replace(query=new_query))
    return url


def is_postgres() -> bool:
    return get_database_url().startswith("postgresql://")


def get_db_info() -> dict:
    """Thông tin database đang kết nối để hiển thị UI."""
    url = get_database_url()
    if url.startswith("postgresql://"):
        parsed = urlparse(url)
        host = parsed.hostname or "postgres"
        provider = "Neon Cloud" if "neon.tech" in host else ("Supabase Cloud" if "supabase" in host else "PostgreSQL Cloud")
        return {
            "mode": "postgres",
            "provider": provider,
            "target": host,
            "badge": f"☁️ {provider}",
        }
    return {
        "mode": "sqlite",
        "provider": "SQLite Local",
        "target": DB_PATH,
        "badge": "💾 SQLite Local",
    }


def reset_db_init_cache():
    global _INIT_DONE_FOR
    _INIT_DONE_FOR = None


class _DBConn:
    """Wrapper thống nhất API cho cả sqlite3 và psycopg2."""

    def __init__(self, raw_conn, pg: bool):
        self.raw = raw_conn
        self.pg = pg

    def _sql(self, sql: str) -> str:
        if not self.pg:
            return sql
        return sql.replace("?", "%s")

    def execute(self, sql: str, params=()):
        cur = self.raw.cursor()
        cur.execute(self._sql(sql), params)
        return cur

    def executemany(self, sql: str, params_seq):
        cur = self.raw.cursor()
        cur.executemany(self._sql(sql), params_seq)
        return cur

    def insert_returning_id(self, sql: str, params=()) -> int:
        if self.pg:
            cur = self.execute(sql.rstrip().rstrip(";") + " RETURNING id", params)
            row = cur.fetchone()
            return row["id"]
        cur = self.execute(sql, params)
        return cur.lastrowid

    def commit(self):
        self.raw.commit()

    def rollback(self):
        self.raw.rollback()

    def close(self):
        self.raw.close()


def _get_integrity_errors():
    errs = [sqlite3.IntegrityError]
    if is_postgres():
        import psycopg2
        errs.append(psycopg2.IntegrityError)
    return tuple(errs)


def get_conn() -> _DBConn:
    url = get_database_url()
    if url.startswith("postgresql://"):
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
        except ImportError as exc:
            raise RuntimeError(
                "Đã cấu hình DATABASE_URL (PostgreSQL/Neon) nhưng chưa cài psycopg2-binary. "
                "Chạy: pip install psycopg2-binary"
            ) from exc

        raw = psycopg2.connect(url, cursor_factory=RealDictCursor, connect_timeout=10)
        return _DBConn(raw, pg=True)

    os.makedirs(DATA_DIR, exist_ok=True)
    raw = sqlite3.connect(DB_PATH, check_same_thread=False)
    raw.row_factory = sqlite3.Row
    raw.execute("PRAGMA foreign_keys = ON")
    return _DBConn(raw, pg=False)


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _schema_statements(pg: bool) -> list[str]:
    pk = "SERIAL PRIMARY KEY" if pg else "INTEGER PRIMARY KEY AUTOINCREMENT"
    flt = "DOUBLE PRECISION" if pg else "REAL"
    now_default = (
        "TEXT DEFAULT TO_CHAR(NOW() AT TIME ZONE 'Asia/Ho_Chi_Minh', 'YYYY-MM-DD HH24:MI:SS')"
        if pg
        else "TEXT DEFAULT (datetime('now','localtime'))"
    )

    return [
        f"""
        CREATE TABLE IF NOT EXISTS users (
            id            {pk},
            username      TEXT NOT NULL UNIQUE,
            full_name     TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role          TEXT DEFAULT 'teacher',
            is_active     INTEGER DEFAULT 1,
            created_at    {now_default}
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS classes (
            id          {pk},
            name        TEXT NOT NULL,
            subject     TEXT NOT NULL,
            grade       TEXT NOT NULL,
            tuition_fee {flt} DEFAULT 0,
            teacher_id  INTEGER REFERENCES users(id),
            note        TEXT,
            created_at  {now_default}
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS students (
            id           {pk},
            full_name    TEXT NOT NULL,
            dob          TEXT,
            gender       TEXT DEFAULT 'Nam',
            grade        TEXT,
            school       TEXT,
            phone        TEXT,
            parent_name  TEXT,
            parent_phone TEXT,
            address      TEXT,
            personality  TEXT,
            class_id     INTEGER REFERENCES classes(id) ON DELETE SET NULL,
            status       TEXT DEFAULT 'active',
            created_at   {now_default}
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS schedules (
            id                  {pk},
            class_id            INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
            day_of_week         TEXT NOT NULL,
            start_time          TEXT NOT NULL,
            end_time            TEXT NOT NULL,
            lessons_per_session INTEGER DEFAULT 2,
            room                TEXT
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS attendance (
            id         {pk},
            student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
            class_id   INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
            date       TEXT NOT NULL,
            status     TEXT DEFAULT 'present',
            note       TEXT,
            created_at {now_default},
            UNIQUE(student_id, class_id, date)
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS fees (
            id          {pk},
            student_id  INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
            class_id    INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
            month       INTEGER NOT NULL,
            year        INTEGER NOT NULL,
            amount      {flt} NOT NULL,
            paid_amount {flt} DEFAULT 0,
            paid_date   TEXT,
            status      TEXT DEFAULT 'unpaid',
            note        TEXT,
            created_at  {now_default},
            UNIQUE(student_id, class_id, month, year)
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS assignments (
            id          {pk},
            class_id    INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
            title       TEXT NOT NULL,
            type        TEXT DEFAULT 'homework',
            description TEXT,
            started_at  TEXT,
            ended_at    TEXT,
            max_score   {flt} DEFAULT 10,
            created_at  {now_default}
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS assignment_results (
            id            {pk},
            assignment_id INTEGER NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
            student_id    INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
            score         {flt},
            note          TEXT,
            submitted_at  TEXT,
            UNIQUE(assignment_id, student_id)
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS student_notes (
            id         {pk},
            student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
            content    TEXT NOT NULL,
            created_at {now_default}
        )
        """,
    ]


def init_db(force: bool = False):
    """Tạo / migrate tất cả bảng (hỗ trợ cả SQLite và PostgreSQL/Neon)."""
    global _INIT_DONE_FOR
    db_key = get_database_url() or DB_PATH
    if not force and _INIT_DONE_FOR == db_key:
        if is_postgres() or os.path.exists(DB_PATH):
            return

    conn = get_conn()
    try:
        for stmt in _schema_statements(conn.pg):
            conn.execute(stmt)
        conn.commit()

        # Migration: thêm cột teacher_id nếu nâng cấp từ DB Phase 1
        if conn.pg:
            conn.execute("ALTER TABLE classes ADD COLUMN IF NOT EXISTS teacher_id INTEGER REFERENCES users(id)")
            conn.commit()
        else:
            try:
                conn.execute("ALTER TABLE classes ADD COLUMN teacher_id INTEGER REFERENCES users(id)")
                conn.commit()
            except Exception:
                pass

        # Tạo tài khoản admin mặc định nếu chưa có
        exists = conn.execute("SELECT id FROM users WHERE role='admin' LIMIT 1").fetchone()
        if not exists:
            conn.execute(
                """
                INSERT INTO users(username, full_name, password_hash, role)
                VALUES(?, ?, ?, ?)
                """,
                ("admin", "Quản trị viên", _hash("admin123"), "admin"),
            )
            conn.commit()

        _INIT_DONE_FOR = db_key
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# USERS
# ══════════════════════════════════════════════════════════════════════════════

def get_user_by_username(username: str):
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE username=? AND is_active=1",
            (username,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def verify_login(username: str, password: str):
    """Trả về user dict nếu đúng mật khẩu, ngược lại None"""
    user = get_user_by_username(username)
    if user and user["password_hash"] == _hash(password):
        return user
    return None


def get_all_users():
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT id,username,full_name,role,is_active,created_at FROM users ORDER BY role DESC, full_name"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_user(username, full_name, password, role="teacher"):
    conn = get_conn()
    try:
        conn.execute(
            """
            INSERT INTO users(username,full_name,password_hash,role)
            VALUES(?,?,?,?)
            """,
            (username.strip(), full_name.strip(), _hash(password), role),
        )
        conn.commit()
        return True, "OK"
    except _get_integrity_errors():
        conn.rollback()
        return False, f"Tên đăng nhập '{username}' đã tồn tại!"
    finally:
        conn.close()


def update_user(user_id, full_name, role, is_active):
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE users SET full_name=?,role=?,is_active=? WHERE id=?",
            (full_name, role, int(is_active), user_id),
        )
        conn.commit()
    finally:
        conn.close()


def change_password(user_id, new_password):
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE users SET password_hash=? WHERE id=?",
            (_hash(new_password), user_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_user(user_id):
    conn = get_conn()
    try:
        conn.execute("UPDATE users SET is_active=0 WHERE id=?", (user_id,))
        conn.commit()
    finally:
        conn.close()


def get_teacher_options():
    """Trả về list dict cho selectbox chọn giáo viên"""
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT id, full_name FROM users WHERE is_active=1 ORDER BY full_name"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# CLASSES
# ══════════════════════════════════════════════════════════════════════════════

def get_all_classes(teacher_id=None):
    """teacher_id=None → admin (thấy tất cả), teacher_id=X → chỉ lớp của GV đó"""
    conn = get_conn()
    try:
        if teacher_id:
            rows = conn.execute(
                """
                SELECT c.*, u.full_name as teacher_name, COUNT(s.id) as student_count
                FROM classes c
                LEFT JOIN users u ON u.id = c.teacher_id
                LEFT JOIN students s ON s.class_id = c.id AND s.status='active'
                WHERE c.teacher_id=?
                GROUP BY c.id, u.full_name ORDER BY c.name
                """,
                (teacher_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT c.*, u.full_name as teacher_name, COUNT(s.id) as student_count
                FROM classes c
                LEFT JOIN users u ON u.id = c.teacher_id
                LEFT JOIN students s ON s.class_id = c.id AND s.status='active'
                GROUP BY c.id, u.full_name ORDER BY c.name
                """
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_class(class_id):
    conn = get_conn()
    try:
        row = conn.execute(
            """
            SELECT c.*, u.full_name as teacher_name
            FROM classes c LEFT JOIN users u ON u.id=c.teacher_id
            WHERE c.id=?
            """,
            (class_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def add_class(name, subject, grade, tuition_fee, teacher_id=None, note=""):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO classes(name,subject,grade,tuition_fee,teacher_id,note) VALUES(?,?,?,?,?,?)",
            (name, subject, grade, tuition_fee, teacher_id, note),
        )
        conn.commit()
    finally:
        conn.close()


def update_class(class_id, name, subject, grade, tuition_fee, teacher_id=None, note=""):
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE classes SET name=?,subject=?,grade=?,tuition_fee=?,teacher_id=?,note=? WHERE id=?",
            (name, subject, grade, tuition_fee, teacher_id, note, class_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_class(class_id):
    conn = get_conn()
    try:
        conn.execute("UPDATE students SET class_id=NULL WHERE class_id=?", (class_id,))
        conn.execute("DELETE FROM classes WHERE id=?", (class_id,))
        conn.commit()
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# STUDENTS
# ══════════════════════════════════════════════════════════════════════════════

def get_all_students(class_id=None, status="active", teacher_id=None):
    conn = get_conn()
    try:
        sql = """
            SELECT s.*, c.name as class_name, c.subject
            FROM students s LEFT JOIN classes c ON c.id = s.class_id
            WHERE s.status=?
        """
        params = [status]
        if class_id:
            sql += " AND s.class_id=?"
            params.append(class_id)
        if teacher_id:
            sql += " AND c.teacher_id=?"
            params.append(teacher_id)
        sql += " ORDER BY s.full_name"
        rows = conn.execute(sql, tuple(params)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_student(student_id):
    conn = get_conn()
    try:
        row = conn.execute(
            """
            SELECT s.*, c.name as class_name, c.subject, c.tuition_fee
            FROM students s LEFT JOIN classes c ON c.id = s.class_id
            WHERE s.id=?
            """,
            (student_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def add_student(
    full_name, dob, gender, grade, school, phone,
    parent_name, parent_phone, address, personality, class_id
):
    conn = get_conn()
    try:
        conn.execute(
            """
            INSERT INTO students(full_name,dob,gender,grade,school,phone,
                                 parent_name,parent_phone,address,personality,class_id)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                full_name, dob, gender, grade, school, phone,
                parent_name, parent_phone, address, personality, class_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def update_student(
    student_id, full_name, dob, gender, grade, school, phone,
    parent_name, parent_phone, address, personality, class_id
):
    conn = get_conn()
    try:
        conn.execute(
            """
            UPDATE students SET full_name=?,dob=?,gender=?,grade=?,school=?,phone=?,
                parent_name=?,parent_phone=?,address=?,personality=?,class_id=?
            WHERE id=?
            """,
            (
                full_name, dob, gender, grade, school, phone,
                parent_name, parent_phone, address, personality, class_id, student_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def delete_student(student_id):
    conn = get_conn()
    try:
        conn.execute("UPDATE students SET status='inactive' WHERE id=?", (student_id,))
        conn.commit()
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# SCHEDULES
# ══════════════════════════════════════════════════════════════════════════════

def get_schedules(class_id):
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM schedules WHERE class_id=? ORDER BY day_of_week, start_time",
            (class_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_schedule(class_id, day_of_week, start_time, end_time, lessons_per_session, room=""):
    conn = get_conn()
    try:
        conn.execute(
            """
            INSERT INTO schedules(class_id,day_of_week,start_time,end_time,lessons_per_session,room)
            VALUES(?,?,?,?,?,?)
            """,
            (class_id, day_of_week, start_time, end_time, lessons_per_session, room),
        )
        conn.commit()
    finally:
        conn.close()


def delete_schedule(schedule_id):
    conn = get_conn()
    try:
        conn.execute("DELETE FROM schedules WHERE id=?", (schedule_id,))
        conn.commit()
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# ATTENDANCE
# ══════════════════════════════════════════════════════════════════════════════

def get_attendance(class_id, date):
    conn = get_conn()
    try:
        rows = conn.execute(
            """
            SELECT a.*, s.full_name FROM attendance a
            JOIN students s ON s.id = a.student_id
            WHERE a.class_id=? AND a.date=? ORDER BY s.full_name
            """,
            (class_id, date),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def save_attendance(student_id, class_id, date, status, note=""):
    conn = get_conn()
    try:
        conn.execute(
            """
            INSERT INTO attendance(student_id,class_id,date,status,note)
            VALUES(?,?,?,?,?)
            ON CONFLICT(student_id,class_id,date) DO UPDATE
                SET status=excluded.status, note=excluded.note
            """,
            (student_id, class_id, date, status, note),
        )
        conn.commit()
    finally:
        conn.close()


def get_attendance_summary(student_id):
    conn = get_conn()
    try:
        rows = conn.execute(
            """
            SELECT status, COUNT(*) as cnt FROM attendance
            WHERE student_id=? GROUP BY status
            """,
            (student_id,),
        ).fetchall()
        return {r["status"]: r["cnt"] for r in rows}
    finally:
        conn.close()


def get_attendance_by_month(class_id, month, year):
    conn = get_conn()
    try:
        rows = conn.execute(
            """
            SELECT s.full_name, a.date, a.status, a.note
            FROM attendance a JOIN students s ON s.id=a.student_id
            WHERE a.class_id=? AND substr(a.date, 1, 7)=?
            ORDER BY a.date, s.full_name
            """,
            (class_id, f"{year}-{month:02d}"),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# FEES
# ══════════════════════════════════════════════════════════════════════════════

def get_fees(class_id=None, month=None, year=None, student_id=None, teacher_id=None):
    conn = get_conn()
    try:
        sql = """
            SELECT f.*, s.full_name, c.name as class_name, c.subject
            FROM fees f
            JOIN students s ON s.id=f.student_id
            JOIN classes c ON c.id=f.class_id
            WHERE 1=1
        """
        params = []
        if class_id:
            sql += " AND f.class_id=?"
            params.append(class_id)
        if student_id:
            sql += " AND f.student_id=?"
            params.append(student_id)
        if month:
            sql += " AND f.month=?"
            params.append(month)
        if year:
            sql += " AND f.year=?"
            params.append(year)
        if teacher_id:
            sql += " AND c.teacher_id=?"
            params.append(teacher_id)
        sql += " ORDER BY f.year DESC, f.month DESC, s.full_name"
        rows = conn.execute(sql, tuple(params)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def save_fee(student_id, class_id, month, year, amount, paid_amount, paid_date, status, note=""):
    conn = get_conn()
    try:
        conn.execute(
            """
            INSERT INTO fees(student_id,class_id,month,year,amount,paid_amount,paid_date,status,note)
            VALUES(?,?,?,?,?,?,?,?,?)
            ON CONFLICT(student_id,class_id,month,year) DO UPDATE
                SET amount=excluded.amount, paid_amount=excluded.paid_amount,
                    paid_date=excluded.paid_date, status=excluded.status, note=excluded.note
            """,
            (student_id, class_id, month, year, amount, paid_amount, paid_date, status, note),
        )
        conn.commit()
    finally:
        conn.close()


def get_fee_summary_by_month(year, teacher_id=None):
    conn = get_conn()
    try:
        sql = """
            SELECT f.month,
                   SUM(f.amount) as total_amount,
                   SUM(f.paid_amount) as total_paid,
                   SUM(f.amount - f.paid_amount) as total_debt,
                   COUNT(*) as student_count
            FROM fees f
            JOIN classes c ON c.id=f.class_id
            WHERE f.year=?
        """
        params = [year]
        if teacher_id:
            sql += " AND c.teacher_id=?"
            params.append(teacher_id)
        sql += " GROUP BY f.month ORDER BY f.month"
        rows = conn.execute(sql, tuple(params)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# ASSIGNMENTS
# ══════════════════════════════════════════════════════════════════════════════

def get_assignments(class_id):
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM assignments WHERE class_id=? ORDER BY created_at DESC",
            (class_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_assignment(class_id, title, atype, description, started_at, ended_at, max_score):
    conn = get_conn()
    try:
        aid = conn.insert_returning_id(
            """
            INSERT INTO assignments(class_id,title,type,description,started_at,ended_at,max_score)
            VALUES(?,?,?,?,?,?,?)
            """,
            (class_id, title, atype, description, started_at, ended_at, max_score),
        )
        conn.commit()
        return aid
    finally:
        conn.close()


def save_result(assignment_id, student_id, score, note, submitted_at):
    conn = get_conn()
    try:
        conn.execute(
            """
            INSERT INTO assignment_results(assignment_id,student_id,score,note,submitted_at)
            VALUES(?,?,?,?,?)
            ON CONFLICT(assignment_id,student_id) DO UPDATE
                SET score=excluded.score, note=excluded.note, submitted_at=excluded.submitted_at
            """,
            (assignment_id, student_id, score, note, submitted_at),
        )
        conn.commit()
    finally:
        conn.close()


def get_results(assignment_id):
    conn = get_conn()
    try:
        rows = conn.execute(
            """
            SELECT r.*, s.full_name FROM assignment_results r
            JOIN students s ON s.id=r.student_id
            WHERE r.assignment_id=? ORDER BY s.full_name
            """,
            (assignment_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# NOTES
# ══════════════════════════════════════════════════════════════════════════════

def get_notes(student_id):
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM student_notes WHERE student_id=? ORDER BY created_at DESC",
            (student_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_note(student_id, content):
    conn = get_conn()
    try:
        conn.execute("INSERT INTO student_notes(student_id,content) VALUES(?,?)", (student_id, content))
        conn.commit()
    finally:
        conn.close()


def delete_note(note_id):
    conn = get_conn()
    try:
        conn.execute("DELETE FROM student_notes WHERE id=?", (note_id,))
        conn.commit()
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD STATS
# ══════════════════════════════════════════════════════════════════════════════

def get_dashboard_stats(teacher_id=None):
    conn = get_conn()
    try:
        stats = {}
        if teacher_id:
            stats["total_students"] = conn.execute(
                """
                SELECT COUNT(s.id) AS cnt FROM students s
                JOIN classes c ON c.id=s.class_id
                WHERE s.status='active' AND c.teacher_id=?
                """,
                (teacher_id,),
            ).fetchone()["cnt"]
            stats["total_classes"] = conn.execute(
                "SELECT COUNT(*) AS cnt FROM classes WHERE teacher_id=?",
                (teacher_id,),
            ).fetchone()["cnt"]
        else:
            stats["total_students"] = conn.execute(
                "SELECT COUNT(*) AS cnt FROM students WHERE status='active'"
            ).fetchone()["cnt"]
            stats["total_classes"] = conn.execute(
                "SELECT COUNT(*) AS cnt FROM classes"
            ).fetchone()["cnt"]

        stats["total_teachers"] = conn.execute(
            "SELECT COUNT(*) AS cnt FROM users WHERE role='teacher' AND is_active=1"
        ).fetchone()["cnt"]

        now = datetime.now()
        stats["month"] = now.month
        stats["year"] = now.year

        fee_sql = """
            SELECT SUM(f.paid_amount) as paid, SUM(f.amount-f.paid_amount) as debt
            FROM fees f JOIN classes c ON c.id=f.class_id
            WHERE f.month=? AND f.year=?
        """
        fee_params = [now.month, now.year]
        if teacher_id:
            fee_sql += " AND c.teacher_id=?"
            fee_params.append(teacher_id)
        fee_row = conn.execute(fee_sql, tuple(fee_params)).fetchone()
        stats["month_paid"] = fee_row["paid"] or 0
        stats["month_debt"] = fee_row["debt"] or 0

        today = now.strftime("%Y-%m-%d")
        att_sql = (
            "SELECT SUM(CASE WHEN a.status='absent' THEN 1 ELSE 0 END) as absent_today "
            "FROM attendance a JOIN classes c ON c.id=a.class_id WHERE a.date=?"
        )
        att_params = [today]
        if teacher_id:
            att_sql += " AND c.teacher_id=?"
            att_params.append(teacher_id)
        att_row = conn.execute(att_sql, tuple(att_params)).fetchone()
        stats["absent_today"] = att_row["absent_today"] or 0
        return stats
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# EXPORT / IMPORT RAW TABLES (Dùng cho Backup & Di chuyển SQLite <-> Neon)
# ══════════════════════════════════════════════════════════════════════════════

def export_all_tables() -> dict:
    """Đọc toàn bộ dữ liệu tất cả bảng dưới dạng dict."""
    conn = get_conn()
    try:
        data = {}
        for table in TABLE_EXPORT_ORDER:
            rows = conn.execute(f"SELECT * FROM {table} ORDER BY id").fetchall()
            data[table] = [dict(r) for r in rows]
        return data
    finally:
        conn.close()


def replace_all_tables(tables_data: dict):
    """
    Ghi đè toàn bộ dữ liệu từ bản backup JSON vào database hiện tại
    (hoạt động cho cả SQLite local và PostgreSQL Neon).
    """
    init_db()
    conn = get_conn()
    try:
        # Xóa ngược thứ tự khóa ngoại
        for table in reversed(TABLE_EXPORT_ORDER):
            conn.execute(f"DELETE FROM {table}")

        # Chèn xuôi thứ tự khóa ngoại
        for table in TABLE_EXPORT_ORDER:
            rows = tables_data.get(table, [])
            if not rows:
                continue
            allowed = set(TABLE_COLUMNS[table])
            cols = [c for c in rows[0].keys() if c in allowed]
            if not cols:
                continue
            col_list = ", ".join(cols)
            placeholders = ", ".join("?" for _ in cols)
            sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"
            values = [tuple(r.get(c) for c in cols) for r in rows]
            conn.executemany(sql, values)

        # Reset PostgreSQL SERIAL sequences để lần INSERT mới không đụng ID cũ
        if conn.pg:
            for table in TABLE_EXPORT_ORDER:
                max_row = conn.execute(f"SELECT COALESCE(MAX(id), 0) AS max_id FROM {table}").fetchone()
                max_id = max_row["max_id"] or 0
                if max_id > 0:
                    conn.execute(
                        f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), ?, true)",
                        (max_id,),
                    )
                else:
                    conn.execute(
                        f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), 1, false)"
                    )

        # Đảm bảo vẫn luôn có ít nhất 1 admin nếu bản backup không có user
        if not tables_data.get("users"):
            conn.execute(
                "INSERT INTO users(username, full_name, password_hash, role) VALUES(?,?,?,?)",
                ("admin", "Quản trị viên", _hash("admin123"), "admin"),
            )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

import os
from datetime import datetime

import mysql.connector


def _load_env_file(env_path: str = ".env") -> None:
    """Load simple KEY=VALUE pairs from a local .env file.

    - Ignores blank lines and lines starting with '#'
    - Supports optional quotes around values
    - Does NOT override already-set environment variables

    This keeps the project dependency-free (no python-dotenv).
    """

    if not os.path.exists(env_path):
        return

    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue

                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if not key:
                    continue

                # Do not override env vars set by OS/shell (they take precedence).
                os.environ.setdefault(key, value)
    except OSError:
        # If the file can't be read, just fall back to OS environment variables.
        return


# ==========================================
# 1. CONFIGURATION & ROLE SETUP
# ==========================================

_load_env_file(".env")

ROLE = os.getenv("ROLE", "primary").lower()  # 'primary' or 'replica'
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
# Nếu chạy bằng docker-compose, mật khẩu root thường là MYSQL_ROOT_PASSWORD.
DB_PASS = os.getenv("DB_PASS", os.getenv("MYSQL_ROOT_PASSWORD", ""))
DB_NAME = os.getenv("DB_NAME", "distributed_db")


def get_db_connection():
    try:
        return mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
        )
    except mysql.connector.Error:
        return None


def _parse_date(date_str: str | None):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return "__invalid__"


def _node_info() -> str:
    return f"ℹ️ Dữ liệu lấy từ LOCAL node ({ROLE.upper()})"


def _write_blocked_message() -> str:
    return "❌ Node hiện tại là REPLICA (Read-Only). Không cho phép thao tác ghi."


# ==========================================
# 2. DATABASE LOGIC + AUTHORIZATION
# ==========================================


def authenticate(username: str, password: str):
    if not username or not password:
        return None, "⚠️ Vui lòng nhập username và password."

    conn = get_db_connection()
    if conn is None:
        return None, "❌ Không kết nối được database local."

    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT username, role, student_id FROM users WHERE username=%s AND password=%s",
            (username.strip(), password),
        )
        row = cur.fetchone()
        if not row:
            return None, "❌ Sai username/password."

        session = {
            "logged_in": True,
            "username": row["username"],
            "role": row["role"],
            "student_id": row.get("student_id"),
        }
        return session, f"✅ Đăng nhập thành công ({row['role']})."
    except mysql.connector.Error as err:
        return None, f"❌ Lỗi DB: {err}"
    finally:
        if conn and conn.is_connected():
            cur.close()
            conn.close()


def _require_login(session: dict | None):
    if not session or not session.get("logged_in"):
        return False, "⚠️ Bạn cần đăng nhập trước."
    return True, ""


def _require_teacher(session: dict | None):
    ok, msg = _require_login(session)
    if not ok:
        return False, msg
    if session.get("role") != "teacher":
        return False, "❌ Chỉ Teacher mới có quyền thao tác này."
    return True, ""

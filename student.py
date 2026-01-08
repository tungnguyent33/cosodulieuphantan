import mysql.connector

from db import (
    ROLE,
    _node_info,
    _parse_date,
    _require_login,
    _write_blocked_message,
    get_db_connection,
)


def student_load_profile(session: dict | None):
    ok, msg = _require_login(session)
    if not ok:
        return "", "", "", "", "", msg, ""
    if session.get("role") != "student":
        return "", "", "", "", "", "❌ Chỉ Student mới dùng chức năng này.", ""

    sid = session.get("student_id")
    if not sid:
        return "", "", "", "", "", "❌ Tài khoản student chưa được gán student_id.", ""

    conn = get_db_connection()
    if conn is None:
        return "", "", "", "", "", "❌ Không kết nối được database local.", ""

    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id, full_name, class_name, email, date_of_birth, address FROM students WHERE id=%s",
            (int(sid),),
        )
        row = cur.fetchone()
        if not row:
            return "", "", "", "", "", "❌ Không tìm thấy hồ sơ sinh viên.", _node_info()
        dob = row["date_of_birth"].strftime("%Y-%m-%d") if row["date_of_birth"] else ""
        return (
            row.get("full_name") or "",
            row.get("class_name") or "",
            row.get("email") or "",
            dob,
            row.get("address") or "",
            "✅ Đã tải hồ sơ.",
            _node_info(),
        )
    except (mysql.connector.Error, ValueError) as err:
        return "", "", "", "", "", f"❌ Lỗi: {err}", ""
    finally:
        if conn and conn.is_connected():
            cur.close()
            conn.close()


def student_update_profile(session: dict | None, full_name, email, date_of_birth, address):
    ok, msg = _require_login(session)
    if not ok:
        return msg
    if session.get("role") != "student":
        return "❌ Chỉ Student mới có quyền cập nhật thông tin cá nhân."
    if ROLE == "replica":
        return _write_blocked_message()

    sid = session.get("student_id")
    if not sid:
        return "❌ Tài khoản student chưa được gán student_id."

    if not full_name:
        return "⚠️ Họ tên không được để trống."
    dob = _parse_date(date_of_birth)
    if dob == "__invalid__":
        return "⚠️ Ngày sinh không hợp lệ. Định dạng đúng: YYYY-MM-DD."

    conn = get_db_connection()
    if conn is None:
        return "❌ Không kết nối được database local."

    try:
        cur = conn.cursor()
        # Student chỉ được ghi: full_name, address, date_of_birth, email
        cur.execute(
            "UPDATE students SET full_name=%s, email=%s, date_of_birth=%s, address=%s WHERE id=%s",
            (full_name, email, None if dob is None else dob, address, int(sid)),
        )
        conn.commit()
        return "✅ Đã cập nhật thông tin cá nhân."
    except (mysql.connector.Error, ValueError) as err:
        return f"❌ Lỗi: {err}"
    finally:
        if conn and conn.is_connected():
            cur.close()
            conn.close()


def student_scores_table(session: dict | None):
    ok, msg = _require_login(session)
    if not ok:
        return [], msg, ""
    if session.get("role") != "student":
        return [], "❌ Chỉ Student mới dùng chức năng này.", ""

    sid = session.get("student_id")
    if not sid:
        return [], "❌ Tài khoản student chưa được gán student_id.", ""

    conn = get_db_connection()
    if conn is None:
        return [], "❌ Không kết nối được database local.", ""

    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT s.subject_code, s.subject_name, s.credits, sc.score "
            "FROM subjects s "
            "LEFT JOIN scores sc ON sc.subject_id=s.id AND sc.student_id=%s "
            "ORDER BY s.id",
            (int(sid),),
        )
        rows = cur.fetchall() or []
        table = [list(r) for r in rows]
        return table, "", _node_info()
    except (mysql.connector.Error, ValueError) as err:
        return [], f"❌ Lỗi: {err}", ""
    finally:
        if conn and conn.is_connected():
            cur.close()
            conn.close()

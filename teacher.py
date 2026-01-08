import gradio as gr
import mysql.connector

from db import (
    ROLE,
    _node_info,
    _parse_date,
    _require_teacher,
    _write_blocked_message,
    get_db_connection,
)


def list_students_table(session: dict | None):
    ok, msg = _require_teacher(session)
    if not ok:
        return [], msg, _node_info()

    conn = get_db_connection()
    if conn is None:
        return [], "❌ Không kết nối được database local.", ""

    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, full_name, class_name, email, date_of_birth, address "
            "FROM students ORDER BY id"
        )
        rows = cur.fetchall() or []
        table = [list(r) for r in rows]
        return table, "", _node_info()
    except mysql.connector.Error as err:
        return [], f"❌ Lỗi DB: {err}", ""
    finally:
        if conn and conn.is_connected():
            cur.close()
            conn.close()


def get_student_detail(session: dict | None, student_id):
    ok, msg = _require_teacher(session)
    if not ok:
        return "", "", "", "", "", msg, ""

    if not student_id:
        return "", "", "", "", "", "⚠️ Vui lòng nhập Student ID.", _node_info()

    conn = get_db_connection()
    if conn is None:
        return "", "", "", "", "", "❌ Không kết nối được database local.", ""

    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id, full_name, class_name, email, date_of_birth, address "
            "FROM students WHERE id=%s",
            (int(student_id),),
        )
        row = cur.fetchone()
        if not row:
            return "", "", "", "", "", "🔍 Không tìm thấy sinh viên.", _node_info()

        dob = row["date_of_birth"].strftime("%Y-%m-%d") if row["date_of_birth"] else ""
        return (
            row.get("full_name") or "",
            row.get("class_name") or "",
            row.get("email") or "",
            dob,
            row.get("address") or "",
            "✅ Đã tải thông tin sinh viên.",
            _node_info(),
        )
    except (mysql.connector.Error, ValueError) as err:
        return "", "", "", "", "", f"❌ Lỗi: {err}", ""
    finally:
        if conn and conn.is_connected():
            cur.close()
            conn.close()


def teacher_create_student(
    session: dict | None,
    full_name,
    class_name,
    email,
    date_of_birth,
    address,
    username,
    password,
):
    ok, msg = _require_teacher(session)
    if not ok:
        return msg
    if ROLE == "replica":
        return _write_blocked_message()

    if not full_name:
        return "⚠️ Họ tên không được để trống."

    if not username or not str(username).strip():
        return "⚠️ Vui lòng nhập username cho sinh viên."
    if not password:
        return "⚠️ Vui lòng nhập password cho sinh viên."

    dob = _parse_date(date_of_birth)
    if dob == "__invalid__":
        return "⚠️ Ngày sinh không hợp lệ. Định dạng đúng: YYYY-MM-DD."

    conn = get_db_connection()
    if conn is None:
        return "❌ Không kết nối được database local."

    username = str(username).strip()

    try:
        cur = conn.cursor()
        conn.start_transaction()
        cur.execute(
            "INSERT INTO students (full_name, class_name, email, date_of_birth, address) "
            "VALUES (%s,%s,%s,%s,%s)",
            (full_name, class_name, email, None if dob is None else dob, address),
        )
        student_id = cur.lastrowid
        cur.execute(
            "INSERT INTO users (username, password, role, student_id) VALUES (%s,%s,'student',%s)",
            (username, password, student_id),
        )
        conn.commit()
        return f"✅ Đã tạo sinh viên (ID={student_id}) và tài khoản ({username})."
    except mysql.connector.Error as err:
        try:
            conn.rollback()
        except mysql.connector.Error:
            pass

        if getattr(err, "errno", None) == 1062:
            return "⚠️ Username đã tồn tại. Vui lòng chọn username khác."
        return f"❌ Lỗi DB: {err}"
    finally:
        if conn and conn.is_connected():
            cur.close()
            conn.close()


def teacher_update_student(session: dict | None, student_id, full_name, class_name, email, date_of_birth, address):
    ok, msg = _require_teacher(session)
    if not ok:
        return msg
    if ROLE == "replica":
        return _write_blocked_message()
    if not student_id:
        return "⚠️ Vui lòng nhập Student ID."
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
        cur.execute(
            "UPDATE students SET full_name=%s, class_name=%s, email=%s, date_of_birth=%s, address=%s "
            "WHERE id=%s",
            (full_name, class_name, email, None if dob is None else dob, address, int(student_id)),
        )
        conn.commit()
        if cur.rowcount == 0:
            return "🔍 Không tìm thấy sinh viên để cập nhật."
        return "✅ Đã cập nhật sinh viên."
    except (mysql.connector.Error, ValueError) as err:
        return f"❌ Lỗi: {err}"
    finally:
        if conn and conn.is_connected():
            cur.close()
            conn.close()


def teacher_delete_student(session: dict | None, student_id):
    ok, msg = _require_teacher(session)
    if not ok:
        return msg
    if ROLE == "replica":
        return _write_blocked_message()
    if not student_id:
        return "⚠️ Vui lòng nhập Student ID."

    conn = get_db_connection()
    if conn is None:
        return "❌ Không kết nối được database local."

    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM students WHERE id=%s", (int(student_id),))
        conn.commit()
        if cur.rowcount == 0:
            return "🔍 Không tìm thấy sinh viên để xoá."
        return "✅ Đã xoá sinh viên (và các dữ liệu liên quan)."
    except (mysql.connector.Error, ValueError) as err:
        return f"❌ Lỗi: {err}"
    finally:
        if conn and conn.is_connected():
            cur.close()
            conn.close()


def teacher_list_subjects_table(session: dict | None):
    ok, msg = _require_teacher(session)
    if not ok:
        return [], msg, _node_info()

    conn = get_db_connection()
    if conn is None:
        return [], "❌ Không kết nối được database local.", ""

    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, subject_code, subject_name, credits "
            "FROM subjects ORDER BY id"
        )
        rows = cur.fetchall() or []
        table = [list(r) for r in rows]
        return table, "", _node_info()
    except mysql.connector.Error as err:
        return [], f"❌ Lỗi DB: {err}", ""
    finally:
        if conn and conn.is_connected():
            cur.close()
            conn.close()


def teacher_get_subject_detail(session: dict | None, subject_id):
    ok, msg = _require_teacher(session)
    if not ok:
        return "", "", None, msg, ""

    if not subject_id:
        return "", "", None, "⚠️ Vui lòng nhập Subject ID.", _node_info()

    conn = get_db_connection()
    if conn is None:
        return "", "", None, "❌ Không kết nối được database local.", ""

    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id, subject_code, subject_name, credits FROM subjects WHERE id=%s",
            (int(subject_id),),
        )
        row = cur.fetchone()
        if not row:
            return "", "", None, "🔍 Không tìm thấy môn học.", _node_info()

        return (
            row.get("subject_code") or "",
            row.get("subject_name") or "",
            row.get("credits"),
            "✅ Đã tải thông tin môn học.",
            _node_info(),
        )
    except (mysql.connector.Error, ValueError) as err:
        return "", "", None, f"❌ Lỗi: {err}", ""
    finally:
        if conn and conn.is_connected():
            cur.close()
            conn.close()


def _validate_subject_inputs(subject_code, subject_name, credits):
    if not subject_code or not str(subject_code).strip():
        return False, "⚠️ Mã môn (subject_code) không được để trống."
    if not subject_name or not str(subject_name).strip():
        return False, "⚠️ Tên môn (subject_name) không được để trống."

    try:
        credits_int = int(credits) if credits is not None and credits != "" else 3
    except (TypeError, ValueError):
        return False, "⚠️ Số tín chỉ (credits) phải là số nguyên."

    if credits_int <= 0:
        return False, "⚠️ Số tín chỉ (credits) phải > 0."

    return True, credits_int


def teacher_refresh_subjects_ui(session: dict | None):
    """Refresh subject table + dropdown choices (for Teacher UI)."""
    table, msg, node = teacher_list_subjects_table(session)
    dropdown_update, _ = teacher_list_subject_choices(session)
    # Prefer list message for refresh action
    msg = msg or "✅ Đã tải danh sách môn học."
    return table, msg, node, dropdown_update


def teacher_refresh_subjects_ui_keep_msg(session: dict | None, current_msg: str | None):
    """Refresh subject table + dropdown but keep existing message (after CRUD)."""
    table, _, node = teacher_list_subjects_table(session)
    dropdown_update, _ = teacher_list_subject_choices(session)
    return table, (current_msg or ""), node, dropdown_update


def teacher_create_subject(session: dict | None, subject_code, subject_name, credits):
    ok, msg = _require_teacher(session)
    if not ok:
        return msg
    if ROLE == "replica":
        return _write_blocked_message()

    valid, credits_or_msg = _validate_subject_inputs(subject_code, subject_name, credits)
    if not valid:
        return credits_or_msg
    credits_int = credits_or_msg

    conn = get_db_connection()
    if conn is None:
        return "❌ Không kết nối được database local."

    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO subjects (subject_code, subject_name, credits) VALUES (%s, %s, %s)",
            (str(subject_code).strip(), str(subject_name).strip(), credits_int),
        )
        conn.commit()
        return "✅ Đã tạo môn học."
    except mysql.connector.Error as err:
        # Duplicate subject_code
        if getattr(err, "errno", None) == 1062:
            return "⚠️ Mã môn đã tồn tại (subject_code bị trùng)."
        return f"❌ Lỗi DB: {err}"
    finally:
        if conn and conn.is_connected():
            cur.close()
            conn.close()


def teacher_update_subject(session: dict | None, subject_id, subject_code, subject_name, credits):
    ok, msg = _require_teacher(session)
    if not ok:
        return msg
    if ROLE == "replica":
        return _write_blocked_message()

    if not subject_id:
        return "⚠️ Vui lòng nhập Subject ID."

    valid, credits_or_msg = _validate_subject_inputs(subject_code, subject_name, credits)
    if not valid:
        return credits_or_msg
    credits_int = credits_or_msg

    conn = get_db_connection()
    if conn is None:
        return "❌ Không kết nối được database local."

    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE subjects SET subject_code=%s, subject_name=%s, credits=%s WHERE id=%s",
            (str(subject_code).strip(), str(subject_name).strip(), credits_int, int(subject_id)),
        )
        conn.commit()
        if cur.rowcount == 0:
            return "🔍 Không tìm thấy môn học để cập nhật."
        return "✅ Đã cập nhật môn học."
    except (mysql.connector.Error, ValueError) as err:
        if getattr(err, "errno", None) == 1062:
            return "⚠️ Mã môn đã tồn tại (subject_code bị trùng)."
        return f"❌ Lỗi: {err}"
    finally:
        if conn and conn.is_connected():
            cur.close()
            conn.close()


def teacher_delete_subject(session: dict | None, subject_id):
    ok, msg = _require_teacher(session)
    if not ok:
        return msg
    if ROLE == "replica":
        return _write_blocked_message()
    if not subject_id:
        return "⚠️ Vui lòng nhập Subject ID."

    conn = get_db_connection()
    if conn is None:
        return "❌ Không kết nối được database local."

    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM subjects WHERE id=%s", (int(subject_id),))
        conn.commit()
        if cur.rowcount == 0:
            return "🔍 Không tìm thấy môn học để xoá."
        return "✅ Đã xoá môn học (và điểm liên quan nếu có)."
    except (mysql.connector.Error, ValueError) as err:
        return f"❌ Lỗi: {err}"
    finally:
        if conn and conn.is_connected():
            cur.close()
            conn.close()


def teacher_list_subject_choices(session: dict | None):
    ok, msg = _require_teacher(session)
    if not ok:
        return gr.update(choices=[], value=None), msg

    conn = get_db_connection()
    if conn is None:
        return gr.update(choices=[], value=None), "❌ Không kết nối được database local."

    try:
        cur = conn.cursor()
        cur.execute("SELECT id, subject_code, subject_name FROM subjects ORDER BY id")
        rows = cur.fetchall() or []
        # label: "1 - DBD - ..."
        choices = [f"{r[0]} - {r[1]} - {r[2]}" for r in rows]
        return gr.update(choices=choices, value=(choices[0] if choices else None)), ""
    except mysql.connector.Error as err:
        return gr.update(choices=[], value=None), f"❌ Lỗi DB: {err}"
    finally:
        if conn and conn.is_connected():
            cur.close()
            conn.close()


def teacher_get_scores_table(session: dict | None, student_id):
    ok, msg = _require_teacher(session)
    if not ok:
        return [], msg, ""
    if not student_id:
        return [], "⚠️ Vui lòng nhập Student ID.", _node_info()

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
            (int(student_id),),
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


def teacher_upsert_score(session: dict | None, student_id, subject_choice, score_val):
    ok, msg = _require_teacher(session)
    if not ok:
        return msg
    if ROLE == "replica":
        return _write_blocked_message()
    if not student_id:
        return "⚠️ Vui lòng nhập Student ID."
    if not subject_choice:
        return "⚠️ Vui lòng chọn môn học."

    try:
        subject_id = int(str(subject_choice).split("-", 1)[0].strip())
    except (TypeError, ValueError):
        return "⚠️ Môn học không hợp lệ."

    if score_val is None or score_val == "":
        return "⚠️ Vui lòng nhập điểm."
    try:
        score_num = float(score_val)
    except (TypeError, ValueError):
        return "⚠️ Điểm phải là số."
    if score_num < 0 or score_num > 10:
        return "⚠️ Điểm phải trong khoảng 0..10."

    conn = get_db_connection()
    if conn is None:
        return "❌ Không kết nối được database local."

    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO scores (student_id, subject_id, score) VALUES (%s,%s,%s) "
            "ON DUPLICATE KEY UPDATE score=VALUES(score)",
            (int(student_id), subject_id, score_num),
        )
        conn.commit()
        return "✅ Đã cập nhật điểm."
    except (mysql.connector.Error, ValueError) as err:
        return f"❌ Lỗi: {err}"
    finally:
        if conn and conn.is_connected():
            cur.close()
            conn.close()

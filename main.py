import gradio as gr
from db import ROLE, authenticate
from student import student_load_profile, student_scores_table, student_update_profile
from teacher import (
    get_student_detail,
    list_students_table,
    teacher_create_student,
    teacher_create_subject,
    teacher_delete_student,
    teacher_delete_subject,
    teacher_get_scores_table,
    teacher_get_subject_detail,
    teacher_list_subject_choices,
    teacher_refresh_subjects_ui,
    teacher_refresh_subjects_ui_keep_msg,
    teacher_update_student,
    teacher_update_subject,
    teacher_upsert_score,
)


# ==========================================
# 3. GRADIO UI (Login + Teacher/Student)
# ==========================================


def _login_ui_updates(session: dict | None, login_message: str):
    if not session or not session.get("logged_in"):
        return (
            {"logged_in": False},
            login_message,
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(value="### Chưa đăng nhập"),
        )

    who = f"### Đã đăng nhập: `{session['username']}` ({session['role']})"
    teacher_visible = session.get("role") == "teacher"
    student_visible = session.get("role") == "student"
    return (
        session,
        login_message,
        gr.update(visible=teacher_visible),
        gr.update(visible=student_visible),
        gr.update(visible=teacher_visible),
        gr.update(visible=student_visible),
        gr.update(value=who),
    )


def do_login(username, password):
    session, msg = authenticate(username, password)
    return _login_ui_updates(session, msg)


def do_logout():
    return _login_ui_updates(None, "✅ Đã đăng xuất.")


CUSTOM_CSS = """
/* --- Spacing between major Teacher features --- */

#teacher_root .teacher-major-section {
    /* user-requested: increase padding-top/padding-bottom and separate features */
    padding-top: 22px;
    padding-bottom: 22px;
    padding-left: 16px;
    padding-right: 16px;
    margin-top: 28px;
    margin-bottom: 28px;
    border: 1px solid rgba(0, 0, 0, 0.08);
    border-radius: 12px;
    background: rgba(0, 0, 0, 0.02);
}

/* Keep spacing strong between major sections, but avoid excessive outer whitespace */
#teacher_root .teacher-major-section:first-of-type {
    margin-top: 16px;
}

#teacher_root .teacher-major-section:last-of-type {
    margin-bottom: 16px;
}

/* Avoid extra bottom spacing inside a major section */
#teacher_root .teacher-major-section > .gr-block:last-child {
    margin-bottom: 0;
}

/* --- Spacing between major Student features --- */

#student_root .student-major-section {
    padding-top: 22px;
    padding-bottom: 22px;
    padding-left: 16px;
    padding-right: 16px;
    margin-top: 24px;
    margin-bottom: 24px;
    border: 1px solid rgba(0, 0, 0, 0.08);
    border-radius: 12px;
    background: rgba(0, 0, 0, 0.02);
}

#student_root .student-major-section:first-of-type {
    margin-top: 16px;
}

#student_root .student-major-section:last-of-type {
    margin-bottom: 16px;
}

/* Increase spacing between columns/controls inside Student rows */
#student_root .gr-row {
    gap: 16px;
}

/* Avoid extra bottom spacing inside a major section */
#student_root .student-major-section > .gr-block:last-child {
    margin-bottom: 0;
}
"""


with gr.Blocks(title="Distributed Database Final Project", fill_height=True) as demo:
    gr.Markdown("# Distributed Database Final Project – MySQL Replication Demo")
    gr.Markdown(f"### Current Node Role: **{ROLE.upper()}**")
    if ROLE == "replica":
        gr.Warning("Node đang chạy ở chế độ REPLICA (Read-Only): các thao tác ghi sẽ bị chặn.")

    with gr.Accordion("System Overview", open=False):
        gr.Markdown(
            """
        **Distributed Database Concepts:**
        - **Single-Primary Replication:** One node (Primary) handles writes, while others (Replicas) stay in sync for reads.
        - **Data Consistency:** Data is automatically synchronized from Primary to Replica via Binary Logs and GTID.
        - **Location Transparency:** Users interact with their local node without worrying about the underlying replication sync.
        """
        )

    session_state = gr.State({"logged_in": False})

    with gr.Tabs():
        with gr.TabItem("Login"):
            with gr.Row():
                with gr.Column(scale=1):
                    username_in = gr.Textbox(label="Username", placeholder="teacher / student")
                    password_in = gr.Textbox(label="Password", type="password", placeholder="teacher / student")
                    with gr.Row():
                        btn_login = gr.Button("Đăng nhập", variant="primary")
                        btn_logout = gr.Button("Đăng xuất", variant="secondary")
                with gr.Column(scale=2):
                    login_status = gr.Textbox(label="Trạng thái", lines=6, interactive=False)
                    whoami = gr.Markdown("### Chưa đăng nhập")

        # Ẩn tab Teacher/Student trước khi đăng nhập; sau khi login sẽ hiện đúng role.
        with gr.TabItem("Teacher", visible=False) as teacher_tab:
            teacher_group = gr.Group(visible=False, elem_id="teacher_root")
            with teacher_group:
                gr.Markdown("### Teacher Dashboard")

                # --- Major section 1: Student management ---
                with gr.Group(elem_classes=["teacher-major-section"]):
                    with gr.Row():
                        with gr.Column(scale=2):
                            btn_refresh_students = gr.Button("🔄 Tải danh sách sinh viên", variant="secondary")
                            students_table = gr.Dataframe(
                                headers=["ID", "Họ tên", "Lớp", "Email", "Ngày sinh", "Địa chỉ"],
                                datatype=["number", "str", "str", "str", "str", "str"],
                                interactive=False,
                                wrap=True,
                                max_height=360,
                            )
                        with gr.Column(scale=1):
                            teacher_msg = gr.Textbox(label="Thông báo", lines=10, interactive=False)
                            teacher_node = gr.Markdown()

                    gr.Markdown("#### Tạo / Sửa / Xoá sinh viên")
                    with gr.Row():
                        with gr.Column(scale=1):
                            t_student_id = gr.Number(label="Student ID", precision=0)
                            btn_load_student = gr.Button("Tải thông tin theo ID", variant="secondary")
                        with gr.Column(scale=2):
                            t_full_name = gr.Textbox(label="Họ tên")
                            t_class_name = gr.Textbox(label="Lớp")
                            t_email = gr.Textbox(label="Email")
                            t_dob = gr.Textbox(label="Ngày sinh (YYYY-MM-DD)")
                            t_address = gr.Textbox(label="Địa chỉ", lines=3)
                            t_student_username = gr.Textbox(label="Username (tài khoản sinh viên)")
                            t_student_password = gr.Textbox(
                                label="Password (tài khoản sinh viên)",
                                type="password",
                            )

                    with gr.Row():
                        btn_create_student = gr.Button(
                            "➕ Tạo sinh viên",
                            variant="primary",
                            interactive=(ROLE == "primary"),
                        )
                        btn_update_student = gr.Button(
                            "💾 Cập nhật sinh viên",
                            variant="primary",
                            interactive=(ROLE == "primary"),
                        )
                        btn_delete_student = gr.Button(
                            "🗑️ Xoá sinh viên",
                            variant="stop",
                            interactive=(ROLE == "primary"),
                        )

                # --- Major section 2: Subject management ---
                with gr.Group(elem_classes=["teacher-major-section"]):
                    with gr.Accordion("Quản lý môn học (Thêm / Sửa / Xoá / Danh sách)", open=True):
                        with gr.Row():
                            with gr.Column(scale=2):
                                btn_refresh_subjects = gr.Button("🔄 Tải danh sách môn học", variant="secondary")
                                subjects_table = gr.Dataframe(
                                    headers=["ID", "Mã môn", "Tên môn", "Số TC"],
                                    datatype=["number", "str", "str", "number"],
                                    interactive=False,
                                    wrap=True,
                                    max_height=260,
                                )
                            with gr.Column(scale=1):
                                subject_msg = gr.Textbox(label="Thông báo môn học", lines=8, interactive=False)

                        with gr.Row():
                            with gr.Column(scale=1):
                                t_subject_id = gr.Number(label="Subject ID", precision=0)
                                btn_load_subject = gr.Button("Tải môn theo ID", variant="secondary")
                            with gr.Column(scale=2):
                                t_subject_code = gr.Textbox(label="Mã môn (subject_code)")
                                t_subject_name = gr.Textbox(label="Tên môn (subject_name)")
                                t_subject_credits = gr.Number(label="Số tín chỉ (credits)", precision=0)

                        with gr.Row():
                            btn_create_subject = gr.Button(
                                "➕ Tạo môn",
                                variant="primary",
                                interactive=(ROLE == "primary"),
                            )
                            btn_update_subject = gr.Button(
                                "💾 Cập nhật môn",
                                variant="primary",
                                interactive=(ROLE == "primary"),
                            )
                            btn_delete_subject = gr.Button(
                                "🗑️ Xoá môn",
                                variant="stop",
                                interactive=(ROLE == "primary"),
                            )

                # --- Major section 3: Scores-by-subject management ---
                with gr.Group(elem_classes=["teacher-major-section"]):
                    gr.Markdown("#### Quản lý điểm theo môn")
                    with gr.Row():
                        with gr.Column(scale=1):
                            score_student_id = gr.Number(label="Student ID", precision=0)
                            btn_load_scores = gr.Button("Tải bảng môn & điểm", variant="secondary")
                        with gr.Column(scale=2):
                            scores_table = gr.Dataframe(
                                headers=["Mã môn", "Tên môn", "Số TC", "Điểm"],
                                datatype=["str", "str", "number", "number"],
                                interactive=False,
                                wrap=True,
                                max_height=300,
                            )

                    with gr.Row():
                        subject_choice = gr.Dropdown(label="Chọn môn", choices=[])
                        score_value = gr.Number(label="Điểm (0..10)")
                        btn_save_score = gr.Button(
                            "Lưu điểm",
                            variant="primary",
                            interactive=(ROLE == "primary"),
                        )

                    teacher_score_msg = gr.Textbox(label="Kết quả điểm", lines=6, interactive=False)

        with gr.TabItem("Student", visible=False) as student_tab:
            student_group = gr.Group(visible=False, elem_id="student_root")
            with student_group:
                gr.Markdown("### Student Dashboard")
                with gr.Row():
                    with gr.Column(scale=1):
                        btn_load_profile = gr.Button("🔄 Tải hồ sơ của tôi", variant="secondary")
                        btn_load_my_scores = gr.Button("🔄 Tải bảng môn & điểm", variant="secondary")
                    with gr.Column(scale=2):
                        student_msg = gr.Textbox(label="Thông báo", lines=8, interactive=False)
                        student_node = gr.Markdown()

                with gr.Group(elem_classes=["student-major-section"]):
                    gr.Markdown(
                        "#### Thông tin cá nhân (Student chỉ được sửa: họ tên, địa chỉ, ngày sinh, email)"
                    )
                    with gr.Row():
                        s_full_name = gr.Textbox(label="Họ tên")
                        s_class_name = gr.Textbox(label="Lớp (chỉ đọc)", interactive=False)
                    with gr.Row():
                        s_email = gr.Textbox(label="Email")
                        s_dob = gr.Textbox(label="Ngày sinh (YYYY-MM-DD)")
                    s_address = gr.Textbox(label="Địa chỉ", lines=3)

                    btn_update_profile = gr.Button(
                        "Cập nhật thông tin của tôi",
                        variant="primary",
                        interactive=(ROLE == "primary"),
                    )

                with gr.Group(elem_classes=["student-major-section"]):
                    gr.Markdown("#### Môn học & Điểm số")
                    my_scores_table = gr.Dataframe(
                        headers=["Mã môn", "Tên môn", "Số TC", "Điểm"],
                        datatype=["str", "str", "number", "number"],
                        interactive=False,
                        wrap=True,
                        max_height=360,
                    )

    # ---- Events: Login/Logout ----
    btn_login.click(
        do_login,
        inputs=[username_in, password_in],
        outputs=[session_state, login_status, teacher_tab, student_tab, teacher_group, student_group, whoami],
    )
    btn_logout.click(
        do_logout,
        inputs=[],
        outputs=[session_state, login_status, teacher_tab, student_tab, teacher_group, student_group, whoami],
    )

    # ---- Events: Teacher ----
    btn_refresh_students.click(
        list_students_table,
        inputs=[session_state],
        outputs=[students_table, teacher_msg, teacher_node],
    )
    btn_load_student.click(
        get_student_detail,
        inputs=[session_state, t_student_id],
        outputs=[t_full_name, t_class_name, t_email, t_dob, t_address, teacher_msg, teacher_node],
    )
    btn_create_student.click(
        teacher_create_student,
        inputs=[
            session_state,
            t_full_name,
            t_class_name,
            t_email,
            t_dob,
            t_address,
            t_student_username,
            t_student_password,
        ],
        outputs=[teacher_msg],
    ).then(
        list_students_table,
        inputs=[session_state],
        outputs=[students_table, teacher_msg, teacher_node],
    )
    btn_update_student.click(
        teacher_update_student,
        inputs=[session_state, t_student_id, t_full_name, t_class_name, t_email, t_dob, t_address],
        outputs=[teacher_msg],
    ).then(
        list_students_table,
        inputs=[session_state],
        outputs=[students_table, teacher_msg, teacher_node],
    )
    btn_delete_student.click(
        teacher_delete_student,
        inputs=[session_state, t_student_id],
        outputs=[teacher_msg],
    ).then(
        list_students_table,
        inputs=[session_state],
        outputs=[students_table, teacher_msg, teacher_node],
    )

    # ---- Events: Subjects (Teacher) ----
    btn_refresh_subjects.click(
        teacher_refresh_subjects_ui,
        inputs=[session_state],
        outputs=[subjects_table, subject_msg, teacher_node, subject_choice],
    )
    btn_load_subject.click(
        teacher_get_subject_detail,
        inputs=[session_state, t_subject_id],
        outputs=[t_subject_code, t_subject_name, t_subject_credits, subject_msg, teacher_node],
    )
    btn_create_subject.click(
        teacher_create_subject,
        inputs=[session_state, t_subject_code, t_subject_name, t_subject_credits],
        outputs=[subject_msg],
    ).then(
        teacher_refresh_subjects_ui_keep_msg,
        inputs=[session_state, subject_msg],
        outputs=[subjects_table, subject_msg, teacher_node, subject_choice],
    )
    btn_update_subject.click(
        teacher_update_subject,
        inputs=[session_state, t_subject_id, t_subject_code, t_subject_name, t_subject_credits],
        outputs=[subject_msg],
    ).then(
        teacher_refresh_subjects_ui_keep_msg,
        inputs=[session_state, subject_msg],
        outputs=[subjects_table, subject_msg, teacher_node, subject_choice],
    )
    btn_delete_subject.click(
        teacher_delete_subject,
        inputs=[session_state, t_subject_id],
        outputs=[subject_msg],
    ).then(
        teacher_refresh_subjects_ui_keep_msg,
        inputs=[session_state, subject_msg],
        outputs=[subjects_table, subject_msg, teacher_node, subject_choice],
    )

    # Load subject choices when teacher opens/refreshes list
    btn_refresh_students.click(
        teacher_list_subject_choices,
        inputs=[session_state],
        outputs=[subject_choice, teacher_msg],
    )

    btn_load_scores.click(
        teacher_get_scores_table,
        inputs=[session_state, score_student_id],
        outputs=[scores_table, teacher_score_msg, teacher_node],
    )
    btn_save_score.click(
        teacher_upsert_score,
        inputs=[session_state, score_student_id, subject_choice, score_value],
        outputs=[teacher_score_msg],
    ).then(
        teacher_get_scores_table,
        inputs=[session_state, score_student_id],
        outputs=[scores_table, teacher_score_msg, teacher_node],
    )

    # ---- Events: Student ----
    btn_load_profile.click(
        student_load_profile,
        inputs=[session_state],
        outputs=[s_full_name, s_class_name, s_email, s_dob, s_address, student_msg, student_node],
    )
    btn_update_profile.click(
        student_update_profile,
        inputs=[session_state, s_full_name, s_email, s_dob, s_address],
        outputs=[student_msg],
    )
    btn_load_my_scores.click(
        student_scores_table,
        inputs=[session_state],
        outputs=[my_scores_table, student_msg, student_node],
    )


if __name__ == "__main__":
    # If running locally on different machines in LAN, 
    # use server_name="0.0.0.0" to make the UI accessible on the network.
    # Gradio 6.0: `css` moved from `gr.Blocks(...)` to `launch(...)`.
    try:
        demo.launch(server_name="0.0.0.0", server_port=7860, share=True, css=CUSTOM_CSS)
    except TypeError:
        # Backward compatibility for older Gradio versions.
        demo.launch(server_name="0.0.0.0", server_port=7860, share=True)

# Distributed Database Final Project – MySQL Replication Demo

Dự án mô phỏng **Cơ sở dữ liệu phân tán theo kiến trúc Single-Primary Replication** bằng MySQL 8, phục vụ cho bài báo cáo/thi thực hành môn Cơ sở dữ liệu phân tán.

Mô hình Master / Slave theo nhóm 2 thành viên:

- Thành viên 1 (MASTER / MAIN): chạy **PRIMARY** (đọc/ghi)
- Thành viên 2 (SLAVE / REPLICA): chạy **REPLICA** (chỉ đọc, tự đồng bộ từ PRIMARY)
- Thành viên 3 (SLAVE / REPLICA): chạy **REPLICA** (chỉ đọc, tự đồng bộ từ PRIMARY)
- Vân vân...

Mỗi người chạy hệ thống **trên máy cá nhân** với thiết lập env tương ứng
---

## 1) Ý nghĩa đề tài (dùng cho phần báo cáo)

Trong thực tế, cơ sở dữ liệu phân tán thường cần:

- **Tăng tính sẵn sàng và độ tin cậy**: dữ liệu có bản sao ở nhiều nút, giảm rủi ro mất dữ liệu khi một nút gặp sự cố.
- **Mở rộng khả năng đọc (read scaling)**: nhiều nút có thể phục vụ truy vấn đọc cục bộ.
- **Minh bạch vị trí (location transparency)**: người dùng chỉ thao tác với “nút gần mình”, không cần quan tâm dữ liệu đang ở đâu.

Trong phạm vi đề tài học phần, dự án này tập trung minh hoạ **Replication** (nhân bản dữ liệu) — một kỹ thuật cốt lõi trong hệ phân tán:

- **Single-Primary Replication**: chỉ có 1 nút PRIMARY nhận ghi; REPLICA chỉ đọc.
- PRIMARY ghi thay đổi vào **binary log**, REPLICA nhận và áp dụng lại thay đổi.
- Dùng **GTID** để định danh giao dịch, giúp cấu hình replication “tự dò vị trí” (`SOURCE_AUTO_POSITION=1`).

Mục tiêu trình diễn trong buổi vấn đáp:

1. Ghi dữ liệu trên PRIMARY
2. Đọc dữ liệu đó ngay trên REPLICA (đọc từ local nhưng dữ liệu đã được đồng bộ)
3. Chứng minh REPLICA là read-only (UI và DB đều chặn thao tác ghi)

---

## 2) Kiến trúc hệ thống

Hệ thống gồm 2 node:

- **MASTER (MAIN machine)**
  - Cho phép **READ + WRITE**
  - Ghi log thay đổi (binlog)
- **SLAVE (REPLICA machine)**
  - Cho phép **READ-ONLY**
  - Tự đồng bộ dữ liệu từ PRIMARY qua replication

Ứng dụng Python/Gradio trên mỗi máy:

- Kết nối **chỉ tới MySQL local** (container MySQL đang chạy trên chính máy đó)
- Đọc dữ liệu luôn là “đọc local node”

### 2.1) Ứng dụng demo (Gradio) + phân quyền

Ứng dụng `main.py` cung cấp UI Gradio để thao tác với dữ liệu sinh viên (phù hợp demo replication).

- **Login demo** (được tạo trong `students.sql`):
  - Teacher: `teacher/teacher`
  - Student (ví dụ): `student1/student1` (gắn với `student_id=1`)
    - Có sẵn thêm: `student2/student2`, `student3/student3`
- **Phân quyền**:
  - Teacher: tạo/sửa/xoá student; xem danh sách nhiều student dạng bảng; xem & cập nhật điểm theo môn.
  - Student: chỉ được sửa **thông tin của chính mình** gồm `họ tên`, `địa chỉ`, `ngày sinh`, `email`; chỉ được xem bảng môn học & điểm.
- **Ràng buộc replication**: nếu chạy với `ROLE=replica` thì mọi thao tác ghi đều bị chặn (dù login Teacher).

### 2.2) Sơ đồ CSDL (ERD) & ý nghĩa (từ `students.sql`)

Schema demo nằm trong database `distributed_db`, gồm 4 bảng chính phục vụ nghiệp vụ “quản lý sinh viên – môn học – điểm” và 1 bảng user cho phần login UI.

#### Sơ đồ quan hệ (dạng text)

```text
students (1) ──< (N) scores (N) >── (1) subjects
    ^
    |
    └── users (0..1)  (mỗi user role=student có thể gắn 1 student_id; teacher thì NULL)
```

Giải thích nhanh:

- `students` và `subjects` có quan hệ **N-N** (một sinh viên học nhiều môn; một môn có nhiều sinh viên).
- Bảng `scores` là bảng **liên kết (junction/associative table)** để biểu diễn quan hệ N-N đó, đồng thời lưu thêm thuộc tính `score`.
- Bảng `users` phục vụ đăng nhập demo trên Gradio:
  - user `role='teacher'` không gắn với sinh viên nào (`student_id = NULL`)
  - user `role='student'` gắn với đúng **1** sinh viên qua `student_id`

#### Ý nghĩa từng bảng + khoá/ràng buộc

1) Bảng `students`

- **Mục đích**: lưu thông tin cơ bản của sinh viên.
- **Khoá chính (PK)**: `id` (AUTO_INCREMENT).
- **Các cột chính**:
  - `full_name`: họ tên (bắt buộc)
  - `class_name`: lớp (tuỳ chọn)
  - `email`, `date_of_birth`, `address`: thông tin cá nhân (tuỳ chọn)

2) Bảng `subjects`

- **Mục đích**: danh mục môn học.
- **PK**: `id` (AUTO_INCREMENT).
- **Ràng buộc UNIQUE**: `subject_code` (mã môn là duy nhất, ví dụ `DBD`, `DSA`, `PY`).
- `credits`: số tín chỉ (mặc định `3`).

3) Bảng `scores`

- **Mục đích**: lưu điểm của *một sinh viên* theo *một môn*.
- **Khoá chính kép (composite PK)**: `(student_id, subject_id)`
  - đảm bảo mỗi cặp “sinh viên – môn học” chỉ có tối đa 1 bản ghi điểm.
- **Khoá ngoại (FK)**:
  - `student_id` → `students(id)`
  - `subject_id` → `subjects(id)`
- **ON DELETE CASCADE**:
  - xoá một `student` thì các dòng điểm của sinh viên đó trong `scores` bị xoá theo.
  - xoá một `subject` thì các dòng điểm liên quan trong `scores` bị xoá theo.

4) Bảng `users`

- **Mục đích**: bảng tài khoản tối giản cho demo login/phân quyền (lưu password plain-text chỉ để demo trong lớp).
- **PK**: `username`.
- `role`: `ENUM('teacher','student')` để app phân quyền.
- `student_id` (NULLable):
  - chỉ dùng khi `role='student'` để liên kết sang `students(id)`.
  - **UNIQUE** `student_id` để đảm bảo mỗi sinh viên tối đa 1 tài khoản login.
  - **FK** `student_id` → `students(id)` với **ON DELETE CASCADE**:
    - nếu xoá sinh viên thì tài khoản gắn với sinh viên đó cũng bị xoá.
  - **CHECK** đảm bảo ràng buộc role:
    - `role='teacher'` ⇒ `student_id IS NULL`
    - `role='student'` ⇒ `student_id IS NOT NULL`

5) User replication `repl` (phục vụ cấu hình replication)

- Trong `students.sql` có tạo user MySQL `repl`/`replpass` và cấp quyền `REPLICATION SLAVE`.
- **Ý nghĩa**: trên node REPLICA, khi chạy lệnh `CHANGE REPLICATION SOURCE TO ... SOURCE_USER='repl' ...` thì MySQL REPLICA sẽ dùng user này để kết nối sang PRIMARY và đọc binary log/GTID.
- User này **không liên quan** tới login của ứng dụng Gradio (app dùng bảng `users`).

#### Liên hệ với nghiệp vụ demo trong app

- Tab Teacher:
  - đọc danh sách nhiều sinh viên từ `students`
  - xem/cập nhật điểm theo môn bằng cách thao tác trên `scores` (join với `subjects` để hiển thị mã/tên môn)
- Tab Student:
  - đọc thông tin cá nhân của chính mình từ `students` (qua `users.student_id`)
  - xem bảng môn học & điểm của chính mình từ `scores` + `subjects`

### Ghi chú: Auto-increment theo node để tránh trùng ID (tuỳ chọn)

Nếu có tình huống **nhiều node cùng ghi** (ví dụ chuyển sang multi-primary/active-active), cần cấu hình:

- `auto_increment_increment = N` (N = số node có thể ghi)
- `auto_increment_offset = i` (i = số thứ tự duy nhất của node, trong khoảng `1..N`)

Khi đó các node sẽ sinh ID xen kẽ nhau (ví dụ N=2: node 1 sinh `1,3,5,...`; node 2 sinh `2,4,6,...`) giúp tránh trùng khoá chính khi replication.

---

## 3) Yêu cầu mạng (LAN)

- Hai máy phải cùng **mạng LAN**.
- Trên máy PRIMARY, cần mở cổng **3306/TCP** để máy REPLICA kết nối replication.
  - Cổng **7860/TCP** chỉ cần mở nếu bạn muốn truy cập UI Gradio từ máy khác trong LAN (tuỳ chọn).
- Xác định IP LAN của máy PRIMARY (ví dụ `192.168.1.10`).

Gợi ý kiểm tra nhanh:

- Từ máy REPLICA ping IP của PRIMARY (nếu bị chặn ICMP thì bỏ qua)
- Đảm bảo firewall không chặn kết nối tới `PRIMARY_IP:3306` và `PRIMARY_IP:7860` (nếu cần truy cập UI)

---

## 4) Cài đặt môi trường (step-by-step)

### 4.1. Chuẩn bị chung (cả 2 máy)

1. Cài **Docker Desktop** (có Docker Engine và Docker Compose) để chạy MySQL container.
2. Cài **Python 3** và `pip`.
3. Tải source code dự án về máy (clone hoặc copy thư mục).

---

## 5) Thiết lập MySQL PRIMARY (máy MAIN)

### Bước 1: Khởi động MySQL PRIMARY bằng Docker Compose

Trong thư mục dự án, chạy:

```bash
docker compose -f docker-compose.primary.yml up -d
```

Nếu máy bạn chưa có plugin `docker compose` (Compose v2), có thể thử lệnh cũ:

```bash
docker-compose -f docker-compose.primary.yml up -d
```

Kiểm tra container:

```bash
docker ps
```

Bạn sẽ thấy container tên `mysql_primary`.

### Bước 2: Kiểm tra database/table đã được khởi tạo

File `students.sql` được mount vào `docker-entrypoint-initdb.d/` nên sẽ tự chạy khi container tạo mới.

Vào MySQL trong container:

```bash
docker exec -it mysql_primary mysql -u root -pdistributed_password
```

Chạy các lệnh kiểm tra:

```sql
SHOW DATABASES;
USE distributed_db;
SHOW TABLES;
SELECT COUNT(*) FROM students;
```

### Bước 3: Kiểm tra các biến cấu hình replication (tuỳ chọn, để trình diễn)

```sql
SHOW VARIABLES LIKE 'server_id';
SHOW VARIABLES LIKE 'gtid_mode';
SHOW VARIABLES LIKE 'enforce_gtid_consistency';
SHOW VARIABLES LIKE 'binlog_format';
```

Kỳ vọng:

- `server_id = 1`
- `gtid_mode = ON`
- `enforce_gtid_consistency = ON`
- `binlog_format = ROW`

Ghi chú: nếu bạn muốn demo thêm phần chống trùng ID theo node (auto-increment increment/offset), hãy tự bổ sung thêm các flag `--auto_increment_increment` và `--auto_increment_offset` trong file compose.

### Bước 4: Xác nhận user replication

`students.sql` cũng tạo user replication:

- User: `repl`
- Password: `replpass`

Bạn có thể kiểm tra:

```sql
SELECT user, host FROM mysql.user WHERE user='repl';
```

---

## 6) Thiết lập MySQL REPLICA (máy thứ 2)

### Bước 1: Khởi động MySQL REPLICA

Trong thư mục dự án trên máy REPLICA:

```bash
docker compose -f docker-compose.replica.yml up -d
```

Nếu máy bạn chưa có plugin `docker compose` (Compose v2), có thể thử lệnh cũ:

```bash
docker-compose -f docker-compose.replica.yml up -d
```

Kiểm tra container:

```bash
docker ps
```

Bạn sẽ thấy container tên `mysql_replica`.

### Bước 2: Vào MySQL trong container REPLICA

```bash
docker exec -it mysql_replica mysql -u root -pdistributed_password
```

### Bước 3: Cấu hình nguồn replication (trỏ về PRIMARY)

Thay `PRIMARY_IP` bằng IP LAN thật của máy PRIMARY:

```sql
CHANGE REPLICATION SOURCE TO
  SOURCE_HOST='PRIMARY_IP',
  SOURCE_PORT=3306,
  SOURCE_USER='repl',
  SOURCE_PASSWORD='replpass',
  SOURCE_AUTO_POSITION=1;

START REPLICA;
```

### Bước 4: Kiểm tra trạng thái replication

```sql
SHOW REPLICA STATUS\G
```

Các trường quan trọng cần quan sát:

- `Replica_IO_Running: Yes`
- `Replica_SQL_Running: Yes`
- `Last_IO_Error` / `Last_SQL_Error` rỗng

Ghi chú: một số bản MySQL hiển thị tên cột kiểu cũ (`Slave_IO_Running`, `Slave_SQL_Running`). Chỉ cần đảm bảo cả 2 “luồng IO” và “luồng SQL” đều đang chạy.

### Bước 5: Xác nhận REPLICA là read-only

REPLICA được bật `--read-only=ON` trong `docker-compose.replica.yml`.

Bạn có thể kiểm tra:

```sql
SHOW VARIABLES LIKE 'read_only';
```

Kỳ vọng:

- `read_only = ON`

---

## 7) Chạy ứng dụng Gradio (step-by-step)

### Bước 1: Cài thư viện Python

Trên từng máy:

```bash
pip install -r requirements.txt
```

### Bước 2: Thiết lập vai trò node bằng file `.env` (khuyến nghị)

Trong thư mục dự án, bạn có thể **tạo** file `.env` để cấu hình nhanh. Trên **mỗi máy**, hãy tạo/mở `.env` và đặt:

- Trên máy PRIMARY (MAIN):

```env
ROLE=primary
# (tuỳ chọn) nếu DB không phải localhost/root hoặc cần set rõ:
# DB_HOST=localhost
# DB_USER=root
# DB_PASS=distributed_password
# DB_NAME=distributed_db
```

- Trên máy REPLICA:

```env
ROLE=replica
# DB_PASS=distributed_password
```

Ghi chú: nếu bạn đặt biến môi trường bằng `export ROLE=...` / `$env:ROLE=...` thì biến môi trường hệ thống sẽ **ưu tiên hơn** `.env`.

### Bước 3: Chạy app (PRIMARY hoặc REPLICA)

macOS/Linux:

```bash
python main.py
```

Windows PowerShell:

```powershell
python main.py
```

Tuỳ chọn (nếu muốn set nhanh qua shell, không cần chỉnh `.env`):

- macOS/Linux:

```bash
export ROLE=primary   # hoặc replica
python main.py
```

- Windows PowerShell:

```powershell
$env:ROLE="primary"  # hoặc replica
python main.py
```

Mặc định app chạy ở `0.0.0.0:7860` (truy cập được trong LAN). Bạn có thể mở trình duyệt vào:

- `http://localhost:7860` (trên chính máy chạy app)

Ghi chú:

- `main.py` hiện đang dùng `share=True` (Gradio) để tạo link public phục vụ demo nhanh.
  - Nếu không muốn expose ra Internet, bạn có thể đổi `share=False` trong `main.py`.

---

## 8) Kịch bản demo cho buổi vấn đáp (đề xuất)

1. **Chuẩn bị**: bật 2 container MySQL và chạy 2 app Gradio trên 2 máy.
2. **Trạng thái ban đầu**:
   - Vào tab `Login` → đăng nhập `teacher/teacher`.
   - Vào tab `Teacher` → bấm `🔄 Tải danh sách sinh viên` để thấy dữ liệu demo (3 sinh viên + môn học + điểm mẫu).
   - (Tuỳ chọn) đăng nhập `student1/student1` để demo Student chỉ xem/sửa dữ liệu của chính mình.
3. **Ghi trên PRIMARY (demo thao tác ghi)**:
   - Trên máy PRIMARY, tab `Teacher`:
     - (Cách 1) Tạo mới sinh viên (nhập họ tên/lớp/email/ngày sinh/địa chỉ + `username/password` cho sinh viên) → `Tạo sinh viên`.
     - (Cách 2) Chọn một sinh viên có sẵn và cập nhật điểm theo môn → `Lưu/Cập nhật điểm`.
4. **Đọc trên PRIMARY**: `🔄 Tải danh sách sinh viên` / `Tải bảng môn & điểm` để thấy dữ liệu đã thay đổi.
5. **Đọc ngay trên REPLICA (đọc local nhưng đã đồng bộ)**:
   - Trên máy REPLICA, cũng đăng nhập `teacher/teacher`.
   - `🔄 Tải danh sách sinh viên` / `Tải bảng môn & điểm` → dữ liệu mới xuất hiện sau khi replication đồng bộ.
6. **Chứng minh REPLICA không cho ghi**:
   - Trên REPLICA, các nút ghi (tạo/sửa/xoá/cập nhật điểm) sẽ bị vô hiệu hoá hoặc trả về thông báo từ chối do `ROLE=replica`.
   - Có thể vào MySQL REPLICA và thử `INSERT/UPDATE` để thấy bị từ chối do read-only.
7. **Tính bền vững**: restart container MySQL (hoặc stop/start) và chứng minh dữ liệu vẫn tồn tại (tuỳ cấu hình volume; trong demo này, dữ liệu vẫn tồn tại trong vòng đời container đang chạy; nếu muốn “bền vững thật sự qua recreate”, hãy bổ sung volume named trong compose).

---

## 9) Cấu trúc project

- `main.py`: UI Gradio + event wiring (import nghiệp vụ từ các module bên dưới).
- `db.py`: load `.env`, cấu hình `ROLE`/DB, tạo kết nối MySQL, và các helper xác thực/phân quyền dùng chung.
- `teacher.py`: nghiệp vụ Teacher (CRUD `students`, CRUD `subjects`, xem/cập nhật `scores`).
- `student.py`: nghiệp vụ Student (tải/cập nhật hồ sơ, xem bảng môn & điểm).
- `.env`: Cấu hình vai trò node (PRIMARY/REPLICA) để app tự load khi chạy.
- `students.sql`: Tạo database `distributed_db`, các table `students`, `subjects`, `scores`, `users`, dữ liệu demo và user replication (`repl/replpass`).
- `docker-compose.primary.yml`: MySQL PRIMARY (server-id=1, GTID, binlog ROW).
- `docker-compose.replica.yml`: MySQL REPLICA (server-id=2, GTID, binlog ROW, read-only).
- `requirements.txt`: Thư viện Python cần cài.

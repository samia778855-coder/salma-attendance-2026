from flask import Flask, render_template, request, jsonify, send_file
import sqlite3
from pathlib import Path
from datetime import date, datetime
from io import BytesIO
import shutil
import pandas as pd


app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DB_FILE = BASE_DIR / "attendance.db"
BACKUP_DIR = BASE_DIR / "backups"

GRADES = [str(i) for i in range(5, 13)]
SECTIONS = [str(i) for i in range(1, 6)]

GRADE_NAMES = {
    "5": "خامس",
    "6": "سادس",
    "7": "سابع",
    "8": "ثامن",
    "9": "تاسع",
    "10": "عاشر",
    "11": "حادي عشر",
    "12": "ثاني عشر",
}


# =========================================================
# DATABASE
# =========================================================

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def table_columns(conn, table_name):
    rows = conn.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return {row["name"] for row in rows}


def add_column_if_missing(conn, table, column, definition):
    columns = table_columns(conn, table)

    if column not in columns:
        conn.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
        )


def ensure_database():
    conn = get_db()

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            grade TEXT NOT NULL,
            section TEXT NOT NULL,
            father_phone TEXT DEFAULT '',
            mother_phone TEXT DEFAULT '',
            father_phone_status TEXT DEFAULT 'غير متوفر',
            mother_phone_status TEXT DEFAULT 'غير متوفر',
            active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            attendance_date TEXT NOT NULL,
            teacher_name TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            academic_year TEXT DEFAULT '',
            note TEXT DEFAULT '',
            absence_status TEXT DEFAULT 'مسجل',
            FOREIGN KEY(student_id) REFERENCES students(id),
            UNIQUE(student_id, attendance_date)
        );

        CREATE TABLE IF NOT EXISTS class_registration (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grade TEXT NOT NULL,
            section TEXT NOT NULL,
            registration_date TEXT NOT NULL,
            teacher_name TEXT NOT NULL,
            no_absence INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            academic_year TEXT DEFAULT '',
            UNIQUE(grade, section, registration_date)
        );

        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            notification_type TEXT,
            phone_type TEXT,
            phone_number TEXT,
            notification_date TEXT,
            note TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(student_id) REFERENCES students(id)
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            description TEXT,
            teacher_name TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            setting_key TEXT UNIQUE NOT NULL,
            setting_value TEXT DEFAULT ''
        );
    """)

    # دعم قواعد البيانات القديمة
    add_column_if_missing(
        conn,
        "students",
        "active",
        "INTEGER DEFAULT 1"
    )

    add_column_if_missing(
        conn,
        "students",
        "created_at",
        "TEXT DEFAULT ''"
    )

    add_column_if_missing(
        conn,
        "attendance",
        "academic_year",
        "TEXT DEFAULT ''"
    )

    add_column_if_missing(
        conn,
        "attendance",
        "note",
        "TEXT DEFAULT ''"
    )

    add_column_if_missing(
        conn,
        "attendance",
        "absence_status",
        "TEXT DEFAULT 'مسجل'"
    )

    add_column_if_missing(
        conn,
        "class_registration",
        "academic_year",
        "TEXT DEFAULT ''"
    )

    defaults = {
        "school_name":
            "مدرسة سلمى بنت قيس للتعليم الأساسي (5–12)",

        "academic_year":
            "2026/2027",

        "absence_alert_limit":
            "8",

        "daily_message":
            "نود إفادتكم أن ابنتكم ({student}) "
            "قد تغيبت اليوم بتاريخ ({date}). "
            "مع تحيات إدارة مدرسة سلمى بنت قيس "
            "للتعليم الأساسي (5–12).",

        "alert_message":
            "نود إفادتكم أن ابنتكم ({student}) "
            "قد تجاوزت عدد الغياب {limit} أيام، "
            "يرجى متابعة الموضوع لدى إدارة مدرسة "
            "سلمى بنت قيس للتعليم الأساسي."
    }

    for key, value in defaults.items():
        conn.execute("""
            INSERT OR IGNORE INTO settings (
                setting_key,
                setting_value
            )
            VALUES (?, ?)
        """, (key, value))

    year = conn.execute("""
        SELECT setting_value
        FROM settings
        WHERE setting_key = 'academic_year'
    """).fetchone()

    current_year = (
        year["setting_value"]
        if year
        else "2026/2027"
    )

    conn.execute("""
        UPDATE attendance
        SET academic_year = ?
        WHERE academic_year IS NULL
           OR academic_year = ''
    """, (current_year,))

    conn.execute("""
        UPDATE class_registration
        SET academic_year = ?
        WHERE academic_year IS NULL
           OR academic_year = ''
    """, (current_year,))

    conn.commit()
    conn.close()


ensure_database()


# =========================================================
# HELPERS
# =========================================================

def get_setting(key, default=""):
    conn = get_db()

    row = conn.execute("""
        SELECT setting_value
        FROM settings
        WHERE setting_key = ?
    """, (key,)).fetchone()

    conn.close()

    if row:
        return row["setting_value"]

    return default


def set_setting(key, value):
    conn = get_db()

    conn.execute("""
        INSERT INTO settings (
            setting_key,
            setting_value
        )
        VALUES (?, ?)
        ON CONFLICT(setting_key)
        DO UPDATE SET setting_value = excluded.setting_value
    """, (key, value))

    conn.commit()
    conn.close()


def convert_arabic_digits(value):
    if value is None:
        return ""

    value = str(value)

    mapping = str.maketrans(
        "٠١٢٣٤٥٦٧٨٩",
        "0123456789"
    )

    return value.translate(mapping)


def clean_phone(value):
    value = convert_arabic_digits(value)

    digits = "".join(
        ch for ch in value
        if ch.isdigit()
    )

    if digits.startswith("00968"):
        digits = digits[5:]

    elif digits.startswith("968") and len(digits) == 11:
        digits = digits[3:]

    if len(digits) == 8:
        return digits

    return digits


def phone_status(phone):
    if not phone:
        return "غير متوفر"

    if len(phone) == 8 and phone.isdigit():
        return "متوفر"

    return "يحتاج مراجعة"


def current_academic_year():
    return get_setting(
        "academic_year",
        "2026/2027"
    )


def get_actual_classes():
    conn = get_db()

    rows = conn.execute("""
        SELECT DISTINCT grade, section
        FROM students
        WHERE active = 1
        ORDER BY
            CAST(grade AS INTEGER) DESC,
            CAST(section AS INTEGER) DESC
    """).fetchall()

    conn.close()

    return [
        (str(row["grade"]), str(row["section"]))
        for row in rows
    ]


def get_unregistered_classes():
    today = date.today().isoformat()
    academic_year = current_academic_year()

    actual_classes = get_actual_classes()

    conn = get_db()

    rows = conn.execute("""
        SELECT grade, section
        FROM class_registration
        WHERE registration_date = ?
          AND academic_year = ?
    """, (
        today,
        academic_year
    )).fetchall()

    conn.close()

    registered = {
        (
            str(row["grade"]),
            str(row["section"])
        )
        for row in rows
    }

    missing = []

    for grade, section in actual_classes:
        if (grade, section) not in registered:
            missing.append({
                "grade": grade,
                "grade_name":
                    GRADE_NAMES.get(
                        grade,
                        grade
                    ),
                "section": section
            })

    return missing


def calculate_dashboard():
    today = date.today().isoformat()
    academic_year = current_academic_year()

    conn = get_db()

    total_students = conn.execute("""
        SELECT COUNT(*)
        FROM students
        WHERE active = 1
    """).fetchone()[0]

    absent_today = conn.execute("""
        SELECT COUNT(DISTINCT student_id)
        FROM attendance
        WHERE attendance_date = ?
          AND academic_year = ?
    """, (
        today,
        academic_year
    )).fetchone()[0]

    registered_classes = conn.execute("""
        SELECT COUNT(*)
        FROM class_registration
        WHERE registration_date = ?
          AND academic_year = ?
    """, (
        today,
        academic_year
    )).fetchone()[0]

    try:
        alert_limit = int(
            get_setting(
                "absence_alert_limit",
                "8"
            )
        )
    except ValueError:
        alert_limit = 8

    alerts = conn.execute("""
        SELECT COUNT(*)
        FROM (
            SELECT student_id
            FROM attendance
            WHERE academic_year = ?
            GROUP BY student_id
            HAVING COUNT(*) > ?
        )
    """, (
        academic_year,
        alert_limit
    )).fetchone()[0]

    conn.close()

    total_classes = len(
        get_actual_classes()
    )

    unregistered_count = max(
        total_classes - registered_classes,
        0
    )

    if total_students:
        absence_percentage = round(
            absent_today / total_students * 100,
            2
        )
    else:
        absence_percentage = 0

    completion_percentage = 0

    if total_classes:
        completion_percentage = round(
            registered_classes /
            total_classes *
            100
        )

    return {
        "total_students":
            total_students,

        "absent_today":
            absent_today,

        "absence_percentage":
            absence_percentage,

        "registered_classes":
            registered_classes,

        "unregistered_count":
            unregistered_count,

        "total_classes":
            total_classes,

        "completion_percentage":
            completion_percentage,

        "alerts":
            alerts
    }


def audit(action, description, teacher_name=""):
    conn = get_db()

    conn.execute("""
        INSERT INTO audit_log (
            action,
            description,
            teacher_name
        )
        VALUES (?, ?, ?)
    """, (
        action,
        description,
        teacher_name
    ))

    conn.commit()
    conn.close()


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():
    return render_template(
        "index.html",
        today=date.today().isoformat(),
        school_name=get_setting(
            "school_name",
            "مدرسة سلمى بنت قيس للتعليم الأساسي (5–12)"
        ),
        academic_year=current_academic_year(),
        alert_limit=get_setting(
            "absence_alert_limit",
            "8"
        )
    )


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/api/dashboard")
def dashboard_api():
    data = calculate_dashboard()

    data["unregistered_classes"] = (
        get_unregistered_classes()
    )

    return jsonify(data)


@app.route("/api/class-status")
def class_status():
    today = date.today().isoformat()
    year = current_academic_year()

    actual_classes = get_actual_classes()

    conn = get_db()

    rows = conn.execute("""
        SELECT
            grade,
            section,
            teacher_name,
            no_absence,
            created_at
        FROM class_registration
        WHERE registration_date = ?
          AND academic_year = ?
    """, (
        today,
        year
    )).fetchall()

    conn.close()

    registered_map = {
        (
            str(row["grade"]),
            str(row["section"])
        ): row
        for row in rows
    }

    result = []

    for grade, section in actual_classes:
        row = registered_map.get(
            (grade, section)
        )

        if row:
            result.append({
                "grade":
                    grade,

                "grade_name":
                    GRADE_NAMES.get(
                        grade,
                        grade
                    ),

                "section":
                    section,

                "registered":
                    True,

                "teacher_name":
                    row["teacher_name"],

                "no_absence":
                    bool(
                        row["no_absence"]
                    ),

                "created_at":
                    row["created_at"]
            })

        else:
            result.append({
                "grade":
                    grade,

                "grade_name":
                    GRADE_NAMES.get(
                        grade,
                        grade
                    ),

                "section":
                    section,

                "registered":
                    False,

                "teacher_name":
                    "",

                "no_absence":
                    False,

                "created_at":
                    ""
            })

    return jsonify(result)


# =========================================================
# STUDENTS
# =========================================================

@app.route("/api/students")
def students_by_class():
    grade = request.args.get(
        "grade",
        ""
    ).strip()

    section = request.args.get(
        "section",
        ""
    ).strip()

    if not grade or not section:
        return jsonify([])

    conn = get_db()

    rows = conn.execute("""
        SELECT
            id,
            student_name,
            grade,
            section,
            father_phone,
            mother_phone,
            father_phone_status,
            mother_phone_status
        FROM students
        WHERE grade = ?
          AND section = ?
          AND active = 1
        ORDER BY student_name
    """, (
        grade,
        section
    )).fetchall()

    conn.close()

    return jsonify([
        dict(row)
        for row in rows
    ])


@app.route(
    "/api/student-search"
)
def student_search():
    query = request.args.get(
        "q",
        ""
    ).strip()

    if not query:
        return jsonify([])

    year = current_academic_year()

    conn = get_db()

    rows = conn.execute("""
        SELECT
            students.*,
            COUNT(attendance.id) AS absence_count,
            MAX(attendance.attendance_date) AS last_absence
        FROM students
        LEFT JOIN attendance
            ON attendance.student_id = students.id
           AND attendance.academic_year = ?
        WHERE students.student_name LIKE ?
        GROUP BY students.id
        ORDER BY students.student_name
        LIMIT 50
    """, (
        year,
        f"%{query}%"
    )).fetchall()

    conn.close()

    return jsonify([
        dict(row)
        for row in rows
    ])


@app.route(
    "/api/student",
    methods=["POST"]
)
def add_student():
    data = request.get_json() or {}

    student_name = str(
        data.get(
            "student_name",
            ""
        )
    ).strip()

    grade = str(
        data.get(
            "grade",
            ""
        )
    ).strip()

    section = str(
        data.get(
            "section",
            ""
        )
    ).strip()

    father_phone = clean_phone(
        data.get(
            "father_phone",
            ""
        )
    )

    mother_phone = clean_phone(
        data.get(
            "mother_phone",
            ""
        )
    )

    if (
        not student_name
        or not grade
        or not section
    ):
        return jsonify({
            "success":
                False,

            "message":
                "اسم الطالبة والمرحلة والشعبة مطلوبة."
        }), 400

    conn = get_db()

    duplicate = conn.execute("""
        SELECT id
        FROM students
        WHERE student_name = ?
          AND grade = ?
          AND section = ?
          AND active = 1
    """, (
        student_name,
        grade,
        section
    )).fetchone()

    if duplicate:
        conn.close()

        return jsonify({
            "success":
                False,

            "message":
                "هذه الطالبة موجودة مسبقًا في نفس الصف."
        }), 409

    cursor = conn.execute("""
        INSERT INTO students (
            student_name,
            grade,
            section,
            father_phone,
            mother_phone,
            father_phone_status,
            mother_phone_status,
            active
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 1)
    """, (
        student_name,
        grade,
        section,
        father_phone,
        mother_phone,
        phone_status(
            father_phone
        ),
        phone_status(
            mother_phone
        )
    ))

    conn.commit()

    student_id = (
        cursor.lastrowid
    )

    conn.close()

    audit(
        "إضافة طالبة",
        f"تمت إضافة الطالبة {student_name} في الصف {grade}/{section}",
        "الإدارة"
    )

    return jsonify({
        "success":
            True,

        "student_id":
            student_id,

        "message":
            "تمت إضافة الطالبة بنجاح."
    })


@app.route(
    "/api/student/<int:student_id>",
    methods=["PUT"]
)
def update_student(student_id):
    data = request.get_json() or {}

    student_name = str(
        data.get(
            "student_name",
            ""
        )
    ).strip()

    grade = str(
        data.get(
            "grade",
            ""
        )
    ).strip()

    section = str(
        data.get(
            "section",
            ""
        )
    ).strip()

    father_phone = clean_phone(
        data.get(
            "father_phone",
            ""
        )
    )

    mother_phone = clean_phone(
        data.get(
            "mother_phone",
            ""
        )
    )

    if (
        not student_name
        or not grade
        or not section
    ):
        return jsonify({
            "success":
                False,

            "message":
                "الاسم والمرحلة والشعبة مطلوبة."
        }), 400

    conn = get_db()

    current = conn.execute("""
        SELECT *
        FROM students
        WHERE id = ?
    """, (
        student_id,
    )).fetchone()

    if not current:
        conn.close()

        return jsonify({
            "success":
                False,

            "message":
                "الطالبة غير موجودة."
        }), 404

    conn.execute("""
        UPDATE students
        SET
            student_name = ?,
            grade = ?,
            section = ?,
            father_phone = ?,
            mother_phone = ?,
            father_phone_status = ?,
            mother_phone_status = ?
        WHERE id = ?
    """, (
        student_name,
        grade,
        section,
        father_phone,
        mother_phone,
        phone_status(
            father_phone
        ),
        phone_status(
            mother_phone
        ),
        student_id
    ))

    conn.commit()
    conn.close()

    audit(
        "تعديل طالبة",
        f"تم تعديل بيانات الطالبة {student_name}",
        "الإدارة"
    )

    return jsonify({
        "success":
            True,

        "message":
            "تم تحديث بيانات الطالبة بنجاح."
    })


@app.route(
    "/api/student/<int:student_id>/deactivate",
    methods=["PUT"]
)
def deactivate_student(student_id):
    conn = get_db()

    student = conn.execute("""
        SELECT student_name
        FROM students
        WHERE id = ?
    """, (
        student_id,
    )).fetchone()

    if not student:
        conn.close()

        return jsonify({
            "success":
                False,

            "message":
                "الطالبة غير موجودة."
        }), 404

    conn.execute("""
        UPDATE students
        SET active = 0
        WHERE id = ?
    """, (
        student_id,
    ))

    conn.commit()
    conn.close()

    audit(
        "تعطيل طالبة",
        f"تم تعطيل الطالبة {student['student_name']}",
        "الإدارة"
    )

    return jsonify({
        "success":
            True,

        "message":
            "تم تعطيل الطالبة دون حذف سجل غيابها."
    })


@app.route(
    "/api/missing-phones"
)
def missing_phones():
    conn = get_db()

    rows = conn.execute("""
        SELECT
            id,
            student_name,
            grade,
            section,
            father_phone,
            mother_phone,
            father_phone_status,
            mother_phone_status
        FROM students
        WHERE active = 1
          AND (
                father_phone_status != 'متوفر'
             OR mother_phone_status != 'متوفر'
          )
        ORDER BY
            CAST(grade AS INTEGER),
            CAST(section AS INTEGER),
            student_name
    """).fetchall()

    conn.close()

    return jsonify([
        dict(row)
        for row in rows
    ])



def parse_class_value(value):
    value = convert_arabic_digits(value).strip().replace("\\", "/").replace(" ", "")
    parts = [x for x in value.split("/") if x]
    if len(parts) < 2 or parts[0] not in GRADES or parts[1] not in SECTIONS:
        return "", ""
    return parts[0], parts[1]


def read_students_excel(file_storage):
    df = pd.read_excel(file_storage, dtype=str).fillna("")
    required = ["اسم الطالبة", "الصف", "رقم هاتف الأب", "رقم هاتف الأم"]
    if any(c not in df.columns for c in required):
        raise ValueError("الأعمدة المطلوبة هي: " + "، ".join(required))
    rows, issues, seen = [], [], set()
    for idx, row in df.iterrows():
        name = str(row["اسم الطالبة"]).strip()
        grade, section = parse_class_value(row["الصف"])
        father, mother = clean_phone(row["رقم هاتف الأب"]), clean_phone(row["رقم هاتف الأم"])
        if not name or not grade or not section:
            issues.append({"row": int(idx)+2, "student_name": name or "-", "reason": "اسم أو صف/شعبة غير صالح"}); continue
        key = name.casefold()
        if key in seen:
            issues.append({"row": int(idx)+2, "student_name": name, "reason": "اسم مكرر داخل ملف Excel"}); continue
        seen.add(key)
        rows.append({"student_name":name,"grade":grade,"section":section,"father_phone":father,"mother_phone":mother,"father_phone_status":phone_status(father),"mother_phone_status":phone_status(mother)})
    return rows, issues


def compare_excel_students(rows, issues):
    conn=get_db(); existing=conn.execute("SELECT * FROM students ORDER BY id").fetchall(); conn.close()
    by_name={}
    for r in existing: by_name.setdefault(str(r["student_name"]).strip().casefold(), []).append(r)
    new_rows, updates, unchanged=[], [], 0
    for item in rows:
        matches=by_name.get(item["student_name"].casefold(), [])
        if len(matches)>1:
            issues.append({"row":"-","student_name":item["student_name"],"reason":"يوجد أكثر من سجل بنفس الاسم في قاعدة البيانات؛ يحتاج مراجعة يدوية"}); continue
        if not matches: new_rows.append(item); continue
        old=matches[0]
        changed=any(str(old[k] or "") != str(item[k] or "") for k in ["grade","section","father_phone","mother_phone"]) or int(old["active"] or 0)!=1
        if changed:
            update=dict(item); update.update({"id":old["id"],"old_class":f'{old["grade"]}/{old["section"]}',"new_class":f'{item["grade"]}/{item["section"]}'})
            updates.append(update)
        else: unchanged += 1
    return {"new":new_rows,"updates":updates,"unchanged":unchanged,"issues":issues}


@app.route("/api/students/import-preview", methods=["POST"])
def students_import_preview():
    file=request.files.get("file")
    if not file or not file.filename: return jsonify({"success":False,"message":"اختاري ملف Excel أولًا."}),400
    try:
        rows,issues=read_students_excel(file); result=compare_excel_students(rows,issues)
        return jsonify({"success":True,"total_valid":len(rows),"new_count":len(result["new"]),"update_count":len(result["updates"]),"unchanged_count":result["unchanged"],"issue_count":len(result["issues"]),"updates":result["updates"][:100],"issues":result["issues"][:100]})
    except Exception as error: return jsonify({"success":False,"message":f"تعذر قراءة الملف: {error}"}),400


@app.route("/api/students/import-confirm", methods=["POST"])
def students_import_confirm():
    file=request.files.get("file")
    if not file or not file.filename: return jsonify({"success":False,"message":"اختاري ملف Excel أولًا."}),400
    try:
        rows,issues=read_students_excel(file); result=compare_excel_students(rows,issues)
        if result["issues"]: return jsonify({"success":False,"message":"يوجد في الملف بيانات تحتاج مراجعة. أصلحيها ثم أعيدي المعاينة."}),400
        conn=get_db(); added=updated=0
        try:
            for x in result["new"]:
                conn.execute("INSERT INTO students (student_name,grade,section,father_phone,mother_phone,father_phone_status,mother_phone_status,active) VALUES (?,?,?,?,?,?,?,1)",(x["student_name"],x["grade"],x["section"],x["father_phone"],x["mother_phone"],x["father_phone_status"],x["mother_phone_status"])); added+=1
            for x in result["updates"]:
                conn.execute("UPDATE students SET student_name=?,grade=?,section=?,father_phone=?,mother_phone=?,father_phone_status=?,mother_phone_status=?,active=1 WHERE id=?",(x["student_name"],x["grade"],x["section"],x["father_phone"],x["mother_phone"],x["father_phone_status"],x["mother_phone_status"],x["id"])); updated+=1
            conn.commit()
        except Exception: conn.rollback(); raise
        finally: conn.close()
        audit("تحديث الطالبات من Excel",f"تمت إضافة {added} وتحديث {updated} طالبة دون حذف سجلات الغياب","الإدارة")
        return jsonify({"success":True,"message":f"تم التحديث بنجاح: إضافة {added}، تحديث {updated}، بدون تغيير {result['unchanged']}."})
    except Exception as error: return jsonify({"success":False,"message":f"تعذر تنفيذ التحديث: {error}"}),400

# =========================================================
# ATTENDANCE
# =========================================================

@app.route(
    "/api/register-absence",
    methods=["POST"]
)
def register_absence():
    data = request.get_json() or {}

    grade = str(
        data.get(
            "grade",
            ""
        )
    ).strip()

    section = str(
        data.get(
            "section",
            ""
        )
    ).strip()

    teacher_name = str(
        data.get(
            "teacher_name",
            ""
        )
    ).strip()

    student_ids = data.get(
        "student_ids",
        []
    )

    if not grade or not section:
        return jsonify({
            "success":
                False,

            "message":
                "يرجى اختيار المرحلة والشعبة."
        }), 400

    if not teacher_name:
        return jsonify({
            "success":
                False,

            "message":
                "يرجى كتابة اسم المعلمة."
        }), 400

    if not student_ids:
        return jsonify({
            "success":
                False,

            "message":
                "اختاري طالبة غائبة واحدة على الأقل."
        }), 400

    today = date.today().isoformat()
    year = current_academic_year()

    conn = get_db()

    previous = conn.execute("""
        SELECT *
        FROM class_registration
        WHERE grade = ?
          AND section = ?
          AND registration_date = ?
          AND academic_year = ?
    """, (
        grade,
        section,
        today,
        year
    )).fetchone()

    if previous:
        conn.close()

        return jsonify({
            "success":
                False,

            "message":
                "تم تسجيل هذا الصف اليوم مسبقًا بواسطة "
                + previous["teacher_name"]
        }), 409

    added = 0

    try:
        for student_id in student_ids:
            student = conn.execute("""
                SELECT id
                FROM students
                WHERE id = ?
                  AND grade = ?
                  AND section = ?
                  AND active = 1
            """, (
                student_id,
                grade,
                section
            )).fetchone()

            if not student:
                continue

            try:
                conn.execute("""
                    INSERT INTO attendance (
                        student_id,
                        attendance_date,
                        teacher_name,
                        academic_year
                    )
                    VALUES (?, ?, ?, ?)
                """, (
                    student_id,
                    today,
                    teacher_name,
                    year
                ))

                added += 1

            except sqlite3.IntegrityError:
                pass

        conn.execute("""
            INSERT INTO class_registration (
                grade,
                section,
                registration_date,
                teacher_name,
                no_absence,
                academic_year
            )
            VALUES (?, ?, ?, ?, 0, ?)
        """, (
            grade,
            section,
            today,
            teacher_name,
            year
        ))

        conn.commit()

    except Exception as error:
        conn.rollback()
        conn.close()

        return jsonify({
            "success":
                False,

            "message":
                str(error)
        }), 500

    conn.close()

    audit(
        "تسجيل غياب",
        f"تم تسجيل {added} طالبة غائبة في الصف {grade}/{section}",
        teacher_name
    )

    return jsonify({
        "success":
            True,

        "message":
            f"تم تسجيل الصف {GRADE_NAMES.get(grade, grade)} / {section} بنجاح.",

        "absence_count":
            added
    })


@app.route(
    "/api/no-absence",
    methods=["POST"]
)
def no_absence():
    data = request.get_json() or {}

    grade = str(
        data.get(
            "grade",
            ""
        )
    ).strip()

    section = str(
        data.get(
            "section",
            ""
        )
    ).strip()

    teacher_name = str(
        data.get(
            "teacher_name",
            ""
        )
    ).strip()

    if not grade or not section:
        return jsonify({
            "success":
                False,

            "message":
                "يرجى اختيار المرحلة والشعبة."
        }), 400

    if not teacher_name:
        return jsonify({
            "success":
                False,

            "message":
                "يرجى كتابة اسم المعلمة."
        }), 400

    today = date.today().isoformat()
    year = current_academic_year()

    conn = get_db()

    previous = conn.execute("""
        SELECT *
        FROM class_registration
        WHERE grade = ?
          AND section = ?
          AND registration_date = ?
          AND academic_year = ?
    """, (
        grade,
        section,
        today,
        year
    )).fetchone()

    if previous:
        conn.close()

        return jsonify({
            "success":
                False,

            "message":
                "تم تسجيل هذا الصف اليوم مسبقًا بواسطة "
                + previous["teacher_name"]
        }), 409

    conn.execute("""
        INSERT INTO class_registration (
            grade,
            section,
            registration_date,
            teacher_name,
            no_absence,
            academic_year
        )
        VALUES (?, ?, ?, ?, 1, ?)
    """, (
        grade,
        section,
        today,
        teacher_name,
        year
    ))

    conn.commit()
    conn.close()

    audit(
        "لا يوجد غياب",
        f"تم تسجيل عدم وجود غياب في الصف {grade}/{section}",
        teacher_name
    )

    return jsonify({
        "success":
            True,

        "message":
            f"تم تسجيل الصف {GRADE_NAMES.get(grade, grade)} / {section}: لا يوجد غياب."
    })


@app.route(
    "/api/today-absences"
)
def today_absences():
    today = date.today().isoformat()
    year = current_academic_year()

    conn = get_db()

    rows = conn.execute("""
        SELECT
            attendance.id AS attendance_id,
            attendance.student_id,
            attendance.attendance_date,
            attendance.teacher_name,
            attendance.created_at,
            attendance.note,
            attendance.absence_status,

            students.student_name,
            students.grade,
            students.section,
            students.father_phone,
            students.mother_phone,
            students.father_phone_status,
            students.mother_phone_status

        FROM attendance

        JOIN students
          ON students.id = attendance.student_id

        WHERE attendance.attendance_date = ?
          AND attendance.academic_year = ?

        ORDER BY
            CAST(students.grade AS INTEGER) DESC,
            CAST(students.section AS INTEGER) DESC,
            students.student_name
    """, (
        today,
        year
    )).fetchall()

    conn.close()

    return jsonify([
        dict(row)
        for row in rows
    ])


@app.route(
    "/api/attendance/<int:attendance_id>",
    methods=["DELETE"]
)
def delete_attendance(attendance_id):
    conn = get_db()

    row = conn.execute("""
        SELECT
            attendance.*,
            students.student_name,
            students.grade,
            students.section
        FROM attendance
        JOIN students
          ON students.id = attendance.student_id
        WHERE attendance.id = ?
    """, (
        attendance_id,
    )).fetchone()

    if not row:
        conn.close()

        return jsonify({
            "success":
                False,

            "message":
                "السجل غير موجود."
        }), 404

    conn.execute("""
        DELETE FROM attendance
        WHERE id = ?
    """, (
        attendance_id,
    ))

    conn.commit()
    conn.close()

    audit(
        "حذف غياب",
        f"تم حذف غياب الطالبة {row['student_name']} من الصف {row['grade']}/{row['section']}",
        "الإدارة"
    )

    return jsonify({
        "success":
            True,

        "message":
            "تم حذف تسجيل الغياب."
    })


@app.route(
    "/api/attendance/<int:attendance_id>/note",
    methods=["PUT"]
)
def update_attendance_note(attendance_id):
    data = request.get_json() or {}

    note = str(
        data.get(
            "note",
            ""
        )
    ).strip()

    absence_status = str(
        data.get(
            "absence_status",
            "مسجل"
        )
    ).strip()

    conn = get_db()

    conn.execute("""
        UPDATE attendance
        SET
            note = ?,
            absence_status = ?
        WHERE id = ?
    """, (
        note,
        absence_status,
        attendance_id
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "success":
            True,

        "message":
            "تم تحديث حالة الغياب."
    })


# =========================================================
# ALERTS
# =========================================================

@app.route(
    "/api/alerts"
)
def alerts():
    year = current_academic_year()

    try:
        limit = int(
            get_setting(
                "absence_alert_limit",
                "8"
            )
        )
    except ValueError:
        limit = 8

    conn = get_db()

    rows = conn.execute("""
        SELECT
            students.id,
            students.student_name,
            students.grade,
            students.section,
            students.father_phone,
            students.mother_phone,
            students.father_phone_status,
            students.mother_phone_status,

            COUNT(attendance.id) AS absence_count,

            MAX(
                attendance.attendance_date
            ) AS last_absence

        FROM students

        JOIN attendance
          ON attendance.student_id = students.id

        WHERE attendance.academic_year = ?
          AND students.active = 1

        GROUP BY students.id

        HAVING COUNT(attendance.id) > ?

        ORDER BY
            absence_count DESC,
            students.student_name
    """, (
        year,
        limit
    )).fetchall()

    conn.close()

    return jsonify([
        dict(row)
        for row in rows
    ])


# =========================================================
# WHATSAPP LOG
# =========================================================

@app.route(
    "/api/log-notification",
    methods=["POST"]
)
def log_notification():
    data = request.get_json() or {}

    conn = get_db()

    conn.execute("""
        INSERT INTO notifications (
            student_id,
            notification_type,
            phone_type,
            phone_number,
            notification_date,
            note
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        data.get("student_id"),
        data.get(
            "notification_type",
            ""
        ),
        data.get(
            "phone_type",
            ""
        ),
        data.get(
            "phone_number",
            ""
        ),
        date.today().isoformat(),
        "تم فتح واتساب من النظام"
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True
    })


# =========================================================
# REPORTS
# =========================================================

@app.route(
    "/api/reports"
)
def reports():
    report_type = request.args.get(
        "type",
        "daily"
    )

    report_date = request.args.get(
        "date",
        date.today().isoformat()
    )

    month = request.args.get(
        "month",
        date.today().strftime(
            "%Y-%m"
        )
    )

    grade = request.args.get(
        "grade",
        ""
    ).strip()

    section = request.args.get(
        "section",
        ""
    ).strip()

    year = current_academic_year()

    conn = get_db()

    params = []

    if report_type == "daily":
        sql = """
            SELECT
                students.student_name,
                students.grade,
                students.section,
                attendance.attendance_date,
                attendance.teacher_name,
                attendance.absence_status,
                attendance.note

            FROM attendance

            JOIN students
              ON students.id = attendance.student_id

            WHERE attendance.attendance_date = ?
              AND attendance.academic_year = ?
        """

        params = [
            report_date,
            year
        ]

        if grade:
            sql += """
                AND students.grade = ?
            """
            params.append(grade)

        if section:
            sql += """
                AND students.section = ?
            """
            params.append(section)

        sql += """
            ORDER BY
                CAST(students.grade AS INTEGER) DESC,
                CAST(students.section AS INTEGER) DESC,
                students.student_name
        """

    elif report_type == "monthly":
        sql = """
            SELECT
                students.student_name,
                students.grade,
                students.section,

                GROUP_CONCAT(
                    attendance.attendance_date,
                    '، '
                ) AS absence_dates,

                COUNT(
                    attendance.id
                ) AS absence_count

            FROM attendance

            JOIN students
              ON students.id = attendance.student_id

            WHERE substr(
                attendance.attendance_date,
                1,
                7
            ) = ?

              AND attendance.academic_year = ?
        """

        params = [
            month,
            year
        ]

        if grade:
            sql += """
                AND students.grade = ?
            """
            params.append(grade)

        if section:
            sql += """
                AND students.section = ?
            """
            params.append(section)

        sql += """
            GROUP BY students.id
            ORDER BY
                absence_count DESC,
                students.student_name
        """

    elif report_type == "classes":
        sql = """
            SELECT
                students.grade,
                students.section,

                COUNT(
                    attendance.id
                ) AS absence_count

            FROM attendance

            JOIN students
              ON students.id = attendance.student_id

            WHERE substr(
                attendance.attendance_date,
                1,
                7
            ) = ?

              AND attendance.academic_year = ?

            GROUP BY
                students.grade,
                students.section

            ORDER BY
                absence_count DESC
        """

        params = [
            month,
            year
        ]

    elif report_type == "students":
        sql = """
            SELECT
                students.student_name,
                students.grade,
                students.section,

                COUNT(
                    attendance.id
                ) AS absence_count,

                MAX(
                    attendance.attendance_date
                ) AS last_absence

            FROM attendance

            JOIN students
              ON students.id = attendance.student_id

            WHERE attendance.academic_year = ?

            GROUP BY students.id

            ORDER BY
                absence_count DESC,
                students.student_name

            LIMIT 100
        """

        params = [year]

    elif report_type == "weekday":
        sql = """
            SELECT
                CASE strftime(
                    '%w',
                    attendance.attendance_date
                )
                    WHEN '0' THEN 'الأحد'
                    WHEN '1' THEN 'الاثنين'
                    WHEN '2' THEN 'الثلاثاء'
                    WHEN '3' THEN 'الأربعاء'
                    WHEN '4' THEN 'الخميس'
                    WHEN '5' THEN 'الجمعة'
                    WHEN '6' THEN 'السبت'
                END AS weekday_name,

                strftime(
                    '%w',
                    attendance.attendance_date
                ) AS weekday_number,

                COUNT(
                    attendance.id
                ) AS absence_count

            FROM attendance

            WHERE substr(
                attendance.attendance_date,
                1,
                7
            ) = ?

              AND attendance.academic_year = ?

            GROUP BY weekday_number

            ORDER BY weekday_number
        """

        params = [
            month,
            year
        ]

    else:
        conn.close()

        return jsonify({
            "success":
                False,

            "message":
                "نوع التقرير غير صحيح."
        }), 400

    rows = conn.execute(
        sql,
        params
    ).fetchall()

    conn.close()

    return jsonify([
        dict(row)
        for row in rows
    ])


# =========================================================
# EXCEL
# =========================================================

@app.route(
    "/export-excel"
)
def export_excel():
    report_type = request.args.get(
        "type",
        "daily"
    )

    report_date = request.args.get(
        "date",
        date.today().isoformat()
    )

    month = request.args.get(
        "month",
        date.today().strftime(
            "%Y-%m"
        )
    )

    year = current_academic_year()

    conn = get_db()

    if report_type == "monthly":
        query = """
            SELECT
                students.student_name
                    AS "اسم الطالبة",

                students.grade || '/' ||
                students.section
                    AS "الصف",

                GROUP_CONCAT(
                    attendance.attendance_date,
                    ' - '
                )
                    AS "تواريخ الغياب",

                COUNT(attendance.id)
                    AS "عدد أيام الغياب"

            FROM attendance

            JOIN students
              ON students.id = attendance.student_id

            WHERE substr(
                attendance.attendance_date,
                1,
                7
            ) = ?

              AND attendance.academic_year = ?

            GROUP BY students.id

            ORDER BY
                COUNT(attendance.id) DESC
        """

        df = pd.read_sql_query(
            query,
            conn,
            params=(
                month,
                year
            )
        )

        filename = (
            f"غياب_شهري_{month}.xlsx"
        )

    else:
        query = """
            SELECT
                attendance.attendance_date
                    AS "التاريخ",

                students.student_name
                    AS "اسم الطالبة",

                students.grade || '/' ||
                students.section
                    AS "الصف",

                attendance.teacher_name
                    AS "اسم المعلمة",

                attendance.absence_status
                    AS "الحالة",

                attendance.note
                    AS "ملاحظات"

            FROM attendance

            JOIN students
              ON students.id = attendance.student_id

            WHERE attendance.attendance_date = ?
              AND attendance.academic_year = ?

            ORDER BY
                CAST(students.grade AS INTEGER) DESC,
                CAST(students.section AS INTEGER) DESC,
                students.student_name
        """

        df = pd.read_sql_query(
            query,
            conn,
            params=(
                report_date,
                year
            )
        )

        filename = (
            f"غياب_{report_date}.xlsx"
        )

    conn.close()

    output = BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:

        df.to_excel(
            writer,
            index=False,
            sheet_name="الغياب"
        )

    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype=(
            "application/vnd.openxmlformats-"
            "officedocument.spreadsheetml.sheet"
        )
    )


# =========================================================
# SETTINGS
# =========================================================

@app.route(
    "/api/settings",
    methods=["GET"]
)
def get_settings():
    keys = [
        "school_name",
        "academic_year",
        "absence_alert_limit",
        "daily_message",
        "alert_message"
    ]

    return jsonify({
        key:
            get_setting(
                key,
                ""
            )
        for key in keys
    })


@app.route(
    "/api/settings",
    methods=["PUT"]
)
def update_settings():
    data = request.get_json() or {}

    allowed = [
        "school_name",
        "academic_year",
        "absence_alert_limit",
        "daily_message",
        "alert_message"
    ]

    for key in allowed:
        if key in data:
            set_setting(
                key,
                str(data[key]).strip()
            )

    audit(
        "تعديل الإعدادات",
        "تم تحديث إعدادات النظام",
        "الإدارة"
    )

    return jsonify({
        "success":
            True,

        "message":
            "تم حفظ الإعدادات بنجاح."
    })


# =========================================================
# BACKUP
# =========================================================

@app.route(
    "/backup"
)
def backup_database():
    BACKUP_DIR.mkdir(
        exist_ok=True
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    backup_file = (
        BACKUP_DIR /
        f"attendance_backup_{timestamp}.db"
    )

    shutil.copy2(
        DB_FILE,
        backup_file
    )

    return send_file(
        backup_file,
        as_attachment=True,
        download_name=backup_file.name
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )
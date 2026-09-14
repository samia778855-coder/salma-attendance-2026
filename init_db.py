import sqlite3
import pandas as pd
import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DB_FILE = BASE_DIR / "attendance.db"
EXCEL_FILE = BASE_DIR / "data" / "students.xlsx"


def convert_arabic_digits(value):
    if value is None:
        return ""

    value = str(value)

    table = str.maketrans(
        "٠١٢٣٤٥٦٧٨٩",
        "0123456789"
    )

    return value.translate(table)


def clean_phone(value):
    if pd.isna(value):
        return ""

    value = convert_arabic_digits(value)

    digits = re.sub(
        r"\D",
        "",
        value
    )

    if digits.startswith("00968"):
        digits = digits[5:]

    elif (
        digits.startswith("968")
        and len(digits) == 11
    ):
        digits = digits[3:]

    return digits


def phone_status(phone):
    if not phone:
        return "غير متوفر"

    if (
        len(phone) == 8
        and phone.isdigit()
    ):
        return "متوفر"

    return "يحتاج مراجعة"


def split_class(value):
    if pd.isna(value):
        return "", ""

    value = convert_arabic_digits(
        value
    ).strip()

    value = value.replace(
        "\\",
        "/"
    )

    parts = [
        part.strip()
        for part in value.split("/")
    ]

    if len(parts) >= 2:
        return (
            parts[0],
            parts[1]
        )

    return value, ""


def create_tables(conn):
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
            FOREIGN KEY(student_id)
                REFERENCES students(id),
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
            UNIQUE(
                grade,
                section,
                registration_date
            )
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
            FOREIGN KEY(student_id)
                REFERENCES students(id)
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
        """, (
            key,
            value
        ))

    conn.commit()


def import_students(conn):
    count = conn.execute("""
        SELECT COUNT(*)
        FROM students
    """).fetchone()[0]

    if count > 0:
        print(
            f"✅ قاعدة البيانات تحتوي بالفعل على {count} طالبة."
        )
        print(
            "ℹ️ لم يتم حذف أو إعادة استيراد الطالبات."
        )
        return

    if not EXCEL_FILE.exists():
        print(
            f"❌ ملف Excel غير موجود: {EXCEL_FILE}"
        )
        return

    df = pd.read_excel(
        EXCEL_FILE
    )

    required = [
        "اسم الطالبة",
        "الصف",
        "رقم هاتف الأب",
        "رقم هاتف الأم"
    ]

    for column in required:
        if column not in df.columns:
            raise ValueError(
                f"العمود غير موجود في Excel: {column}"
            )

    added = 0
    needs_review = 0

    for _, row in df.iterrows():
        student_name = str(
            row["اسم الطالبة"]
        ).strip()

        if (
            not student_name
            or student_name.lower() == "nan"
        ):
            continue

        grade, section = split_class(
            row["الصف"]
        )

        father_phone = clean_phone(
            row["رقم هاتف الأب"]
        )

        mother_phone = clean_phone(
            row["رقم هاتف الأم"]
        )

        father_status = phone_status(
            father_phone
        )

        mother_status = phone_status(
            mother_phone
        )

        if (
            father_status != "متوفر"
            or mother_status != "متوفر"
        ):
            needs_review += 1

        conn.execute("""
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
            father_status,
            mother_status
        ))

        added += 1

    conn.commit()

    print("-----------------------------------")
    print("✅ تم تجهيز قاعدة البيانات")
    print(
        f"✅ عدد الطالبات المضافة: {added}"
    )
    print(
        f"⚠️ أرقام تحتاج مراجعة: {needs_review}"
    )
    print(
        f"📁 قاعدة البيانات: {DB_FILE.name}"
    )
    print("-----------------------------------")


def main():
    conn = sqlite3.connect(
        DB_FILE
    )

    conn.row_factory = sqlite3.Row

    create_tables(
        conn
    )

    import_students(
        conn
    )

    conn.close()


if __name__ == "__main__":
    main()
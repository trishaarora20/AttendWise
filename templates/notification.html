import sqlite3

DATABASE = "attendwise.db"


def get_db():

    conn = sqlite3.connect(DATABASE)

    conn.row_factory = sqlite3.Row

    conn.execute("PRAGMA foreign_keys = ON")

    return conn


def init_db():

    conn = get_db()

    # =========================
    # USERS
    # =========================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    """)

    # =========================
    # SUBJECTS
    # =========================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,

            FOREIGN KEY (user_id)
            REFERENCES users(id)
            ON DELETE CASCADE
        )
    """)

    # =========================
    # TIMETABLE
    # =========================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS timetable (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,

            day_of_week INTEGER NOT NULL,
            class_time TEXT NOT NULL,

            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,

            FOREIGN KEY (user_id)
            REFERENCES users(id)
            ON DELETE CASCADE,

            FOREIGN KEY (subject_id)
            REFERENCES subjects(id)
            ON DELETE CASCADE
        )
    """)

    # =========================
    # ACTUAL CLASS INSTANCES
    # =========================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            timetable_id INTEGER,

            class_date TEXT NOT NULL,
            class_time TEXT NOT NULL,

            status TEXT NOT NULL DEFAULT 'scheduled',

            cancellation_reason TEXT,

            UNIQUE(timetable_id, class_date, class_time),

            FOREIGN KEY (user_id)
            REFERENCES users(id)
            ON DELETE CASCADE,

            FOREIGN KEY (subject_id)
            REFERENCES subjects(id)
            ON DELETE CASCADE
        )
    """)

    # =========================
    # ATTENDANCE
    # =========================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,
            class_id INTEGER NOT NULL,

            status TEXT NOT NULL,

            UNIQUE(class_id),

            FOREIGN KEY (user_id)
            REFERENCES users(id)
            ON DELETE CASCADE,

            FOREIGN KEY (class_id)
            REFERENCES classes(id)
            ON DELETE CASCADE
        )
    """)

    # =========================
    # HOLIDAYS
    # =========================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS holidays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            holiday_date TEXT NOT NULL,
            name TEXT NOT NULL,

            UNIQUE(user_id, holiday_date),

            FOREIGN KEY (user_id)
            REFERENCES users(id)
            ON DELETE CASCADE
        )
    """)

    # =========================
    # NOTIFICATION SETTINGS
    # =========================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS notification_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            enabled INTEGER NOT NULL DEFAULT 0,
            reminder_minutes INTEGER NOT NULL DEFAULT 10,

            FOREIGN KEY (user_id)
            REFERENCES users(id)
            ON DELETE CASCADE
        )
    """)

    # =========================
    # PUSH SUBSCRIPTIONS
    # =========================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS push_subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            endpoint TEXT NOT NULL UNIQUE,
            p256dh TEXT NOT NULL,
            auth TEXT NOT NULL,

            FOREIGN KEY (user_id)
            REFERENCES users(id)
            ON DELETE CASCADE
        )
    """)

    conn.commit()

    conn.close()


if __name__ == "__main__":

    init_db()

    print("AttendWise database created successfully!")
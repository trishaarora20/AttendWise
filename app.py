from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify
)

from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from database import get_db, init_db

from datetime import date, datetime, timedelta
import json
import os

try:
    from pywebpush import webpush, WebPushException
except ImportError:
    webpush = None
    WebPushException = Exception


# =========================================================
# APP
# =========================================================

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("ATTENDWISE_SECRET_KEY", "attendwise-local-secret-key")
app.config["VAPID_PUBLIC_KEY"] = os.environ.get("VAPID_PUBLIC_KEY", "")


# =========================================================
# LOGIN MANAGER
# =========================================================

login_manager = LoginManager()

login_manager.init_app(app)

login_manager.login_view = "login"


# =========================================================
# USER
# =========================================================

class User(UserMixin):

    def __init__(self, user_id, name, email, password):

        self.id = user_id
        self.name = name
        self.email = email
        self.password = password


@login_manager.user_loader
def load_user(user_id):

    conn = get_db()

    user = conn.execute(
        """
        SELECT *
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    ).fetchone()

    conn.close()

    if user:

        return User(
            user["id"],
            user["name"],
            user["email"],
            user["password"]
        )

    return None


# =========================================================
# CLASS GENERATION
# =========================================================

def ensure_classes(user_id, start_date, end_date):

    conn = get_db()

    timetable = conn.execute(
        """
        SELECT *
        FROM timetable
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchall()

    holidays = conn.execute(
        """
        SELECT holiday_date
        FROM holidays
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchall()

    holiday_dates = {
        row["holiday_date"]
        for row in holidays
    }

    current_date = start_date

    while current_date <= end_date:

        # Sunday = holiday automatically
        if current_date.weekday() != 6:

            date_string = current_date.isoformat()

            for rule in timetable:

                if rule["day_of_week"] != current_date.weekday():
                    continue

                rule_start = date.fromisoformat(
                    rule["start_date"]
                )

                rule_end = date.fromisoformat(
                    rule["end_date"]
                )

                if not (rule_start <= current_date <= rule_end):
                    continue

                if date_string in holiday_dates:

                    status = "cancelled"
                    reason = "holiday"

                else:

                    status = "scheduled"
                    reason = None

                conn.execute(
                    """
                    INSERT OR IGNORE INTO classes
                    (
                        user_id,
                        subject_id,
                        timetable_id,
                        class_date,
                        class_time,
                        status,
                        cancellation_reason
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        rule["subject_id"],
                        rule["id"],
                        date_string,
                        rule["class_time"],
                        status,
                        reason
                    )
                )

                # Existing class becomes holiday-cancelled
                if date_string in holiday_dates:

                    conn.execute(
                        """
                        UPDATE classes
                        SET status = 'cancelled',
                            cancellation_reason = 'holiday'
                        WHERE user_id = ?
                        AND timetable_id = ?
                        AND class_date = ?
                        AND cancellation_reason IS NULL
                        """,
                        (
                            user_id,
                            rule["id"],
                            date_string
                        )
                    )

        current_date += timedelta(days=1)

    conn.commit()

    conn.close()


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    if current_user.is_authenticated:

        return redirect(
            url_for("dashboard")
        )

    return redirect(
        url_for("login")
    )


# =========================================================
# SIGNUP
# =========================================================

@app.route("/signup", methods=["GET", "POST"])
def signup():

    if current_user.is_authenticated:

        return redirect(
            url_for("dashboard")
        )

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        if not name or not email or not password:

            flash("Please fill in all fields.")

            return redirect(
                url_for("signup")
            )

        if len(password) < 6:

            flash(
                "Password must be at least 6 characters."
            )

            return redirect(
                url_for("signup")
            )

        conn = get_db()

        existing_user = conn.execute(
            """
            SELECT id
            FROM users
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

        if existing_user:

            conn.close()

            flash(
                "An account with this email already exists."
            )

            return redirect(
                url_for("login")
            )

        hashed_password = generate_password_hash(
            password
        )

        conn.execute(
            """
            INSERT INTO users
            (name, email, password)
            VALUES (?, ?, ?)
            """,
            (
                name,
                email,
                hashed_password
            )
        )

        conn.commit()

        conn.close()

        flash(
            "Account created successfully! Please log in."
        )

        return redirect(
            url_for("login")
        )

    return render_template("signup.html")


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:

        return redirect(
            url_for("dashboard")
        )

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        conn = get_db()

        user = conn.execute(
            """
            SELECT *
            FROM users
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            logged_in_user = User(
                user["id"],
                user["name"],
                user["email"],
                user["password"]
            )

            login_user(
                logged_in_user,
                remember=True
            )

            return redirect(
                url_for("dashboard")
            )

        flash(
            "Invalid email or password."
        )

    return render_template("login.html")


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
@login_required
def logout():

    logout_user()

    return redirect(
        url_for("login")
    )


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
@login_required
def dashboard():

    today = date.today()

    ensure_classes(
        current_user.id,
        today,
        today
    )

    conn = get_db()

    subjects = conn.execute(
        """
        SELECT *
        FROM subjects
        WHERE user_id = ?
        ORDER BY name
        """,
        (current_user.id,)
    ).fetchall()

    today_classes = conn.execute(
        """
        SELECT
            classes.*,
            subjects.name AS subject_name,
            attendance.status AS attendance_status

        FROM classes

        JOIN subjects
        ON classes.subject_id = subjects.id

        LEFT JOIN attendance
        ON classes.id = attendance.class_id

        WHERE classes.user_id = ?
        AND classes.class_date = ?

        ORDER BY classes.class_time
        """,
        (
            current_user.id,
            today.isoformat()
        )
    ).fetchall()

    attendance_stats = conn.execute(
        """
        SELECT
            SUM(
                CASE
                    WHEN attendance.status = 'present'
                    THEN 1
                    ELSE 0
                END
            ) AS present_count,

            SUM(
                CASE
                    WHEN attendance.status = 'absent'
                    THEN 1
                    ELSE 0
                END
            ) AS absent_count

        FROM attendance

        JOIN classes
        ON attendance.class_id = classes.id

        WHERE attendance.user_id = ?

        AND classes.status = 'scheduled'
        """,
        (current_user.id,)
    ).fetchone()

    conn.close()

    present = attendance_stats["present_count"] or 0
    absent = attendance_stats["absent_count"] or 0

    total_marked = present + absent

    if total_marked:

        percentage = round(
            present / total_marked * 100,
            2
        )

    else:

        percentage = 0

    return render_template(
        "dashboard.html",

        user=current_user,

        subjects=subjects,

        today_classes=today_classes,

        attendance_percentage=percentage,

        present_count=present,

        absent_count=absent
    )


# =========================================================
# SUBJECTS
# =========================================================

@app.route("/subjects", methods=["GET", "POST"])
@login_required
def subjects():

    conn = get_db()

    if request.method == "POST":

        subject_name = request.form.get(
            "subject_name",
            ""
        ).strip()

        if not subject_name:

            conn.close()

            flash(
                "Please enter a subject name."
            )

            return redirect(
                url_for("subjects")
            )

        conn.execute(
            """
            INSERT INTO subjects
            (user_id, name)
            VALUES (?, ?)
            """,
            (
                current_user.id,
                subject_name
            )
        )

        conn.commit()

        conn.close()

        flash(
            "Subject added successfully! ✨"
        )

        return redirect(
            url_for("subjects")
        )

    user_subjects = conn.execute(
        """
        SELECT *
        FROM subjects
        WHERE user_id = ?
        ORDER BY name
        """,
        (current_user.id,)
    ).fetchall()

    conn.close()

    return render_template(
        "subjects.html",
        subjects=user_subjects
    )


@app.route(
    "/subjects/delete/<int:subject_id>",
    methods=["POST"]
)
@login_required
def delete_subject(subject_id):

    conn = get_db()

    conn.execute(
        """
        DELETE FROM subjects
        WHERE id = ?
        AND user_id = ?
        """,
        (
            subject_id,
            current_user.id
        )
    )

    conn.commit()

    conn.close()

    flash(
        "Subject deleted."
    )

    return redirect(
        url_for("subjects")
    )


# =========================================================
# TIMETABLE
# =========================================================

@app.route("/timetable", methods=["GET", "POST"])
@login_required
def timetable():

    conn = get_db()

    if request.method == "POST":

        subject_id = request.form.get("subject_id")
        day_of_week = request.form.get("day_of_week")
        class_time = request.form.get("class_time")
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")

        if not all([
            subject_id,
            day_of_week,
            class_time,
            start_date,
            end_date
        ]):
            conn.close()
            flash("Please fill in all timetable fields.")
            return redirect(url_for("timetable"))

        try:
            day_of_week = int(day_of_week)
            start_obj = date.fromisoformat(start_date)
            end_obj = date.fromisoformat(end_date)
        except (ValueError, TypeError):
            conn.close()
            flash("Invalid date or day selected.")
            return redirect(url_for("timetable"))

        if day_of_week < 0 or day_of_week > 5:
            conn.close()
            flash("Sunday is automatically treated as a holiday.")
            return redirect(url_for("timetable"))

        if start_obj > end_obj:
            conn.close()
            flash("End date must be after start date.")
            return redirect(url_for("timetable"))

        subject = conn.execute(
            """
            SELECT id
            FROM subjects
            WHERE id = ?
            AND user_id = ?
            """,
            (subject_id, current_user.id)
        ).fetchone()

        if not subject:
            conn.close()
            flash("Invalid subject.")
            return redirect(url_for("timetable"))

        conn.execute(
            """
            INSERT INTO timetable
            (
                user_id,
                subject_id,
                day_of_week,
                class_time,
                start_date,
                end_date
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                current_user.id,
                subject_id,
                day_of_week,
                class_time,
                start_date,
                end_date
            )
        )

        conn.commit()
        conn.close()

        ensure_classes(
            current_user.id,
            start_obj,
            end_obj
        )

        flash("Timetable added successfully! 🗓️")
        return redirect(url_for("timetable"))

    timetable_rows = conn.execute(
        """
        SELECT
            timetable.*,
            subjects.name AS subject_name
        FROM timetable
        JOIN subjects
            ON timetable.subject_id = subjects.id
        WHERE timetable.user_id = ?
        ORDER BY
            timetable.day_of_week,
            timetable.class_time
        """,
        (current_user.id,)
    ).fetchall()

    user_subjects = conn.execute(
        """
        SELECT *
        FROM subjects
        WHERE user_id = ?
        ORDER BY name
        """,
        (current_user.id,)
    ).fetchall()

    edit_rule = None
    edit_id = request.args.get("edit")

    if edit_id:
        try:
            edit_id = int(edit_id)
            edit_rule = conn.execute(
                """
                SELECT *
                FROM timetable
                WHERE id = ?
                AND user_id = ?
                """,
                (edit_id, current_user.id)
            ).fetchone()
        except (ValueError, TypeError):
            edit_rule = None

    conn.close()

    return render_template(
        "timetable.html",
        timetable=timetable_rows,
        subjects=user_subjects,
        edit_rule=edit_rule
    )


@app.route(
    "/timetable/update/<int:rule_id>",
    methods=["POST"]
)
@login_required
def update_timetable(rule_id):

    conn = get_db()

    old_rule = conn.execute(
        """
        SELECT *
        FROM timetable
        WHERE id = ?
        AND user_id = ?
        """,
        (rule_id, current_user.id)
    ).fetchone()

    if not old_rule:
        conn.close()
        flash("Timetable entry not found.")
        return redirect(url_for("timetable"))

    subject_id = request.form.get("subject_id")
    day_of_week = request.form.get("day_of_week")
    class_time = request.form.get("class_time")
    start_date = request.form.get("start_date")
    end_date = request.form.get("end_date")

    if not all([
        subject_id,
        day_of_week,
        class_time,
        start_date,
        end_date
    ]):
        conn.close()
        flash("Please fill in all timetable fields.")
        return redirect(url_for("timetable", edit=rule_id))

    try:
        day_of_week = int(day_of_week)
        new_start = date.fromisoformat(start_date)
        new_end = date.fromisoformat(end_date)
    except (ValueError, TypeError):
        conn.close()
        flash("Invalid date or day selected.")
        return redirect(url_for("timetable", edit=rule_id))

    if day_of_week < 0 or day_of_week > 5:
        conn.close()
        flash("Sunday is automatically treated as a holiday.")
        return redirect(url_for("timetable", edit=rule_id))

    if new_start > new_end:
        conn.close()
        flash("End date must be after start date.")
        return redirect(url_for("timetable", edit=rule_id))

    subject = conn.execute(
        """
        SELECT id
        FROM subjects
        WHERE id = ?
        AND user_id = ?
        """,
        (subject_id, current_user.id)
    ).fetchone()

    if not subject:
        conn.close()
        flash("Invalid subject.")
        return redirect(url_for("timetable", edit=rule_id))

    # Delete only future class instances that have NO attendance.
    # Historical classes and attendance records are preserved.
    today = date.today().isoformat()

    conn.execute(
        """
        DELETE FROM classes
        WHERE timetable_id = ?
        AND user_id = ?
        AND class_date >= ?
        AND id NOT IN (
            SELECT class_id
            FROM attendance
        )
        """,
        (
            rule_id,
            current_user.id,
            today
        )
    )

    conn.execute(
        """
        UPDATE timetable
        SET
            subject_id = ?,
            day_of_week = ?,
            class_time = ?,
            start_date = ?,
            end_date = ?
        WHERE id = ?
        AND user_id = ?
        """,
        (
            subject_id,
            day_of_week,
            class_time,
            start_date,
            end_date,
            rule_id,
            current_user.id
        )
    )

    conn.commit()
    conn.close()

    ensure_classes(
        current_user.id,
        new_start,
        new_end
    )

    flash(
        "Timetable updated successfully! Existing attendance was preserved."
    )

    return redirect(url_for("timetable"))


@app.route(
    "/timetable/delete/<int:rule_id>",
    methods=["POST"]
)
@login_required
def delete_timetable(rule_id):

    conn = get_db()

    # Delete only the timetable rule.
    # Existing class instances remain,
    # preserving attendance history.

    conn.execute(
        """
        DELETE FROM timetable
        WHERE id = ?
        AND user_id = ?
        """,
        (
            rule_id,
            current_user.id
        )
    )

    conn.commit()

    conn.close()

    flash(
        "Timetable rule deleted. Existing attendance history was preserved."
    )

    return redirect(
        url_for("timetable")
    )


# =========================================================
# ATTENDANCE
# =========================================================

@app.route(
    "/attendance",
    methods=["GET"]
)
@login_required
def attendance():

    selected_date = request.args.get(
        "date"
    )

    if not selected_date:

        selected_date = date.today().isoformat()

    try:

        selected = date.fromisoformat(
            selected_date
        )

    except ValueError:

        selected = date.today()

        selected_date = selected.isoformat()

    ensure_classes(
        current_user.id,
        selected,
        selected
    )

    conn = get_db()

    classes = conn.execute(
        """
        SELECT
            classes.*,
            subjects.name AS subject_name,
            attendance.status AS attendance_status

        FROM classes

        JOIN subjects
        ON classes.subject_id = subjects.id

        LEFT JOIN attendance
        ON classes.id = attendance.class_id

        WHERE classes.user_id = ?
        AND classes.class_date = ?

        ORDER BY classes.class_time
        """,
        (
            current_user.id,
            selected_date
        )
    ).fetchall()

    conn.close()

    return render_template(
        "attendance.html",

        classes=classes,

        selected_date=selected_date
    )


@app.route(
    "/attendance/mark",
    methods=["POST"]
)
@login_required
def mark_attendance():

    class_id = request.form.get(
        "class_id"
    )

    status = request.form.get(
        "status"
    )

    if status not in [
        "present",
        "absent"
    ]:

        flash(
            "Invalid attendance status."
        )

        return redirect(
            url_for("attendance")
        )

    conn = get_db()

    class_row = conn.execute(
        """
        SELECT *
        FROM classes
        WHERE id = ?
        AND user_id = ?
        """,
        (
            class_id,
            current_user.id
        )
    ).fetchone()

    if not class_row:

        conn.close()

        flash(
            "Class not found."
        )

        return redirect(
            url_for("attendance")
        )

    if class_row["status"] == "cancelled":

        conn.close()

        flash(
            "Cancelled classes cannot be marked."
        )

        return redirect(
            url_for(
                "attendance",
                date=class_row["class_date"]
            )
        )

    conn.execute(
        """
        INSERT INTO attendance
        (
            user_id,
            class_id,
            status
        )
        VALUES (?, ?, ?)

        ON CONFLICT(class_id)
        DO UPDATE SET status = excluded.status
        """,
        (
            current_user.id,
            class_id,
            status
        )
    )

    conn.commit()

    conn.close()

    flash(
        "Attendance updated! ✅"
    )

    return redirect(
        url_for(
            "attendance",
            date=class_row["class_date"]
        )
    )


# =========================================================
# CANCEL INDIVIDUAL CLASS
# =========================================================

@app.route(
    "/class/cancel/<int:class_id>",
    methods=["POST"]
)
@login_required
def cancel_class(class_id):

    conn = get_db()

    conn.execute(
        """
        UPDATE classes

        SET status = 'cancelled',
            cancellation_reason = 'class'

        WHERE id = ?
        AND user_id = ?
        """,
        (
            class_id,
            current_user.id
        )
    )

    conn.commit()

    conn.close()

    flash(
        "Class cancelled."
    )

    return redirect(
        request.referrer
        or url_for("attendance")
    )


# =========================================================
# HISTORY
# =========================================================

@app.route("/history")
@login_required
def history():

    conn = get_db()

    summary = conn.execute(
        """
        SELECT
            subjects.id,
            subjects.name,

            SUM(
                CASE
                    WHEN attendance.status = 'present'
                    THEN 1
                    ELSE 0
                END
            ) AS present_count,

            SUM(
                CASE
                    WHEN attendance.status = 'absent'
                    THEN 1
                    ELSE 0
                END
            ) AS absent_count

        FROM subjects

        LEFT JOIN classes
        ON subjects.id = classes.subject_id
        AND classes.status = 'scheduled'

        LEFT JOIN attendance
        ON classes.id = attendance.class_id

        WHERE subjects.user_id = ?

        GROUP BY subjects.id

        ORDER BY subjects.name
        """,
        (current_user.id,)
    ).fetchall()

    records = conn.execute(
        """
        SELECT
            classes.class_date,
            classes.class_time,
            subjects.name AS subject_name,
            attendance.status

        FROM attendance

        JOIN classes
        ON attendance.class_id = classes.id

        JOIN subjects
        ON classes.subject_id = subjects.id

        WHERE attendance.user_id = ?

        ORDER BY
            classes.class_date DESC,
            classes.class_time DESC

        LIMIT 100
        """,
        (current_user.id,)
    ).fetchall()

    conn.close()

    return render_template(
        "history.html",

        summary=summary,

        records=records
    )


# =========================================================
# HOLIDAYS
# =========================================================

@app.route(
    "/holidays",
    methods=["GET", "POST"]
)
@login_required
def holidays():

    conn = get_db()

    if request.method == "POST":

        holiday_date = request.form.get(
            "holiday_date"
        )

        holiday_name = request.form.get(
            "holiday_name",
            ""
        ).strip()

        if not holiday_date or not holiday_name:

            conn.close()

            flash(
                "Please enter the holiday date and name."
            )

            return redirect(
                url_for("holidays")
            )

        conn.execute(
            """
            INSERT OR REPLACE INTO holidays
            (
                user_id,
                holiday_date,
                name
            )
            VALUES (?, ?, ?)
            """,
            (
                current_user.id,
                holiday_date,
                holiday_name
            )
        )

        # Classes on this day become cancelled
        conn.execute(
            """
            UPDATE classes

            SET status = 'cancelled',
                cancellation_reason = 'holiday'

            WHERE user_id = ?
            AND class_date = ?
            """,
            (
                current_user.id,
                holiday_date
            )
        )

        conn.commit()

        conn.close()

        flash(
            "Holiday added. Classes on that day won't count. 🎉"
        )

        return redirect(
            url_for("holidays")
        )

    holiday_rows = conn.execute(
        """
        SELECT *
        FROM holidays

        WHERE user_id = ?

        ORDER BY holiday_date
        """,
        (current_user.id,)
    ).fetchall()

    conn.close()

    return render_template(
        "holidays.html",

        holidays=holiday_rows
    )


@app.route(
    "/holidays/delete/<int:holiday_id>",
    methods=["POST"]
)
@login_required
def delete_holiday(holiday_id):

    conn = get_db()

    holiday = conn.execute(
        """
        SELECT holiday_date
        FROM holidays

        WHERE id = ?
        AND user_id = ?
        """,
        (
            holiday_id,
            current_user.id
        )
    ).fetchone()

    if holiday:

        holiday_date = holiday["holiday_date"]

        conn.execute(
            """
            DELETE FROM holidays

            WHERE id = ?
            AND user_id = ?
            """,
            (
                holiday_id,
                current_user.id
            )
        )

        # Reactivate classes cancelled specifically
        # because of this holiday.
        conn.execute(
            """
            UPDATE classes

            SET status = 'scheduled',
                cancellation_reason = NULL

            WHERE user_id = ?
            AND class_date = ?
            AND cancellation_reason = 'holiday'
            """,
            (
                current_user.id,
                holiday_date
            )
        )

        conn.commit()

    conn.close()

    flash(
        "Holiday removed."
    )

    return redirect(
        url_for("holidays")
    )




# =========================================================
# CAN I SKIP CALCULATOR
# =========================================================

@app.route("/calculator", methods=["GET", "POST"])
@login_required
def calculator():
    conn = get_db()
    stats = conn.execute(
        """SELECT COALESCE(SUM(CASE WHEN status = 'present' THEN 1 ELSE 0 END), 0) AS present_count,
                  COALESCE(SUM(CASE WHEN status = 'absent' THEN 1 ELSE 0 END), 0) AS absent_count
           FROM attendance WHERE user_id = ?""",
        (current_user.id,)
    ).fetchone()
    conn.close()

    present = int(stats["present_count"] or 0)
    absent = int(stats["absent_count"] or 0)
    total = present + absent
    target = 75.0

    if request.method == "POST":
        try:
            target = float(request.form.get("target", 75))
        except (TypeError, ValueError):
            target = 75.0
    target = max(1.0, min(100.0, target))

    current_percentage = (present / total * 100) if total else 0.0

    if total == 0:
        can_skip_next = False
        max_skips = 0
    else:
        can_skip_next = (present / (total + 1) * 100) >= target
        maximum = (present * 100 / target) - total
        max_skips = max(0, int(maximum + 1e-9))

    if current_percentage >= target:
        classes_needed = 0
    elif target >= 100:
        classes_needed = None
    else:
        required = ((target / 100) * total - present) / (1 - target / 100)
        classes_needed = max(0, int(required + 0.999999))

    return render_template("calculator.html", present=present, absent=absent, total=total,
                           current_percentage=round(current_percentage, 2), target=target,
                           can_skip_next=can_skip_next, max_skips=max_skips,
                           classes_needed=classes_needed)



# =========================================================
# NOTIFICATIONS
# =========================================================

@app.route("/notifications")
@login_required
def notifications():

    conn = get_db()

    settings = conn.execute(
        """
        SELECT *
        FROM notification_settings
        WHERE user_id = ?
        """,
        (current_user.id,)
    ).fetchone()

    if not settings:
        conn.execute(
            """
            INSERT INTO notification_settings
            (user_id, enabled, reminder_minutes)
            VALUES (?, 0, 10)
            """,
            (current_user.id,)
        )
        conn.commit()
        settings = conn.execute(
            """
            SELECT * FROM notification_settings WHERE user_id = ?
            """,
            (current_user.id,)
        ).fetchone()

    conn.close()

    return render_template(
        "notifications.html",
        settings=settings
    )


@app.route("/notifications/settings", methods=["POST"])
@login_required
def update_notification_settings():

    enabled = 1 if request.form.get("enabled") == "on" else 0
    reminder_minutes = request.form.get("reminder_minutes", "10")

    try:
        reminder_minutes = int(reminder_minutes)
    except (ValueError, TypeError):
        reminder_minutes = 10

    if reminder_minutes not in (5, 10, 15):
        reminder_minutes = 10

    conn = get_db()
    conn.execute(
        """
        INSERT INTO notification_settings
        (user_id, enabled, reminder_minutes)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            enabled = excluded.enabled,
            reminder_minutes = excluded.reminder_minutes
        """,
        (current_user.id, enabled, reminder_minutes)
    )
    conn.commit()
    conn.close()

    flash("Notification settings saved. 🔔")
    return redirect(url_for("notifications"))


@app.route("/api/push/subscribe", methods=["POST"])
@login_required
def push_subscribe():

    data = request.get_json(silent=True) or {}
    endpoint = data.get("endpoint")
    keys = data.get("keys") or {}

    if not endpoint or not keys.get("p256dh") or not keys.get("auth"):
        return jsonify({"ok": False, "error": "Invalid push subscription."}), 400

    conn = get_db()
    conn.execute(
        """
        INSERT INTO push_subscriptions
        (user_id, endpoint, p256dh, auth)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(endpoint) DO UPDATE SET
            user_id = excluded.user_id,
            p256dh = excluded.p256dh,
            auth = excluded.auth
        """,
        (
            current_user.id,
            endpoint,
            keys["p256dh"],
            keys["auth"]
        )
    )
    conn.commit()
    conn.close()

    return jsonify({"ok": True})


@app.route("/api/push/unsubscribe", methods=["POST"])
@login_required
def push_unsubscribe():

    data = request.get_json(silent=True) or {}
    endpoint = data.get("endpoint")

    conn = get_db()
    if endpoint:
        conn.execute(
            """
            DELETE FROM push_subscriptions
            WHERE user_id = ? AND endpoint = ?
            """,
            (current_user.id, endpoint)
        )
    else:
        conn.execute(
            """
            DELETE FROM push_subscriptions
            WHERE user_id = ?
            """,
            (current_user.id,)
        )
    conn.commit()
    conn.close()

    return jsonify({"ok": True})


@app.route("/api/push/test", methods=["POST"])
@login_required
def push_test():

    if webpush is None:
        return jsonify({
            "ok": False,
            "error": "pywebpush is not installed yet."
        }), 500

    private_key = os.environ.get("VAPID_PRIVATE_KEY")
    subject = os.environ.get("VAPID_SUBJECT", "mailto:attendwise@example.com")

    if not private_key:
        return jsonify({
            "ok": False,
            "error": "VAPID_PRIVATE_KEY is not configured yet."
        }), 500

    conn = get_db()
    subscriptions = conn.execute(
        """
        SELECT id, endpoint, p256dh, auth
        FROM push_subscriptions
        WHERE user_id = ?
        """,
        (current_user.id,)
    ).fetchall()
    conn.close()

    if not subscriptions:
        return jsonify({
            "ok": False,
            "error": "No phone/browser notification subscription found."
        }), 400

    payload = json.dumps({
        "title": "AttendWise 🔔",
        "body": "Test notification received successfully!",
        "url": "/notifications"
    })

    sent = 0

    for subscription in subscriptions:
        info = {
            "endpoint": subscription["endpoint"],
            "keys": {
                "p256dh": subscription["p256dh"],
                "auth": subscription["auth"]
            }
        }

        try:
            webpush(
                subscription_info=info,
                data=payload,
                vapid_private_key=private_key,
                vapid_claims={"sub": subject},
                ttl=300
            )
            sent += 1
        except WebPushException:
            continue

    return jsonify({"ok": sent > 0, "sent": sent})


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    init_db()

    app.run(
        debug=True
    )

from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from database import get_db_connection, create_tables

import os
import re
from collections import Counter

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "development-secret-key-change-before-deployment"
)

create_tables()

CATEGORIES = ["Personal", "Academic", "Work", "Projects"]
PRIORITIES = ["High", "Medium", "Low"]


# --------------------------------------------------
# HELPER: SMART CATEGORIZATION
# --------------------------------------------------

def detect_category(title, content, tags):

    text = f"{title} {content} {tags}".lower()

    keywords = {
        "Academic": [
            "exam", "study", "assignment", "lecture",
            "college", "university", "subject", "notes",
            "homework", "class", "research", "python",
            "programming", "lab", "semester"
        ],

        "Work": [
            "office", "meeting", "client", "deadline",
            "business", "employee", "work", "manager",
            "project meeting", "task", "team"
        ],

        "Projects": [
            "project", "development", "flask",
            "application", "software", "database",
            "coding", "implementation", "testing"
        ],

        "Personal": [
            "personal", "family", "health", "daily",
            "goals", "shopping", "routine", "life"
        ]
    }

    scores = {}

    for category, words in keywords.items():
        scores[category] = sum(
            1 for word in words if word in text
        )

    best_category = max(scores, key=scores.get)

    if scores[best_category] == 0:
        return "Personal"

    return best_category


# --------------------------------------------------
# HELPER: TEXT SUMMARIZATION
# --------------------------------------------------

def generate_summary(content):

    if not content or not content.strip():
        return "No content available to summarize."

    # Split content into sentences
    sentences = re.split(r'(?<=[.!?])\s+', content.strip())

    if len(sentences) <= 2:
        return content.strip()

    # Remove common words
    stop_words = {
        "the", "is", "a", "an", "and", "or", "to",
        "of", "in", "on", "for", "with", "this",
        "that", "it", "are", "was", "were", "be",
        "as", "by", "at", "from", "has", "have"
    }

    words = re.findall(r'\b[a-zA-Z]+\b', content.lower())

    filtered_words = [
        word for word in words if word not in stop_words
    ]

    frequency = Counter(filtered_words)

    scored_sentences = []

    for index, sentence in enumerate(sentences):

        sentence_words = re.findall(
            r'\b[a-zA-Z]+\b',
            sentence.lower()
        )

        score = sum(
            frequency[word]
            for word in sentence_words
            if word not in stop_words
        )

        scored_sentences.append((score, index, sentence))

    # Select the three most important sentences
    selected = sorted(
        sorted(
            scored_sentences,
            key=lambda item: item[0],
            reverse=True
        )[:3],
        key=lambda item: item[1]
    )

    return " ".join(item[2] for item in selected)


# --------------------------------------------------
# HOME
# --------------------------------------------------

@app.route("/")
def home():

    if "user_id" in session:
        return redirect(url_for("dashboard"))

    return redirect(url_for("login"))


# --------------------------------------------------
# REGISTER
# --------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not username or not email or len(password) < 8:
            flash("Enter valid details. Password must be at least 8 characters.")
            return render_template("register.html")

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()

        try:

            conn.execute(
                """
                INSERT INTO users (username, email, password)
                VALUES (?, ?, ?)
                """,
                (username, email, hashed_password)
            )

            conn.commit()

            flash("Registration successful! Please login.")
            return redirect(url_for("login"))

        except Exception:

            flash("Email already registered or invalid details.")

        finally:
            conn.close()

    return render_template("register.html")


# --------------------------------------------------
# LOGIN
# --------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db_connection()

        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(user["password"], password):

            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]

            flash("Login successful!")
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.")

    return render_template("login.html")


# --------------------------------------------------
# DASHBOARD + ADVANCED SEARCH
# --------------------------------------------------

@app.route("/dashboard", methods=["GET"])
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    search = request.args.get("search", "").strip()
    category = request.args.get("category", "").strip()
    priority = request.args.get("priority", "").strip()
    tag = request.args.get("tag", "").strip()

    query = """
        SELECT * FROM notes
        WHERE user_id = ?
    """

    params = [session["user_id"]]

    if search:

        query += """
            AND (
                title LIKE ?
                OR content LIKE ?
                OR tags LIKE ?
                OR summary LIKE ?
            )
        """

        keyword = f"%{search}%"
        params.extend([keyword, keyword, keyword, keyword])

    if category in CATEGORIES:
        query += " AND category = ?"
        params.append(category)

    if priority in PRIORITIES:
        query += " AND priority = ?"
        params.append(priority)

    if tag:
        query += " AND tags LIKE ?"
        params.append(f"%{tag}%")

    # Pinned notes appear first
    query += """
        ORDER BY is_pinned DESC, updated_at DESC
    """

    conn = get_db_connection()

    notes = conn.execute(query, params).fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        notes=notes,
        categories=CATEGORIES,
        priorities=PRIORITIES,
        selected_category=category,
        selected_priority=priority,
        selected_tag=tag,
        search=search
    )


# --------------------------------------------------
# ADD NOTE + SMART CATEGORY
# --------------------------------------------------

@app.route("/add-note", methods=["GET", "POST"])
def add_note():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        category = request.form.get("category", "Personal")
        tags = request.form.get("tags", "").strip()
        priority = request.form.get("priority", "Medium")
        reminder = request.form.get("reminder_at", "").strip()

        if not title:
            flash("Note title is required.")
            return render_template(
                "add_note.html",
                categories=CATEGORIES,
                priorities=PRIORITIES
            )

        if category == "Auto Detect":
            category = detect_category(title, content, tags)

        elif category not in CATEGORIES:
            category = "Personal"

        if priority not in PRIORITIES:
            priority = "Medium"

        conn = get_db_connection()

        conn.execute(
            """
            INSERT INTO notes
            (user_id, title, content, category, tags,
             priority, reminder_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session["user_id"], title, content,
                category, tags, priority, reminder or None
            )
        )

        conn.commit()
        conn.close()

        flash("Note created successfully!")
        return redirect(url_for("dashboard"))

    return render_template(
        "add_note.html",
        categories=CATEGORIES,
        priorities=PRIORITIES
    )


# --------------------------------------------------
# EDIT NOTE
# --------------------------------------------------

@app.route("/edit-note/<int:note_id>", methods=["GET", "POST"])
def edit_note(note_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()

    note = conn.execute(
        """
        SELECT * FROM notes
        WHERE id = ? AND user_id = ?
        """,
        (note_id, session["user_id"])
    ).fetchone()

    if note is None:
        conn.close()
        flash("Note not found.")
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        category = request.form.get("category", "Personal")
        tags = request.form.get("tags", "").strip()
        priority = request.form.get("priority", "Medium")
        reminder = request.form.get("reminder_at", "").strip()

        if not title:
            conn.close()
            flash("Note title is required.")
            return redirect(url_for("edit_note", note_id=note_id))

        if category == "Auto Detect":
            category = detect_category(title, content, tags)

        elif category not in CATEGORIES:
            category = "Personal"

        if priority not in PRIORITIES:
            priority = "Medium"

        conn.execute(
            """
            UPDATE notes
            SET title = ?, content = ?, category = ?,
                tags = ?, priority = ?, reminder_at = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
            """,
            (
                title, content, category, tags,
                priority, reminder or None,
                note_id, session["user_id"]
            )
        )

        conn.commit()
        conn.close()

        flash("Note updated successfully!")
        return redirect(url_for("dashboard"))

    conn.close()

    return render_template(
        "edit_note.html",
        note=note,
        categories=CATEGORIES,
        priorities=PRIORITIES
    )


# --------------------------------------------------
# AI-STYLE NOTE SUMMARIZATION
# --------------------------------------------------

@app.route("/summarize-note/<int:note_id>", methods=["POST"])
def summarize_note(note_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()

    note = conn.execute(
        """
        SELECT * FROM notes
        WHERE id = ? AND user_id = ?
        """,
        (note_id, session["user_id"])
    ).fetchone()

    if note is None:
        conn.close()
        flash("Note not found.")
        return redirect(url_for("dashboard"))

    summary = generate_summary(note["content"])

    conn.execute(
        """
        UPDATE notes
        SET summary = ?
        WHERE id = ? AND user_id = ?
        """,
        (summary, note_id, session["user_id"])
    )

    conn.commit()
    conn.close()

    flash("Note summary generated successfully!")

    return redirect(url_for("dashboard"))


# --------------------------------------------------
# PIN / UNPIN NOTE
# --------------------------------------------------

@app.route("/toggle-pin/<int:note_id>", methods=["POST"])
def toggle_pin(note_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()

    note = conn.execute(
        """
        SELECT is_pinned FROM notes
        WHERE id = ? AND user_id = ?
        """,
        (note_id, session["user_id"])
    ).fetchone()

    if note is None:
        conn.close()
        flash("Note not found.")
        return redirect(url_for("dashboard"))

    new_status = 0 if note["is_pinned"] else 1

    conn.execute(
        """
        UPDATE notes
        SET is_pinned = ?
        WHERE id = ? AND user_id = ?
        """,
        (new_status, note_id, session["user_id"])
    )

    conn.commit()
    conn.close()

    flash("Note pinned!" if new_status else "Note unpinned!")

    return redirect(url_for("dashboard"))


# --------------------------------------------------
# DELETE NOTE
# --------------------------------------------------

@app.route("/delete-note/<int:note_id>", methods=["POST"])
def delete_note(note_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()

    conn.execute(
        """
        DELETE FROM notes
        WHERE id = ? AND user_id = ?
        """,
        (note_id, session["user_id"])
    )

    conn.commit()
    conn.close()

    flash("Note deleted successfully!")

    return redirect(url_for("dashboard"))


# --------------------------------------------------
# LOGOUT
# --------------------------------------------------

@app.route("/logout")
def logout():

    session.clear()
    flash("Logged out successfully!")

    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True, port=5000)

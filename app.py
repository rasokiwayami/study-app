from flask import Flask, jsonify, request, render_template
import sqlite3
from datetime import date, timedelta

app = Flask(__name__)
DB_PATH = "study_records.db"

SUBJECT_COLORS = [
    "#5B8DEF", "#FF6B6B", "#5BC47F", "#FFB347",
    "#C77DFF", "#56CFE1", "#FF85A1", "#FFD93D",
]


# ── DB ────────────────────────────────────────────────────────────────────────

def get_db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    con = get_db()
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL UNIQUE,
            color        TEXT NOT NULL DEFAULT '#5B8DEF',
            goal_seconds INTEGER NOT NULL DEFAULT 0
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL,
            date       TEXT NOT NULL,
            seconds    INTEGER NOT NULL,
            memo       TEXT NOT NULL DEFAULT '',
            FOREIGN KEY (subject_id) REFERENCES subjects(id)
        )
    """)
    for stmt in [
        "ALTER TABLE subjects ADD COLUMN color TEXT NOT NULL DEFAULT '#5B8DEF'",
        "ALTER TABLE subjects ADD COLUMN goal_seconds INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE records ADD COLUMN memo TEXT NOT NULL DEFAULT ''",
    ]:
        try:
            cur.execute(stmt)
        except sqlite3.OperationalError:
            pass
    con.commit()
    con.close()


def fmt(seconds):
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


# ── API ───────────────────────────────────────────────────────────────────────

@app.get("/api/subjects")
def api_get_subjects():
    con = get_db()
    rows = con.execute(
        "SELECT id, name, color, goal_seconds FROM subjects ORDER BY name"
    ).fetchall()
    con.close()
    return jsonify([dict(r) for r in rows])


@app.post("/api/subjects")
def api_add_subject():
    data = request.json
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "名前が空です"}), 400
    con = get_db()
    try:
        existing = con.execute("SELECT color FROM subjects").fetchall()
        used = [r["color"] for r in existing]
        color = next((c for c in SUBJECT_COLORS if c not in used),
                     SUBJECT_COLORS[len(existing) % len(SUBJECT_COLORS)])
        con.execute(
            "INSERT INTO subjects (name, color, goal_seconds) VALUES (?, ?, 0)",
            (name, color),
        )
        con.commit()
        row = con.execute(
            "SELECT id, name, color, goal_seconds FROM subjects WHERE name = ?", (name,)
        ).fetchone()
        return jsonify(dict(row)), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": f"「{name}」はすでに登録されています"}), 409
    finally:
        con.close()


@app.delete("/api/subjects/<int:subject_id>")
def api_delete_subject(subject_id):
    con = get_db()
    con.execute("DELETE FROM records WHERE subject_id = ?", (subject_id,))
    con.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))
    con.commit()
    con.close()
    return "", 204


@app.patch("/api/subjects/<int:subject_id>")
def api_update_subject(subject_id):
    data = request.json
    con = get_db()
    if "goal_seconds" in data:
        con.execute(
            "UPDATE subjects SET goal_seconds = ? WHERE id = ?",
            (int(data["goal_seconds"]), subject_id),
        )
    if "color" in data:
        con.execute(
            "UPDATE subjects SET color = ? WHERE id = ?",
            (data["color"], subject_id),
        )
    con.commit()
    con.close()
    return "", 204


@app.post("/api/records")
def api_save_record():
    data = request.json
    subject_id = data.get("subject_id")
    seconds = int(data.get("seconds", 0))
    memo = (data.get("memo") or "").strip()
    record_date = data.get("date") or date.today().isoformat()
    if not subject_id or seconds < 1:
        return jsonify({"error": "無効なデータ"}), 400
    con = get_db()
    con.execute(
        "INSERT INTO records (subject_id, date, seconds, memo) VALUES (?, ?, ?, ?)",
        (subject_id, record_date, seconds, memo),
    )
    con.commit()
    con.close()
    return "", 201


@app.get("/api/today")
def api_today():
    con = get_db()
    rows = con.execute("""
        SELECT s.name, SUM(r.seconds) as seconds, s.color, s.goal_seconds
        FROM records r
        JOIN subjects s ON s.id = r.subject_id
        WHERE r.date = ?
        GROUP BY s.id
        ORDER BY SUM(r.seconds) DESC
    """, (date.today().isoformat(),)).fetchall()
    con.close()
    return jsonify([dict(r) for r in rows])


@app.get("/api/streak")
def api_streak():
    con = get_db()
    rows = con.execute(
        "SELECT DISTINCT date FROM records ORDER BY date DESC"
    ).fetchall()
    con.close()
    if not rows:
        return jsonify({"streak": 0})
    dates = [date.fromisoformat(r["date"]) for r in rows]
    yesterday = date.today() - timedelta(days=1)
    if dates[0] < yesterday:
        return jsonify({"streak": 0})
    streak = 0
    expected = dates[0]
    for d in dates:
        if d == expected:
            streak += 1
            expected -= timedelta(days=1)
        else:
            break
    return jsonify({"streak": streak})


@app.get("/api/history")
def api_history():
    con = get_db()
    rows = con.execute("""
        SELECT r.date, s.name, SUM(r.seconds) as seconds,
               COALESCE(GROUP_CONCAT(
                   CASE WHEN r.memo != '' THEN r.memo END, ' / '
               ), '') as memo
        FROM records r
        JOIN subjects s ON s.id = r.subject_id
        GROUP BY r.date, s.id
        ORDER BY r.date DESC, SUM(r.seconds) DESC
        LIMIT 200
    """).fetchall()
    con.close()
    result = []
    for r in rows:
        d = dict(r)
        d["time_str"] = fmt(d["seconds"])
        result.append(d)
    return jsonify(result)


@app.get("/api/graph/week")
def api_graph_week():
    today = date.today()
    days = [(today - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
    con = get_db()
    rows = con.execute("""
        SELECT date, SUM(seconds) as seconds FROM records
        WHERE date >= ? GROUP BY date
    """, (days[0],)).fetchall()
    con.close()
    data_map = {r["date"]: r["seconds"] for r in rows}
    return jsonify([{"date": d, "seconds": data_map.get(d, 0)} for d in days])


@app.get("/api/graph/month")
def api_graph_month():
    today = date.today()
    first = date(today.year, today.month, 1)
    if today.month == 12:
        last = date(today.year + 1, 1, 1) - timedelta(days=1)
    else:
        last = date(today.year, today.month + 1, 1) - timedelta(days=1)
    con = get_db()
    rows = con.execute("""
        SELECT date, SUM(seconds) as seconds FROM records
        WHERE date >= ? AND date <= ? GROUP BY date
    """, (first.isoformat(), last.isoformat())).fetchall()
    con.close()
    data_map = {r["date"]: r["seconds"] for r in rows}
    result = []
    d = first
    while d <= last:
        result.append({"date": d.isoformat(), "seconds": data_map.get(d.isoformat(), 0)})
        d += timedelta(days=1)
    return jsonify(result)


@app.get("/api/date-colors")
def api_date_colors():
    con = get_db()
    rows = con.execute("""
        SELECT r.date, s.color
        FROM records r JOIN subjects s ON s.id = r.subject_id
        GROUP BY r.date, s.id
        ORDER BY r.date, SUM(r.seconds) DESC
    """).fetchall()
    con.close()
    seen = set()
    result = {}
    for r in rows:
        d, clr = r["date"], r["color"]
        if d not in seen:
            result[d] = clr
            seen.add(d)
    return jsonify(result)


# ── ページ ────────────────────────────────────────────────────────────────────

@app.get("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)

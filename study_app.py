import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
import time
from datetime import datetime, date, timedelta


DB_PATH = "study_records.db"

# ── カラーパレット（ダークテーマ）────────────────────────────────────────────
BG         = "#12121E"
SURFACE    = "#1E1E30"
SURFACE2   = "#252540"
ACCENT     = "#5B8DEF"
ACCENT_D   = "#4A7CE0"
DANGER     = "#FF6B6B"
DANGER_D   = "#E05555"
SUCCESS    = "#5BC47F"
SUCCESS_D  = "#4AAD6D"
TEXT1      = "#EAEAF2"
TEXT2      = "#8A8AA8"
BORDER     = "#2E2E4A"
STREAK_CLR = "#FFB347"

SUBJECT_COLORS = [
    "#5B8DEF", "#FF6B6B", "#5BC47F", "#FFB347",
    "#C77DFF", "#56CFE1", "#FF85A1", "#FFD93D",
]


# ── データベース ──────────────────────────────────────────────────────────────

def init_db():
    con = sqlite3.connect(DB_PATH)
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
    # 既存DBへのマイグレーション
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


def get_subjects():
    con = sqlite3.connect(DB_PATH)
    rows = con.execute(
        "SELECT id, name, color, goal_seconds FROM subjects ORDER BY name"
    ).fetchall()
    con.close()
    return rows


def add_subject(name):
    con = sqlite3.connect(DB_PATH)
    try:
        existing = con.execute("SELECT color FROM subjects").fetchall()
        used = [r[0] for r in existing]
        color = next((c for c in SUBJECT_COLORS if c not in used),
                     SUBJECT_COLORS[len(existing) % len(SUBJECT_COLORS)])
        con.execute(
            "INSERT INTO subjects (name, color, goal_seconds) VALUES (?, ?, 0)",
            (name, color)
        )
        con.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        con.close()


def delete_subject(subject_id):
    con = sqlite3.connect(DB_PATH)
    con.execute("DELETE FROM records WHERE subject_id = ?", (subject_id,))
    con.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))
    con.commit()
    con.close()


def update_subject_goal(subject_id, goal_seconds):
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "UPDATE subjects SET goal_seconds = ? WHERE id = ?",
        (goal_seconds, subject_id)
    )
    con.commit()
    con.close()


def update_subject_color(subject_id, color):
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "UPDATE subjects SET color = ? WHERE id = ?",
        (color, subject_id)
    )
    con.commit()
    con.close()


def save_record(subject_id, seconds, memo=""):
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "INSERT INTO records (subject_id, date, seconds, memo) VALUES (?, ?, ?, ?)",
        (subject_id, date.today().isoformat(), seconds, memo),
    )
    con.commit()
    con.close()


def get_today_summary():
    con = sqlite3.connect(DB_PATH)
    rows = con.execute("""
        SELECT s.name, SUM(r.seconds), s.color, s.goal_seconds
        FROM records r
        JOIN subjects s ON s.id = r.subject_id
        WHERE r.date = ?
        GROUP BY s.id
        ORDER BY SUM(r.seconds) DESC
    """, (date.today().isoformat(),)).fetchall()
    con.close()
    return rows


def get_streak():
    con = sqlite3.connect(DB_PATH)
    rows = con.execute(
        "SELECT DISTINCT date FROM records ORDER BY date DESC"
    ).fetchall()
    con.close()
    if not rows:
        return 0
    dates = [date.fromisoformat(r[0]) for r in rows]
    yesterday = date.today() - timedelta(days=1)
    if dates[0] < yesterday:
        return 0
    streak = 0
    expected = dates[0]
    for d in dates:
        if d == expected:
            streak += 1
            expected -= timedelta(days=1)
        else:
            break
    return streak


def get_history():
    con = sqlite3.connect(DB_PATH)
    rows = con.execute("""
        SELECT r.date, s.name, SUM(r.seconds),
               COALESCE(GROUP_CONCAT(
                   CASE WHEN r.memo != '' THEN r.memo END, ' / '
               ), '')
        FROM records r
        JOIN subjects s ON s.id = r.subject_id
        GROUP BY r.date, s.id
        ORDER BY r.date DESC, SUM(r.seconds) DESC
        LIMIT 200
    """).fetchall()
    con.close()
    return rows


def get_weekly_data():
    today = date.today()
    days = [(today - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
    con = sqlite3.connect(DB_PATH)
    rows = con.execute("""
        SELECT date, SUM(seconds) FROM records
        WHERE date >= ? GROUP BY date
    """, (days[0],)).fetchall()
    con.close()
    data = {d: s for d, s in rows}
    return [(d, data.get(d, 0)) for d in days]


def get_monthly_data():
    today = date.today()
    first = date(today.year, today.month, 1)
    if today.month == 12:
        last = date(today.year + 1, 1, 1) - timedelta(days=1)
    else:
        last = date(today.year, today.month + 1, 1) - timedelta(days=1)
    con = sqlite3.connect(DB_PATH)
    rows = con.execute("""
        SELECT date, SUM(seconds) FROM records
        WHERE date >= ? AND date <= ? GROUP BY date
    """, (first.isoformat(), last.isoformat())).fetchall()
    con.close()
    data = {d: s for d, s in rows}
    result = []
    d = first
    while d <= last:
        result.append((d.isoformat(), data.get(d.isoformat(), 0)))
        d += timedelta(days=1)
    return result


def get_date_colors():
    """日付ごとに最も多く勉強した科目の色を返す"""
    con = sqlite3.connect(DB_PATH)
    rows = con.execute("""
        SELECT r.date, s.color
        FROM records r JOIN subjects s ON s.id = r.subject_id
        GROUP BY r.date, s.id
        ORDER BY r.date, SUM(r.seconds) DESC
    """).fetchall()
    con.close()
    seen = set()
    result = {}
    for d, clr in rows:
        if d not in seen:
            result[d] = clr
            seen.add(d)
    return result


# ── ユーティリティ ────────────────────────────────────────────────────────────

def fmt(seconds):
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


# ── アプリ本体 ────────────────────────────────────────────────────────────────

class StudyApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Study Tracker")
        self.geometry("760x610")
        self.resizable(False, False)
        self.configure(bg=BG)

        self.running = False
        self.start_time = None
        self.selected_subject_id = None
        self.selected_subject_name = ""
        self.selected_subject_color = ACCENT
        self._after_id = None

        init_db()
        self._apply_styles()
        self._build_ui()
        self._refresh_subjects()
        self._refresh_today()
        self._refresh_streak()

    # ── ttk スタイル ──────────────────────────────────────────────────────────

    def _apply_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure("Dark.TNotebook",
                        background=BG, borderwidth=0, tabmargins=[0, 0, 0, 0])
        style.configure("Dark.TNotebook.Tab",
                        background=SURFACE2, foreground=TEXT2,
                        font=("Yu Gothic UI", 12, "bold"),
                        padding=[24, 10], borderwidth=0, focuscolor=BG)
        style.map("Dark.TNotebook.Tab",
                  background=[("selected", SURFACE), ("active", SURFACE2)],
                  foreground=[("selected", TEXT1), ("active", TEXT1)])

        style.configure("Dark.Treeview",
                        background=SURFACE, foreground=TEXT1,
                        fieldbackground=SURFACE, rowheight=32,
                        font=("Yu Gothic UI", 10), borderwidth=0)
        style.configure("Dark.Treeview.Heading",
                        background=SURFACE2, foreground=TEXT2,
                        font=("Yu Gothic UI", 10, "bold"),
                        relief="flat", borderwidth=0)
        style.map("Dark.Treeview",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", "#FFFFFF")])
        style.map("Dark.Treeview.Heading",
                  background=[("active", SURFACE2)])

        style.configure("Dark.Vertical.TScrollbar",
                        background=SURFACE2, troughcolor=SURFACE,
                        borderwidth=0, arrowcolor=TEXT2, relief="flat")

    # ── UI 構築 ───────────────────────────────────────────────────────────────

    def _build_ui(self):
        header = tk.Frame(self, bg=BG, height=56)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="Study Tracker", font=("Yu Gothic UI", 18, "bold"),
                 bg=BG, fg=TEXT1).pack(side="left", padx=24, pady=12)
        try:
            today_str = date.today().strftime("%Y年%m月%d日")
        except Exception:
            today_str = date.today().isoformat()
        tk.Label(header, text=today_str, font=("Yu Gothic UI", 11),
                 bg=BG, fg=TEXT2).pack(side="right", padx=24)

        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        nb = ttk.Notebook(self, style="Dark.TNotebook")
        nb.pack(fill="both", expand=True)

        self.tab_timer   = tk.Frame(nb, bg=BG)
        self.tab_history = tk.Frame(nb, bg=BG)
        self.tab_graph   = tk.Frame(nb, bg=BG)
        nb.add(self.tab_timer,   text="  タイマー  ")
        nb.add(self.tab_history, text="  履歴  ")
        nb.add(self.tab_graph,   text="  グラフ  ")

        self._build_timer_tab()
        self._build_history_tab()
        self._build_graph_tab()

    # ── タイマータブ ──────────────────────────────────────────────────────────

    def _build_timer_tab(self):
        parent = self.tab_timer

        # 左：科目リスト
        left = tk.Frame(parent, bg=SURFACE, width=220)
        left.pack(side="left", fill="y", padx=(16, 8), pady=16)
        left.pack_propagate(False)

        tk.Label(left, text="科目リスト",
                 font=("Yu Gothic UI", 13, "bold"),
                 bg=SURFACE, fg=TEXT1).pack(pady=(16, 8), padx=16, anchor="w")
        tk.Frame(left, bg=BORDER, height=1).pack(fill="x", padx=16)

        self.subject_listbox = tk.Listbox(
            left, font=("Yu Gothic UI", 12), selectmode="single",
            activestyle="none", relief="flat", bd=0,
            bg=SURFACE, fg=TEXT1,
            selectbackground=ACCENT, selectforeground="#FFFFFF",
            highlightthickness=0,
        )
        self.subject_listbox.pack(fill="both", expand=True, pady=8)
        self.subject_listbox.bind("<<ListboxSelect>>", self._on_subject_select)
        self.subject_listbox.bind("<Button-3>", self._on_subject_right_click)

        tk.Frame(left, bg=BORDER, height=1).pack(fill="x", padx=16)

        btn_row1 = tk.Frame(left, bg=SURFACE)
        btn_row1.pack(pady=(8, 4), padx=16, fill="x")
        self._flat_btn(btn_row1, "＋ 追加", self._add_subject,
                       ACCENT, ACCENT_D, "#FFFFFF").pack(
            side="left", fill="x", expand=True, padx=(0, 4))
        self._flat_btn(btn_row1, "削除", self._delete_subject,
                       DANGER, DANGER_D, "#FFFFFF").pack(
            side="left", fill="x", expand=True, padx=(4, 0))

        btn_row2 = tk.Frame(left, bg=SURFACE)
        btn_row2.pack(pady=(0, 12), padx=16, fill="x")
        self._flat_btn(btn_row2, "目標設定", self._set_goal,
                       SURFACE2, BORDER, TEXT2).pack(
            side="left", fill="x", expand=True, padx=(0, 4))
        self._flat_btn(btn_row2, "色変更", self._change_color,
                       SURFACE2, BORDER, TEXT2).pack(
            side="left", fill="x", expand=True, padx=(4, 0))

        # 右：タイマー
        right = tk.Frame(parent, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=(0, 16), pady=16)

        # ストリークカード
        self.streak_card = tk.Frame(right, bg=SURFACE2, padx=16, pady=6)
        self.streak_card.pack(fill="x", padx=24, pady=(8, 0))
        self.lbl_streak = tk.Label(
            self.streak_card, text="",
            font=("Yu Gothic UI", 11, "bold"),
            bg=SURFACE2, fg=STREAK_CLR,
        )
        self.lbl_streak.pack(side="left")

        # 科目名ラベル
        self.lbl_subject = tk.Label(
            right, text="科目を選択してください",
            font=("Yu Gothic UI", 15), bg=BG, fg=TEXT2,
        )
        self.lbl_subject.pack(pady=(10, 0))

        # タイマーカード
        timer_card = tk.Frame(right, bg=SURFACE, padx=32, pady=14)
        timer_card.pack(pady=(10, 0), padx=24, fill="x")
        self.lbl_timer = tk.Label(
            timer_card, text="00:00:00",
            font=("Yu Gothic UI", 52, "bold"), bg=SURFACE, fg=ACCENT,
        )
        self.lbl_timer.pack()

        # 開始/停止ボタン
        self.btn_toggle = tk.Button(
            right, text="開始", font=("Yu Gothic UI", 15, "bold"),
            bg=SUCCESS, fg="#FFFFFF",
            activebackground=SUCCESS_D, activeforeground="#FFFFFF",
            relief="flat", bd=0, width=14, height=2, cursor="hand2",
            command=self._toggle_timer,
        )
        self.btn_toggle.pack(pady=10)

        # 今日の集計
        tk.Label(right, text="今日の勉強時間",
                 font=("Yu Gothic UI", 12, "bold"),
                 bg=BG, fg=TEXT2).pack(anchor="w", padx=24, pady=(2, 4))
        self.today_card = tk.Frame(right, bg=SURFACE, padx=16, pady=10)
        self.today_card.pack(fill="x", padx=24)

    # ── 履歴タブ ──────────────────────────────────────────────────────────────

    def _build_history_tab(self):
        parent = self.tab_history

        tk.Label(parent, text="学習履歴",
                 font=("Yu Gothic UI", 14, "bold"),
                 bg=BG, fg=TEXT1).pack(anchor="w", padx=20, pady=(16, 8))

        frame = tk.Frame(parent, bg=BG)
        frame.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        cols = ("date", "subject", "time", "memo")
        self.tree = ttk.Treeview(
            frame, columns=cols, show="headings",
            height=15, style="Dark.Treeview",
        )
        self.tree.heading("date",    text="日付")
        self.tree.heading("subject", text="科目")
        self.tree.heading("time",    text="勉強時間")
        self.tree.heading("memo",    text="メモ")
        self.tree.column("date",    width=120, anchor="center")
        self.tree.column("subject", width=180, anchor="w")
        self.tree.column("time",    width=110, anchor="center")
        self.tree.column("memo",    width=290, anchor="w")

        sb = ttk.Scrollbar(frame, orient="vertical",
                           command=self.tree.yview,
                           style="Dark.Vertical.TScrollbar")
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        parent.bind("<Visibility>", lambda e: self._refresh_history())

    # ── グラフタブ ────────────────────────────────────────────────────────────

    def _build_graph_tab(self):
        parent = self.tab_graph
        self._graph_mode = "week"

        header = tk.Frame(parent, bg=BG)
        header.pack(fill="x", padx=20, pady=(14, 8))
        tk.Label(header, text="勉強時間グラフ",
                 font=("Yu Gothic UI", 14, "bold"),
                 bg=BG, fg=TEXT1).pack(side="left")

        btn_area = tk.Frame(header, bg=BG)
        btn_area.pack(side="right")
        self._btn_week = tk.Button(
            btn_area, text="週", font=("Yu Gothic UI", 11, "bold"),
            bg=ACCENT, fg="#FFFFFF",
            activebackground=ACCENT_D, activeforeground="#FFFFFF",
            relief="flat", bd=0, padx=16, pady=4, cursor="hand2",
            command=self._show_week,
        )
        self._btn_week.pack(side="left", padx=(0, 4))
        self._btn_month = tk.Button(
            btn_area, text="月", font=("Yu Gothic UI", 11, "bold"),
            bg=SURFACE2, fg=TEXT2,
            activebackground=SURFACE2, activeforeground=TEXT1,
            relief="flat", bd=0, padx=16, pady=4, cursor="hand2",
            command=self._show_month,
        )
        self._btn_month.pack(side="left")

        self._graph_canvas = tk.Canvas(
            parent, bg=SURFACE, highlightthickness=0,
            width=716, height=406,
        )
        self._graph_canvas.pack(padx=20, pady=(0, 14))

        parent.bind("<Visibility>", lambda e: self._draw_graph())

    # ── ウィジェット補助 ──────────────────────────────────────────────────────

    def _flat_btn(self, parent, text, cmd, bg, bg_active, fg):
        return tk.Button(
            parent, text=text, command=cmd,
            font=("Yu Gothic UI", 10, "bold"),
            bg=bg, fg=fg,
            activebackground=bg_active, activeforeground=TEXT1,
            relief="flat", bd=0, padx=8, pady=6, cursor="hand2",
        )

    # ── 科目操作 ──────────────────────────────────────────────────────────────

    def _refresh_subjects(self):
        self.subject_listbox.delete(0, "end")
        self._subjects = get_subjects()  # (id, name, color, goal_seconds)
        for _, name, color, _ in self._subjects:
            self.subject_listbox.insert("end", f"  {name}")
            self.subject_listbox.itemconfig(
                self.subject_listbox.size() - 1, fg=color
            )

    def _on_subject_select(self, _event=None):
        if self.running:
            return
        sel = self.subject_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        sid, sname, scolor, _ = self._subjects[idx]
        self.selected_subject_id = sid
        self.selected_subject_name = sname
        self.selected_subject_color = scolor
        self.lbl_subject.config(text=sname, fg=scolor)
        self.lbl_timer.config(fg=scolor)

    def _on_subject_right_click(self, event):
        idx = self.subject_listbox.nearest(event.y)
        if idx < 0 or idx >= len(self._subjects):
            return
        self.subject_listbox.selection_clear(0, "end")
        self.subject_listbox.selection_set(idx)
        self._on_subject_select()
        menu = tk.Menu(self, tearoff=0, bg=SURFACE2, fg=TEXT1,
                       activebackground=ACCENT, activeforeground="#FFFFFF",
                       borderwidth=0)
        menu.add_command(label="目標設定", command=self._set_goal)
        menu.add_command(label="色変更",   command=self._change_color)
        menu.add_separator()
        menu.add_command(label="削除",     command=self._delete_subject)
        menu.tk_popup(event.x_root, event.y_root)

    def _add_subject(self):
        name = simpledialog.askstring("科目を追加", "科目名を入力してください:", parent=self)
        if not name:
            return
        name = name.strip()
        if not name:
            return
        if add_subject(name):
            self._refresh_subjects()
        else:
            messagebox.showwarning("重複", f"「{name}」はすでに登録されています。")

    def _delete_subject(self):
        sel = self.subject_listbox.curselection()
        if not sel:
            messagebox.showinfo("選択なし", "削除する科目を選択してください。")
            return
        idx = sel[0]
        sid, sname, _, _ = self._subjects[idx]
        if self.running and self.selected_subject_id == sid:
            messagebox.showwarning("計測中", "計測中の科目は削除できません。")
            return
        if messagebox.askyesno("確認", f"「{sname}」とその記録を削除しますか？"):
            delete_subject(sid)
            if self.selected_subject_id == sid:
                self.selected_subject_id = None
                self.selected_subject_name = ""
                self.selected_subject_color = ACCENT
                self.lbl_subject.config(text="科目を選択してください", fg=TEXT2)
                self.lbl_timer.config(fg=ACCENT)
            self._refresh_subjects()
            self._refresh_today()

    def _set_goal(self):
        sel = self.subject_listbox.curselection()
        if not sel:
            messagebox.showinfo("選択なし", "目標を設定する科目を選択してください。")
            return
        idx = sel[0]
        sid, sname, _, current_goal = self._subjects[idx]
        val = simpledialog.askinteger(
            "目標時間設定",
            f"「{sname}」の1日の目標時間（分）:\n（0 で目標なし）",
            initialvalue=current_goal // 60,
            minvalue=0, maxvalue=1440,
            parent=self,
        )
        if val is None:
            return
        update_subject_goal(sid, val * 60)
        self._refresh_subjects()
        self._refresh_today()

    def _change_color(self):
        sel = self.subject_listbox.curselection()
        if not sel:
            messagebox.showinfo("選択なし", "色を変更する科目を選択してください。")
            return
        idx = sel[0]
        sid, sname, current_color, _ = self._subjects[idx]
        new_color = self._pick_color_dialog(current_color)
        if new_color and new_color != current_color:
            update_subject_color(sid, new_color)
            if self.selected_subject_id == sid:
                self.selected_subject_color = new_color
                self.lbl_subject.config(fg=new_color)
                self.lbl_timer.config(fg=new_color)
            self._refresh_subjects()
            self._refresh_today()

    def _pick_color_dialog(self, current_color):
        result = [None]
        dlg = tk.Toplevel(self)
        dlg.title("色を選択")
        dlg.configure(bg=BG)
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.geometry(f"+{self.winfo_x() + 180}+{self.winfo_y() + 180}")

        tk.Label(dlg, text="科目の色を選択してください",
                 font=("Yu Gothic UI", 12, "bold"),
                 bg=BG, fg=TEXT1).pack(pady=(20, 14), padx=24)

        frame = tk.Frame(dlg, bg=BG)
        frame.pack(padx=24, pady=(0, 20))

        for i, color in enumerate(SUBJECT_COLORS):
            outer = tk.Frame(
                frame,
                bg=TEXT1 if color == current_color else BG,
                padx=2, pady=2
            )
            outer.grid(row=0, column=i, padx=5)
            tk.Button(
                outer, bg=color, width=3, height=1,
                relief="flat", cursor="hand2", bd=0,
                command=lambda c=color: [result.__setitem__(0, c), dlg.destroy()]
            ).pack()

        self.wait_window(dlg)
        return result[0]

    # ── タイマー ──────────────────────────────────────────────────────────────

    def _toggle_timer(self):
        if not self.running:
            self._start_timer()
        else:
            self._stop_timer()

    def _start_timer(self):
        if self.selected_subject_id is None:
            messagebox.showinfo("科目未選択", "計測する科目を選択してください。")
            return
        self.running = True
        self.start_time = time.time()
        self.btn_toggle.config(text="停止", bg=DANGER, activebackground=DANGER_D)
        self._tick()

    def _stop_timer(self):
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        self.running = False
        total = int(time.time() - self.start_time)
        memo = ""
        if total >= 1:
            memo = self._ask_memo()
            save_record(self.selected_subject_id, total, memo)
        self.btn_toggle.config(text="開始", bg=SUCCESS, activebackground=SUCCESS_D)
        self.lbl_timer.config(text="00:00:00")
        self._refresh_today()
        self._refresh_streak()
        if total >= 1:
            self._show_result(total)

    def _ask_memo(self):
        memo = simpledialog.askstring(
            "メモ", "この学習セッションのメモ（省略可）:",
            parent=self,
        )
        return memo.strip() if memo else ""

    def _tick(self):
        if not self.running:
            return
        elapsed = int(time.time() - self.start_time)
        self.lbl_timer.config(text=fmt(elapsed))
        self._after_id = self.after(500, self._tick)

    def _show_result(self, seconds):
        messagebox.showinfo(
            "記録完了",
            f"{self.selected_subject_name}\n勉強時間: {fmt(seconds)} を記録しました！",
        )

    # ── ストリーク ────────────────────────────────────────────────────────────

    def _refresh_streak(self):
        streak = get_streak()
        if streak == 0:
            self.lbl_streak.config(
                text="連続 0 日  ─  今日から始めよう！", fg=TEXT2)
        elif streak == 1:
            self.lbl_streak.config(
                text="連続 1 日継続中  ─  いいスタート！", fg=STREAK_CLR)
        else:
            self.lbl_streak.config(
                text=f"連続 {streak} 日継続中！", fg=STREAK_CLR)

    # ── 今日の集計 ────────────────────────────────────────────────────────────

    def _refresh_today(self):
        for w in self.today_card.winfo_children():
            w.destroy()

        summary = get_today_summary()  # (name, seconds, color, goal_seconds)
        if not summary:
            tk.Label(self.today_card, text="まだ記録がありません",
                     font=("Yu Gothic UI", 11), bg=SURFACE, fg=TEXT2).pack(pady=4)
            return

        total_all = sum(s for _, s, _, _ in summary)
        bar_w = 190

        for name, sec, color, goal_sec in summary:
            row = tk.Frame(self.today_card, bg=SURFACE)
            row.pack(fill="x", pady=(3, 0))

            # カラードット
            dot = tk.Canvas(row, bg=SURFACE, width=10, height=10,
                            highlightthickness=0)
            dot.create_oval(1, 1, 9, 9, fill=color, outline="")
            dot.pack(side="left", padx=(0, 6))

            tk.Label(row, text=name, font=("Yu Gothic UI", 11),
                     bg=SURFACE, fg=TEXT1, anchor="w").pack(side="left")

            if goal_sec > 0:
                pct = min(sec / goal_sec, 1.0)
                pct_str = f"{int(pct * 100)}%"
                tk.Label(row,
                         text=f"{fmt(sec)}  {pct_str}",
                         font=("Yu Gothic UI", 11, "bold"),
                         bg=SURFACE, fg=color).pack(side="right")
                # プログレスバー
                pb_row = tk.Frame(self.today_card, bg=SURFACE)
                pb_row.pack(fill="x", pady=(1, 2))
                pb = tk.Canvas(pb_row, bg=SURFACE2, width=bar_w, height=5,
                               highlightthickness=0)
                pb.create_rectangle(0, 0, int(bar_w * pct), 5,
                                    fill=color, outline="")
                pb.pack(side="left", padx=(16, 0))
                goal_h = goal_sec // 3600
                goal_m = (goal_sec % 3600) // 60
                goal_lbl = f"目標 {goal_h}h{goal_m:02d}m"
                tk.Label(pb_row, text=goal_lbl,
                         font=("Yu Gothic UI", 9), bg=SURFACE, fg=TEXT2).pack(
                    side="left", padx=8)
            else:
                tk.Label(row, text=fmt(sec),
                         font=("Yu Gothic UI", 11, "bold"),
                         bg=SURFACE, fg=color).pack(side="right")

        tk.Frame(self.today_card, bg=BORDER, height=1).pack(fill="x", pady=6)
        row = tk.Frame(self.today_card, bg=SURFACE)
        row.pack(fill="x")
        tk.Label(row, text="合計", font=("Yu Gothic UI", 12, "bold"),
                 bg=SURFACE, fg=TEXT1, anchor="w").pack(side="left")
        tk.Label(row, text=fmt(total_all), font=("Yu Gothic UI", 14, "bold"),
                 bg=SURFACE, fg=ACCENT).pack(side="right")

    # ── 履歴 ─────────────────────────────────────────────────────────────────

    def _refresh_history(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for d, name, sec, memo in get_history():
            self.tree.insert("", "end", values=(d, name, fmt(sec), memo or ""))

    # ── グラフ ────────────────────────────────────────────────────────────────

    def _show_week(self):
        self._graph_mode = "week"
        self._btn_week.config(bg=ACCENT, fg="#FFFFFF")
        self._btn_month.config(bg=SURFACE2, fg=TEXT2)
        self._draw_graph()

    def _show_month(self):
        self._graph_mode = "month"
        self._btn_month.config(bg=ACCENT, fg="#FFFFFF")
        self._btn_week.config(bg=SURFACE2, fg=TEXT2)
        self._draw_graph()

    def _draw_graph(self):
        c = self._graph_canvas
        c.delete("all")

        if self._graph_mode == "week":
            data = get_weekly_data()
            week_days = ["月", "火", "水", "木", "金", "土", "日"]
            labels = [
                week_days[datetime.strptime(d, "%Y-%m-%d").weekday()] + f"\n{d[5:]}"
                for d, _ in data
            ]
        else:
            data = get_monthly_data()
            labels = [d[8:].lstrip("0") or "0" for d, _ in data]

        W, H = 716, 406
        pad_l, pad_r, pad_t, pad_b = 56, 16, 24, 52
        chart_w = W - pad_l - pad_r
        chart_h = H - pad_t - pad_b

        max_sec = max((s for _, s in data), default=0)
        if max_sec == 0:
            max_sec = 3600

        max_h = max_sec / 3600
        for threshold in [1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24]:
            if max_h <= threshold:
                y_max_h = threshold
                break
        else:
            y_max_h = int(max_h) + 1
        y_max_sec = y_max_h * 3600

        # グリッド & y軸ラベル
        grid_count = 4
        for i in range(grid_count + 1):
            y = pad_t + chart_h - int(chart_h * i / grid_count)
            c.create_line(pad_l, y, pad_l + chart_w, y, fill=BORDER, width=1)
            sec_val = int(y_max_sec * i / grid_count)
            h_val = sec_val // 3600
            m_val = (sec_val % 3600) // 60
            label = f"{h_val}h" if m_val == 0 else f"{h_val}:{m_val:02d}"
            c.create_text(pad_l - 6, y, text=label, anchor="e",
                          font=("Yu Gothic UI", 9), fill=TEXT2)

        n = len(data)
        if n == 0:
            return

        today_str = date.today().isoformat()
        bar_area_w = chart_w / n
        bar_w = max(4, bar_area_w * (0.6 if n <= 14 else 0.75))
        date_color = get_date_colors()

        for i, ((d, sec), lbl) in enumerate(zip(data, labels)):
            cx = pad_l + bar_area_w * i + bar_area_w / 2
            bar_h = int(chart_h * sec / y_max_sec)
            x0 = cx - bar_w / 2
            x1 = cx + bar_w / 2
            y_top = pad_t + chart_h - bar_h
            y_bot = pad_t + chart_h

            color = SUCCESS if d == today_str else date_color.get(d, ACCENT)

            if bar_h > 0:
                c.create_rectangle(x0, y_top + 4, x1, y_bot, fill=color, outline="")
                c.create_oval(x0, y_top, x1, y_top + 8, fill=color, outline="")

            font_size = 9 if n <= 14 else 8
            for j, line in enumerate(lbl.split("\n")):
                c.create_text(cx, pad_t + chart_h + 8 + j * 14, text=line,
                              anchor="n", font=("Yu Gothic UI", font_size), fill=TEXT2)

            if sec > 0 and bar_h > 14:
                h = sec // 3600
                m = (sec % 3600) // 60
                val_str = f"{h}h{m:02d}m" if h > 0 else f"{m}m"
                c.create_text(cx, y_top - 4, text=val_str, anchor="s",
                              font=("Yu Gothic UI", 8), fill=TEXT1)

        c.create_line(pad_l, pad_t + chart_h, pad_l + chart_w, pad_t + chart_h,
                      fill=BORDER, width=1)


if __name__ == "__main__":
    app = StudyApp()
    app.mainloop()

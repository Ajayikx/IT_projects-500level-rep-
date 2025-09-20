# app.py - Main Application File
import customtkinter as ctk
from tkinter import filedialog, messagebox
import sqlite3, os, hashlib, secrets, json, csv

# Set appearance mode
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")
QUIZ_DB_PATH = os.path.join(os.path.dirname(__file__), "quiz.db")


# ---------- Security helpers ----------
def hash_password(password: str, salt: bytes = None) -> tuple:
    if salt is None:
        salt = secrets.token_bytes(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return salt, hashed


def verify_password(password: str, salt: bytes, hashed: bytes) -> bool:
    test_hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return secrets.compare_digest(test_hashed, hashed)


# ---------- Database Functions ----------
def init_user_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
              CREATE TABLE IF NOT EXISTS users
              (
                  id
                  INTEGER
                  PRIMARY
                  KEY
                  AUTOINCREMENT,
                  username
                  TEXT
                  UNIQUE
                  NOT
                  NULL,
                  salt
                  BLOB
                  NOT
                  NULL,
                  password_hash
                  BLOB
                  NOT
                  NULL
              )
              """)
    conn.commit()
    conn.close()


def init_quiz_db():
    conn = sqlite3.connect(QUIZ_DB_PATH)
    cur = conn.cursor()

    # Create questions table
    cur.execute('''
                CREATE TABLE IF NOT EXISTS questions
                (
                    id
                    INTEGER
                    PRIMARY
                    KEY
                    AUTOINCREMENT,
                    type
                    TEXT
                    NOT
                    NULL,
                    text
                    TEXT
                    NOT
                    NULL,
                    choices
                    TEXT,
                    answer
                    TEXT
                    NOT
                    NULL
                )
                ''')

    # Create history table
    cur.execute('''
                CREATE TABLE IF NOT EXISTS history
                (
                    id
                    INTEGER
                    PRIMARY
                    KEY
                    AUTOINCREMENT,
                    username
                    TEXT
                    NOT
                    NULL,
                    score
                    INTEGER
                    NOT
                    NULL,
                    total
                    INTEGER
                    NOT
                    NULL,
                    date
                    TIMESTAMP
                    DEFAULT
                    CURRENT_TIMESTAMP
                )
                ''')

    # Check if date column exists in history table, add it if missing
    cur.execute("PRAGMA table_info(history)")
    columns = [column[1] for column in cur.fetchall()]

    if 'date' not in columns:
        try:
            cur.execute("ALTER TABLE history ADD COLUMN date TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            # Update existing records with current timestamp
            cur.execute("UPDATE history SET date = CURRENT_TIMESTAMP WHERE date IS NULL")
        except sqlite3.Error:
            pass  # Column might already exist

    conn.commit()
    conn.close()


def register_user(username: str, password: str):
    username = username.strip()
    if not username or not password:
        return False, "Provide username and password."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    if sum(c.isdigit() for c in password) < 1 or sum(c.isalpha() for c in password) < 1:
        return False, "Password should include letters and numbers."

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username = ?", (username,))
    if c.fetchone():
        conn.close()
        return False, "Username already exists."

    salt, hashed = hash_password(password)
    try:
        c.execute("INSERT INTO users (username, salt, password_hash) VALUES (?, ?, ?)", (username, salt, hashed))
        conn.commit()
        return True, "Registration successful."
    except sqlite3.IntegrityError:
        return False, "Username already exists."
    finally:
        conn.close()


def authenticate_user(username: str, password: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT salt, password_hash FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()
    if not row:
        return False
    salt, stored_hash = row[0], row[1]
    return verify_password(password, salt, stored_hash)


def insert_question(question, options, answer, qtype):
    conn = sqlite3.connect(QUIZ_DB_PATH)
    cur = conn.cursor()
    options_str = "|".join(options) if isinstance(options, list) else str(options)
    cur.execute("INSERT INTO questions (type, text, choices, answer) VALUES (?, ?, ?, ?)",
                (qtype, question, options_str, answer))
    conn.commit()
    conn.close()


def load_questions_from_db():
    conn = sqlite3.connect(QUIZ_DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM questions")
    rows = cur.fetchall()
    conn.close()
    return rows


def save_history(username, score, total):
    conn = sqlite3.connect(QUIZ_DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO history (username, score, total) VALUES (?, ?, ?)",
                (username, score, total))
    conn.commit()
    conn.close()


def load_history(username):
    conn = sqlite3.connect(QUIZ_DB_PATH)
    cur = conn.cursor()

    # Check if date column exists
    cur.execute("PRAGMA table_info(history)")
    columns = [column[1] for column in cur.fetchall()]

    if 'date' in columns:
        cur.execute("SELECT * FROM history WHERE username = ? ORDER BY date DESC", (username,))
    else:
        cur.execute("SELECT * FROM history WHERE username = ?", (username,))

    rows = cur.fetchall()
    conn.close()
    return rows


# ---------- Gradient Frame ----------
class GradientFrame(ctk.CTkCanvas):
    def __init__(self, master, color1="#6a11cb", color2="#2575fc", **kwargs):
        super().__init__(master, **kwargs, highlightthickness=0)
        self.color1 = color1
        self.color2 = color2
        self.bind("<Configure>", self._draw_gradient)

    def _draw_gradient(self, event=None):
        self.delete("gradient")
        width, height = self.winfo_width(), self.winfo_height()
        if width <= 1 or height <= 1:
            return

        try:
            (r1, g1, b1) = self.winfo_rgb(self.color1)
            (r2, g2, b2) = self.winfo_rgb(self.color2)
            r_ratio = float(r2 - r1) / height
            g_ratio = float(g2 - g1) / height
            b_ratio = float(b2 - b1) / height

            for i in range(height):
                nr = int(r1 + (r_ratio * i))
                ng = int(g1 + (g_ratio * i))
                nb = int(b1 + (b_ratio * i))
                color = f"#{nr >> 8:02x}{ng >> 8:02x}{nb >> 8:02x}"
                self.create_line(0, i, width, i, tags=("gradient",), fill=color)
            self.lower("gradient")
        except:
            pass


# ---------- Quiz Screen ----------
class QuizScreen(ctk.CTkFrame):
    def __init__(self, master, app, username="Guest", duration=180):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.username = username
        self.pack(fill="both", expand=True)

        # Load questions
        self.questions = load_questions_from_db()
        if not self.questions:
            messagebox.showwarning("No Questions", "No quiz available. Please add questions first.")
            app.show_home()
            return

        self.index = 0
        self.user_answers = {}
        self.total = len(self.questions)
        self.timer_seconds = duration
        self.initial_duration = duration
        self.timer_id = None
        self.quiz_submitted = False

        self.option_widgets = []
        self.var = None

        self._build_ui()
        self._load_question()
        self._start_timer()

    def _build_ui(self):
        # Progress bar
        self.progress = ctk.CTkProgressBar(self, width=700, height=12)
        self.progress.set(0)
        self.progress.pack(pady=(15, 5), padx=20)

        # Header info
        self.header_info = ctk.CTkFrame(self, fg_color="transparent")
        self.header_info.pack(fill="x", padx=20, pady=5)

        self.timer_label = ctk.CTkLabel(
            self.header_info,
            text=self._format_time(self.timer_seconds),
            font=("Segoe UI", 14, "bold")
        )
        self.timer_label.pack(side="right")

        self.question_counter = ctk.CTkLabel(
            self.header_info,
            text=f"Question {self.index + 1} of {self.total}",
            font=("Segoe UI", 14)
        )
        self.question_counter.pack(side="left")

        # Question area
        self.q_label = ctk.CTkLabel(
            self,
            text="",
            wraplength=680,
            font=("Segoe UI", 18, "bold"),
            anchor="w",
            justify="left"
        )
        self.q_label.pack(pady=(20, 15), padx=20, anchor="w")

        self.options_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.options_frame.pack(pady=10, padx=40, fill="x")

        # Navigation
        self.nav_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.nav_frame.pack(pady=20)

        self.prev_btn = ctk.CTkButton(
            self.nav_frame,
            text="Previous",
            width=120,
            command=self._prev_question,
            state="disabled"
        )
        self.prev_btn.grid(row=0, column=0, padx=10)

        self.next_btn = ctk.CTkButton(
            self.nav_frame,
            text="Next",
            width=120,
            command=self._next_question
        )
        self.next_btn.grid(row=0, column=1, padx=10)

        # Action buttons
        self.action_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.action_frame.pack(pady=15)

        self.review_btn = ctk.CTkButton(
            self.action_frame,
            text="Review Answers",
            width=160,
            height=35,
            fg_color="#9b59b6",
            hover_color="#8e44ad",
            command=self._show_review
        )
        self.review_btn.grid(row=0, column=0, padx=8)

        self.submit_btn = ctk.CTkButton(
            self.action_frame,
            text="Submit Quiz",
            width=160,
            height=35,
            command=self._confirm_submit
        )
        self.submit_btn.grid(row=0, column=1, padx=8)

    def _format_time(self, seconds):
        minutes = seconds // 60
        secs = seconds % 60
        return f"Time: {minutes:02d}:{secs:02d}"

    def _start_timer(self):
        self._update_timer()

    def _update_timer(self):
        if self.quiz_submitted:
            return

        if self.timer_seconds > 0:
            self.timer_label.configure(text=self._format_time(self.timer_seconds))

            if self.timer_seconds <= 60:
                self.timer_label.configure(text_color="#e74c3c")
            elif self.timer_seconds <= 300:
                self.timer_label.configure(text_color="#f39c12")

            self.timer_seconds -= 1
            self.timer_id = self.after(1000, self._update_timer)
        else:
            self._time_expired()

    def _time_expired(self):
        messagebox.showwarning("Time Expired", "Time's up! Your quiz will be submitted automatically.")
        self._submit_quiz()

    def _load_question(self):
        # Clear previous options
        for widget in self.option_widgets:
            widget.destroy()
        self.option_widgets.clear()

        # Update counters
        self.question_counter.configure(text=f"Question {self.index + 1} of {self.total}")

        # Update navigation
        self.prev_btn.configure(state="normal" if self.index > 0 else "disabled")

        # Highlight submit on last question
        if self.index == self.total - 1:
            self.next_btn.configure(text="Last Question")
            self.submit_btn.configure(
                text="SUBMIT QUIZ",
                width=180,
                height=40,
                fg_color="#e74c3c",
                hover_color="#c0392b"
            )
        else:
            self.next_btn.configure(text="Next")
            self.submit_btn.configure(
                text="Submit Quiz",
                width=160,
                height=35,
                fg_color="#3498db",
                hover_color="#2980b9"
            )

        # Load question data
        question_data = self.questions[self.index]
        q_id, q_type, q_text, choices, correct_answer = question_data

        self.q_label.configure(text=f"Q{self.index + 1}. {q_text}")
        self.var = ctk.StringVar(value=self.user_answers.get(self.index, ""))

        # Create options based on question type
        if q_type == "mcq":
            for i, choice in enumerate(choices.split("|")):
                choice = choice.strip()
                rb = ctk.CTkRadioButton(
                    self.options_frame,
                    text=f"{chr(65 + i)}. {choice}",
                    variable=self.var,
                    value=choice,
                    font=("Segoe UI", 15)
                )
                rb.pack(anchor="w", pady=8, padx=10)
                self.option_widgets.append(rb)

        elif q_type == "truefalse":
            for choice in ["True", "False"]:
                rb = ctk.CTkRadioButton(
                    self.options_frame,
                    text=choice,
                    variable=self.var,
                    value=choice,
                    font=("Segoe UI", 15)
                )
                rb.pack(anchor="w", pady=8, padx=10)
                self.option_widgets.append(rb)

        elif q_type == "fill":
            entry = ctk.CTkEntry(
                self.options_frame,
                textvariable=self.var,
                placeholder_text="Type your answer here...",
                font=("Segoe UI", 15),
                height=40
            )
            entry.pack(pady=10, fill="x", padx=20)
            entry.focus()
            self.option_widgets.append(entry)

        self.progress.set((self.index + 1) / self.total)

    def _save_current_answer(self):
        if self.var:
            self.user_answers[self.index] = self.var.get().strip()

    def _next_question(self):
        self._save_current_answer()
        if self.index < self.total - 1:
            self.index += 1
            self._load_question()

    def _prev_question(self):
        self._save_current_answer()
        if self.index > 0:
            self.index -= 1
            self._load_question()

    def _show_review(self):
        self._save_current_answer()

        review_window = ctk.CTkToplevel(self)
        review_window.title("Review Your Answers")
        review_window.geometry("800x600")
        review_window.transient(self)
        review_window.grab_set()

        header = ctk.CTkLabel(
            review_window,
            text="Review Your Answers",
            font=("Segoe UI", 20, "bold")
        )
        header.pack(pady=20)

        scroll_frame = ctk.CTkScrollableFrame(review_window, width=750, height=400)
        scroll_frame.pack(pady=10, padx=20, fill="both", expand=True)

        unanswered_count = 0
        for i, question_data in enumerate(self.questions):
            q_text = question_data[2]
            user_answer = self.user_answers.get(i, "")

            q_frame = ctk.CTkFrame(scroll_frame)
            q_frame.pack(fill="x", pady=5, padx=10)

            ctk.CTkLabel(
                q_frame,
                text=f"Q{i + 1}. {q_text}",
                font=("Segoe UI", 14, "bold"),
                anchor="w",
                wraplength=650
            ).pack(anchor="w", padx=10, pady=(10, 5))

            answer_text = f"Your Answer: {user_answer}" if user_answer else "Not Answered"
            answer_color = "#2c3e50" if user_answer else "#e74c3c"
            if not user_answer:
                unanswered_count += 1

            ctk.CTkLabel(
                q_frame,
                text=answer_text,
                font=("Segoe UI", 12),
                text_color=answer_color,
                anchor="w"
            ).pack(anchor="w", padx=10, pady=(0, 10))

        if unanswered_count > 0:
            warning = ctk.CTkLabel(
                review_window,
                text=f"Warning: {unanswered_count} question(s) not answered",
                font=("Segoe UI", 12, "bold"),
                text_color="#e74c3c"
            )
            warning.pack(pady=10)

        button_frame = ctk.CTkFrame(review_window, fg_color="transparent")
        button_frame.pack(pady=20)

        ctk.CTkButton(
            button_frame,
            text="Continue Editing",
            command=review_window.destroy,
            width=150
        ).grid(row=0, column=0, padx=10)

        ctk.CTkButton(
            button_frame,
            text="Submit Quiz",
            command=lambda: [review_window.destroy(), self._submit_quiz()],
            fg_color="#e74c3c",
            width=150
        ).grid(row=0, column=1, padx=10)

    def _confirm_submit(self):
        self._save_current_answer()

        unanswered = sum(1 for i in range(self.total) if not self.user_answers.get(i, "").strip())

        message = f"Submit Quiz Confirmation\n\n"
        message += f"Answered: {self.total - unanswered}/{self.total} questions\n"

        if unanswered > 0:
            message += f"Unanswered: {unanswered} questions\n\n"
            message += "Unanswered questions will be marked as incorrect.\n\n"

        message += "Are you sure you want to submit your quiz?"

        result = messagebox.askyesno("Submit Quiz", message)
        if result:
            self._submit_quiz()

    def _submit_quiz(self):
        if self.quiz_submitted:
            return

        self.quiz_submitted = True

        if self.timer_id:
            self.after_cancel(self.timer_id)

        score, feedback = self._calculate_results()

        try:
            save_history(self.username, score, self.total)
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not save quiz history: {str(e)}")

        self._show_results(score, feedback)

    def _calculate_results(self):
        score = 0
        feedback = []

        for i, question_data in enumerate(self.questions):
            _, q_type, q_text, choices, correct_answer = question_data
            user_answer = self.user_answers.get(i, "").strip()

            is_correct = self._check_answer(q_type, user_answer, correct_answer)

            if is_correct:
                score += 1

            feedback.append((q_text, user_answer, correct_answer, is_correct))

        return score, feedback

    def _check_answer(self, q_type, user_answer, correct_answer):
        if not user_answer:
            return False

        if q_type == "mcq":
            return user_answer == correct_answer
        elif q_type == "truefalse":
            return user_answer.lower() == correct_answer.lower()
        elif q_type == "fill":
            return user_answer.lower() == correct_answer.strip().lower()

        return False

    def _show_results(self, score, feedback):
        # Clear current content
        for widget in self.winfo_children():
            widget.destroy()

        # Create main container
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=20, pady=10)

        percentage = (score / max(1, len(feedback))) * 100

        # Header
        header = ctk.CTkLabel(
            main_container,
            text="Quiz Results",
            font=("Segoe UI", 24, "bold")
        )
        header.pack(pady=(10, 5))

        score_label = ctk.CTkLabel(
            main_container,
            text=f"Score: {score}/{len(feedback)} ({percentage:.1f}%)",
            font=("Segoe UI", 18, "bold"),
            text_color="#27ae60" if percentage >= 70 else "#e74c3c"
        )
        score_label.pack(pady=(0, 10))

        # Progress bar
        pbar = ctk.CTkProgressBar(main_container, width=500, height=20)
        pbar.set(percentage / 100)
        pbar.pack(pady=(0, 10))

        # Performance message
        if percentage >= 90:
            message = "Excellent work!"
        elif percentage >= 70:
            message = "Good job!"
        elif percentage >= 50:
            message = "Keep practicing!"
        else:
            message = "Don't give up - try again!"

        ctk.CTkLabel(
            main_container,
            text=message,
            font=("Segoe UI", 16)
        ).pack(pady=(0, 15))

        # Results label
        ctk.CTkLabel(
            main_container,
            text="Detailed Results:",
            font=("Segoe UI", 16, "bold")
        ).pack(pady=(0, 10))

        # Scrollable results
        scroll = ctk.CTkScrollableFrame(
            main_container,
            width=700,
            height=180,
            corner_radius=8
        )
        scroll.pack(pady=(0, 15), fill="x")

        for i, (q_text, user_answer, correct_answer, is_correct) in enumerate(feedback, 1):
            box = ctk.CTkFrame(scroll, corner_radius=6)
            box.pack(fill="x", pady=3, padx=8)

            # Question text
            display_text = f"Q{i}. {q_text[:50]}..." if len(q_text) > 50 else f"Q{i}. {q_text}"
            ctk.CTkLabel(
                box,
                text=display_text,
                font=("Segoe UI", 12, "bold"),
                anchor="w"
            ).pack(anchor="w", padx=10, pady=(6, 2))

            # Answer details
            user_display = user_answer if user_answer else "No Answer"
            result_icon = "✓" if is_correct else "✗"
            result_color = "#27ae60" if is_correct else "#e74c3c"

            detail_text = f"Your: {user_display} | Correct: {correct_answer} {result_icon}"

            ctk.CTkLabel(
                box,
                text=detail_text,
                font=("Segoe UI", 11),
                anchor="w",
                text_color=result_color
            ).pack(anchor="w", padx=10, pady=(0, 6))

        # Action buttons
        self._show_action_buttons(main_container)

    def _show_action_buttons(self, parent):
        actions = ctk.CTkFrame(parent, fg_color="transparent")
        actions.pack(side="bottom", fill="x", pady=(10, 0))

        button_container = ctk.CTkFrame(actions, fg_color="transparent")
        button_container.pack()

        ctk.CTkButton(
            button_container,
            text="Retake Quiz",
            width=140,
            height=40,
            command=lambda: self.app.show_quiz(self.username, self.initial_duration)
        ).grid(row=0, column=0, padx=8)

        ctk.CTkButton(
            button_container,
            text="Main Menu",
            width=140,
            height=40,
            command=self.app.show_home
        ).grid(row=0, column=1, padx=8)

        ctk.CTkButton(
            button_container,
            text="Exit",
            width=100,
            height=40,
            fg_color="#e74c3c",
            hover_color="#c0392b",
            command=self.app.destroy
        ).grid(row=0, column=2, padx=8)

    def destroy(self):
        if self.timer_id:
            self.after_cancel(self.timer_id)
        super().destroy()


# ---------- Author Screen ----------
class AuthorScreen(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.pack(fill="both", expand=True)

        ctk.CTkLabel(self, text="Author Quiz", font=("Segoe UI", 20, "bold")).pack(pady=15)

        # Question Entry
        self.q_entry = ctk.CTkEntry(self, placeholder_text="Enter question", width=400)
        self.q_entry.pack(pady=8, fill="x", padx=20)

        # Type Selector
        self.q_type = ctk.StringVar(value="mcq")
        ctk.CTkLabel(self, text="Question Type:").pack(pady=(10, 5))
        ctk.CTkOptionMenu(self, variable=self.q_type, values=["mcq", "truefalse", "fill"],
                          command=self._on_type_change).pack(pady=5)

        # Choices Frame
        self.choices_frame = ctk.CTkFrame(self)
        self.choices_frame.pack(pady=10, fill="x", padx=20)

        self.choice_entries = []
        self._create_choice_entries()

        # Answer Entry
        ctk.CTkLabel(self, text="Correct Answer:").pack(pady=(10, 5))
        self.ans_entry = ctk.CTkEntry(self, placeholder_text="Enter correct answer", width=300)
        self.ans_entry.pack(pady=5, padx=20)

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=15)

        ctk.CTkButton(btn_frame, text="Add Question", command=self._add_question,
                      fg_color="#28a745").grid(row=0, column=0, padx=10)
        ctk.CTkButton(btn_frame, text="Clear All", command=self._clear_fields,
                      fg_color="#ffc107").grid(row=0, column=1, padx=10)
        ctk.CTkButton(btn_frame, text="Back to Home", command=self.app.show_home,
                      fg_color="#6c757d").grid(row=0, column=2, padx=10)

    def _create_choice_entries(self):
        for widget in self.choices_frame.winfo_children():
            widget.destroy()
        self.choice_entries.clear()

        if self.q_type.get() == "mcq":
            ctk.CTkLabel(self.choices_frame, text="Multiple Choice Options:").pack(pady=(5, 10))
            for i in range(4):
                entry = ctk.CTkEntry(self.choices_frame, placeholder_text=f"Choice {chr(65 + i)}", width=350)
                entry.pack(pady=3, padx=10)
                self.choice_entries.append(entry)

    def _on_type_change(self, choice):
        self._create_choice_entries()

    def _add_question(self):
        q_text = self.q_entry.get().strip()
        q_type = self.q_type.get()
        answer = self.ans_entry.get().strip()

        if not q_text or not answer:
            messagebox.showwarning("Missing Information", "Please fill in question and answer fields.")
            return

        try:
            if q_type == "mcq":
                choices = [entry.get().strip() for entry in self.choice_entries if entry.get().strip()]
                if len(choices) < 2:
                    messagebox.showwarning("Insufficient Choices",
                                           "Please provide at least 2 choices for multiple choice questions.")
                    return
                if answer not in choices:
                    messagebox.showwarning("Invalid Answer", "The correct answer must be one of the provided choices.")
                    return
                insert_question(q_text, choices, answer, "mcq")
            elif q_type == "truefalse":
                if answer.lower() not in ["true", "false"]:
                    messagebox.showwarning("Invalid Answer",
                                           "Answer for True/False questions must be 'True' or 'False'.")
                    return
                insert_question(q_text, "", answer, "truefalse")
            elif q_type == "fill":
                insert_question(q_text, "", answer, "fill")

            messagebox.showinfo("Success", "Question added successfully!")
            self._clear_fields()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to add question: {str(e)}")

    def _clear_fields(self):
        self.q_entry.delete(0, "end")
        self.ans_entry.delete(0, "end")
        for entry in self.choice_entries:
            entry.delete(0, "end")


# ---------- History Screen ----------
class HistoryScreen(ctk.CTkFrame):
    def __init__(self, master, app, username="Guest"):
        super().__init__(master)
        self.app = app
        self.username = username
        self.pack(fill="both", expand=True)

        ctk.CTkLabel(self, text=f"{self.username}'s Quiz History",
                     font=("Segoe UI", 20, "bold")).pack(pady=15)

        history = load_history(username)

        if not history:
            ctk.CTkLabel(self, text="No quiz history found.",
                         font=("Segoe UI", 14)).pack(pady=20)
        else:
            # Create scrollable frame for history
            scroll_frame = ctk.CTkScrollableFrame(self, width=600, height=300)
            scroll_frame.pack(pady=10, padx=20, fill="both", expand=True)

            # Calculate statistics
            total_quizzes = len(history)
            total_score = sum(row[2] for row in history)
            total_possible = sum(row[3] for row in history)
            avg_percentage = (total_score / total_possible * 100) if total_possible > 0 else 0

            # Stats header
            stats_frame = ctk.CTkFrame(scroll_frame)
            stats_frame.pack(fill="x", pady=10, padx=10)

            ctk.CTkLabel(stats_frame, text="Statistics",
                         font=("Segoe UI", 16, "bold")).pack(pady=5)
            ctk.CTkLabel(stats_frame,
                         text=f"Total Quizzes: {total_quizzes} | Average Score: {avg_percentage:.1f}%",
                         font=("Segoe UI", 12)).pack(pady=5)

            # Individual quiz results
            for i, record in enumerate(history, 1):
                quiz_id, username, score, total, date = record
                percentage = (score / total * 100) if total > 0 else 0

                quiz_frame = ctk.CTkFrame(scroll_frame)
                quiz_frame.pack(fill="x", pady=5, padx=10)

                # Quiz info
                info_text = f"Quiz #{i} - Score: {score}/{total} ({percentage:.1f}%)"
                ctk.CTkLabel(quiz_frame, text=info_text,
                             font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=10, pady=(5, 0))

                # Date
                ctk.CTkLabel(quiz_frame, text=f"Date: {date}",
                             font=("Segoe UI", 10),
                             text_color="#666").pack(anchor="w", padx=10, pady=(0, 5))

        # Back button
        ctk.CTkButton(self, text="Back to Home", command=self.app.show_home,
                      width=150).pack(side="bottom", pady=20)


# ---------- Main Application ----------
class QuizWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Digital Quiz Application")
        self.geometry("800x600")
        self.resizable(True, True)
        self.current_user = None

        # Initialize databases
        init_user_db()
        init_quiz_db()

        # Create gradient background
        self.gradient = GradientFrame(self, color1="#2c3e50", color2="#3498db")
        self.gradient.pack(fill="both", expand=True)

        # Main container
        self.container = ctk.CTkFrame(self.gradient, fg_color="#f8f9fa", corner_radius=15)
        self.container.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.85, relheight=0.9)

        self.show_login()

    def clear(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    # ---------- Authentication Screens ----------
    def show_login(self):
        self.clear()

        # Title
        title = ctk.CTkLabel(self.container, text="Digital Quiz App - Login",
                             font=("Segoe UI", 24, "bold"))
        title.pack(pady=30)

        # Login form
        form_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        form_frame.pack(pady=20)

        username_entry = ctk.CTkEntry(form_frame, placeholder_text="Username",
                                      width=300, height=40, font=("Segoe UI", 14))
        username_entry.pack(pady=10)

        password_entry = ctk.CTkEntry(form_frame, placeholder_text="Password",
                                      show="*", width=300, height=40, font=("Segoe UI", 14))
        password_entry.pack(pady=10)

        # Show password checkbox
        show_var = ctk.BooleanVar()
        show_check = ctk.CTkCheckBox(form_frame, text="Show Password", variable=show_var,
                                     command=lambda: password_entry.configure(show="" if show_var.get() else "*"))
        show_check.pack(pady=5)

        # Login function
        def attempt_login():
            username = username_entry.get().strip()
            password = password_entry.get()

            if not username or not password:
                messagebox.showwarning("Missing Information", "Please enter both username and password.")
                return

            if authenticate_user(username, password):
                self.current_user = username
                self.show_home()
            else:
                messagebox.showerror("Login Failed", "Invalid username or password.")

        # Bind Enter key to login
        password_entry.bind("<Return>", lambda e: attempt_login())

        # Buttons
        button_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        button_frame.pack(pady=20)

        login_btn = ctk.CTkButton(button_frame, text="Login", command=attempt_login,
                                  width=140, height=40, font=("Segoe UI", 12, "bold"))
        login_btn.grid(row=0, column=0, padx=10)

        register_btn = ctk.CTkButton(button_frame, text="Register", command=self.show_register,
                                     fg_color="#28a745", hover_color="#218838",
                                     width=140, height=40, font=("Segoe UI", 12, "bold"))
        register_btn.grid(row=0, column=1, padx=10)

        # Guest login
        guest_btn = ctk.CTkButton(self.container, text="Continue as Guest",
                                  command=lambda: [setattr(self, 'current_user', 'Guest'), self.show_home()],
                                  fg_color="#6c757d", hover_color="#545b62",
                                  width=200, height=35)
        guest_btn.pack(side="bottom", pady=20)

    def show_register(self):
        self.clear()

        title = ctk.CTkLabel(self.container, text="Create New Account",
                             font=("Segoe UI", 24, "bold"))
        title.pack(pady=30)

        # Registration form
        form_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        form_frame.pack(pady=20)

        username_entry = ctk.CTkEntry(form_frame, placeholder_text="Choose a username",
                                      width=300, height=40, font=("Segoe UI", 14))
        username_entry.pack(pady=8)

        password_entry = ctk.CTkEntry(form_frame, placeholder_text="Password (min 6 chars)",
                                      show="*", width=300, height=40, font=("Segoe UI", 14))
        password_entry.pack(pady=8)

        confirm_entry = ctk.CTkEntry(form_frame, placeholder_text="Confirm password",
                                     show="*", width=300, height=40, font=("Segoe UI", 14))
        confirm_entry.pack(pady=8)

        # Password requirements
        req_label = ctk.CTkLabel(form_frame,
                                 text="Password must contain at least 6 characters with letters and numbers",
                                 font=("Segoe UI", 10), text_color="#666")
        req_label.pack(pady=5)

        # Registration function
        def attempt_register():
            username = username_entry.get().strip()
            password = password_entry.get()
            confirm = confirm_entry.get()

            if password != confirm:
                messagebox.showerror("Password Mismatch", "Passwords do not match.")
                return

            success, message = register_user(username, password)
            if success:
                messagebox.showinfo("Registration Successful", message + " Please login with your new account.")
                self.show_login()
            else:
                messagebox.showerror("Registration Failed", message)

        # Bind Enter key
        confirm_entry.bind("<Return>", lambda e: attempt_register())

        # Buttons
        button_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        button_frame.pack(pady=20)

        create_btn = ctk.CTkButton(button_frame, text="Create Account", command=attempt_register,
                                   fg_color="#28a745", hover_color="#218838",
                                   width=150, height=40, font=("Segoe UI", 12, "bold"))
        create_btn.grid(row=0, column=0, padx=10)

        back_btn = ctk.CTkButton(button_frame, text="Back to Login", command=self.show_login,
                                 fg_color="#6c757d", hover_color="#545b62",
                                 width=150, height=40, font=("Segoe UI", 12, "bold"))
        back_btn.grid(row=0, column=1, padx=10)

    # ---------- Main Application Screens ----------
    def show_home(self):
        self.clear()

        # Welcome header
        welcome_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        welcome_frame.pack(pady=20)

        ctk.CTkLabel(welcome_frame, text=f"Welcome, {self.current_user}!",
                     font=("Segoe UI", 22, "bold")).pack()

        ctk.CTkLabel(welcome_frame, text="Choose an option below to get started",
                     font=("Segoe UI", 12), text_color="#666").pack(pady=5)

        # Main options
        options_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        options_frame.pack(pady=30)

        # Author Quiz
        author_btn = ctk.CTkButton(options_frame, text="Create Questions",
                                   command=self.show_author,
                                   width=200, height=50, font=("Segoe UI", 14, "bold"),
                                   fg_color="#17a2b8", hover_color="#138496")
        author_btn.grid(row=0, column=0, padx=15, pady=10)

        # Start Quiz
        quiz_btn = ctk.CTkButton(options_frame, text="Take Quiz",
                                 command=self.show_quiz,
                                 width=200, height=50, font=("Segoe UI", 14, "bold"),
                                 fg_color="#28a745", hover_color="#218838")
        quiz_btn.grid(row=0, column=1, padx=15, pady=10)

        # Load Quiz File
        load_btn = ctk.CTkButton(options_frame, text="Import Quiz File",
                                 command=self.load_quiz_file,
                                 width=200, height=50, font=("Segoe UI", 14, "bold"),
                                 fg_color="#ffc107", hover_color="#e0a800", text_color="#000")
        load_btn.grid(row=1, column=0, padx=15, pady=10)

        # History
        history_btn = ctk.CTkButton(options_frame, text="View History",
                                    command=self.show_history,
                                    width=200, height=50, font=("Segoe UI", 14, "bold"),
                                    fg_color="#6f42c1", hover_color="#5a2d91")
        history_btn.grid(row=1, column=1, padx=15, pady=10)

        # Quiz duration setting
        settings_frame = ctk.CTkFrame(self.container)
        settings_frame.pack(pady=20)

        ctk.CTkLabel(settings_frame, text="Quiz Settings",
                     font=("Segoe UI", 16, "bold")).pack(pady=10)

        duration_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        duration_frame.pack(pady=10)

        ctk.CTkLabel(duration_frame, text="Quiz Duration:").grid(row=0, column=0, padx=10)

        self.duration_var = ctk.StringVar(value="180")
        duration_menu = ctk.CTkOptionMenu(duration_frame, variable=self.duration_var,
                                          values=["60 seconds", "120 seconds", "180 seconds", "300 seconds",
                                                  "600 seconds"],
                                          width=150)
        duration_menu.grid(row=0, column=1, padx=10)

        # Logout/Exit buttons
        bottom_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        bottom_frame.pack(side="bottom", pady=20)

        if self.current_user != "Guest":
            logout_btn = ctk.CTkButton(bottom_frame, text="Logout",
                                       command=self.show_login,
                                       fg_color="#dc3545", hover_color="#c82333",
                                       width=120, height=35)
            logout_btn.grid(row=0, column=0, padx=10)

        exit_btn = ctk.CTkButton(bottom_frame, text="Exit Application",
                                 command=self.destroy,
                                 fg_color="#343a40", hover_color="#23272b",
                                 width=140, height=35)
        exit_btn.grid(row=0, column=1, padx=10)

    def load_quiz_file(self):
        filepath = filedialog.askopenfilename(
            title="Select Quiz File",
            filetypes=[
                ("CSV Files", "*.csv"),
                ("JSON Files", "*.json"),
                ("All Files", "*.*")
            ]
        )
        if not filepath:
            return

        try:
            questions_added = 0

            if filepath.endswith(".json"):
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        insert_question(item["question"], item.get("options", []),
                                        item["answer"], item["type"])
                        questions_added += 1

            elif filepath.endswith(".csv"):
                with open(filepath, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        options = row.get("options", "").split("|") if row.get("options") else []
                        insert_question(row["question"], options, row["answer"], row["type"])
                        questions_added += 1

            messagebox.showinfo("Import Successful",
                                f"Successfully imported {questions_added} questions from the file!")

        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to load quiz file:\n{str(e)}")

    def show_author(self):
        self.clear()
        AuthorScreen(self.container, self)

    def show_quiz(self, username=None, duration=None):
        self.clear()
        if username is None:
            username = self.current_user
        if duration is None:
            duration_str = self.duration_var.get() if hasattr(self, 'duration_var') else "180 seconds"
            duration = int(duration_str.split()[0])
        QuizScreen(self.container, self, username, duration)

    def show_history(self):
        self.clear()
        HistoryScreen(self.container, self, self.current_user)


# ---------- Run Application ----------
if __name__ == "__main__":
    try:
        app = QuizWindow()
        app.mainloop()
    except Exception as e:
        print(f"Application error: {e}")
        messagebox.showerror("Application Error", f"An error occurred: {e}")
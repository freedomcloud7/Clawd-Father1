"""
OpenClaw Dashboard — native Mac GUI
Tkinter-based dashboard window with live revenue, agent log, and controls.
"""
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import queue
from datetime import datetime


LOG_QUEUE = queue.Queue()


def log(message: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    LOG_QUEUE.put(f"[{timestamp}] {message}")


class Dashboard(tk.Tk):
    def __init__(self, on_run_task=None, on_stop=None):
        super().__init__()

        self.on_run_task = on_run_task
        self.on_stop = on_stop
        self.running = False

        self.title("OpenClaw Colony")
        self.geometry("900x650")
        self.configure(bg="#0d0d0d")
        self.resizable(True, True)

        self._build_ui()
        self._poll_log()
        self._poll_revenue()

    def _build_ui(self):
        # ── Header ────────────────────────────────────────────────────────────
        header = tk.Frame(self, bg="#0d0d0d", pady=16)
        header.pack(fill="x", padx=20)

        tk.Label(
            header, text="⚡ OpenClaw Colony",
            font=("SF Pro Display", 28, "bold"),
            fg="#ffffff", bg="#0d0d0d"
        ).pack(side="left")

        self.status_dot = tk.Label(
            header, text="● OFFLINE",
            font=("SF Pro Text", 12), fg="#666666", bg="#0d0d0d"
        )
        self.status_dot.pack(side="right", pady=8)

        # ── Revenue Cards ─────────────────────────────────────────────────────
        cards = tk.Frame(self, bg="#0d0d0d")
        cards.pack(fill="x", padx=20, pady=(0, 16))

        self.monthly_var = tk.StringVar(value="$0.00")
        self.weekly_var = tk.StringVar(value="$0.00")
        self.goal_var = tk.StringVar(value="0%")

        for label, var, color in [
            ("Monthly Revenue", self.monthly_var, "#00ff88"),
            ("This Week", self.weekly_var, "#00ccff"),
            ("Goal Progress", self.goal_var, "#ff9900"),
        ]:
            card = tk.Frame(cards, bg="#1a1a1a", padx=20, pady=14)
            card.pack(side="left", fill="x", expand=True, padx=(0, 10))
            tk.Label(card, text=label, font=("SF Pro Text", 11),
                     fg="#888888", bg="#1a1a1a").pack(anchor="w")
            tk.Label(card, textvariable=var, font=("SF Pro Display", 22, "bold"),
                     fg=color, bg="#1a1a1a").pack(anchor="w")

        # ── Progress Bar ──────────────────────────────────────────────────────
        prog_frame = tk.Frame(self, bg="#0d0d0d", padx=20)
        prog_frame.pack(fill="x", pady=(0, 16))

        tk.Label(prog_frame, text="$5,000/month target",
                 font=("SF Pro Text", 10), fg="#666666", bg="#0d0d0d").pack(anchor="w")

        self.progress = ttk.Progressbar(prog_frame, length=860, mode="determinate",
                                         maximum=5000)
        self.progress.pack(fill="x", pady=4)

        # ── Task Input ────────────────────────────────────────────────────────
        input_frame = tk.Frame(self, bg="#0d0d0d", padx=20)
        input_frame.pack(fill="x", pady=(0, 12))

        self.task_entry = tk.Entry(
            input_frame,
            font=("SF Pro Text", 13),
            bg="#1a1a1a", fg="#ffffff",
            insertbackground="#ffffff",
            relief="flat", bd=8
        )
        self.task_entry.pack(side="left", fill="x", expand=True, ipady=8)
        self.task_entry.insert(0, "Give the colony a goal or task...")
        self.task_entry.bind("<FocusIn>", self._clear_placeholder)
        self.task_entry.bind("<Return>", self._run_task)

        self.run_btn = tk.Button(
            input_frame, text="▶ RUN",
            font=("SF Pro Text", 12, "bold"),
            bg="#00ff88", fg="#000000",
            relief="flat", padx=20, pady=8,
            cursor="hand2",
            command=self._run_task
        )
        self.run_btn.pack(side="left", padx=(8, 0))

        self.stop_btn = tk.Button(
            input_frame, text="■ STOP",
            font=("SF Pro Text", 12, "bold"),
            bg="#ff4444", fg="#ffffff",
            relief="flat", padx=20, pady=8,
            cursor="hand2",
            command=self._stop
        )
        self.stop_btn.pack(side="left", padx=(8, 0))

        # ── Activity Log ──────────────────────────────────────────────────────
        log_frame = tk.Frame(self, bg="#0d0d0d", padx=20)
        log_frame.pack(fill="both", expand=True, pady=(0, 16))

        tk.Label(log_frame, text="AGENT ACTIVITY",
                 font=("SF Pro Text", 10, "bold"),
                 fg="#666666", bg="#0d0d0d").pack(anchor="w", pady=(0, 4))

        self.log_box = scrolledtext.ScrolledText(
            log_frame,
            font=("SF Mono", 11),
            bg="#111111", fg="#00ff88",
            insertbackground="#00ff88",
            relief="flat", bd=0,
            state="disabled"
        )
        self.log_box.pack(fill="both", expand=True)

    def _clear_placeholder(self, event):
        if self.task_entry.get() == "Give the colony a goal or task...":
            self.task_entry.delete(0, "end")

    def _run_task(self, event=None):
        task = self.task_entry.get().strip()
        if not task or task == "Give the colony a goal or task...":
            return
        if self.running:
            return

        self.running = True
        self.status_dot.config(text="● RUNNING", fg="#00ff88")
        self.run_btn.config(state="disabled")
        log(f"Starting task: {task}")

        if self.on_run_task:
            thread = threading.Thread(
                target=self._task_thread, args=(task,), daemon=True
            )
            thread.start()

    def _task_thread(self, task: str):
        try:
            if self.on_run_task:
                result = self.on_run_task(task)
                log(f"Task complete.")
        except Exception as e:
            log(f"Error: {e}")
        finally:
            self.running = False
            self.after(0, lambda: self.status_dot.config(text="● IDLE", fg="#ffaa00"))
            self.after(0, lambda: self.run_btn.config(state="normal"))

    def _stop(self):
        if self.on_stop:
            self.on_stop()
        self.running = False
        self.status_dot.config(text="● STOPPED", fg="#ff4444")
        self.run_btn.config(state="normal")
        log("Colony stopped by user.")

    def _poll_log(self):
        while not LOG_QUEUE.empty():
            msg = LOG_QUEUE.get()
            self.log_box.config(state="normal")
            self.log_box.insert("end", msg + "\n")
            self.log_box.see("end")
            self.log_box.config(state="disabled")
        self.after(300, self._poll_log)

    def _poll_revenue(self):
        try:
            from colony.tracker import get_monthly_revenue, get_weekly_revenue
            monthly = get_monthly_revenue()
            weekly = get_weekly_revenue()
            self.monthly_var.set(f"${monthly:,.2f}")
            self.weekly_var.set(f"${weekly:,.2f}")
            pct = min(monthly / 5000 * 100, 100)
            self.goal_var.set(f"{pct:.1f}%")
            self.progress["value"] = monthly
        except Exception:
            pass
        self.after(10000, self._poll_revenue)

    def append_log(self, text: str):
        log(text)

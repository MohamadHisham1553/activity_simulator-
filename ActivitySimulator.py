"""
activity_simulator.py — Anti-Away Activity Simulator
Keeps your status active in messaging/team apps by simulating subtle mouse or keyboard activity.

Dependencies:
    pip install pyautogui pynput pillow

To build as a standalone .exe:
    pip install pyinstaller
    pyinstaller --onefile --windowed --name ActivitySimulator activity_simulator.py

    Optional: add a custom icon
    pyinstaller --onefile --windowed --icon=icon.ico --name ActivitySimulator activity_simulator.py
"""

import tkinter as tk
from tkinter import messagebox
import threading
import time
import math

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

try:
    from pynput.keyboard import Controller as KeyboardController
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False

try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False


# ──────────────────────────────────────────────────────────────────────────────
# Core simulation logic
# ──────────────────────────────────────────────────────────────────────────────

class ActivitySimulator:
    """Runs periodic mouse / keyboard activity in a background thread."""

    def __init__(self):
        self._stop_event = threading.Event()
        self._thread = None
        self.on_tick = None
        self.on_error = None

    def start(self, mode: str, interval: float, key: str):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            args=(mode, interval, key),
            daemon=True,
        )
        self._thread.start()

    def stop(self):
        self._stop_event.set()

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _run(self, mode: str, interval: float, key: str):
        keyboard = KeyboardController() if PYNPUT_AVAILABLE else None
        while not self._stop_event.wait(timeout=interval):
            try:
                if mode == "mouse":
                    self._nudge_mouse()
                else:
                    self._press_key(keyboard, key)
                if self.on_tick:
                    self.on_tick()
            except Exception as exc:
                if self.on_error:
                    self.on_error(str(exc))
                break

    @staticmethod
    def _nudge_mouse():
        if not PYAUTOGUI_AVAILABLE:
            return
        pyautogui.moveRel(3, 0, duration=0.1)
        pyautogui.moveRel(-3, 0, duration=0.1)

    @staticmethod
    def _press_key(keyboard, key: str):
        if keyboard is None:
            return
        keyboard.press(key)
        time.sleep(0.05)
        keyboard.release(key)


# ──────────────────────────────────────────────────────────────────────────────
# Vibrant Color Theme
# ──────────────────────────────────────────────────────────────────────────────

BG          = "#0d0d1a"
CARD_BG     = "#12122a"
BORDER      = "#2a2a50"
CYAN        = "#00f5ff"
MAGENTA     = "#ff2d9b"
YELLOW      = "#ffe600"
GREEN       = "#00ff88"
RED         = "#ff4444"
WHITE       = "#ffffff"
DIM         = "#5a5a8a"
FONT_TITLE  = ("Courier New", 20, "bold")
FONT_HEAD   = ("Courier New", 9, "bold")
FONT_BODY   = ("Courier New", 10)
FONT_BIG    = ("Courier New", 14, "bold")
FONT_SMALL  = ("Courier New", 8)


# ──────────────────────────────────────────────────────────────────────────────
# Canvas Pulse Ring Animation
# ──────────────────────────────────────────────────────────────────────────────

class PulseRing(tk.Canvas):
    """Animated pulsing ring that plays when simulator is running."""

    RADIUS = 28
    RINGS  = 3

    def __init__(self, parent, **kwargs):
        size = (self.RADIUS + 22) * 2
        super().__init__(parent, width=size, height=size,
                         bg=BG, highlightthickness=0, **kwargs)
        self._cx = self._cy = size // 2
        self._active = False
        self._phase = 0.0
        self._color = CYAN
        self._draw_idle()

    def set_active(self, active: bool, color: str = CYAN):
        self._active = active
        self._color  = color
        if active:
            self._animate()
        else:
            self._draw_idle()

    def _draw_idle(self):
        self.delete("all")
        r = self.RADIUS
        self.create_oval(
            self._cx - r, self._cy - r,
            self._cx + r, self._cy + r,
            outline=DIM, width=2
        )
        self.create_text(self._cx, self._cy, text="●",
                         font=("Courier New", 18), fill=DIM)

    def _animate(self):
        if not self._active:
            return
        self.delete("all")
        self._phase = (self._phase + 0.07) % (2 * math.pi)

        # Outer expanding rings
        for i in range(self.RINGS):
            offset = (self._phase + i * (2 * math.pi / self.RINGS)) % (2 * math.pi)
            t = offset / (2 * math.pi)
            r = self.RADIUS + t * 22
            alpha_val = max(0, int(220 * (1 - t)))
            hex_a = f"{alpha_val:02x}"
            # tkinter doesn't support alpha on canvas items, simulate with stipple width
            width = max(1, int(2.5 * (1 - t)))
            self.create_oval(
                self._cx - r, self._cy - r,
                self._cx + r, self._cy + r,
                outline=self._color, width=width
            )

        # Core dot
        r = self.RADIUS
        pulse = 1 + 0.08 * math.sin(self._phase * 3)
        rp = r * pulse
        self.create_oval(
            self._cx - rp, self._cy - rp,
            self._cx + rp, self._cy + rp,
            fill=self._color, outline=""
        )
        self.create_text(self._cx, self._cy, text="✦",
                         font=("Courier New", 14, "bold"), fill=BG)

        self.after(40, self._animate)


# ──────────────────────────────────────────────────────────────────────────────
# Main Application
# ──────────────────────────────────────────────────────────────────────────────

class ActivitySimulatorApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.simulator = ActivitySimulator()
        self.simulator.on_tick  = self._on_tick
        self.simulator.on_error = self._on_sim_error

        self._tick_count = 0
        self._tray_icon  = None

        self._build_window()
        self._build_ui()
        self._check_deps()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── window ────────────────────────────────────────────────────────────────

    def _build_window(self):
        self.title("Activity Simulator")
        self.resizable(False, False)
        self.configure(bg=BG)
        w, h = 440, 560
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── gradient-look header strip ──
        header = tk.Frame(self, bg="#0a0a1f", height=6)
        header.pack(fill="x")
        for i, col in enumerate([CYAN, MAGENTA, YELLOW, GREEN, MAGENTA, CYAN]):
            tk.Frame(header, bg=col, width=74, height=6).place(x=i*74, y=0)

        # ── title ──
        title_frame = tk.Frame(self, bg=BG)
        title_frame.pack(pady=(18, 0))
        tk.Label(title_frame, text="⚡ ACTIVITY SIMULATOR",
                 font=FONT_TITLE, bg=BG, fg=CYAN).pack()
        tk.Label(title_frame, text="keep your status alive · no interruptions · fully automatic",
                 font=FONT_SMALL, bg=BG, fg=DIM).pack(pady=(2, 0))

        # ── pulse ring + status card ──
        status_outer = tk.Frame(self, bg=BORDER, bd=0)
        status_outer.pack(fill="x", padx=18, pady=(14, 6))
        status_card = tk.Frame(status_outer, bg=CARD_BG, bd=0)
        status_card.pack(fill="x", padx=1, pady=1)

        left = tk.Frame(status_card, bg=CARD_BG)
        left.pack(side="left", padx=14, pady=12)

        self._pulse = PulseRing(left)
        self._pulse.pack()

        right = tk.Frame(status_card, bg=CARD_BG)
        right.pack(side="left", pady=12)

        self._status_label = tk.Label(right, text="INACTIVE",
                                      font=("Courier New", 16, "bold"),
                                      bg=CARD_BG, fg=RED)
        self._status_label.pack(anchor="w")

        self._status_sub = tk.Label(right, text="Press START to begin simulation",
                                    font=FONT_SMALL, bg=CARD_BG, fg=DIM)
        self._status_sub.pack(anchor="w")

        self._tick_label = tk.Label(status_card, text="",
                                    font=("Courier New", 22, "bold"),
                                    bg=CARD_BG, fg=YELLOW)
        self._tick_label.pack(side="right", padx=18)

        # ── mode selection ──
        self._section("▸  MODE", MAGENTA)
        mode_card = self._card()
        self._mode = tk.StringVar(value="mouse")

        for val, icon, lbl in [("mouse", "🖱", "Mouse Nudge"), ("keyboard", "⌨", "Key Press")]:
            rb_frame = tk.Frame(mode_card, bg=CARD_BG, cursor="hand2")
            rb_frame.pack(side="left", expand=True)
            rb = tk.Radiobutton(
                rb_frame, text=f" {icon}  {lbl}",
                variable=self._mode, value=val,
                command=self._on_mode_change,
                font=FONT_BODY, bg=CARD_BG, fg=WHITE,
                selectcolor="#1e1e3e",
                activebackground=CARD_BG, activeforeground=CYAN,
                indicatoron=True,
            )
            rb.pack(padx=10, pady=10)

        # ── key input ──
        self._section("▸  KEY  (keyboard mode only)", YELLOW)
        key_card = self._card()
        tk.Label(key_card, text="LETTER:", font=FONT_HEAD,
                 bg=CARD_BG, fg=DIM).pack(side="left", padx=(14, 8), pady=12)

        vcmd = (self.register(lambda v: len(v) <= 1), "%P")
        self._key_var = tk.StringVar(value="a")
        self._key_entry = tk.Entry(
            key_card, textvariable=self._key_var,
            width=3, font=("Courier New", 16, "bold"),
            bg="#1e1e3e", fg=CYAN, insertbackground=CYAN,
            bd=0, relief="flat", justify="center",
            validate="key", validatecommand=vcmd,
        )
        self._key_entry.pack(side="left", ipady=6, ipadx=6)
        tk.Label(key_card, text="single character",
                 font=FONT_SMALL, bg=CARD_BG, fg=DIM).pack(side="left", padx=10)

        # ── interval ──
        self._section("▸  INTERVAL  (seconds between actions)", GREEN)
        int_card = self._card()
        tk.Label(int_card, text="EVERY:", font=FONT_HEAD,
                 bg=CARD_BG, fg=DIM).pack(side="left", padx=(14, 8), pady=12)

        self._interval_var = tk.StringVar(value="30")
        self._interval_entry = tk.Entry(
            int_card, textvariable=self._interval_var,
            width=5, font=("Courier New", 16, "bold"),
            bg="#1e1e3e", fg=GREEN, insertbackground=GREEN,
            bd=0, relief="flat", justify="center",
        )
        self._interval_entry.pack(side="left", ipady=6, ipadx=6)
        tk.Label(int_card, text="seconds",
                 font=FONT_BODY, bg=CARD_BG, fg=DIM).pack(side="left", padx=10)

        # ── tray option ──
        self._tray_var = tk.BooleanVar(value=False)
        tray_row = tk.Frame(self, bg=BG)
        tray_row.pack(fill="x", padx=20, pady=(4, 0))
        tk.Checkbutton(
            tray_row, text="Minimise to system tray on close",
            variable=self._tray_var, font=FONT_SMALL,
            bg=BG, fg=DIM, selectcolor="#1a1a3a",
            activebackground=BG, activeforeground=WHITE,
        ).pack(anchor="w")

        # ── buttons ──
        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.pack(pady=12, padx=18, fill="x")

        self._start_btn = self._glow_button(btn_frame, "▶  START", CYAN,   self._start)
        self._stop_btn  = self._glow_button(btn_frame, "■  STOP",  MAGENTA, self._stop)
        self._start_btn.pack(side="left", expand=True, fill="x", padx=(0, 6))
        self._stop_btn.pack (side="left", expand=True, fill="x", padx=(6, 0))
        self._stop_btn.config(state="disabled")

        # ── log ──
        self._section("▸  LOG", DIM)
        log_outer = tk.Frame(self, bg=BORDER)
        log_outer.pack(fill="both", expand=True, padx=18, pady=(2, 18))
        log_card = tk.Frame(log_outer, bg=CARD_BG)
        log_card.pack(fill="both", expand=True, padx=1, pady=1)
        self._log = tk.Text(
            log_card, height=5, bg=CARD_BG, fg="#6effe0",
            font=FONT_SMALL, bd=0, relief="flat",
            state="disabled", wrap="word",
            selectbackground=BORDER,
        )
        self._log.pack(fill="both", expand=True, padx=10, pady=8)

        # bottom accent bar
        foot = tk.Frame(self, bg=BG, height=4)
        foot.pack(fill="x")
        for i, col in enumerate([GREEN, CYAN, MAGENTA, YELLOW, CYAN, GREEN]):
            tk.Frame(foot, bg=col, width=74, height=4).place(x=i*74, y=0)

        self._on_mode_change()

    # ── helpers ───────────────────────────────────────────────────────────────

    def _section(self, label: str, color: str = DIM):
        f = tk.Frame(self, bg=BG)
        f.pack(fill="x", padx=18, pady=(10, 2))
        tk.Label(f, text=label, font=FONT_HEAD,
                 bg=BG, fg=color).pack(side="left")
        tk.Frame(f, bg=color, height=1).pack(side="left", fill="x",
                                              expand=True, padx=(8, 0))

    def _card(self):
        outer = tk.Frame(self, bg=BORDER)
        outer.pack(fill="x", padx=18, pady=1)
        inner = tk.Frame(outer, bg=CARD_BG)
        inner.pack(fill="x", padx=1, pady=1)
        return inner

    def _glow_button(self, parent, text, color, cmd):
        return tk.Button(
            parent, text=text, command=cmd,
            font=("Courier New", 11, "bold"),
            bg=color, fg=BG,
            activebackground=WHITE, activeforeground=BG,
            bd=0, relief="flat", cursor="hand2",
            pady=11,
        )

    def _log_msg(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        self._log.config(state="normal")
        self._log.insert("end", f"[{ts}]  {msg}\n")
        self._log.see("end")
        self._log.config(state="disabled")

    def _set_status(self, active: bool):
        if active:
            self._status_label.config(text="ACTIVE", fg=GREEN)
            self._status_sub.config(text="Simulation running…")
            self._pulse.set_active(True, GREEN)
        else:
            self._status_label.config(text="INACTIVE", fg=RED)
            self._status_sub.config(text="Press START to begin simulation")
            self._tick_label.config(text="")
            self._pulse.set_active(False)

    # ── event handlers ────────────────────────────────────────────────────────

    def _on_mode_change(self):
        state = "normal" if self._mode.get() == "keyboard" else "disabled"
        self._key_entry.config(state=state)

    def _start(self):
        try:
            interval = float(self._interval_var.get())
            if interval < 1:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Interval",
                                 "Interval must be a number ≥ 1 second.")
            return

        mode = self._mode.get()
        key  = self._key_var.get() or "a"

        if mode == "keyboard" and not PYNPUT_AVAILABLE:
            messagebox.showerror("Missing Dependency",
                                 "pynput is required for keyboard mode.\n"
                                 "Run:  pip install pynput")
            return

        if mode == "mouse" and not PYAUTOGUI_AVAILABLE:
            messagebox.showerror("Missing Dependency",
                                 "pyautogui is required for mouse mode.\n"
                                 "Run:  pip install pyautogui")
            return

        self._tick_count = 0
        self.simulator.start(mode, interval, key)
        self._set_status(True)
        self._start_btn.config(state="disabled")
        self._stop_btn.config(state="normal")
        self._log_msg(f"Started  |  mode={mode}  interval={interval}s"
                      + (f"  key={key!r}" if mode == "keyboard" else ""))

    def _stop(self):
        self.simulator.stop()
        self._set_status(False)
        self._start_btn.config(state="normal")
        self._stop_btn.config(state="disabled")
        self._log_msg(f"Stopped  |  {self._tick_count} action(s) performed")

    def _on_tick(self):
        self._tick_count += 1
        self.after(0, lambda: self._tick_label.config(text=f"×{self._tick_count}"))

    def _on_sim_error(self, msg: str):
        self.after(0, lambda: (self._stop(), self._log_msg(f"ERROR: {msg}")))

    def _on_close(self):
        if self._tray_var.get() and TRAY_AVAILABLE:
            self._minimise_to_tray()
        else:
            self._quit()

    def _quit(self):
        self.simulator.stop()
        if self._tray_icon:
            self._tray_icon.stop()
        self.destroy()

    # ── system tray ───────────────────────────────────────────────────────────

    def _minimise_to_tray(self):
        self.withdraw()
        if self._tray_icon:
            return
        img = Image.new("RGB", (64, 64), color=(13, 13, 26))
        draw = ImageDraw.Draw(img)
        draw.ellipse([8, 8, 56, 56], fill=(0, 245, 255))
        menu = pystray.Menu(
            pystray.MenuItem("Show", self._restore_from_tray, default=True),
            pystray.MenuItem("Quit", lambda icon, item: self._quit()),
        )
        self._tray_icon = pystray.Icon("ActivitySimulator", img,
                                        "Activity Simulator", menu)
        threading.Thread(target=self._tray_icon.run, daemon=True).start()

    def _restore_from_tray(self, icon=None, item=None):
        self.after(0, self.deiconify)

    # ── dependency check ──────────────────────────────────────────────────────

    def _check_deps(self):
        missing = []
        if not PYAUTOGUI_AVAILABLE:
            missing.append("pyautogui  (mouse mode)")
        if not PYNPUT_AVAILABLE:
            missing.append("pynput  (keyboard mode)")
        if missing:
            self._log_msg("Missing deps — some modes disabled:")
            for m in missing:
                self._log_msg(f"  pip install {m.split()[0]}")
        else:
            self._log_msg("All dependencies OK. Ready to simulate.")


# ──────────────────────────────────────────────────────────────────────────────

def main():
    app = ActivitySimulatorApp()
    app.mainloop()


if __name__ == "__main__":
    main()

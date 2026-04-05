# activity_simulator-
⚡ Activity Simulator  A lightweight desktop utility that keeps your status active in messaging and team apps (Slack, Teams, etc.) by simulating subtle mouse nudges or key presses at a configurable interval so you never go idle.

Built with Python + Tkinter. No background services, no installs, just run it.

---

**Features**
- 🖱 Mouse nudge mode — micro-moves the cursor and returns it
- ⌨️ Keyboard mode — presses a configurable key quietly in the background
- ⏱ Adjustable interval (seconds between actions)
- 🔴🟢 Live status indicator with animated pulse ring and action counter
- 🗂 Optional system tray minimization
- Graceful handling of missing optional dependencies

**Requirements**
```
pip install pyautogui pynput
```
Optional (system tray support):
```
pip install pystray pillow
```

**Run**
```
python activity_simulator.py
```

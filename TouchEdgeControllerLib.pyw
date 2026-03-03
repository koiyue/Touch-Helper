# -*- coding: utf-8 -*-
import sys, os, time, ctypes, subprocess
from ctypes import wintypes

# Win32 API
import win32api, win32con, win32gui

# PyQt6
from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu,
    QInputDialog, QMessageBox, QWidget, QLabel
)
from PyQt6.QtGui import QIcon, QAction, QColor, QPainter
from PyQt6.QtCore import Qt, QRect, QTimer

user32 = ctypes.windll.user32

EDGE_THRESHOLD = 25
SLIDE_THRESHOLD = 100
BLACKLIST_FILE = "blacklist.txt"
TOUCH_STATE_FILE = "last_touch_state.txt"

blacklist = None
tip_window = None
tip_timer = None
tip_shown = False
last_state = None
cur_state = None


def init_blacklist():
    if not os.path.exists(BLACKLIST_FILE):
        default_apps = [
            "Shell_TrayWnd","Progman","Button","WorkerW",
            "TaskManagerWindow","Windows.UI.Core.CoreWindow"
        ]
        with open(BLACKLIST_FILE,"w",encoding="utf-8") as f:
            for app in default_apps:
                f.write(app+"\n")

def load_blacklist():
    global blacklist
    with open(BLACKLIST_FILE,"r",encoding="utf-8") as f:
        blacklist = [line.strip() for line in f if line.strip()]

def get_last_touch_state():
    if os.path.exists(TOUCH_STATE_FILE):
        with open(TOUCH_STATE_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

def get_window_under_cursor():
    pt = win32api.GetCursorPos()
    hwnd = win32gui.WindowFromPoint(pt)
    hwnd = win32gui.GetAncestor(hwnd, win32con.GA_ROOT)
    return hwnd

def send_command_to_foreground():
    global blacklist
    hwnd = get_window_under_cursor()
    if hwnd:
        title = win32gui.GetWindowText(hwnd)
        clsname = win32gui.GetClassName(hwnd)
        for item in blacklist:
            if item.lower() in title.lower() or item.lower() in clsname.lower():
                return
        user32.PostMessageW(hwnd, win32con.WM_CLOSE, 0, 0)


class EdgeBlocker(QWidget):
    def __init__(self, rect: QRect, edge: str):
        super().__init__()
        self.edge = edge
        self.start_pos = None
        self.slide_count = 0
        self.last_slide_time = 0

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint |
                            Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setGeometry(rect)
        self.setWindowOpacity(0.5)
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_state)
        self.timer.start(200)

    def check_state(self):
        global last_state, cur_state
        cur_state = get_last_touch_state()
        if (cur_state in ["按下", "按下-移动", "按下-驻留"] or not (last_state == cur_state)) and self.windowOpacity() == 0:
            self.restore_bg()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            global last_state
            last_state = get_last_touch_state()
            if last_state not in ["按下", "按下-移动","按下-驻留"]:
                self.setWindowOpacity(0)
                show_tip("触控手势已关闭", 1000)
                return
            self.start_pos = event.pos()

    def restore_bg(self):
        self.setWindowOpacity(0.01)
        show_tip("触控手势已恢复", 1000)

    def mouseReleaseEvent(self, event):
        global blacklist
        hwnd1 = get_window_under_cursor()
        title = win32gui.GetWindowText(hwnd1)
        clsname = win32gui.GetClassName(hwnd1)
        for item in blacklist:
            if item.lower() in title.lower() or item.lower() in clsname.lower():
                return

        if self.start_pos:
            global last_state
            last_state = get_last_touch_state()
            if last_state not in ["松开"]:
                return
            delta_x = event.pos().x() - self.start_pos.x()
            delta_y = event.pos().y() - self.start_pos.y()
            triggered = False

            if self.edge == "left" and delta_x >= SLIDE_THRESHOLD:
                triggered = True
            elif self.edge == "right" and -delta_x >= SLIDE_THRESHOLD:
                triggered = True
            elif self.edge == "bottom" and -delta_y >= SLIDE_THRESHOLD:
                triggered = True
                trigger_win_tab()

            if triggered and self.edge != "bottom":
                now = time.time()
                if now - self.last_slide_time <= 1.5:
                    self.slide_count += 1
                else:
                    self.slide_count = 1
                    show_tip("再次滑动以关闭")
                self.last_slide_time = now

                if self.slide_count == 2:
                    send_command_to_foreground()
                    close_tip()
                    self.slide_count = 0
                    self.last_slide_time = 0

            self.start_pos = None


class TipWindow(QWidget):
    def __init__(self, text, time=1500, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint |
                            Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.label = QLabel(text, self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("color: white; font-size: 30px; padding: 20px;")
        self.label.adjustSize()
        self.resize(self.label.width() + 40, self.label.height() + 40)

        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.center().x() - self.width() // 2,
                  screen.center().y() - self.height() // 2)

        global tip_timer
        tip_timer = QTimer(self)
        tip_timer.setSingleShot(True)
        tip_timer.timeout.connect(close_tip)
        tip_timer.start(time)


def show_tip(text, time=1500):
    global tip_shown, tip_window
    if tip_window:
        close_tip()
    tip_window = TipWindow(text, time)
    tip_window.show()
    tip_shown = True

def trigger_win_tab():
    win32api.keybd_event(win32con.VK_LWIN, 0, 0, 0)
    win32api.keybd_event(win32con.VK_TAB, 0, 0, 0)
    win32api.keybd_event(win32con.VK_TAB, 0, win32con.KEYEVENTF_KEYUP, 0)
    win32api.keybd_event(win32con.VK_LWIN, 0, win32con.KEYEVENTF_KEYUP, 0)
    show_tip("任务视图已打开", 1000)

def close_tip():
    global tip_shown, tip_window, tip_timer
    if tip_window:
        tip_window.close()
        tip_timer.stop()
        tip_window = None
    tip_shown = False

def force_above_taskbar(widget):
    hwnd = int(widget.winId())
    win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST,
                          0, 0, 0, 0,
                          win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE)


class TouchEdgeManager:
    def __init__(self, app: QApplication):
        self.app = app
        self.edge_blockers = []
        init_blacklist()
        load_blacklist()

    def enable(self):
        screen = self.app.primaryScreen()
        geometry = screen.geometry()
        screen_width = geometry.width()
        screen_height = geometry.height()
        edge_width = 1

        left_rect = QRect(0, 0, edge_width, screen_height)
        right_rect = QRect(screen_width - edge_width, 0, edge_width, screen_height)
        bottom_rect = QRect(0, screen_height - edge_width, screen_width, edge_width)

        self.edge_blockers = [
            EdgeBlocker(left_rect, "left"),
            EdgeBlocker(right_rect, "right"),
            EdgeBlocker(bottom_rect, "bottom")
        ]
        for blocker in self.edge_blockers:
            blocker.show()
            force_above_taskbar(blocker)
        show_tip("触控助手已启用", 1000)

    def disable(self):
        for blocker in self.edge_blockers:
            blocker.close()
        self.edge_blockers = [] # 清空引用，避免残留
        show_tip("触控助手已禁用", 1000)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 创建并启用触控助手
    manager = TouchEdgeManager(app)
    manager.enable()

    # 保持事件循环运行
    sys.exit(app.exec())

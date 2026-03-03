# -*- coding: utf-8 -*-
import sys
import time
import ctypes
import win32api
import win32con
import win32gui
from PyQt6.QtWidgets import QApplication


class MouseClickDirectionInterceptor:
    def __init__(self, target_class="DV2ControlHost", interval=0.14):
        """
        target_class: 需要检测的前台窗口类名
        interval: 快速点击判定的最大时间间隔（秒）
        """
        self.target_class = target_class
        self.interval = interval
        self.last_click_time = 0
        self.last_direction = None
        self.hook_id = None
        self.pointer = None

    def _mouse_proc(self, nCode, wParam, lParam):
        if nCode == win32con.HC_ACTION:
            if wParam == win32con.WM_LBUTTONDOWN:
                hwnd = win32gui.GetForegroundWindow()
                class_name = win32gui.GetClassName(hwnd)
                pt = win32api.GetCursorPos()
                screen_width = win32api.GetSystemMetrics(0)

                if class_name == self.target_class:
                    now = time.time()
                    direction = "left" if pt[0] < screen_width / 2 else "right"

                    if now - self.last_click_time < self.interval:
                        if self.last_direction == direction:
                            print(f"快速连续点击方向一致 → 触发 Ctrl+{direction.capitalize()}")
                            self._send_ctrl_arrow(direction)

                    self.last_click_time = now
                    self.last_direction = direction
        return ctypes.windll.user32.CallNextHookEx(self.hook_id, nCode, wParam, lParam)

    def _send_ctrl_arrow(self, direction):
        vk = win32con.VK_LEFT if direction == "left" else win32con.VK_RIGHT
        win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
        win32api.keybd_event(vk, 0, 0, 0)
        win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)

    def _install_hook(self):
        if self.hook_id:
            return
        WH_MOUSE_LL = 14
        CMPFUNC = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_void_p)
        self.pointer = CMPFUNC(self._mouse_proc)
        self.hook_id = ctypes.windll.user32.SetWindowsHookExA(
            WH_MOUSE_LL,
            self.pointer,
            0,
            0
        )
        print("钩子已安装")

    def stop(self):
        if self.hook_id:
            ctypes.windll.user32.UnhookWindowsHookEx(self.hook_id)
            self.hook_id = None
            print("钩子已卸载")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    interceptor = MouseClickDirectionInterceptor(target_class="DV2ControlHost", interval=0.14)
    interceptor._install_hook()
    sys.exit(app.exec())

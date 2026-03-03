# -*- coding: utf-8 -*-
import sys

# Win32 API
import win32api, win32gui

# PyQt6
from PyQt6.QtWidgets import QApplication
import TouchEdgeControllerLib

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 创建并启用触控助手
    manager = TouchEdgeControllerLib.TouchEdgeManager(app)
    manager.enable()

    # 保持事件循环运行
    sys.exit(app.exec())

# -*- coding: utf-8 -*-
import sys, os, subprocess
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import Qt

def is_process_running(name: str) -> bool:
    """检测进程是否存在"""
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        result = subprocess.run(
            ["tasklist", "/fi", f"imagename eq {name}"],
            capture_output=True, text=True,
            startupinfo=startupinfo, creationflags=subprocess.CREATE_NO_WINDOW
        )
        return name.lower() in result.stdout.lower()
    except Exception as e:
        print(f"检测进程失败: {e}")
        return False

def kill_process_by_name(name: str):
    """强制结束进程"""
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        subprocess.run(
            ["taskkill", "/f", "/im", name],
            check=True,
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        print(f"已终止进程: {name}")
    except subprocess.CalledProcessError:
        print(f"未找到进程: {name}")

class TrayController:
    def __init__(self, app: QApplication):
        self.app = app
        self.tray = QSystemTrayIcon(QIcon(self.resource_path("th_enabled.ico")), app)
        self.tray.setToolTip("触控助手")
        self.menu = QMenu()

        self.enable_action = QAction("启用触控助手")
        self.disable_action = QAction("禁用触控助手")
        self.restart_action = QAction("重启所有外部程序")
        self.exit_action = QAction("退出")

        self.enable_action.triggered.connect(self.enable_manager)
        self.disable_action.triggered.connect(self.disable_manager)
        self.restart_action.triggered.connect(self.restart_all_exes)
        self.exit_action.triggered.connect(self.exit_app)
        self.icon_enabled = QIcon(self.resource_path("th_enabled.ico"))
        self.icon_disabled = QIcon(self.resource_path("th_disabled.ico"))
        self.tray.setIcon(self.icon_enabled)


        self.menu.addAction(self.enable_action)
        self.menu.addAction(self.disable_action)
        self.menu.addAction(self.restart_action)
        self.menu.addSeparator()
        self.menu.addAction(self.exit_action)

        self.tray.setContextMenu(self.menu)
        self.tray.show()

        # 双击托盘图标切换启用/禁用
        self.tray.activated.connect(self.on_tray_activated)

        self.run_external_exe("TouchEdgeController.exe")
        self.run_external_exe("TouchStartMenu.exe")
        self.run_external_exe("TouchStateController.exe")

    def resource_path(self, relative_path):
        if hasattr(sys, "_MEIPASS"):
            return os.path.join(sys._MEIPASS, "TouchHelper/"+relative_path)
        print(os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path))
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)

    def run_external_exe(self, exe_name):
        exe_path = self.resource_path(exe_name)
        if os.path.exists(exe_path):
            if is_process_running(exe_name):
                print(f"外部程序已在运行，准备重启: {exe_name}")
                kill_process_by_name(exe_name)
            try:
                # 启动 exe 时也隐藏窗口
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                subprocess.Popen(
                    exe_path,
                    startupinfo=startupinfo,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                print(f"已启动外部程序: {exe_name}")
            except Exception as e:
                print(f"启动外部程序失败: {e}")
        else:
            print(f"未找到外部程序: {exe_path}")

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            print(self.resource_path("th_enabled.ico"))
            print(QIcon(self.resource_path("th_enabled.ico")).cacheKey())
            print(self.tray.icon().cacheKey())
            if self.tray.icon().cacheKey() == self.icon_enabled.cacheKey():
                self.disable_manager()
            else:
                self.enable_manager()

    def enable_manager(self):
        self.run_external_exe("TouchEdgeController.exe")
        self.tray.setIcon(self.icon_enabled)
        self.tray.showMessage("触控助手", "触控助手已启用", QSystemTrayIcon.MessageIcon.Information)
        print("触控助手已启用")

    def disable_manager(self):
        kill_process_by_name("TouchEdgeController.exe")
        self.tray.setIcon(self.icon_disabled)
        self.tray.showMessage("触控助手", "触控助手已禁用并清理残留", QSystemTrayIcon.MessageIcon.Information)
        print("触控助手已禁用")

    def restart_all_exes(self):
        print("正在重启所有外部程序...")
        self.run_external_exe("TouchEdgeController.exe")
        self.run_external_exe("TouchStartMenu.exe")
        self.run_external_exe("TouchStateController.exe")
        self.tray.setIcon(self.icon_enabled)
        self.tray.showMessage("触控助手", "所有外部程序已重启", QSystemTrayIcon.MessageIcon.Information)

    def exit_app(self):
        kill_process_by_name("TouchEdgeController.exe")
        kill_process_by_name("TouchStartMenu.exe")
        kill_process_by_name("TouchStateController.exe")
        print("程序已退出")
        os._exit(0)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    tray = TrayController(app)
    sys.exit(app.exec())

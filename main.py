import os
import sys

# ensure the script's own folder is searchable, regardless of how it's launched
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 主窗口关闭时是"最小化到托盘"而不是真的关闭，
    # 但悬浮条本身也是一个窗口，这里确保它单独存在时不会导致整个程序退出
    app.setQuitOnLastWindowClosed(False)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

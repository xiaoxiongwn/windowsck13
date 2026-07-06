from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton


class DetailDialog(QDialog):
    """双击卡片弹出的详情窗口：显示完整标题 + 内容。"""

    def __init__(self, item, parent=None):
        super().__init__(parent)
        self.setWindowTitle(item.title)
        self.resize(420, 320)

        layout = QVBoxLayout()

        title_label = QLabel(item.title)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")

        content_view = QTextEdit()
        content_view.setPlainText(item.content)
        content_view.setReadOnly(True)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)

        layout.addWidget(title_label)
        layout.addWidget(content_view)
        layout.addWidget(close_btn)

        self.setLayout(layout)

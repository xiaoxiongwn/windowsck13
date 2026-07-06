from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QComboBox, QSpinBox, QPushButton, QHBoxLayout
)


class EditDialog(QDialog):
    """
    双击列表里的某一条时弹出，可以修改：
    标题 / 内容 / 分类 / 优先级(星级)
    保存后直接调用 data_manager.update_item()。
    """

    def __init__(self, item, manager, categories, on_saved=None, parent=None):
        super().__init__(parent)
        self.item = item
        self.manager = manager
        self.on_saved = on_saved

        self.setWindowTitle(f"编辑：{item.title}")
        self.resize(420, 380)

        form = QFormLayout()

        self.title_input = QLineEdit(item.title)
        form.addRow("标题：", self.title_input)

        self.category_input = QComboBox()
        self.category_input.setEditable(True)
        self.category_input.addItems(categories)
        idx = self.category_input.findText(item.category)
        if idx >= 0:
            self.category_input.setCurrentIndex(idx)
        else:
            self.category_input.setCurrentText(item.category)
        form.addRow("分类：", self.category_input)

        self.priority_input = QSpinBox()
        self.priority_input.setRange(1, 5)
        self.priority_input.setValue(item.priority)
        self.priority_input.setSuffix(" 星")
        form.addRow("优先级：", self.priority_input)

        self.content_input = QTextEdit()
        self.content_input.setPlainText(item.content)

        btn_row = QHBoxLayout()
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.save_and_close)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(self.content_input)
        layout.addLayout(btn_row)
        self.setLayout(layout)

    def save_and_close(self):
        title = self.title_input.text().strip()
        if not title:
            return

        self.manager.update_item(
            self.item.id,
            title=title,
            content=self.content_input.toPlainText().strip(),
            category=self.category_input.currentText().strip() or "未分类",
            priority=self.priority_input.value(),
        )

        if self.on_saved:
            self.on_saved()
        self.accept()

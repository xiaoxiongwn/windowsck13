from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLineEdit, QLabel, QMessageBox, QInputDialog
)


class CategoryDialog(QDialog):
    """
    管理分类：新增 / 重命名 / 删除。
    - 新增：加一个新的分类名字，以后新增内容时下拉框里就会有它
    - 重命名：选中一个分类改名字，所有用到这个分类的内容会跟着一起改
    - 删除：选中一个分类删除；如果还有内容在用这个分类，
            会先询问是否把这些内容转移到"未分类"
    """

    def __init__(self, config, manager, on_changed=None, parent=None):
        super().__init__(parent)
        self.config = config
        self.manager = manager
        self.on_changed = on_changed

        self.setWindowTitle("管理分类")
        self.resize(320, 380)

        layout = QVBoxLayout()

        self.list_widget = QListWidget()
        layout.addWidget(QLabel("现有分类："))
        layout.addWidget(self.list_widget)

        add_row = QHBoxLayout()
        self.new_input = QLineEdit()
        self.new_input.setPlaceholderText("输入新分类名字")
        add_btn = QPushButton("新增")
        add_btn.clicked.connect(self.add_category)
        add_row.addWidget(self.new_input)
        add_row.addWidget(add_btn)
        layout.addLayout(add_row)

        btn_row = QHBoxLayout()
        rename_btn = QPushButton("重命名选中")
        rename_btn.clicked.connect(self.rename_selected)
        delete_btn = QPushButton("删除选中")
        delete_btn.clicked.connect(self.delete_selected)
        btn_row.addWidget(rename_btn)
        btn_row.addWidget(delete_btn)
        layout.addLayout(btn_row)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        self.setLayout(layout)
        self._refresh_list()

    def _get_categories(self):
        saved = self.config.get("categories") or []
        # 把实际数据里用到、但还没加进配置列表的分类也补进来，避免"漏掉"
        for cat in self.manager.categories():
            if cat not in saved:
                saved.append(cat)
        return saved

    def _refresh_list(self):
        self.list_widget.clear()
        for cat in self._get_categories():
            count = self.manager.count_by_category(cat)
            self.list_widget.addItem(QListWidgetItem(f"{cat}（{count}条）"))

    def _selected_category_name(self):
        current = self.list_widget.currentItem()
        if current is None:
            return None
        # 显示文字是"名字（N条）"，取到括号前面的部分
        return current.text().split("（")[0]

    def add_category(self):
        name = self.new_input.text().strip()
        if not name:
            return

        categories = self._get_categories()
        if name in categories:
            QMessageBox.information(self, "提示", "这个分类已经存在了")
            return

        categories.append(name)
        self.config.update(categories=categories)
        self.new_input.clear()
        self._refresh_list()
        if self.on_changed:
            self.on_changed()

    def rename_selected(self):
        old_name = self._selected_category_name()
        if old_name is None:
            return

        new_name, ok = QInputDialog.getText(self, "重命名分类", f"把「{old_name}」改成：", text=old_name)
        if not ok:
            return
        new_name = new_name.strip()
        if not new_name or new_name == old_name:
            return

        categories = self._get_categories()
        categories = [new_name if c == old_name else c for c in categories]
        # 避免改名后和另一个已有分类重复
        seen = []
        deduped = []
        for c in categories:
            if c not in seen:
                seen.append(c)
                deduped.append(c)
        self.config.update(categories=deduped)

        self.manager.rename_category(old_name, new_name)

        self._refresh_list()
        if self.on_changed:
            self.on_changed()

    def delete_selected(self):
        name = self._selected_category_name()
        if name is None:
            return

        count = self.manager.count_by_category(name)
        if count > 0:
            reply = QMessageBox.question(
                self,
                "删除分类",
                f"「{name}」这个分类下还有 {count} 条内容，删除分类后这些内容会转移到「未分类」，确定要继续吗？",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
            self.manager.reassign_category(name, "未分类")

        categories = [c for c in self._get_categories() if c != name]
        self.config.update(categories=categories)

        self._refresh_list()
        if self.on_changed:
            self.on_changed()

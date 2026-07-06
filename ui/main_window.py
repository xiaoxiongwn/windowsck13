import json

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QTextEdit, QPushButton, QListWidget, QLabel, QListWidgetItem,
    QComboBox, QSpinBox, QSystemTrayIcon, QMenu, QFileDialog, QMessageBox,
    QApplication
)

from models.data_manager import DataManager
from models.item import Item
from ui.ticker_window import TickerWindow
from ui.settings_dialog import SettingsDialog
from ui.edit_dialog import EditDialog
from ui.category_dialog import CategoryDialog
from utils.config import AppConfig
from utils.app_info import APP_NAME

DEFAULT_CATEGORIES = ["未分类", "工作", "学习", "股票", "服务器"]


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(APP_NAME)

        self.config = AppConfig()
        self.resize(
            self.config.get("window_width", 900),
            self.config.get("window_height", 600),
        )

        self.manager = DataManager()
        self.ticker_window = None

        layout = QVBoxLayout()

        # ---- 新增区域 ----
        input_row = QHBoxLayout()

        title_col = QVBoxLayout()
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("输入标题")
        title_col.addWidget(QLabel("标题"))
        title_col.addWidget(self.title_input)

        category_col = QVBoxLayout()
        self.category_input = QComboBox()
        self.category_input.setEditable(True)
        category_col.addWidget(QLabel("分类"))
        category_col.addWidget(self.category_input)

        priority_col = QVBoxLayout()
        self.priority_input = QSpinBox()
        self.priority_input.setRange(1, 5)
        self.priority_input.setValue(3)
        self.priority_input.setSuffix(" 星")
        priority_col.addWidget(QLabel("优先级"))
        priority_col.addWidget(self.priority_input)

        input_row.addLayout(title_col, 3)
        input_row.addLayout(category_col, 2)
        input_row.addLayout(priority_col, 1)

        self.content_input = QTextEdit()
        self.content_input.setPlaceholderText("输入内容")

        btn_row = QHBoxLayout()
        self.add_btn = QPushButton("新增")
        self.add_btn.clicked.connect(self.add_item)
        self.edit_btn = QPushButton("编辑选中")
        self.edit_btn.clicked.connect(self.edit_selected)
        self.delete_btn = QPushButton("删除选中")
        self.delete_btn.clicked.connect(self.delete_selected)
        btn_row.addWidget(self.add_btn)
        btn_row.addWidget(self.edit_btn)
        btn_row.addWidget(self.delete_btn)

        status_row = QHBoxLayout()
        self.favorite_btn = QPushButton("★ 收藏/取消收藏")
        self.favorite_btn.clicked.connect(self.toggle_favorite_selected)
        self.completed_btn = QPushButton("✓ 标记完成/取消完成")
        self.completed_btn.clicked.connect(self.toggle_completed_selected)
        status_row.addWidget(self.favorite_btn)
        status_row.addWidget(self.completed_btn)

        tool_row = QHBoxLayout()
        self.ticker_btn = QPushButton("打开桌面悬浮条")
        self.ticker_btn.clicked.connect(self.open_ticker)
        self.settings_btn = QPushButton("设置")
        self.settings_btn.clicked.connect(self.open_settings)
        self.export_btn = QPushButton("导出数据")
        self.export_btn.clicked.connect(self.export_data)
        self.import_btn = QPushButton("导入数据")
        self.import_btn.clicked.connect(self.import_data)
        self.category_manage_btn = QPushButton("管理分类")
        self.category_manage_btn.clicked.connect(self.open_category_manager)
        tool_row.addWidget(self.ticker_btn)
        tool_row.addWidget(self.settings_btn)
        tool_row.addWidget(self.export_btn)
        tool_row.addWidget(self.import_btn)
        tool_row.addWidget(self.category_manage_btn)

        # ---- 搜索 / 筛选区域 ----
        filter_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索标题或内容…")
        self.search_input.textChanged.connect(self.refresh)

        self.category_filter = QComboBox()
        self.category_filter.currentIndexChanged.connect(self.refresh)

        filter_row.addWidget(QLabel("搜索："))
        filter_row.addWidget(self.search_input, 3)
        filter_row.addWidget(QLabel("分类："))
        filter_row.addWidget(self.category_filter, 1)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.edit_item_from_list)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_list_context_menu)

        layout.addLayout(input_row)
        layout.addWidget(QLabel("内容"))
        layout.addWidget(self.content_input)
        layout.addLayout(btn_row)
        layout.addLayout(status_row)
        layout.addLayout(tool_row)
        layout.addLayout(filter_row)
        layout.addWidget(QLabel("已有内容（双击可编辑）"))
        layout.addWidget(self.list_widget)

        self.setLayout(layout)

        self._refresh_category_choices()
        self.refresh()
        self._init_tray_icon()

    # ---------- 列表刷新 / 筛选 ----------

    def _get_all_categories(self):
        """分类下拉框统一从这里取：config 里保存的分类 + 实际数据里用到但还没保存的分类。"""
        categories = list(self.config.get("categories") or DEFAULT_CATEGORIES)
        for cat in self.manager.categories():
            if cat not in categories:
                categories.append(cat)
        return categories

    def _refresh_category_choices(self):
        all_categories = self._get_all_categories()

        # 新增内容用的分类下拉框
        current_input_text = self.category_input.currentText()
        self.category_input.blockSignals(True)
        self.category_input.clear()
        self.category_input.addItems(all_categories)
        if current_input_text:
            self.category_input.setCurrentText(current_input_text)
        self.category_input.blockSignals(False)

        # 筛选用的分类下拉框
        current_filter = self.category_filter.currentText()
        self.category_filter.blockSignals(True)
        self.category_filter.clear()
        self.category_filter.addItem("全部")
        for cat in all_categories:
            self.category_filter.addItem(cat)
        idx = self.category_filter.findText(current_filter)
        self.category_filter.setCurrentIndex(idx if idx >= 0 else 0)
        self.category_filter.blockSignals(False)

    def refresh(self):
        keyword = self.search_input.text().strip().lower()
        category = self.category_filter.currentText()

        self.list_widget.clear()
        for item in self.manager.items:
            if category and category != "全部" and item.category != category:
                continue
            if keyword and keyword not in item.title.lower() and keyword not in item.content.lower():
                continue

            stars = "★" * item.priority
            favorite_mark = "⭐" if item.favorite else ""
            done_mark = "✓ " if item.completed else ""
            display_text = f"{done_mark}[{item.category}] {stars} {favorite_mark}{item.title}"

            list_item = QListWidgetItem(display_text)
            list_item.setData(Qt.UserRole, item.id)
            if item.completed:
                font = list_item.font()
                font.setStrikeOut(True)
                list_item.setFont(font)
            self.list_widget.addItem(list_item)

    def _current_item_id(self):
        current = self.list_widget.currentItem()
        if current is None:
            return None
        return current.data(Qt.UserRole)

    def _show_list_context_menu(self, pos):
        list_item = self.list_widget.itemAt(pos)
        if list_item is None:
            return
        self.list_widget.setCurrentItem(list_item)

        menu = QMenu(self)
        edit_action = menu.addAction("编辑")
        favorite_action = menu.addAction("★ 收藏/取消收藏")
        completed_action = menu.addAction("✓ 标记完成/取消完成")
        menu.addSeparator()
        delete_action = menu.addAction("删除")

        action = menu.exec(self.list_widget.mapToGlobal(pos))

        if action == delete_action:
            self.delete_selected()
        elif action == edit_action:
            self.edit_item_from_list(list_item)
        elif action == favorite_action:
            self.toggle_favorite_selected()
        elif action == completed_action:
            self.toggle_completed_selected()

    # ---------- 增删改 ----------

    def add_item(self):
        title = self.title_input.text().strip()
        content = self.content_input.toPlainText().strip()
        category = self.category_input.currentText().strip() or "未分类"
        priority = self.priority_input.value()

        if not title:
            return

        self.manager.add_item(title, content, category=category, priority=priority)

        self.title_input.clear()
        self.content_input.clear()
        self.priority_input.setValue(3)

        self._refresh_category_choices()
        self.refresh()
        self._sync_ticker()

    def edit_selected(self):
        item_id = self._current_item_id()
        if item_id is None:
            return
        self._open_edit_dialog(item_id)

    def edit_item_from_list(self, list_item):
        item_id = list_item.data(Qt.UserRole)
        self._open_edit_dialog(item_id)

    def _open_edit_dialog(self, item_id):
        item = self.manager.get_item(item_id)
        if item is None:
            return

        categories = self._get_all_categories()

        def on_saved():
            self._refresh_category_choices()
            self.refresh()
            self._sync_ticker()

        dialog = EditDialog(item, self.manager, categories, on_saved=on_saved, parent=self)
        dialog.exec()

    def delete_selected(self):
        item_id = self._current_item_id()
        if item_id is None:
            return

        self.manager.delete_item(item_id)
        self._refresh_category_choices()
        self.refresh()
        self._sync_ticker()

    def toggle_favorite_selected(self):
        item_id = self._current_item_id()
        if item_id is None:
            return
        self.manager.toggle_favorite(item_id)
        self.refresh()
        self._sync_ticker()

    def toggle_completed_selected(self):
        item_id = self._current_item_id()
        if item_id is None:
            return
        self.manager.toggle_completed(item_id)
        self.refresh()
        self._sync_ticker()

    # ---------- 悬浮条 / 设置 ----------

    def open_ticker(self):
        if self.ticker_window is None:
            self.ticker_window = TickerWindow(config=self.config)
        self.ticker_window.refresh_data()
        self.ticker_window.show()
        self.ticker_window.raise_()

    def open_settings(self):
        dialog = SettingsDialog(self.config, on_apply=self._sync_ticker, parent=self)
        dialog.exec()

    def open_category_manager(self):
        dialog = CategoryDialog(
            self.config, self.manager, on_changed=self._refresh_category_choices, parent=self
        )
        dialog.exec()
        # 分类管理里可能改了某些内容的分类归属，顺便刷新列表和悬浮条
        self.refresh()
        self._sync_ticker()

    def _sync_ticker(self):
        if self.ticker_window is not None:
            self.ticker_window.refresh_data()
            self.ticker_window.apply_settings()

    # ---------- 系统托盘 ----------

    def _make_icon(self):
        """没有现成的图标文件，就自己画一个简单的圆形小图标。"""
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#4682DC"))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(4, 4, 56, 56)
        painter.end()
        return QIcon(pixmap)

    def _init_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self._make_icon(), self)
        self.tray_icon.setToolTip(APP_NAME)

        tray_menu = QMenu()
        show_action = tray_menu.addAction("显示主窗口")
        show_action.triggered.connect(self._show_from_tray)
        ticker_action = tray_menu.addAction("打开桌面悬浮条")
        ticker_action.triggered.connect(self.open_ticker)
        tray_menu.addSeparator()
        quit_action = tray_menu.addAction(f"退出 {APP_NAME}")
        quit_action.triggered.connect(self.quit_app)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason):
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._show_from_tray()

    def _show_from_tray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        # 点右上角关闭按钮时，最小化到系统托盘，而不是真的退出程序，
        # 这样悬浮条可以继续在桌面上显示。
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            APP_NAME,
            "已最小化到系统托盘，双击托盘图标可重新打开主窗口",
            QSystemTrayIcon.MessageIcon.Information,
            2000,
        )

    def quit_app(self):
        if self.ticker_window is not None:
            self.ticker_window.close()
        self.tray_icon.hide()
        QApplication.instance().quit()

    # ---------- 导入 / 导出 ----------

    def export_data(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "导出数据", f"{APP_NAME}_backup.json", "JSON 文件 (*.json)"
        )
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(
                    [i.to_dict() for i in self.manager.items],
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
        except OSError as e:
            QMessageBox.warning(self, "导出失败", f"写入文件失败：\n{e}")
            return

        QMessageBox.information(self, "导出成功", f"已导出到：\n{path}")

    def import_data(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "导入数据", "", "JSON 文件 (*.json)"
        )
        if not path:
            return

        reply = QMessageBox.question(
            self,
            "导入数据",
            "导入会覆盖当前所有数据（建议先用「导出数据」备份一下），确定要继续吗？",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            new_items = [Item(**i) for i in raw]
        except (OSError, json.JSONDecodeError, TypeError) as e:
            QMessageBox.warning(self, "导入失败", f"文件格式不正确：\n{e}")
            return

        self.manager.items = new_items
        self.manager.save()

        self._refresh_category_choices()
        self.refresh()
        self._sync_ticker()
        QMessageBox.information(self, "导入成功", "数据已导入")

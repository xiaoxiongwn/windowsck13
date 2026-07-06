from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QFontComboBox, QSpinBox,
    QPushButton, QSlider, QCheckBox, QHBoxLayout, QLabel, QColorDialog,
    QComboBox
)
from PySide6.QtCore import Qt

from utils import autostart

DEFAULT_PRIORITY_COLORS = {
    "1": "#4A90D9",
    "2": "#3FB88F",
    "3": "#E8A33D",
    "4": "#E0703D",
    "5": "#D9434E",
}


class SettingsDialog(QDialog):
    """
    设置窗口：字体、字号、按星级配色、透明度、是否置顶、是否悬停暂停、开机自启。
    点"保存"后写入 config.json，并立即通知悬浮条应用新设置。
    """

    def __init__(self, config, on_apply=None, parent=None):
        super().__init__(parent)
        self.config = config
        self.on_apply = on_apply

        saved_colors = config.get("priority_colors") or {}
        # 以星级 1~5 为准，缺失的用默认颜色补齐
        self._priority_colors = {
            str(p): saved_colors.get(str(p), DEFAULT_PRIORITY_COLORS[str(p)])
            for p in range(1, 6)
        }

        self.setWindowTitle("设置")
        self.resize(380, 420)

        form = QFormLayout()

        self.font_combo = QFontComboBox()
        current_family = config.get("font_family")
        if current_family:
            self.font_combo.setCurrentText(current_family)
        form.addRow("字体：", self.font_combo)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(1, 36)
        self.font_size_spin.setValue(config.get("font_size", 14))
        form.addRow("字号：", self.font_size_spin)

        self.orientation_combo = QComboBox()
        self.orientation_combo.addItem("横向（从右往左滚动）", "horizontal")
        self.orientation_combo.addItem("竖向（从下往上滚动）", "vertical")
        current_orientation = config.get("orientation", "horizontal")
        idx = self.orientation_combo.findData(current_orientation)
        self.orientation_combo.setCurrentIndex(idx if idx >= 0 else 0)
        form.addRow("悬浮条方向：", self.orientation_combo)

        # ---- 按星级配色：1~5 星各一个颜色按钮 ----
        self._color_previews = {}
        for p in range(1, 6):
            row = QHBoxLayout()
            preview = QLabel()
            preview.setFixedSize(24, 24)
            self._color_previews[str(p)] = preview
            self._update_color_preview(str(p))

            btn = QPushButton("选择颜色")
            btn.clicked.connect(lambda checked=False, star=str(p): self.pick_color(star))

            row.addWidget(preview)
            row.addWidget(btn)
            form.addRow(f"{'★' * p} 卡片颜色：", row)

        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(20, 100)
        self.opacity_slider.setValue(config.get("opacity", 85))
        form.addRow("悬浮条透明度：", self.opacity_slider)

        self.top_checkbox = QCheckBox("悬浮条始终置顶")
        self.top_checkbox.setChecked(config.get("always_on_top", True))
        form.addRow(self.top_checkbox)

        self.hover_checkbox = QCheckBox("鼠标悬停时暂停滚动")
        self.hover_checkbox.setChecked(config.get("pause_on_hover", True))
        form.addRow(self.hover_checkbox)

        self.autostart_checkbox = QCheckBox("开机自动启动（仅 Windows 有效）")
        self.autostart_checkbox.setChecked(autostart.is_autostart_enabled())
        form.addRow(self.autostart_checkbox)

        btn_row = QHBoxLayout()
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.save_and_close)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addLayout(btn_row)
        self.setLayout(layout)

    def _update_color_preview(self, star):
        color = self._priority_colors[star]
        self._color_previews[star].setStyleSheet(
            f"background-color: {color}; border: 1px solid #888;"
        )

    def pick_color(self, star):
        current = QColor(self._priority_colors[star])
        color = QColorDialog.getColor(current, self)
        if color.isValid():
            self._priority_colors[star] = color.name()
            self._update_color_preview(star)

    def save_and_close(self):
        self.config.update(
            font_family=self.font_combo.currentText(),
            font_size=self.font_size_spin.value(),
            orientation=self.orientation_combo.currentData(),
            priority_colors=dict(self._priority_colors),
            opacity=self.opacity_slider.value(),
            always_on_top=self.top_checkbox.isChecked(),
            pause_on_hover=self.hover_checkbox.isChecked(),
        )

        if self.autostart_checkbox.isChecked():
            autostart.enable_autostart()
        else:
            autostart.disable_autostart()

        if self.on_apply:
            self.on_apply()
        self.accept()

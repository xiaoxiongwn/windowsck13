from PySide6.QtCore import Qt, QTimer, QRect, QPoint
from PySide6.QtGui import QPainter, QColor, QFontMetrics, QPainterPath, QFont
from PySide6.QtWidgets import QWidget, QApplication, QMenu

from models.data_manager import DataManager
from ui.detail_dialog import DetailDialog
from utils.config import AppConfig


CARD_HEIGHT = 40
CARD_GAP = 16
CARD_PADDING_X = 16
CARD_PADDING_Y = 10
BAR_HEIGHT = 60
DEFAULT_WIDTH = 560
VERTICAL_DEFAULT_WIDTH = 260
VERTICAL_DEFAULT_HEIGHT = 480
RESIZE_MARGIN = 8
MIN_WIDTH = 240
MIN_HEIGHT = 44

# 星级 -> 卡片颜色，数字越大越重要，颜色也更醒目/更"警示"
DEFAULT_PRIORITY_COLORS = {
    "1": "#4A90D9",  # 蓝色
    "2": "#3FB88F",  # 青绿色
    "3": "#E8A33D",  # 橙色
    "4": "#E0703D",  # 深橙色
    "5": "#D9434E",  # 红色
}


class TickerWindow(QWidget):
    """
    桌面悬浮滚动条：
    - 无边框、置顶、半透明背景
    - 卡片一张一张从右向左滚动
    - 鼠标悬停暂停，移开继续滚动
    - 双击某张卡片弹出详情
    - 可拖动到桌面任意位置
    - 外观 (字体/颜色/透明度) 和行为 (置顶/悬停暂停) 都从 config 读取
    """

    def __init__(self, config=None):
        super().__init__()

        self.config = config or AppConfig()

        self.manager = DataManager()
        self.speed = self.config.get("scroll_speed", 2)
        self.offset = 0.0
        self.paused = False
        self._drag_offset = None
        self._pause_on_hover = self.config.get("pause_on_hover", True)
        self._hovering = False
        self._orientation = self.config.get("orientation", "horizontal")

        # 缩放相关状态
        self._resizing = False
        self._resize_edge = None
        self._resize_start_geo = None
        self._resize_start_mouse = None

        # 每次绘制时记录每张卡片当前的屏幕位置，用来判断双击点到了哪一张
        self._card_rects = []  # list of (QRect, item)
        self._sequence = []  # 按优先级加权、跳过已完成后的滚动播放序列

        self._restore_geometry()
        self._apply_window_flags()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_tick)
        self.timer.start(16)  # 约 60 FPS

        self.setMouseTracking(True)

        self._rebuild_sequence()

    # ---------- 位置 / 大小 / 窗口标志 ----------

    def _restore_geometry(self):
        """优先使用上次保存的位置和大小，没有则用默认值（按当前方向选取合适的默认尺寸）。"""
        default_w, default_h = self._default_size_for_orientation()

        x = self.config.get("ticker_x")
        y = self.config.get("ticker_y")
        w = self.config.get("ticker_width") or default_w
        h = self.config.get("ticker_height") or default_h

        self.resize(max(w, MIN_WIDTH), max(h, MIN_HEIGHT))

        if x is not None and y is not None:
            self.move(x, y)
        else:
            self._move_to_default_position()

    def _default_size_for_orientation(self):
        if self._orientation == "vertical":
            return VERTICAL_DEFAULT_WIDTH, VERTICAL_DEFAULT_HEIGHT
        return DEFAULT_WIDTH, BAR_HEIGHT

    def _save_geometry(self):
        self.config.update(
            ticker_x=self.x(),
            ticker_y=self.y(),
            ticker_width=self.width(),
            ticker_height=self.height(),
        )

    def _apply_window_flags(self):
        flags = Qt.FramelessWindowHint | Qt.Tool
        if self.config.get("always_on_top", True):
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def _move_to_default_position(self):
        screen = QApplication.primaryScreen().availableGeometry()
        if self._orientation == "vertical":
            x = screen.x() + screen.width() - self.width() - 40
            y = screen.y() + (screen.height() - self.height()) // 2
        else:
            x = screen.x() + (screen.width() - self.width()) // 2
            y = screen.y() + screen.height() - self.height() - 40
        self.move(x, y)

    # ---------- 数据 ----------

    def refresh_data(self):
        """当主窗口新增/删除数据后调用，让滚动条同步最新内容。"""
        self.manager.load()
        self._rebuild_sequence()

    def _rebuild_sequence(self):
        """
        滚动播放顺序：每条只出现一次（不再按优先级重复），
        已完成的条目直接跳过，不出现在悬浮条里。
        重要性改用卡片颜色区分，见 paintEvent。
        """
        self._sequence = [i for i in self.manager.items if not i.completed]
        self.offset = 0.0

    def apply_settings(self):
        """设置窗口保存后调用，让悬浮条立即应用新的外观/行为设置。"""
        self.speed = self.config.get("scroll_speed", self.speed)
        self._pause_on_hover = self.config.get("pause_on_hover", True)

        new_orientation = self.config.get("orientation", "horizontal")
        if new_orientation != self._orientation:
            # 方向变了：把宽高对调一下，横向的"矮长条"变成竖向的"瘦高条"（反之亦然），
            # 这样切换方向后形状会更合理，不用你自己手动重新拖一遍。
            self._orientation = new_orientation
            self.resize(self.height(), self.width())
            self._move_to_default_position()
            self._save_geometry()
            self.offset = 0.0

        was_visible = self.isVisible()
        self._apply_window_flags()
        if was_visible:
            self.show()
        self.update()

    # ---------- 滚动动画 ----------

    def _on_tick(self):
        if self.paused or not self._sequence:
            return
        self.offset += self.speed
        self.update()

    def enterEvent(self, event):
        if self._pause_on_hover:
            self.paused = True
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.paused = False
        self.setCursor(Qt.ArrowCursor)
        super().leaveEvent(event)

    # ---------- 绘制 ----------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        is_vertical = self._orientation == "vertical"

        opacity_pct = self.config.get("opacity", 85)
        bg_alpha = int(255 * (opacity_pct / 100) * 0.75)
        card_alpha = int(255 * (opacity_pct / 100))

        priority_colors = self.config.get("priority_colors") or DEFAULT_PRIORITY_COLORS

        font_family = self.config.get("font_family", "Microsoft YaHei")
        base_font_size = self.config.get("font_size", 14)

        # primary_extent：滚动方向上的长度（横向是宽度，竖向是高度）
        # cross_extent：垂直于滚动方向的"粗细"（横向是高度，竖向是宽度）
        primary_extent = self.height() if is_vertical else self.width()
        cross_extent = self.width() if is_vertical else self.height()

        # 悬浮条被拉得越"粗"，字体跟着等比例放大，方便当大屏幕展示用
        scale = max(1.0, cross_extent / BAR_HEIGHT)
        font_size = int(base_font_size * scale)
        painter.setFont(QFont(font_family, font_size))

        # 整条背景（圆角、半透明深色）
        bg_path = QPainterPath()
        bg_path.addRoundedRect(0, 0, self.width(), self.height(), 16, 16)
        painter.fillPath(bg_path, QColor(30, 30, 30, bg_alpha))

        items = self._sequence
        self._card_rects = []

        if not items:
            painter.setPen(QColor(255, 255, 255, 200))
            painter.drawText(self.rect(), Qt.AlignCenter, "暂无内容，先在主窗口里新增一条吧")
            painter.end()
            return

        metrics = QFontMetrics(painter.font())

        # 预先算出每张卡片的显示文字
        # （加上序号方便区分，收藏的再加个星标前缀）
        card_texts = []
        for idx, item in enumerate(items):
            prefix = f"{idx + 1}、"
            star = "⭐ " if item.favorite else ""
            card_texts.append(f"{prefix}{star}{item.title}")

        if is_vertical:
            # 竖向：每条内容占一行，长度(高度)固定为字体行高+上下留白，
            # 文字本身还是横着写的，只是一条条往上滚动
            card_primary_sizes = [metrics.height() + CARD_PADDING_Y * 2 for _ in card_texts]
        else:
            # 横向：每条内容的长度(宽度)按文字长短决定
            card_primary_sizes = [
                metrics.horizontalAdvance(text) + CARD_PADDING_X * 2
                for text in card_texts
            ]

        card_thickness = max(28, int(cross_extent * 0.6))
        cross_pos = (cross_extent - card_thickness) // 2

        def draw_card(pos_along, size_along, index):
            if is_vertical:
                card_rect = QRect(cross_pos, int(pos_along), card_thickness, size_along)
                out_of_view = card_rect.bottom() < 0 or card_rect.top() > self.height()
            else:
                card_rect = QRect(int(pos_along), cross_pos, size_along, card_thickness)
                out_of_view = card_rect.right() < 0 or card_rect.left() > self.width()

            if out_of_view:
                return

            item = items[index]
            card_color = QColor(priority_colors.get(str(item.priority), "#4682DC"))
            card_color.setAlpha(card_alpha)

            card_path = QPainterPath()
            card_path.addRoundedRect(card_rect, 10, 10)
            painter.fillPath(card_path, card_color)

            painter.setPen(QColor(255, 255, 255))
            painter.drawText(card_rect, Qt.AlignCenter, card_texts[index])

            self._card_rects.append((QRect(card_rect), item))

        # 把"1、2、3……"这一整组内容当成一个整体：
        # 一开始完全藏在滚动方向的起点外面（一个字都看不见)，
        # 然后逐渐滑入、划过、再逐渐滑出到终点外面完全消失，
        # 才重新进入下一圈。横向是从右边进、左边出；竖向是从下边进、上边出。
        cum_offsets = []
        running = 0
        for idx, size in enumerate(card_primary_sizes):
            cum_offsets.append(running)
            running += size
            if idx < len(card_primary_sizes) - 1:
                running += CARD_GAP
        group_length = running  # 这一整组内容加起来的总长度

        # 总位移距离 = 滚动方向长度 + 整组内容长度，
        # 这样才能覆盖"完全在起点外" 到 "完全在终点外" 的完整滑动过程。
        total_unit = max(1, primary_extent + group_length)
        self.offset %= total_unit
        cycle_pos = self.offset

        group_pos = primary_extent - cycle_pos

        for i, size in enumerate(card_primary_sizes):
            pos_along = group_pos + cum_offsets[i]
            draw_card(pos_along, size, i)

        painter.end()

    # ---------- 鼠标交互：拖动 / 缩放 / 双击 ----------

    def _detect_edge(self, pos):
        """判断鼠标当前在窗口的哪个边缘/角落，用于缩放。"""
        margin = RESIZE_MARGIN
        w, h = self.width(), self.height()

        left = pos.x() <= margin
        right = pos.x() >= w - margin
        top = pos.y() <= margin
        bottom = pos.y() >= h - margin

        if top and left:
            return "top-left"
        if top and right:
            return "top-right"
        if bottom and left:
            return "bottom-left"
        if bottom and right:
            return "bottom-right"
        if left:
            return "left"
        if right:
            return "right"
        if top:
            return "top"
        if bottom:
            return "bottom"
        return None

    _EDGE_CURSORS = {
        "left": Qt.SizeHorCursor,
        "right": Qt.SizeHorCursor,
        "top": Qt.SizeVerCursor,
        "bottom": Qt.SizeVerCursor,
        "top-left": Qt.SizeFDiagCursor,
        "bottom-right": Qt.SizeFDiagCursor,
        "top-right": Qt.SizeBDiagCursor,
        "bottom-left": Qt.SizeBDiagCursor,
    }

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            edge = self._detect_edge(event.position().toPoint())
            if edge:
                self._resizing = True
                self._resize_edge = edge
                self._resize_start_geo = self.geometry()
                self._resize_start_mouse = event.globalPosition().toPoint()
            else:
                self._drag_offset = event.globalPosition().toPoint() - self.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resizing and event.buttons() & Qt.LeftButton:
            self._perform_resize(event.globalPosition().toPoint())
        elif self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
        else:
            # 没有按键的普通移动：根据是否靠近边缘，切换鼠标光标样式
            edge = self._detect_edge(event.position().toPoint())
            self.setCursor(self._EDGE_CURSORS.get(edge, Qt.ArrowCursor))
        super().mouseMoveEvent(event)

    def _perform_resize(self, global_pos):
        delta = global_pos - self._resize_start_mouse
        geo = QRect(self._resize_start_geo)
        edge = self._resize_edge

        if "left" in edge:
            new_left = geo.left() + delta.x()
            if geo.right() - new_left + 1 >= MIN_WIDTH:
                geo.setLeft(new_left)
        if "right" in edge:
            new_width = geo.width() + delta.x()
            if new_width >= MIN_WIDTH:
                geo.setWidth(new_width)
        if "top" in edge:
            new_top = geo.top() + delta.y()
            if geo.bottom() - new_top + 1 >= MIN_HEIGHT:
                geo.setTop(new_top)
        if "bottom" in edge:
            new_height = geo.height() + delta.y()
            if new_height >= MIN_HEIGHT:
                geo.setHeight(new_height)

        self.setGeometry(geo)

    def mouseReleaseEvent(self, event):
        if self._resizing:
            self._resizing = False
            self._resize_edge = None
            self._save_geometry()
        if self._drag_offset is not None:
            self._save_geometry()
        self._drag_offset = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        pos = event.position().toPoint()
        for rect, item in self._card_rects:
            if rect.contains(pos):
                dialog = DetailDialog(item, self)
                dialog.exec()
                return
        super().mouseDoubleClickEvent(event)

    # ---------- 右键菜单：调速 / 关闭 ----------

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        speed_up = menu.addAction("加快滚动")
        slow_down = menu.addAction("减慢滚动")
        menu.addSeparator()
        reset_size = menu.addAction("还原默认大小/位置")
        menu.addSeparator()
        close_action = menu.addAction("关闭悬浮条")

        action = menu.exec(event.globalPos())

        if action == speed_up:
            self.speed = min(self.speed + 1, 20)
        elif action == slow_down:
            self.speed = max(self.speed - 1, 1)
        elif action == reset_size:
            default_w, default_h = self._default_size_for_orientation()
            self.resize(default_w, default_h)
            self._move_to_default_position()
            self._save_geometry()
        elif action == close_action:
            self.close()

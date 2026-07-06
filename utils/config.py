import json
import os

from utils.paths import get_app_dir

DEFAULT_CONFIG = {
    "window_width": 900,
    "window_height": 600,
    "font_family": "Microsoft YaHei",
    "font_size": 14,
    "card_color": "#4682DC",
    "priority_colors": {
        "1": "#4A90D9",
        "2": "#3FB88F",
        "3": "#E8A33D",
        "4": "#E0703D",
        "5": "#D9434E",
    },
    "opacity": 85,          # 0-100，悬浮条整体透明度
    "scroll_speed": 2,      # 悬浮条默认滚动速度
    "always_on_top": True,
    "pause_on_hover": True,
    "orientation": "horizontal",  # horizontal(横向) 或 vertical(竖向)
    "ticker_x": None,
    "ticker_y": None,
    "ticker_width": None,
    "ticker_height": None,
    "categories": ["未分类", "工作", "学习", "股票", "服务器"],
}


class AppConfig:
    """
    统一管理 config.json 的读写。
    以后设置窗口、悬浮条、主窗口都只通过这一层读写配置，
    不直接碰文件。
    """

    def __init__(self, file_path=None):
        self.file_path = file_path or os.path.join(get_app_dir(), "config.json")
        self.data = dict(DEFAULT_CONFIG)
        self.load()

    def load(self):
        if not os.path.exists(self.file_path):
            return

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                saved = json.load(f)
        except (json.JSONDecodeError, OSError):
            return

        # 用保存过的值覆盖默认值，缺失的字段自动保留默认值，
        # 这样以后新增配置项也不会导致旧 config.json 读取失败
        self.data.update(saved)

    def save(self):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value

    def update(self, **kwargs):
        self.data.update(kwargs)
        self.save()

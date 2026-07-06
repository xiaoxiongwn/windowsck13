import json
import os

from models.item import Item
from utils.paths import get_app_dir


class DataManager:
    """
    整个软件的数据大脑。
    以后所有窗口 (滚动窗口、设置窗口、搜索、分类、提醒...)
    都只通过这一层读写数据，不直接碰文件，方便以后统一维护。
    """

    def __init__(self, file_path=None):
        self.file_path = file_path or os.path.join(get_app_dir(), "data.json")
        self.items = []
        self.load()

    def load(self):
        if not os.path.exists(self.file_path):
            self.items = []
            return

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            # 文件损坏或读取失败时，不让软件崩溃，回退成空列表
            self.items = []
            return

        self.items = [Item(**i) for i in data]

    def save(self):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(
                [i.to_dict() for i in self.items],
                f,
                ensure_ascii=False,
                indent=2,
            )

    def add_item(self, title, content, category="未分类", priority=3):
        new_id = max([i.id for i in self.items], default=0) + 1
        item = Item(new_id, title, content, category=category, priority=priority)
        self.items.append(item)
        self.save()
        return item

    def update_item(self, item_id, **fields):
        """
        修改一条已有数据（标题/内容/分类/优先级等），
        以后设置窗口、编辑弹窗都调用这个方法，不用直接改 item 对象。
        """
        item = self.get_item(item_id)
        if item is None:
            return None

        if "title" in fields:
            item.title = fields["title"]
        if "content" in fields:
            item.content = fields["content"]
        if "category" in fields:
            item.category = fields["category"]
        if "priority" in fields:
            item.priority = max(1, min(5, int(fields["priority"])))
        if "favorite" in fields:
            item.favorite = bool(fields["favorite"])
        if "completed" in fields:
            item.completed = bool(fields["completed"])

        self.save()
        return item

    def toggle_favorite(self, item_id):
        item = self.get_item(item_id)
        if item is None:
            return None
        item.favorite = not item.favorite
        self.save()
        return item

    def toggle_completed(self, item_id):
        item = self.get_item(item_id)
        if item is None:
            return None
        item.completed = not item.completed
        self.save()
        return item

    def categories(self):
        """返回当前已经用过的所有分类，用于下拉框选项。"""
        seen = []
        for i in self.items:
            if i.category not in seen:
                seen.append(i.category)
        return seen

    def count_by_category(self, category):
        """这个分类目前有多少条内容在用，删除/重命名分类前用来提示用户。"""
        return sum(1 for i in self.items if i.category == category)

    def rename_category(self, old_name, new_name):
        """
        把所有用到 old_name 这个分类的条目，批量改成 new_name。
        用于"管理分类"里的重命名功能。
        """
        changed = 0
        for i in self.items:
            if i.category == old_name:
                i.category = new_name
                changed += 1
        if changed:
            self.save()
        return changed

    def reassign_category(self, old_name, new_name="未分类"):
        """把某个分类下的所有条目，重新归到另一个分类（默认归到"未分类"）。
        用于删除一个分类之前，先把用到它的内容转移出去。"""
        return self.rename_category(old_name, new_name)

    def delete_item(self, item_id):
        self.items = [i for i in self.items if i.id != item_id]
        self.save()

    def get_item(self, item_id):
        for i in self.items:
            if i.id == item_id:
                return i
        return None

class Item:
    """
    表示一条待办/信息条目。

    priority: 1~5，星级优先级，数字越大越重要，
              悬浮条里星级高的会更频繁出现。
    favorite: 是否收藏。
    completed: 是否已完成；已完成的条目不会出现在悬浮条滚动里。
    """

    def __init__(
        self,
        id,
        title,
        content,
        category="未分类",
        priority=3,
        favorite=False,
        completed=False,
        **extra,
    ):
        self.id = id
        self.title = title
        self.content = content
        self.category = category
        self.priority = max(1, min(5, int(priority)))
        self.favorite = bool(favorite)
        self.completed = bool(completed)
        # 预留字段，以后新增属性也不会导致旧数据读取失败
        self.extra = extra

    def to_dict(self):
        data = {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "category": self.category,
            "priority": self.priority,
            "favorite": self.favorite,
            "completed": self.completed,
        }
        data.update(self.extra)
        return data

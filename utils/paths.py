import os
import sys


def get_app_dir():
    """
    返回程序自身所在的文件夹：
    - 如果是 PyInstaller 打包后的 exe（sys.frozen 为 True），
      返回 exe 文件所在的目录；
    - 如果是用 python main.py 直接跑的开发模式，
      返回 main.py 所在的目录。

    这样 data.json / config.json 无论程序怎么启动
    （双击、快捷方式、从别的目录调用）都能稳定找到，
    也方便把整个文件夹拷到别的电脑上直接用。
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(sys.argv[0]))

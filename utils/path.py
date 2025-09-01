# utils/path.py
import sys, os

def resource_path(rel: str) -> str:
    """
    開發時回傳專案根目錄下的相對路徑；
    打包後回傳 PyInstaller 展開的臨時目錄下路徑。
    用法：resource_path("static/img/icon/icon.ico")
    """
    base = getattr(sys, "_MEIPASS", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    return os.path.join(base, rel)

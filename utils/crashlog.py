# ===================== utils/crashlog.py =====================
import os, sys, faulthandler, datetime, traceback

def _log_dir() -> str:
    d = os.path.join(os.path.dirname(getattr(sys, "_MEIPASS", os.getcwd())), "logs")
    os.makedirs(d, exist_ok=True)
    return d

def _new_log_path(prefix: str = "crash") -> str:
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    return os.path.join(_log_dir(), f"{prefix}-{stamp}.txt")

def setup_crashlog():
    """把未捕捉例外與低階崩潰寫入 logs/*.txt"""
    path = _new_log_path()
    try:
        f = open(path, "w", encoding="utf-8")
        faulthandler.enable(f)  # 原生崩潰也能寫
    except Exception:
        f = None

    def _hook(exc_type, exc, tb):
        try:
            with open(_new_log_path(), "w", encoding="utf-8") as out:
                out.write("UNCAUGHT EXCEPTION\n")
                out.write("=".ljust(60, "=") + "\n")
                traceback.print_exception(exc_type, exc, tb, file=out)
        finally:
            # 再交回預設處理，避免僵住
            sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = _hook

def log_exception(title: str, exc: BaseException):
    """在非致命錯誤時主動寫入一份 log。"""
    with open(_new_log_path("error"), "w", encoding="utf-8") as out:
        out.write(f"[{title}] {type(exc).__name__}: {exc}\n")
        out.write("Traceback:\n")
        out.write("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))

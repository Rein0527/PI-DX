# utils/crashlog.py
import os, sys, faulthandler, datetime, traceback, threading

_fault_file = None

def log_dir() -> str:
    d = os.path.join(os.path.dirname(getattr(sys, "_MEIPASS", os.getcwd())), "logs")
    os.makedirs(d, exist_ok=True)
    return d

def _new_log_path(prefix: str = "crash") -> str:
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    return os.path.join(log_dir(), f"{prefix}-{stamp}.txt")

def setup_crashlog():
    global _fault_file
    try:
        if _fault_file is None:
            _fault_file = open(_new_log_path("native"), "w", encoding="utf-8")
        faulthandler.enable(_fault_file, all_threads=True)
    except Exception:
        _fault_file = None

    def _hook(exc_type, exc, tb):
        try:
            with open(_new_log_path("crash"), "w", encoding="utf-8") as out:
                out.write("UNCAUGHT EXCEPTION\n")
                out.write("=" * 60 + "\n")
                traceback.print_exception(exc_type, exc, tb, file=out)
        finally:
            sys.__excepthook__(exc_type, exc, tb)
    sys.excepthook = _hook

    def _thread_hook(args):
        _hook(args.exc_type, args.exc_value, args.exc_traceback)
    if hasattr(threading, "excepthook"):
        threading.excepthook = _thread_hook

    try:
        import asyncio
        loop = asyncio.get_event_loop()
        def _async_handler(loop, context):
            exc = context.get("exception"); msg = context.get("message")
            try:
                with open(_new_log_path("async"), "w", encoding="utf-8") as out:
                    out.write("ASYNCIO EXCEPTION\n")
                    out.write("=" * 60 + "\n")
                    if exc:
                        traceback.print_exception(type(exc), exc, exc.__traceback__, file=out)
                    else:
                        out.write(str(msg))
            finally:
                loop.default_exception_handler(context)
        loop.set_exception_handler(_async_handler)
    except Exception:
        pass

def log_exception(title: str, exc: BaseException):
    with open(_new_log_path("error"), "w", encoding="utf-8") as out:
        out.write(f"[{title}] {type(exc).__name__}: {exc}\n")
        out.write("Traceback:\n")
        out.write("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))

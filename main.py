# main.py
import sys, os
sys.path.append(os.path.dirname(__file__))  # 確保能找到 config.py

from utils.crashlog import setup_crashlog, log_exception, log_dir
setup_crashlog()

import argparse
from config import AppConfig, RenderConfig, ReductionConfig, AudioConfig
from app import App
import logging, traceback

def _init_logging():
    logs = log_dir()
    os.makedirs(logs, exist_ok=True)
    log_path = os.path.join(logs, "app.log")

    if logging.getLogger().handlers:
        return

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        encoding="utf-8"
    )
    try:
        from logging.handlers import RotatingFileHandler
        fh = RotatingFileHandler(log_path, maxBytes=2*1024*1024, backupCount=3, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        logging.getLogger().addHandler(fh)
    except Exception:
        pass

def main():
    _init_logging()
    logging.info("應用程式啟動")

    ap = argparse.ArgumentParser()
    ap.add_argument('--pps', type=float, default=280)
    ap.add_argument('--reduction_mode', default='basic', choices=['basic','melody_bass'])
    ap.add_argument('--reduction_vel', type=int, default=1)
    ap.add_argument('--reduction_poly', type=int, default=16)
    ap.add_argument('--slice_ms', type=int, default=40)
    args = ap.parse_args()

    cfg = AppConfig(
        render=RenderConfig(pixels_per_second=args.pps),
        reduce=ReductionConfig(
            min_velocity=args.reduction_vel,
            max_poly_per_slice=args.reduction_poly,
            slice_ms=args.slice_ms,
            mode=args.reduction_mode
        ),
        audio=AudioConfig(sf2_path=None),
    )

    App(cfg, notes=[]).run()

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        try:
            log_exception("Top-level exception", e)
        except Exception:
            pass
        logging.error("未捕捉的例外：%s", e, exc_info=True)
        print("程式發生錯誤，請到 logs/ 資料夾看 app.log 與 error-*.txt")
        traceback.print_exc()

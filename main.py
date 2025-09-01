# ========================= main.py =========================
import sys, os
sys.path.append(os.path.dirname(__file__))  # 確保能找到 config.py
from utils.crashlog import setup_crashlog
setup_crashlog()
import argparse
from config import AppConfig, RenderConfig, ReductionConfig, AudioConfig
from app import App
import logging
import traceback

# 初始化 logging
logging.basicConfig(
    filename="app.log",
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8"
)

def main():
    ap = argparse.ArgumentParser()
    # 參數改為全部可選；啟動後用狀態列的按鈕載入檔案
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
        audio=AudioConfig(sf2_path=None),  # 開始時可先不載音色，之後從 UI 載入
    )

    # 一開始沒有 notes，使用者從 UI 載入
    App(cfg, notes=[]).run()

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        # 捕捉任何例外，寫入 app.log
        logging.error("未捕捉的例外: %s", e, exc_info=True)
        print("程式發生錯誤，請查看 app.log")
        # 可選：也把 traceback 輸出到 console（方便 debug）
        traceback.print_exc()
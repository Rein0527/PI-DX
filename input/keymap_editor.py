# ========================= input/keymap_editor.py =========================
import tkinter as tk
from tkinter import ttk
from typing import Dict, Optional, Tuple
import pygame  # 用於 keysym -> pygame keycode 轉換

FIRST_MIDI, LAST_MIDI = 21, 108
WHITE_SET = {0, 2, 4, 5, 7, 9, 11}

def midi_is_black(p: int) -> bool:
    return (p % 12) not in WHITE_SET

class KeymapEditor(tk.Toplevel):
    """
    視覺化 Keymap 編輯器（Modal）：
    - 滑鼠點某個琴鍵 -> 提示「請按電腦鍵」
    - 按鍵後即完成綁定，紅字顯示在該琴鍵上
    - Done 回傳新的 keymap（pygame keycode -> midi pitch），Cancel 回 None
    """
    def __init__(self, parent, keymap: Dict[int, int]):
        super().__init__(parent)
        self.title("Keymap Editor")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)

        # 將現有 keymap 反轉成 pitch -> [keynames] 方便顯示
        self.kc_to_pitch: Dict[int, int] = dict(keymap)  # 會被更新

        self.selected_pitch: Optional[int] = None
        self.waiting_key = False

        # 介面
        self.info = ttk.Label(self, text="Click a piano key, then press a computer key to bind.",
                              font=("Consolas", 11))
        self.info.pack(padx=10, pady=(10, 6), anchor="w")

        # 畫布
        self.width = 1100
        self.white_h = 120
        self.black_h = int(self.white_h * 0.6)
        self.height = self.white_h + 40  # 上方留文字
        self.canvas = tk.Canvas(self, width=self.width, height=self.height, bg="#0e0e0e", highlightthickness=0)
        self.canvas.pack(padx=10, pady=6)

        # 底部按鈕
        btns = ttk.Frame(self)
        btns.pack(padx=10, pady=(6, 10), fill="x")
        ttk.Button(btns, text="Clear Selected", command=self.clear_selected).pack(side="left")
        ttk.Button(btns, text="Clear All", command=self.clear_all).pack(side="left", padx=(6, 0))
        ttk.Button(btns, text="Done", command=self.on_done).pack(side="right")
        ttk.Button(btns, text="Cancel", command=self.on_cancel).pack(side="right", padx=(0, 6))

        # 幾何資料
        self.white_keys: list[tuple[int, float, float]] = []  # (pitch, x0, x1)
        self.black_keys: list[tuple[int, float, float]] = []  # (pitch, x0, x1)
        self._layout_keys()
        self._redraw()

        # 事件
        self.canvas.bind("<Button-1>", self.on_click)
        self.bind("<Key>", self.on_key)             # 專門吃鍵盤
        self.canvas.focus_set()                     # 聚焦在本窗
        self.focus_force()                          # 強制把焦點拉過來（避免你說的「當機/無反應」）
        self.transient(parent)
        self.grab_set()                             # Modal：鎖定本窗

        self.result: Optional[Dict[int, int]] = None

    # ---------- 幾何與繪製 ----------
    def _layout_keys(self):
        total_white = sum(1 for p in range(FIRST_MIDI, LAST_MIDI + 1) if (p % 12) in WHITE_SET)
        white_w = self.width / total_white

        # 白鍵
        x = 0.0
        for p in range(FIRST_MIDI, LAST_MIDI + 1):
            if (p % 12) in WHITE_SET:
                self.white_keys.append((p, x, x + white_w))
                x += white_w

        # 黑鍵（放在相鄰白鍵之間）
        idx_white = 0
        for p in range(FIRST_MIDI, LAST_MIDI + 1):
            pc = p % 12
            if pc in WHITE_SET:
                if pc in {0, 2, 5, 7, 9} and idx_white + 1 < len(self.white_keys):  # C D F G A 右側有黑鍵
                    left_white_x0 = self.white_keys[idx_white][1]
                    right_white_x0 = self.white_keys[idx_white + 1][1]
                    white_w = right_white_x0 - left_white_x0
                    bx = left_white_x0 + white_w * 0.7
                    bw = white_w * 0.6
                    self.black_keys.append((p + 1, bx, bx + bw))  # p+1 為對應黑鍵
                idx_white += 1

    def _redraw(self):
        self.canvas.delete("all")
        # 背景
        self.canvas.create_rectangle(0, 0, self.width, self.height, fill="#0e0e0e", width=0)
        # 白鍵
        for p, x0, x1 in self.white_keys:
            fill = "#ffdca8" if self.selected_pitch == p else "#e6e6e6"
            self.canvas.create_rectangle(x0, self.height - self.white_h, x1, self.height,
                                         fill=fill, outline="#333333")
        # 黑鍵
        for p, x0, x1 in self.black_keys:
            fill = "#ffb86b" if self.selected_pitch == p else "#121214"
            self.canvas.create_rectangle(x0, self.height - self.white_h, x1, self.height - self.white_h + self.black_h,
                                         fill=fill, outline="#444444")

        # 顯示已綁定鍵名（紅字）
        for kc, pitch in self.kc_to_pitch.items():
            name = pygame.key.name(kc)
            x, y = self._label_anchor(pitch)
            if x is not None:
                self.canvas.create_text(x, y, text=name, fill="#e74c3c", font=("Consolas", 12, "bold"))

        # 提示
        tip = "Click a piano key, then press a computer key…"
        if self.waiting_key and self.selected_pitch is not None:
            tip = f"Selected pitch {self.selected_pitch} • Press a computer key to bind"
        self.canvas.create_text(10, 14, text=tip, fill="#c8c8d0", anchor="w", font=("Consolas", 11))

    def _label_anchor(self, pitch: int) -> Tuple[Optional[float], Optional[float]]:
        for p, x0, x1 in self.black_keys:
            if p == pitch:
                return (x0 + x1) / 2, self.height - self.white_h - 8
        for p, x0, x1 in self.white_keys:
            if p == pitch:
                return (x0 + x1) / 2, self.height - 18
        return None, None

    # ---------- 互動 ----------
    def on_click(self, event):
        x, y = event.x, event.y
        # 先測黑鍵
        if self.height - self.white_h <= y <= self.height - self.white_h + self.black_h:
            for p, x0, x1 in self.black_keys:
                if x0 <= x <= x1:
                    self.selected_pitch = p
                    self.waiting_key = True
                    self._redraw()
                    return
        # 再測白鍵
        for p, x0, x1 in self.white_keys:
            if x0 <= x <= x1:
                self.selected_pitch = p
                self.waiting_key = True
                self._redraw()
                return

    def on_key(self, event):
        if not self.waiting_key or self.selected_pitch is None:
            return
        keysym = event.keysym  # 'a', 'comma', 'Shift_L', ...
        # Tk -> pygame keycode 嘗試對應
        name_map = {
            "Shift_L": "shift", "Shift_R": "shift",
            "Control_L": "ctrl", "Control_R": "ctrl",
            "Alt_L": "alt", "Alt_R": "alt",
            "Return": "return", "BackSpace": "backspace",
            "Escape": "escape", "space": "space",
        }
        name = name_map.get(keysym, keysym).lower()
        try:
            kc = pygame.key.key_code(name)
        except Exception:
            return  # 不支援/未知鍵：忽略

        # 綁定
        self.kc_to_pitch[kc] = self.selected_pitch
        self.waiting_key = False
        self.selected_pitch = None
        self._redraw()

    def clear_selected(self):
        if self.selected_pitch is None:
            return
        to_del = [kc for kc, p in self.kc_to_pitch.items() if p == self.selected_pitch]
        for kc in to_del:
            del self.kc_to_pitch[kc]
        self.waiting_key = False
        self._redraw()

    def clear_all(self):
        self.kc_to_pitch.clear()
        self.waiting_key = False
        self._redraw()

    def on_done(self):
        self.result = dict(self.kc_to_pitch)
        self.destroy()

    def on_cancel(self):
        self.result = None
        self.destroy()

    def show(self) -> Optional[Dict[int, int]]:
        self.wait_window(self)  # modal 等待
        return self.result

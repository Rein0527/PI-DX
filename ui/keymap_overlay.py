# ui/keymap_overlay.py
import pygame
from typing import Dict, Optional, Tuple

WHITE_SET = {0, 2, 4, 5, 7, 9, 11}

class KeymapOverlay:
    """Keymap 編輯器：新增 Save KM / Load KM 按鈕，透過旗標通知 App。"""
    def __init__(self, screen_size: Tuple[int, int], current_keymap: Dict[int, int],
                 first_midi: int = 21, last_midi: int = 108):
        self.w, self.h = screen_size
        self.first_midi, self.last_midi = first_midi, last_midi

        self.active = True
        self.finished = False
        self.cancelled = False
        self.result_keymap: Optional[Dict[int, int]] = None

        self.kc_to_pitch: Dict[int, int] = dict(current_keymap)
        self.selected_pitch: Optional[int] = None
        self.waiting_key = False

        # 供 App 查詢的請求旗標
        self.want_save = False
        self.want_load = False

        self.panel_w = int(self.w * 0.94)
        self.panel_h = 260
        self.panel_x = (self.w - self.panel_w) // 2
        self.panel_y = (self.h - self.panel_h) // 2

        self.piano_margin = 16
        self.white_h = 120
        self.black_h = int(self.white_h * 0.6)
        self.piano_y0 = self.panel_y + 84
        self.piano_y1 = self.piano_y0 + self.white_h
        self.piano_w = self.panel_w - self.piano_margin * 2
        self.piano_x0 = self.panel_x + self.piano_margin

        # 按鈕列（左到右）
        self.btn_save      = pygame.Rect(self.panel_x + 16,  self.panel_y + 20, 90, 30)
        self.btn_load      = pygame.Rect(self.panel_x + 112, self.panel_y + 20, 90, 30)
        self.btn_clear_sel = pygame.Rect(self.panel_x + 216, self.panel_y + 20, 130, 30)
        self.btn_clear_all = pygame.Rect(self.panel_x + 352, self.panel_y + 20, 120, 30)
        self.btn_done      = pygame.Rect(self.panel_x + self.panel_w - 200, self.panel_y + 20, 80, 30)
        self.btn_cancel    = pygame.Rect(self.panel_x + self.panel_w - 110, self.panel_y + 20, 80, 30)

        self.white_keys: list[tuple[int, float, float]] = []
        self.black_keys: list[tuple[int, float, float]] = []
        self._layout_keys()

        self.font       = pygame.font.SysFont("consolas", 16)
        self.font_small = pygame.font.SysFont("consolas", 14)
        self.font_bold  = pygame.font.SysFont("consolas", 16, bold=True)

    # ---- 幾何 ----
    def _layout_keys(self):
        total_white = sum(1 for p in range(self.first_midi, self.last_midi + 1) if (p % 12) in WHITE_SET)
        white_w = self.piano_w / max(1, total_white)
        x = self.piano_x0
        for p in range(self.first_midi, self.last_midi + 1):
            if (p % 12) in WHITE_SET:
                self.white_keys.append((p, x, x + white_w))
                x += white_w
        idx_white = 0
        for p in range(self.first_midi, self.last_midi + 1):
            pc = p % 12
            if pc in WHITE_SET:
                if pc in {0, 2, 5, 7, 9} and idx_white + 1 < len(self.white_keys):
                    left_x0 = self.white_keys[idx_white][1]
                    right_x0 = self.white_keys[idx_white + 1][1]
                    ww = right_x0 - left_x0
                    bx = left_x0 + ww * 0.7
                    bw = ww * 0.6
                    self.black_keys.append((p + 1, bx, bx + bw))
                idx_white += 1

    # ---- 事件 ----
    def handle_event(self, e: pygame.event.Event):
        if not self.active:
            return
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            mx, my = e.pos
            # 功能鍵
            if self.btn_save.collidepoint(mx, my):
                self.want_save = True;  return
            if self.btn_load.collidepoint(mx, my):
                self.want_load = True;  return
            if self.btn_clear_sel.collidepoint(mx, my):
                self._clear_selected();  return
            if self.btn_clear_all.collidepoint(mx, my):
                self.kc_to_pitch.clear(); return
            if self.btn_done.collidepoint(mx, my):
                self.finished = True; self.active = False
                self.result_keymap = dict(self.kc_to_pitch); return
            if self.btn_cancel.collidepoint(mx, my):
                self.cancelled = True; self.active = False; return

            # 點擊琴鍵
            if self.piano_y0 <= my <= self.piano_y0 + self.black_h:
                for p, x0, x1 in self.black_keys:
                    if x0 <= mx <= x1:
                        self.selected_pitch = p; self.waiting_key = True; return
            if self.piano_y0 <= my <= self.piano_y1:
                for p, x0, x1 in self.white_keys:
                    if x0 <= mx <= x1:
                        self.selected_pitch = p; self.waiting_key = True; return

        if e.type == pygame.KEYDOWN and self.waiting_key and self.selected_pitch is not None:
            self.kc_to_pitch[e.key] = self.selected_pitch
            self.waiting_key = False
            self.selected_pitch = None

    def update(self, dt: float): pass

    # ---- 繪製 ----
    def draw(self, surface: pygame.Surface):
        mask = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        mask.fill((0, 0, 0, 140))
        surface.blit(mask, (0, 0))

        pygame.draw.rect(surface, (30, 32, 36),
                         (self.panel_x, self.panel_y, self.panel_w, self.panel_h), border_radius=10)
        pygame.draw.rect(surface, (80, 80, 90),
                         (self.panel_x, self.panel_y, self.panel_w, self.panel_h), 1, border_radius=10)

        # 按鈕
        self._draw_button(surface, self.btn_save, "Save KM")
        self._draw_button(surface, self.btn_load, "Load KM")
        self._draw_button(surface, self.btn_clear_sel, "Clear Selected")
        self._draw_button(surface, self.btn_clear_all, "Clear All")
        self._draw_button(surface, self.btn_done, "Done")
        self._draw_button(surface, self.btn_cancel, "Cancel")

        tip = "Click a piano key, then press a computer key to bind"
        if self.waiting_key and self.selected_pitch is not None:
            tip = f"Selected pitch {self.selected_pitch} — press a computer key…"
        txt = self.font.render(tip, True, (230, 230, 235))
        surface.blit(txt, (self.panel_x + 16, self.panel_y + 58))

        # 鍵盤
        for p, x0, x1 in self.white_keys:
            fill = (230, 230, 230) if self.selected_pitch != p else (255, 220, 168)
            pygame.draw.rect(surface, fill, (x0, self.piano_y0, x1 - x0 - 1, self.white_h))
            pygame.draw.rect(surface, (50, 50, 56), (x0, self.piano_y0, x1 - x0 - 1, self.white_h), 1)
        for p, x0, x1 in self.black_keys:
            fill = (18, 18, 20) if self.selected_pitch != p else (255, 184, 107)
            pygame.draw.rect(surface, fill, (x0, self.piano_y0, x1 - x0, self.black_h))
            pygame.draw.rect(surface, (60, 60, 66), (x0, self.piano_y0, x1 - x0, self.black_h), 1)

        # 綁定標籤
        for kc, pitch in self.kc_to_pitch.items():
            name = pygame.key.name(kc)
            cx, cy = self._label_anchor(pitch)
            if cx is not None:
                text = self.font_bold.render(name, True, (231, 76, 60))
                surface.blit(text, (cx - text.get_width()/2, cy - text.get_height()/2))

    def _label_anchor(self, pitch: int) -> Tuple[Optional[float], Optional[float]]:
        for p, x0, x1 in self.black_keys:
            if p == pitch:
                return (x0 + x1) / 2, self.piano_y0 - 10
        for p, x0, x1 in self.white_keys:
            if p == pitch:
                return (x0 + x1) / 2, self.piano_y1 - 16
        return None, None

    def _clear_selected(self):
        if self.selected_pitch is None: return
        to_del = [kc for kc, p in self.kc_to_pitch.items() if p == self.selected_pitch]
        for kc in to_del: del self.kc_to_pitch[kc]
        self.waiting_key = False

    def _draw_button(self, surface: pygame.Surface, rect: pygame.Rect, label: str):
        pygame.draw.rect(surface, (46, 48, 54), rect, border_radius=6)
        pygame.draw.rect(surface, (85, 88, 96), rect, 1, border_radius=6)
        t = self.font_small.render(label, True, (220, 220, 230))
        surface.blit(t, (rect.x + (rect.w - t.get_width()) // 2, rect.y + (rect.h - t.get_height()) // 2))

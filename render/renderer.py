# render/renderer.py
import os, pygame, logging
from bisect import bisect_left, bisect_right
from notes.model import Note
from config import RenderConfig

STATUS_H = 36
BTN_PAD_X = 12
BTN_GAP = 10
WHITE_SET = {0, 2, 4, 5, 7, 9, 11}

class Renderer:
    def __init__(self, cfg: RenderConfig):
        pygame.init()
        self.cfg = cfg
        self.screen = pygame.display.set_mode((cfg.window_w, cfg.window_h))
        pygame.display.set_caption("piano→IIDX")
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "..", "static", "img", "icon", "icon.png")
            pygame.display.set_icon(pygame.image.load(icon_path))
        except Exception as e:
            print("[WARN] set_icon failed:", e)
        self.font = pygame.font.SysFont("consolas", 18)
        self.font_small = pygame.font.SysFont("consolas", 14)
        self.clock = pygame.time.Clock()
        self.button_rects = {}

        self.marquee_offset = 0.0
        self.marquee_speed = 80.0
        self.marquee_gap = 48
        self._last_tick_ms = pygame.time.get_ticks()

        self.first_midi = 21
        self.last_midi = 108
        self.total_white = 1
        self.white_w = float(self.cfg.window_w)
        self.white_left_edges = []
        self.white_index_by_pitch = {}
        self.xw_by_pitch = {}

        self.set_key_range(self.cfg.key_range)

    def _rebuild_layout(self):
        try:
            whites = [p for p in range(self.first_midi, self.last_midi + 1) if (p % 12) in WHITE_SET]
            self.total_white = len(whites) or 1
            self.white_w = float(self.cfg.window_w) / float(self.total_white)

            self.white_left_edges = []
            x = 0.0
            for _ in whites:
                self.white_left_edges.append(x); x += self.white_w

            self.white_index_by_pitch = {}
            idx = 0
            for p in range(self.first_midi, self.last_midi + 1):
                if (p % 12) in WHITE_SET:
                    idx += 1
                self.white_index_by_pitch[p] = idx

            self.xw_by_pitch = {}
            for p in range(self.first_midi, self.last_midi + 1):
                idx = self.white_index_by_pitch[p]
                base_x = max(0, idx - 1) * self.white_w
                is_black = (p % 12) not in WHITE_SET
                if is_black:
                    x = base_x + self.white_w * 0.7; w = self.white_w * 0.6
                else:
                    x = base_x; w = self.white_w - 1
                self.xw_by_pitch[p] = (int(x), int(w), is_black)

            logging.debug("Keyboard layout rebuilt: range=[%d,%d], total_white=%d, white_w=%.3f",
                          self.first_midi, self.last_midi, self.total_white, self.white_w)
        except Exception:
            logging.exception("重建鍵盤版面失敗")
            self.total_white = max(1, self.total_white)
            self.white_w = float(self.cfg.window_w) / float(self.total_white)

    def _ensure_layout_fresh(self):
        current_total_width = self.white_w * self.total_white
        if abs(current_total_width - float(self.cfg.window_w)) > 0.5:
            self._rebuild_layout()

    def set_key_range(self, mode: str):
        if str(mode) == "76":   self.first_midi, self.last_midi = 28, 103
        elif str(mode) == "61": self.first_midi, self.last_midi = 36, 96
        else:                   self.first_midi, self.last_midi = 21, 108
        self._rebuild_layout()

    def tick(self, fps=60) -> float:
        return self.clock.tick(fps) / 1000.0

    def begin_frame(self):
        self.screen.fill((12, 12, 14))
        self._ensure_layout_fresh()

    def end_frame(self):
        pygame.display.flip()

    def draw_status_bar(self, right_info_text: str = "", song_title: str = ""):
        now = pygame.time.get_ticks()
        dt = (now - self._last_tick_ms) / 1000.0
        self._last_tick_ms = now
        self.marquee_offset = (self.marquee_offset + self.marquee_speed * dt) % 1_000_000

        pygame.draw.rect(self.screen, (24, 24, 28), (0, 0, self.cfg.window_w, STATUS_H))
        pygame.draw.line(self.screen, (60, 60, 66), (0, STATUS_H), (self.cfg.window_w, STATUS_H), 1)

        buttons = ["LOAD MIDI", "KEYMAP", "PLAY/PAUSE", "AUTO SOUND", "SPEED", "KEY RANGE", "QUIT"]
        x = 10; self.button_rects.clear()
        for label in buttons:
            surf = self.font_small.render(label, True, (220, 220, 230))
            rect = surf.get_rect(); rect.topleft = (x + BTN_PAD_X, (STATUS_H - rect.height)//2)
            box = pygame.Rect(x, 4, rect.width + BTN_PAD_X*2, STATUS_H - 8)
            pygame.draw.rect(self.screen, (40, 40, 46), box, border_radius=6)
            pygame.draw.rect(self.screen, (75, 75, 85), box, 1, border_radius=6)
            self.screen.blit(surf, rect)
            self.button_rects[label] = box
            x += box.width + BTN_GAP
        buttons_end_x = x

        right_w = 0
        if right_info_text:
            right = self.font_small.render(right_info_text, True, (180, 180, 190))
            right_w = right.get_width()
            self.screen.blit(right, (self.cfg.window_w - right_w - 10, (STATUS_H - right.get_height())//2))

        area_x = buttons_end_x + 6
        area_w = max(0, self.cfg.window_w - right_w - 20 - area_x)
        if area_w > 50 and song_title:
            area_rect = pygame.Rect(area_x, 4, area_w, STATUS_H - 8)
            pygame.draw.rect(self.screen, (34, 34, 40), area_rect, border_radius=6)
            pygame.draw.rect(self.screen, (70, 70, 80), area_rect, 1, border_radius=6)
            sep = "   •   "
            text = song_title + sep
            surf = self.font_small.render(text, True, (220, 220, 230))
            tw = surf.get_width()
            if tw > 0:
                scroll = self.marquee_offset % (tw + self.marquee_gap)
                start_x = area_rect.x - scroll
                clip_prev = self.screen.get_clip()
                self.screen.set_clip(area_rect)
                x_draw = start_x
                while x_draw < area_rect.right:
                    self.screen.blit(surf, (x_draw, (STATUS_H - surf.get_height())//2))
                    x_draw += tw + self.marquee_gap
                self.screen.set_clip(clip_prev)

    # ------- piano -------
    def draw_keyboard(self, highlight: set[int] | None = None):
        highlight = highlight or set()
        w, h, ph = self.cfg.window_w, self.cfg.window_h, self.cfg.piano_h
        pygame.draw.rect(self.screen, (28, 28, 32), (0, h - ph, w, ph))

        x = 0.0
        whites = [p for p in range(self.first_midi, self.last_midi + 1) if (p % 12) in WHITE_SET]
        for p in whites:
            fill = (230, 230, 230) if p not in highlight else (255, 240, 170)
            pygame.draw.rect(self.screen, fill, (x, h - ph, self.white_w - 1, ph))
            pygame.draw.rect(self.screen, (60, 60, 66), (x, h - ph, self.white_w - 1, ph), 1)
            x += self.white_w

        idx_white = 0
        for p in range(self.first_midi, self.last_midi + 1):
            pc = p % 12
            if pc in WHITE_SET:
                if pc in {0, 2, 5, 7, 9} and idx_white + 1 < len(self.white_left_edges):
                    left = self.white_left_edges[idx_white]
                    bw = self.white_w * 0.6; bh = ph * 0.6
                    bx = left + self.white_w * 0.7; by = h - ph
                    fill = (18, 18, 20) if (p + 1) not in highlight else (255, 200, 120)
                    pygame.draw.rect(self.screen, fill, (bx, by, bw, bh))
                    pygame.draw.rect(self.screen, (60, 60, 66), (bx, by, bw, bh), 1)
                idx_white += 1

        hit_y = h - ph - 6
        pygame.draw.line(self.screen, (90, 90, 90), (0, hit_y), (w, hit_y), 2)

    def pitch_to_xw(self, pitch: int):
        try:
            return self.xw_by_pitch[pitch]
        except KeyError:
            logging.warning("pitch_to_xw: pitch=%r 超出範圍 [%d, %d]，將進行 clamp",
                            pitch, self.first_midi, self.last_midi)
            p = min(max(pitch, self.first_midi), self.last_midi)
            return self.xw_by_pitch[p]

    # ------- notes -------
    def draw_notes(self, notes_sorted: list[Note], note_starts: list[float], time_s: float):
        if not notes_sorted:
            return
        hit_y = self.cfg.window_h - self.cfg.piano_h - 6
        pps = self.cfg.pixels_per_second
        visible_from = time_s - 0.1
        visible_to = time_s + (self.cfg.window_h - STATUS_H) / max(1e-6, pps)

        end_idx = bisect_right(note_starts, visible_to + 0.05)
        LOOKBACK = 8.0
        start_probe = max(0.0, visible_from - LOOKBACK)
        start_idx = bisect_left(note_starts, start_probe)

        for i in range(start_idx, end_idx):
            n = notes_sorted[i]
            if n.end < visible_from:
                continue
            try:
                x, w, is_black = self.pitch_to_xw(n.pitch)
            except Exception:
                logging.error("單一音符繪製失敗，跳過該音符：%r", n, exc_info=True)
                continue
            y_start = hit_y - (n.start - time_s) * pps
            h = n.dur * pps
            color = (90, 160, 255) if is_black else (80, 200, 120)
            pygame.draw.rect(self.screen, color, (x, y_start - h, w, h), border_radius=6)

    def hud(self, t: float):
        surf = self.font.render(
            f"t={t:6.2f}s  speed={self.cfg.pixels_per_second:.0f}px/s  range={self.cfg.key_range}",
            True, (200, 200, 210)
        )
        self.screen.blit(surf, (10, STATUS_H + 6))

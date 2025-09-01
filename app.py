# app.py
import json, heapq
import pygame
from typing import List, Optional, Dict
from bisect import bisect_right
from config import AppConfig
from notes.model import Note
from render.renderer import Renderer, STATUS_H
from audio.synth import Synth
from input.keymap import DEFAULT_KEYMAP, serialize_keymap, deserialize_keymap
from ui.keymap_overlay import KeymapOverlay
from midi.parser import parse_midi_to_notes
from utils.crashlog import log_exception

POLYPHONY_LIMIT = 24  # 限制自動播放同時活躍音數（以 token 計）

def pick_file_dialog(title: str, patterns: list[tuple[str, str]]) -> Optional[str]:
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk(); root.withdraw()
        file = filedialog.askopenfilename(title=title, filetypes=patterns)
        root.update(); root.destroy()
        return file or None
    except Exception:
        return None

def save_file_dialog(title: str, default_ext: str, patterns: list[tuple[str, str]]) -> Optional[str]:
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk(); root.withdraw()
        file = filedialog.asksaveasfilename(title=title, defaultextension=default_ext, filetypes=patterns)
        root.update(); root.destroy()
        return file or None
    except Exception:
        return None

class App:
    def __init__(self, cfg: AppConfig, notes: List[Note]):
        self.cfg = cfg
        self.renderer = Renderer(cfg.render)
        self.synth = Synth(cfg.audio)

        self.notes: List[Note] = notes
        self.notes_sorted: List[Note] = sorted(notes, key=lambda n: n.start)
        self.note_starts: List[float] = [n.start for n in self.notes_sorted]

        self.time = 0.0
        self.is_playing = False
        self.auto_sound = False

        self.playing: set[int] = set()             # 用於鍵盤高亮
        self._playing_counts: Dict[int, int] = {}  # pitch -> 疊加次數
        self._active_heap: list[tuple[float, int|None, int, int]] = []  # (end, token, pitch, vel)
        self._active_tokens: int = 0               # 現在活躍 token 數

        self.current_midi: Optional[str] = None
        self.keymap: Dict[int, int] = dict(DEFAULT_KEYMAP)
        self.highlight_pitches: set[int] = set()
        self._key_token: Dict[int, int] = {}       # keycode -> token（手動彈鍵）

        self.overlay: Optional[KeymapOverlay] = None

        self.playback_rates = [0.5, 0.75, 1.0, 1.25, 1.5]
        self.playback_idx = 2  # 100%

        self._next_on_idx = 0
        self._msg = ""; self._msg_time = 0.0

    def _toast(self, msg: str, secs: float = 4.0):
        self._msg = msg
        self._msg_time = max(self._msg_time, secs)

    def load_midi_interactive(self):
        path = pick_file_dialog("Select a MIDI file", [("MIDI files", "*.mid *.midi"), ("All files", "*.*")])
        if not path: return False
        try:
            notes, _ = parse_midi_to_notes(path)
            from notes.reduction import make_reduction
            reducer = make_reduction(self.cfg.reduce.mode)
            notes = reducer.apply(notes, self.cfg.reduce)

            self.notes = notes
            self.notes_sorted = sorted(notes, key=lambda n: n.start)
            self.note_starts = [n.start for n in self.notes_sorted]

            self.current_midi = path
            self.time = 0.0
            self._stop_all()
            self.is_playing = False
            self._next_on_idx = 0
            self._active_heap.clear()
            self._toast("Loaded MIDI ✓", 2.0)
            return True
        except Exception as e:
            log_exception("load_midi_interactive", e)
            self.current_midi = None
            self._toast("Failed to load MIDI (see logs)", 6.0)
            return False

    def load_sf2_interactive(self):
        return False  # 保留接口

    def open_keymap_overlay(self):
        self.is_playing = False
        self.overlay = KeymapOverlay(
            (self.renderer.cfg.window_w, self.renderer.cfg.window_h),
            self.keymap,
            first_midi=self.renderer.first_midi,
            last_midi=self.renderer.last_midi
        )

    def save_keymap_json(self, mapping: Optional[Dict[int, int]] = None):
        path = save_file_dialog("Save Keymap JSON", ".json", [("JSON", "*.json"), ("All files", "*.*")])
        if not path: return False
        try:
            m = mapping if mapping is not None else self.keymap
            with open(path, "w", encoding="utf-8") as f:
                json.dump(serialize_keymap(m), f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def load_keymap_json(self) -> Optional[Dict[int, int]]:
        path = pick_file_dialog("Load Keymap JSON", [("JSON", "*.json"), ("All files", "*.*")])
        if not path: return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                obj = json.load(f)
            return deserialize_keymap(obj)
        except Exception:
            return None

    def _stop_all(self):
        # 關掉所有聲音
        self.synth.all_notes_off()
        self.playing.clear()
        self.highlight_pitches.clear()
        self._playing_counts.clear()
        self._active_heap.clear()
        self._active_tokens = 0

    def _adjust_speed(self, delta: float):
        new_pps = self.renderer.cfg.pixels_per_second + delta
        new_pps = max(60.0, min(1200.0, new_pps))
        self.renderer.cfg.pixels_per_second = new_pps

    def run(self):
        running = True
        while running:
            dt = self.renderer.tick(60)
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self._stop_all(); running = False

                if self.overlay and self.overlay.active:
                    self.overlay.handle_event(e)
                    continue

                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_SPACE:
                        self.is_playing = not self.is_playing; continue

                    if e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        self.auto_sound = not self.auto_sound
                        if not self.auto_sound:
                            self._stop_all()
                        continue

                    if e.key in (pygame.K_KP_PLUS, getattr(pygame, "K_PLUS", pygame.K_EQUALS)):
                        mods = pygame.key.get_mods()
                        if e.key != pygame.K_EQUALS or (mods & pygame.KMOD_SHIFT):
                            self._adjust_speed(+20); continue
                    if e.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                        self._adjust_speed(-20); continue

                    # 手動演奏鍵
                    if e.key in self.keymap:
                        pitch = self.keymap[e.key]
                        self.highlight_pitches.add(pitch)
                        tok = self.synth.note_on(pitch, 110)
                        if tok is not None:
                            self._key_token[e.key] = tok

                if e.type == pygame.KEYUP:
                    if e.key not in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER) and e.key in self.keymap:
                        pitch = self.keymap[e.key]
                        self.highlight_pitches.discard(pitch)
                        tok = self._key_token.pop(e.key, None)
                        if tok is not None:
                            self.synth.note_off_token(tok)
                        else:
                            self.synth.note_off(pitch)

                if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    mx, my = e.pos
                    if my <= STATUS_H:
                        for label, rect in self.renderer.button_rects.items():
                            if rect.collidepoint(mx, my):
                                if label == "LOAD MIDI":
                                    self.load_midi_interactive()
                                elif label == "KEYMAP":
                                    self.open_keymap_overlay()
                                elif label == "PLAY/PAUSE":
                                    self.is_playing = not self.is_playing
                                elif label == "AUTO SOUND":
                                    self.auto_sound = not self.auto_sound
                                    if not self.auto_sound:
                                        self._stop_all()
                                elif label == "SPEED":
                                    self.playback_idx = (self.playback_idx + 1) % len(self.playback_rates)
                                elif label == "KEY RANGE":
                                    if self.renderer.cfg.key_range == "88":
                                        self.renderer.cfg.key_range = "76"
                                    elif self.renderer.cfg.key_range == "76":
                                        self.renderer.cfg.key_range = "61"
                                    else:
                                        self.renderer.cfg.key_range = "88"
                                    self.renderer.set_key_range(self.renderer.cfg.key_range)
                                    self._stop_all()
                                elif label == "QUIT":
                                    self._stop_all(); running = False

            if not running: break

            # toast
            if self._msg_time > 0:
                self._msg_time -= dt
                if self._msg_time <= 0:
                    self._msg_time = 0; self._msg = ""

            # keymap overlay Save/Load
            if self.overlay:
                self.overlay.update(dt)
                if getattr(self.overlay, "want_save", False):
                    self.save_keymap_json(mapping=self.overlay.kc_to_pitch); self.overlay.want_save = False
                if getattr(self.overlay, "want_load", False):
                    loaded = self.load_keymap_json()
                    if loaded is not None: self.overlay.kc_to_pitch = loaded
                    self.overlay.want_load = False
                if self.overlay.finished:
                    if self.overlay.result_keymap is not None:
                        self.keymap = self.overlay.result_keymap
                    self.overlay = None
                elif self.overlay.cancelled:
                    self.overlay = None

            # ===== 時間軸播放（token 精準關閉） =====
            if (not self.overlay) and self.is_playing and self.notes_sorted:
                prev_t = self.time
                self.time += dt * self.playback_rates[self.playback_idx]
                tol = 0.003

                while self._next_on_idx < len(self.notes_sorted) and \
                      self.notes_sorted[self._next_on_idx].start <= self.time + tol:
                    n = self.notes_sorted[self._next_on_idx]
                    tok = None
                    if self.auto_sound and self._active_tokens < POLYPHONY_LIMIT:
                        tok = self.synth.note_on(n.pitch, max(10, min(120, n.velocity)))
                        if tok is not None:
                            self._active_tokens += 1
                    self._playing_counts[n.pitch] = self._playing_counts.get(n.pitch, 0) + 1
                    self.playing.add(n.pitch)
                    heapq.heappush(self._active_heap, (n.end, tok, n.pitch, n.velocity))
                    self._next_on_idx += 1

                while self._active_heap and self._active_heap[0][0] < self.time - tol:
                    end, tok, pitch, _ = heapq.heappop(self._active_heap)
                    if self.auto_sound and tok is not None:
                        self.synth.note_off_token(tok)
                        if self._active_tokens > 0:
                            self._active_tokens -= 1
                    elif self.auto_sound:
                        self.synth.note_off(pitch)

                    cnt = self._playing_counts.get(pitch, 0)
                    if cnt <= 1:
                        self._playing_counts.pop(pitch, None)
                        self.playing.discard(pitch)
                    else:
                        self._playing_counts[pitch] = cnt - 1

            # ----- Render -----
            self.renderer.begin_frame()
            song_title = self.current_midi.split('/')[-1] if self.current_midi else ""
            right_fields = [
                f"PLAY: {'ON' if self.is_playing else 'OFF'}",
                f"AUTO SOUND: {'ON' if self.auto_sound else 'OFF'}",
                f"SPEED: {int(self.playback_rates[self.playback_idx]*100)}%",
                f"RANGE: {self.renderer.cfg.key_range}",
                f"KEYS: {len(self.keymap)}",
            ]
            if self._msg: right_fields.append(self._msg)
            right_info = "  |  ".join(right_fields)

            self.renderer.draw_status_bar(right_info_text=right_info, song_title=song_title)
            highlight = set(self.highlight_pitches) | (set(self.playing) if self.auto_sound else set())
            self.renderer.draw_notes(self.notes_sorted, self.note_starts, self.time)
            self.renderer.draw_keyboard(highlight=highlight)

            if self.overlay and self.overlay.active:
                self.overlay.draw(self.renderer.screen)
            self.renderer.end_frame()

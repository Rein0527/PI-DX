# ========================= app.py =========================
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

POLYPHONY_LIMIT = 24  # 自動發聲同時最多幾個音，避免爆裝置

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
        
        #時間變數
        self.playback_rates = [0.5, 0.75, 1.0, 1.25, 1.5]
        self.playback_idx = 1  # 預設 100%
        
        self.time = 0.0
        self.is_playing = False
        self.auto_sound = False
        self.playing: set[int] = set()
        self.current_midi: Optional[str] = None
        self.keymap: Dict[int, int] = dict(DEFAULT_KEYMAP)
        self.highlight_pitches: set[int] = set()
        self.overlay: Optional[KeymapOverlay] = None

        # 時間軸觸發指標與最小堆（依 note.end 排序）
        self._next_on_idx = 0
        self._active_heap: list[tuple[float, int, int]] = []  # (end, pitch, vel)

    # ---------- Loading ----------
    def load_midi_interactive(self):
        path = pick_file_dialog("Select a MIDI file", [("MIDI files", "*.mid *.midi"), ("All files", "*.*")])
        if not path:
            return False
        notes, _ = parse_midi_to_notes(path)
        from notes.reduction import make_reduction
        reducer = make_reduction(self.cfg.reduce.mode)
        notes = reducer.apply(notes, self.cfg.reduce)

        # 建索引
        self.notes = notes
        self.notes_sorted = sorted(notes, key=lambda n: n.start)
        self.note_starts = [n.start for n in self.notes_sorted]

        self.current_midi = path
        self.time = 0.0
        self._stop_all()
        self.is_playing = False
        self._next_on_idx = 0
        self._active_heap.clear()
        return True

    def load_sf2_interactive(self):
        return False  # 使用系統 MIDI

    # ---------- Keymap ----------
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

    # ---------- Audio / state ----------
    def _stop_all(self):
        for p in list(self.playing):
            if self.auto_sound:
                self.synth.note_off(p)
        self.playing.clear()
        self.highlight_pitches.clear()
        self._active_heap.clear()

    def _adjust_speed(self, delta: float):
        new_pps = self.renderer.cfg.pixels_per_second + delta
        new_pps = max(60.0, min(1200.0, new_pps))
        self.renderer.cfg.pixels_per_second = new_pps

    # ---------- Main loop ----------
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
                            for p in list(self.playing): self.synth.note_off(p)
                        continue
                    if e.key in (pygame.K_KP_PLUS, getattr(pygame, "K_PLUS", pygame.K_EQUALS)):
                        mods = pygame.key.get_mods()
                        if e.key != pygame.K_EQUALS or (mods & pygame.KMOD_SHIFT):
                            self._adjust_speed(+20); continue
                    if e.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                        self._adjust_speed(-20); continue
                    if e.key in self.keymap:
                        pitch = self.keymap[e.key]
                        self.highlight_pitches.add(pitch)
                        self.synth.note_on(pitch, 110)

                if e.type == pygame.KEYUP:
                    if e.key not in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER) and e.key in self.keymap:
                        pitch = self.keymap[e.key]
                        self.highlight_pitches.discard(pitch)
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
                                        for p in list(self.playing): self.synth.note_off(p)
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

            # Overlay 的檔案操作
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

            # ===== 高效時間軸播放（不掃全曲） =====
            if (not self.overlay) and self.is_playing and self.notes_sorted:
                prev_t = self.time
                #self.time += dt
                self.time += dt * self.playback_rates[self.playback_idx]
                tol = 0.003

                # Note ON：把 start 落在 (prev_t, time] 的事件依序觸發
                while self._next_on_idx < len(self.notes_sorted) and \
                      self.notes_sorted[self._next_on_idx].start <= self.time + tol:
                    n = self.notes_sorted[self._next_on_idx]
                    # 控制自動發聲的多音數上限
                    if self.auto_sound and len(self.playing) < POLYPHONY_LIMIT:
                        self.synth.note_on(n.pitch, max(10, min(120, n.velocity)))
                    self.playing.add(n.pitch)
                    heapq.heappush(self._active_heap, (n.end, n.pitch, n.velocity))
                    self._next_on_idx += 1

                # Note OFF：把 end < time 的都關掉
                while self._active_heap and self._active_heap[0][0] < self.time - tol:
                    end, pitch, _ = heapq.heappop(self._active_heap)
                    if self.auto_sound: self.synth.note_off(pitch)
                    self.playing.discard(pitch)

            # ----- Render -----
            self.renderer.begin_frame()
            song_title = self.current_midi.split('/')[-1] if self.current_midi else ""
            right_info = "  |  ".join([
                f"PLAY: {'ON' if self.is_playing else 'OFF'}",
                f"AUTO SOUND: {'ON' if self.auto_sound else 'OFF'}",
                f"SPEED: {int(self.playback_rates[self.playback_idx]*100)}%",
                f"RANGE: {self.renderer.cfg.key_range}",
                f"KEYS: {len(self.keymap)}",
            ])
            self.renderer.draw_status_bar(right_info_text=right_info, song_title=song_title)

            # AUTO SOUND 關閉時不自動高亮
            highlight = set(self.highlight_pitches) | (set(self.playing) if self.auto_sound else set())

            # 給 renderer 提供「排序後的 notes 與 starts」以便用 bisect 取可視區
            self.renderer.draw_notes(self.notes_sorted, self.note_starts, self.time)
            self.renderer.draw_keyboard(highlight=highlight)

            if self.overlay and self.overlay.active:
                self.overlay.draw(self.renderer.screen)
            self.renderer.end_frame()

# audio/synth.py
import pygame.midi

DRUM_CH = 9  # GM: ch10(索引9)為打擊，避免使用

class Synth:
    """
    系統 MIDI 音源 + 簡易多語音分配（token）：
    - note_on(p, v) -> token
    - note_off_token(token) 精準關閉該次觸發
    - note_off(pitch) 關掉該 pitch 的最後一發（後備）
    """
    def __init__(self, cfg):
        self.cfg = cfg
        self.midi_out = None
        self.use_midi_out = False

        self.channels = [ch for ch in range(16) if ch != DRUM_CH]
        self._rr_index = 0
        self._next_token = 1
        self._token_map = {}              # token -> (ch, pitch)
        self._active_stack_by_pitch = {}  # pitch -> [token1, token2, ...]

        try:
            pygame.midi.init()
            dev = pygame.midi.get_default_output_id()
            if dev != -1:
                self.midi_out = pygame.midi.Output(dev)
                for ch in self.channels:
                    self.midi_out.set_instrument(0, ch)  # Acoustic Grand
                self.use_midi_out = True
                print(f"[Synth] Using system MIDI out (device {dev})")
            else:
                print("[Synth] No MIDI output device found")
        except Exception as e:
            print("[Synth] MIDI init failed:", e)

    def close(self):
        try:
            if self.midi_out:
                self.all_notes_off()
                del self.midi_out
        except Exception:
            pass
        pygame.midi.quit()
        self.midi_out = None
        self.use_midi_out = False

    def _alloc_channel(self) -> int:
        ch = self.channels[self._rr_index % len(self.channels)]
        self._rr_index += 1
        return ch

    def _new_token(self, ch: int, pitch: int) -> int:
        t = self._next_token; self._next_token += 1
        self._token_map[t] = (ch, pitch)
        self._active_stack_by_pitch.setdefault(pitch, []).append(t)
        return t

    def note_on(self, pitch: int, vel: int = 100):
        if not (self.use_midi_out and self.midi_out): return None
        try:
            ch = self._alloc_channel()
            v = max(1, min(int(vel), 127))
            self.midi_out.note_on(int(pitch), v, ch)
            return self._new_token(ch, int(pitch))
        except Exception:
            return None

    def note_off(self, pitch: int):
        if not (self.use_midi_out and self.midi_out): return
        stack = self._active_stack_by_pitch.get(int(pitch))
        if stack:
            t = stack.pop()
            ch, p = self._token_map.pop(t, (None, None))
            if ch is not None:
                try: self.midi_out.note_off(p, 0, ch)
                except Exception: pass
            if not stack:
                self._active_stack_by_pitch.pop(int(pitch), None)
            return
        for ch in self.channels:
            try: self.midi_out.note_off(int(pitch), 0, ch)
            except Exception: pass

    def note_off_token(self, token: int):
        if not (self.use_midi_out and self.midi_out): return
        ch, p = self._token_map.pop(int(token), (None, None))
        if ch is None: return
        try: self.midi_out.note_off(p, 0, ch)
        except Exception: pass
        st = self._active_stack_by_pitch.get(p)
        if st:
            try: st.remove(token)
            except ValueError: pass
            if not st: self._active_stack_by_pitch.pop(p, None)

    def all_notes_off(self):
        if not (self.use_midi_out and self.midi_out): return
        for ch in self.channels:
            for p in range(21, 109):
                try: self.midi_out.note_off(p, 0, ch)
                except Exception: pass
        self._token_map.clear()
        self._active_stack_by_pitch.clear()

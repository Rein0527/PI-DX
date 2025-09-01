# ========================= audio/synth.py =========================
import pygame.midi

class Synth:
    """
    使用系統內建 MIDI 音源 (如 Windows 的 Microsoft GS Wavetable Synth)。
    不需要 SF2，直接 note_on / note_off 就能發聲。
    """
    def __init__(self, cfg):
        self.cfg = cfg
        self.midi_out = None
        self.use_midi_out = False
        try:
            pygame.midi.init()
            dev = pygame.midi.get_default_output_id()
            if dev != -1:
                self.midi_out = pygame.midi.Output(dev)
                self.midi_out.set_instrument(0)  # Acoustic Grand Piano
                self.use_midi_out = True
                print(f"[Synth] Using system MIDI out (device {dev})")
            else:
                print("[Synth] No MIDI output device found")
        except Exception as e:
            print("[Synth] MIDI init failed:", e)

    def close(self):
        if self.midi_out:
            try:
                del self.midi_out
            except Exception:
                pass
        pygame.midi.quit()
        self.midi_out = None
        self.use_midi_out = False

    def load_sf2(self, path: str):
        # 保留介面；此模式不支援 SF2
        return False, "SF2 not supported (using system MIDI instead)"

    def note_on(self, pitch: int, vel: int = 100):
        if self.use_midi_out and self.midi_out:
            try:
                self.midi_out.note_on(int(pitch), max(1, min(int(vel), 127)))
            except Exception:
                pass

    def note_off(self, pitch: int):
        if self.use_midi_out and self.midi_out:
            try:
                self.midi_out.note_off(int(pitch), 0)
            except Exception:
                pass

    def all_notes_off(self):
        if self.use_midi_out and self.midi_out:
            for p in range(21, 109):
                try:
                    self.midi_out.note_off(p, 0)
                except Exception:
                    pass

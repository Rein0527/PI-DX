# notes/model.py
from dataclasses import dataclass

@dataclass(frozen=True)
class Note:
    pitch: int      # MIDI note number
    start: float    # seconds
    end: float      # seconds
    velocity: int
    channel: int

    @property
    def dur(self) -> float:
        return max(0.001, self.end - self.start)
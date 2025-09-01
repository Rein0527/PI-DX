# timeline/scheduler.py
from typing import Iterable
from notes.model import Note

class Timeline:
    """Advances time and yields notes that start/stop around current time.
    Renderer and Audio subscribe to events from this class.
    """
    def __init__(self, notes: Iterable[Note]):
        self.notes = list(notes)
        self.i = 0
        self.time = 0.0

    def step(self, dt: float):
        self.time += dt

    def starting_notes(self, tolerance: float = 0.004):
        t = self.time
        while self.i < len(self.notes) and self.notes[self.i].start <= t + tolerance:
            yield self.notes[self.i]
            self.i += 1

    def ending_at(self, t: float) -> list[Note]:
        return [n for n in self.notes if abs(n.end - t) < 0.002]

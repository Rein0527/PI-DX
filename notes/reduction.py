# ========================= notes/reduction.py =========================
from typing import List
from notes.model import Note
from config import ReductionConfig

class ReductionStrategy:
    def apply(self, notes: List[Note], cfg: ReductionConfig) -> List[Note]:
        raise NotImplementedError

class BasicReduction(ReductionStrategy):
    """Drop low-velocity notes and cap polyphony per time slice."""
    def apply(self, notes: List[Note], cfg: ReductionConfig) -> List[Note]:
        filt = [n for n in notes if n.velocity >= cfg.min_velocity]
        # bucket by onset
        buckets = {}
        for n in filt:
            b = int((n.start * 1000) // cfg.slice_ms)
            buckets.setdefault(b, []).append(n)
        out: List[Note] = []
        for _, arr in buckets.items():
            arr.sort(key=lambda x: (-x.velocity, -x.dur, x.pitch))
            out.extend(arr[: cfg.max_poly_per_slice])
        out.sort(key=lambda n: (n.start, n.pitch))
        return out

class MelodyBassReduction(ReductionStrategy):
    """Keep line-of-maximum (melody high), plus lowest (bass), then fill rest by velocity."""
    def apply(self, notes: List[Note], cfg: ReductionConfig) -> List[Note]:
        filt = [n for n in notes if n.velocity >= cfg.min_velocity]
        buckets = {}
        for n in filt:
            b = int((n.start * 1000) // cfg.slice_ms)
            buckets.setdefault(b, []).append(n)
        out: List[Note] = []
        for _, arr in buckets.items():
            arr.sort(key=lambda x: (x.start, x.pitch))
            melody = max(arr, key=lambda x: x.pitch)
            bass = min(arr, key=lambda x: x.pitch)
            chosen = {melody, bass}
            # fill remaining by velocity
            for n in sorted(arr, key=lambda x: -x.velocity):
                if len(chosen) >= cfg.max_poly_per_slice:
                    break
                chosen.add(n)
            out.extend(sorted(list(chosen), key=lambda n: (n.start, n.pitch)))
        out.sort(key=lambda n: (n.start, n.pitch))
        return out

def make_reduction(mode: str) -> ReductionStrategy:
    return MelodyBassReduction() if mode == "melody_bass" else BasicReduction()
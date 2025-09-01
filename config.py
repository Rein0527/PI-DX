# ========================= config.py =========================
from dataclasses import dataclass
from typing import Optional

@dataclass
class RenderConfig:
    window_w: int = 1600
    window_h: int = 900
    piano_h: int = 120
    pixels_per_second: float = 280.0  # fall speed
    spawn_seconds: float = 3.0        # note runway above screen
    key_range: str = "88"

@dataclass
class ReductionConfig:
    min_velocity: int = 1
    max_poly_per_slice: int = 16
    slice_ms: int = 40
    mode: str = "basic"  # or "melody_bass" etc.

@dataclass
class AudioConfig:
    sf2_path: Optional[str] = None
    sample_rate: int = 44100

@dataclass
class AppConfig:
    render: RenderConfig = RenderConfig()
    reduce: ReductionConfig = ReductionConfig()
    audio: AudioConfig = AudioConfig()

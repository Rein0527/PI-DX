# ========================= input/keymap.py =========================
import pygame
from typing import Dict

# 預設配置（可被程式內動態覆蓋）
DEFAULT_KEYMAP: Dict[int, int] = {
    pygame.K_z: 60,  # C4
    pygame.K_s: 61,
    pygame.K_x: 62,
    pygame.K_d: 63,
    pygame.K_c: 64,
    pygame.K_v: 65,
    pygame.K_g: 66,
    pygame.K_b: 67,
    pygame.K_h: 68,
    pygame.K_n: 69,
    pygame.K_j: 70,
    pygame.K_m: 71,
    pygame.K_COMMA: 72,  # C5
}

def keycode_to_name(k: int) -> str:
    try:
        return pygame.key.name(k)
    except Exception:
        return str(k)

def name_to_keycode(name: str) -> int:
    """把 'z', 'comma' 等名稱轉回 pygame 的 keycode。"""
    try:
        return pygame.key.key_code(name)
    except Exception:
        # 允許純數字 keycode
        try:
            return int(name)
        except Exception:
            raise ValueError(f"Unknown key name: {name}")

def serialize_keymap(kmap: Dict[int, int]) -> dict:
    """以 key 名稱輸出，便於人看與儲存 JSON。"""
    return {keycode_to_name(k): v for k, v in kmap.items()}

def deserialize_keymap(obj: dict) -> Dict[int, int]:
    """從名稱->pitch 的 JSON 還原為 keycode->pitch。"""
    out: Dict[int, int] = {}
    for kname, pitch in obj.items():
        kc = name_to_keycode(str(kname))
        out[kc] = int(pitch)
    return out

# midi/parser.py
import mido
from typing import List, Tuple
from notes.model import Note

def parse_midi_to_notes(path: str) -> Tuple[List[Note], float]:
    mid = mido.MidiFile(path)
    tpb = mid.ticks_per_beat
    tempo = 500000  # default 120 bpm
    time_sec = 0.0
    active = {}
    notes: List[Note] = []

    for msg in mido.merge_tracks(mid.tracks):
        time_sec += mido.tick2second(msg.time, tpb, tempo)
        if msg.is_meta:
            if msg.type == 'set_tempo':
                tempo = msg.tempo
        else:
            if msg.type == 'note_on' and msg.velocity > 0:
                active[(msg.channel, msg.note)] = (time_sec, msg.velocity)
            elif msg.type in ('note_off',) or (msg.type == 'note_on' and msg.velocity == 0):
                key = (msg.channel, msg.note)
                if key in active:
                    st, vel = active.pop(key)
                    notes.append(Note(pitch=msg.note, start=st, end=time_sec, velocity=vel, channel=msg.channel))
    # close dangling
    for (ch, p), (st, vel) in active.items():
        notes.append(Note(pitch=p, start=st, end=time_sec, velocity=vel, channel=ch))
    total = max((n.end for n in notes), default=0.0)
    notes.sort(key=lambda n: (n.start, n.pitch))
    return notes, total
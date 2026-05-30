"""
Visual detector for falling-notes kalimba videos.

Detects note events by watching for the yellow strike flash on each tine
(y=470-485). When a tine is struck, it glows yellow (R>150, G>100, B<80),
distinct from the normal pink glow (B~175) of upcoming notes.
"""

import numpy as np
from PIL import Image
from pathlib import Path

TINE_X = [14, 87, 165, 258, 338, 401, 477, 558, 633, 720, 793, 865, 940, 1021, 1098, 1187, 1255]
TINE_NOTES = ["2''", "7'", "5'", "3'", "1'", "6", "4", "2", "1", "3", "5", "7",
              "2'", "4'", "6'", "1''", "3''"]

# Y-range of the tine body where yellow strike flash is visible
FLASH_TOP = 468
FLASH_BOT = 488

# Song frames have an orange/wood centre pixel (B channel < 80 at centre)
def _is_song_frame(arr: np.ndarray) -> bool:
    return int(arr[200, 640, 2]) < 80


def _is_yellow(r: float, g: float, b: float) -> bool:
    """Yellow strike flash: high R and G, low B — distinct from pink (high B) tines."""
    return r > 150 and g > 100 and b < 80


def _tine_struck(arr: np.ndarray, tine_x: int) -> bool:
    x0 = max(0, tine_x - 12)
    x1 = min(arr.shape[1], tine_x + 12)
    region = arr[FLASH_TOP:FLASH_BOT, x0:x1, :].astype(np.float32)
    r = region[:, :, 0].mean()
    g = region[:, :, 1].mean()
    b = region[:, :, 2].mean()
    return _is_yellow(r, g, b)


def detect_notes_visual(
    frames_dir: str,
    fps: float = 10.0,
    chord_gap_ms: float = 150.0,
) -> list[tuple[float, list[str]]]:
    """
    Return list of (time_seconds, [notes]) events detected via yellow tine strike flash.
    chord_gap_ms: notes within this many milliseconds are grouped as a chord.
                  150ms catches micro-offsets without merging distinct hits.
    """
    frame_paths = sorted(Path(frames_dir).glob("frame_*.jpg"))
    if not frame_paths:
        raise RuntimeError(f"No frames found in {frames_dir}")

    chord_gap_frames = chord_gap_ms / 1000.0 * fps

    prev_struck = [False] * len(TINE_X)
    raw: list[tuple[int, str]] = []  # (frame_index, note)

    for fi, path in enumerate(frame_paths):
        arr = np.array(Image.open(path))

        if not _is_song_frame(arr):
            prev_struck = [False] * len(TINE_X)
            continue

        curr_struck = [_tine_struck(arr, x) for x in TINE_X]

        for i, (was, now) in enumerate(zip(prev_struck, curr_struck)):
            if now and not was:
                raw.append((fi, TINE_NOTES[i]))

        prev_struck = curr_struck

    if not raw:
        return []

    # Group into chords using time-based window
    grouped: list[tuple[float, list[str]]] = []
    current: list[str] = [raw[0][1]]
    current_fi = raw[0][0]

    for fi, note in raw[1:]:
        if fi - current_fi <= chord_gap_frames:
            if note not in current:
                current.append(note)
        else:
            grouped.append((current_fi / fps, current))
            current = [note]
            current_fi = fi

    grouped.append((current_fi / fps, current))
    return grouped


def format_events(events: list[tuple[float, list[str]]], phrase_gap_s: float = 1.0) -> str:
    """
    Format events as kalimba tab notation, inserting a blank line between phrases
    (gaps longer than phrase_gap_s seconds) and wrapping at 8 tokens per line.
    """
    if not events:
        return ""

    phrases: list[list[str]] = []
    current_phrase: list[str] = []

    prev_t = events[0][0]
    for t, notes in events:
        token = notes[0] if len(notes) == 1 else "(" + " ".join(notes) + ")"
        if t - prev_t >= phrase_gap_s and current_phrase:
            phrases.append(current_phrase)
            current_phrase = []
        current_phrase.append(token)
        prev_t = t

    if current_phrase:
        phrases.append(current_phrase)

    stanzas = []
    for tokens in phrases:
        lines = [" ".join(tokens[i:i+8]) for i in range(0, len(tokens), 8)]
        stanzas.append("\n".join(lines))

    return "\n\n".join(stanzas)

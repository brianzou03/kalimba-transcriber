"""
Visual detector for falling-notes kalimba videos.

Detects note events by tracking when blocks enter the approach zone
(y=280–370) above the tine bar, using brightness to distinguish
pink and gray blocks from the brown wooden background.
"""

import numpy as np
from PIL import Image
from pathlib import Path

TINE_X     = [14, 87, 165, 258, 338, 401, 477, 558, 633, 720, 793, 865, 940, 1021, 1098, 1187, 1255]
TINE_NOTES = ["2''", "7'", "5'", "3'", "1'", "6", "4", "2", "1", "3", "5", "7",
              "2'", "4'", "6'", "1''", "3''"]

# Detection window: block must be in this y range to count as "imminent"
DETECT_TOP = 280
DETECT_BOT = 370

# Brightness threshold to distinguish block from wood background (~93)
BLOCK_BRIGHTNESS = 150

# Song starts when the centre column is orange/wood-coloured (B channel < 80)
def _is_song_frame(arr: np.ndarray) -> bool:
    return int(arr[200, 640, 2]) < 80


def _block_lowest_y(arr: np.ndarray, tine_x: int) -> int | None:
    """Y of the lowest bright row in the approach window, or None."""
    x0 = max(0, tine_x - 14)
    x1 = min(arr.shape[1], tine_x + 14)
    region = arr[DETECT_TOP:DETECT_BOT, x0:x1, :].astype(np.float32)
    brightness = region.mean(axis=(1, 2))  # per-row average
    for row in range(len(brightness) - 1, -1, -1):
        if brightness[row] > BLOCK_BRIGHTNESS:
            return DETECT_TOP + row
    return None


def detect_notes_visual(frames_dir: str, chord_gap: int = 2) -> list[list[str]]:
    """
    Return list of note events (each event = list of simultaneous tab strings).
    chord_gap: frames within which notes are grouped into a chord.
    """
    frame_paths = sorted(Path(frames_dir).glob("frame_*.jpg"))
    if not frame_paths:
        raise RuntimeError(f"No frames found in {frames_dir}")

    # prev_present[i] = was tine i occupied last frame?
    prev_present = [False] * len(TINE_X)
    raw: list[tuple[int, str]] = []  # (frame_index, note)

    for fi, path in enumerate(frame_paths):
        arr = np.array(Image.open(path))

        if not _is_song_frame(arr):
            prev_present = [False] * len(TINE_X)
            continue

        curr_present = []
        for x in TINE_X:
            curr_present.append(_block_lowest_y(arr, x) is not None)

        for i, (was, now) in enumerate(zip(prev_present, curr_present)):
            if now and not was:
                raw.append((fi, TINE_NOTES[i]))

        prev_present = curr_present

    if not raw:
        return []

    # Group into chords
    grouped: list[list[str]] = []
    current: list[str] = [raw[0][1]]
    current_fi = raw[0][0]

    for fi, note in raw[1:]:
        if fi - current_fi <= chord_gap:
            if note not in current:
                current.append(note)
        else:
            grouped.append(current)
            current = [note]
            current_fi = fi

    grouped.append(current)
    return grouped


def format_events(events: list[list[str]]) -> str:
    tokens = [
        notes[0] if len(notes) == 1 else "(" + " ".join(notes) + ")"
        for notes in events
    ]
    lines = [" ".join(tokens[i:i+8]) for i in range(0, len(tokens), 8)]
    return "\n".join(lines)

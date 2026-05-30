"""
Piano sheet music → kalimba tab transcriber.

Supports MusicXML (.xml, .mxl, .musicxml) and MIDI (.mid, .midi) files.
Notes outside the 17-key kalimba range are mapped to the nearest available note.
Notes with accidentals (sharps/flats) are mapped to the nearest diatonic kalimba note.
"""

from __future__ import annotations
from pathlib import Path

# 17-key C major kalimba: pitch name → tab notation
# MIDI note numbers for reference: C4=60, D4=62, E4=64, F4=65, G4=67, A4=69, B4=71 ...
KALIMBA_NOTES: list[tuple[int, str]] = [
    (60, "1"),    # C4
    (62, "2"),    # D4
    (64, "3"),    # E4
    (65, "4"),    # F4
    (67, "5"),    # G4
    (69, "6"),    # A4
    (71, "7"),    # B4
    (72, "1'"),   # C5
    (74, "2'"),   # D5
    (76, "3'"),   # E5
    (77, "4'"),   # F5
    (79, "5'"),   # G5
    (81, "6'"),   # A5
    (83, "7'"),   # B5
    (84, "1''"),  # C6
    (86, "2''"),  # D6
    (88, "3''"),  # E6
]

_MIDI_TO_TAB: dict[int, str] = {midi: tab for midi, tab in KALIMBA_NOTES}
_ALL_MIDI = [midi for midi, _ in KALIMBA_NOTES]


def midi_to_tab(midi_note: int) -> str:
    """Map any MIDI note to the nearest kalimba tab, transposing by octaves if needed."""
    if midi_note in _MIDI_TO_TAB:
        return _MIDI_TO_TAB[midi_note]
    # Find closest kalimba note by semitone distance
    best = min(_ALL_MIDI, key=lambda m: abs(m - midi_note))
    return _MIDI_TO_TAB[best]


def _format_tabs(events: list[tuple[float, list[str]]], phrase_gap_s: float = 2.0) -> str:
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


def _transcribe_musicxml(path: Path, chord_gap_s: float, phrase_gap_s: float) -> str:
    import music21
    score = music21.converter.parse(str(path))

    # Flatten to a single stream of notes/chords with offsets in seconds
    flat = score.flatten().getElementsByClass(["Note", "Chord"])

    events: list[tuple[float, list[str]]] = []
    prev_t: float | None = None

    for el in flat:
        try:
            t = float(el.getOffsetInHierarchy(score.flatten()))
        except Exception:
            continue

        if isinstance(el, music21.note.Note):
            tabs = [midi_to_tab(el.pitch.midi)]
        else:  # Chord
            tabs = [midi_to_tab(p.midi) for p in el.pitches]
            tabs = list(dict.fromkeys(tabs))  # deduplicate while preserving order

        if prev_t is not None and t - prev_t < chord_gap_s and events:
            for tab in tabs:
                if tab not in events[-1][1]:
                    events[-1][1].append(tab)
        else:
            events.append((t, tabs))
        prev_t = t

    return _format_tabs(events, phrase_gap_s)


def _transcribe_midi(path: Path, chord_gap_s: float, phrase_gap_s: float) -> str:
    import mido

    mid = mido.MidiFile(str(path))
    ticks_per_beat = mid.ticks_per_beat
    tempo = 500000  # default 120 BPM in microseconds per beat

    # Collect all note-on events with absolute time in seconds
    raw: list[tuple[float, int]] = []  # (time_s, midi_note)
    abs_tick = 0
    abs_time_s = 0.0

    # Merge all tracks into a single timeline
    for msg in mido.merge_tracks(mid.tracks):
        delta_s = mido.tick2second(msg.time, ticks_per_beat, tempo)
        abs_time_s += delta_s
        if msg.type == "set_tempo":
            tempo = msg.tempo
        elif msg.type == "note_on" and msg.velocity > 0:
            raw.append((abs_time_s, msg.note))

    if not raw:
        return ""

    # Group into chord events
    events: list[tuple[float, list[str]]] = []
    for t, midi_note in raw:
        tab = midi_to_tab(midi_note)
        if events and t - events[-1][0] < chord_gap_s:
            if tab not in events[-1][1]:
                events[-1][1].append(tab)
        else:
            events.append((t, [tab]))

    return _format_tabs(events, phrase_gap_s)


def transcribe_sheet(
    file_path: str,
    chord_gap_s: float = 0.08,
    phrase_gap_s: float = 2.0,
) -> str:
    """
    Transcribe a piano sheet music file to kalimba tab notation.

    Args:
        file_path: Path to a MusicXML (.xml, .mxl, .musicxml) or MIDI (.mid, .midi) file.
        chord_gap_s: Notes within this many seconds are grouped as a chord (default 80ms).
        phrase_gap_s: Gap in seconds that marks a new phrase/stanza (default 2s).

    Returns:
        Kalimba tab notation as a string.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    suffix = path.suffix.lower()
    if suffix in (".xml", ".mxl", ".musicxml"):
        return _transcribe_musicxml(path, chord_gap_s, phrase_gap_s)
    elif suffix in (".mid", ".midi"):
        return _transcribe_midi(path, chord_gap_s, phrase_gap_s)
    else:
        raise ValueError(f"Unsupported file type '{suffix}'. Use .xml, .mxl, .musicxml, .mid, or .midi")

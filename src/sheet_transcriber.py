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

# Physical left→right tine order on a 17-key kalimba (used for consistent chord notation)
_TINE_NOTES_ORDER = ["2''", "7'", "5'", "3'", "1'", "6", "4", "2", "1", "3", "5", "7",
                     "2'", "4'", "6'", "1''", "3''"]
_TINE_ORDER: dict[str, int] = {note: i for i, note in enumerate(_TINE_NOTES_ORDER)}

# Preferred MIDI ceiling for melody: notes above B5 are transposed down one octave
# so the melody sits in the natural kalimba playing range (C4–B5)
_MELODY_MAX_MIDI = 83  # B5


def _clamp_to_melody_range(midi: int) -> int:
    """Transpose a MIDI note down by octaves until it's within the preferred melody range."""
    while midi > _MELODY_MAX_MIDI:
        midi -= 12
    return midi


def midi_to_tab(midi_note: int) -> str:
    """Map any MIDI note to the nearest kalimba tab."""
    if midi_note in _MIDI_TO_TAB:
        return _MIDI_TO_TAB[midi_note]
    best = min(_ALL_MIDI, key=lambda m: abs(m - midi_note))
    return _MIDI_TO_TAB[best]


def _sort_chord(notes: list[str]) -> list[str]:
    """Sort chord notes by ascending physical tine index (left→right on kalimba)."""
    return sorted(notes, key=lambda n: _TINE_ORDER.get(n, 99))


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


def _midi_to_seconds(offset_in_quarter_notes: float, score) -> float:
    """Convert a score offset (in quarter notes) to seconds using the score's tempo map."""
    import music21
    try:
        return score.secondsMap[float(offset_in_quarter_notes)]["offsetSeconds"]
    except Exception:
        pass
    # Fall back: use first tempo marking
    tempos = score.flatten().getElementsByClass(music21.tempo.MetronomeMark)
    bpm = float(tempos[0].number) if tempos else 120.0
    return offset_in_quarter_notes * (60.0 / bpm)


def _extract_melody_events(part, score) -> list[tuple[float, int]]:
    """
    Extract (time_s, midi_pitch) pairs from a part, taking only the highest
    pitch at each position (melody note).
    """
    import music21
    events = []
    for el in part.flatten().getElementsByClass(["Note", "Chord"]):
        offset = float(el.getOffsetInHierarchy(part))
        t = _midi_to_seconds(offset, score)
        if isinstance(el, music21.note.Note):
            events.append((t, el.pitch.midi))
        else:  # Chord — take the highest pitch (melody)
            top = max(p.midi for p in el.pitches)
            events.append((t, top))
    return events


def _transcribe_musicxml(path: Path, chord_gap_s: float, phrase_gap_s: float) -> str:
    import music21
    score = music21.converter.parse(str(path))

    parts = score.parts
    if not parts:
        return ""

    # Treble part = part 0 (right hand melody)
    # Bass part = part 1 (left hand accompaniment), optional
    treble_events = _extract_melody_events(parts[0], score)
    bass_events = _extract_melody_events(parts[1], score) if len(parts) > 1 else []

    # Merge treble (melody) with bass (lowest note at same time = one accompaniment note)
    # Build a timeline: for each beat, take melody + optional bass
    all_times = sorted({t for t, _ in treble_events} | {t for t, _ in bass_events})

    treble_map: dict[float, int] = {}
    for t, midi in treble_events:
        # Keep highest pitch per timestamp, then clamp to melody range
        treble_map[t] = max(treble_map.get(t, 0), midi)

    bass_map: dict[float, int] = {}
    for t, midi in bass_events:
        bass_map[t] = min(bass_map.get(t, midi), midi)

    # Build events: melody note + bass note if they differ
    raw_events: list[tuple[float, list[str]]] = []
    for t in all_times:
        notes = []
        if t in treble_map:
            melody_midi = _clamp_to_melody_range(treble_map[t])
            notes.append(midi_to_tab(melody_midi))
        if t in bass_map:
            bass_tab = midi_to_tab(bass_map[t])
            if bass_tab not in notes:
                notes.append(bass_tab)
        notes = list(dict.fromkeys(notes))[:2]
        if notes:
            raw_events.append((t, _sort_chord(notes)))

    # Merge events that are within chord_gap_s of each other
    if not raw_events:
        return ""

    merged: list[tuple[float, list[str]]] = [raw_events[0]]
    for t, notes in raw_events[1:]:
        if t - merged[-1][0] < chord_gap_s:
            for n in notes:
                if n not in merged[-1][1] and len(merged[-1][1]) < 2:
                    merged[-1][1].append(n)
            merged[-1] = (merged[-1][0], _sort_chord(merged[-1][1]))
        else:
            merged.append((t, notes))

    return _format_tabs(merged, phrase_gap_s)


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
    phrase_gap_s: float = 4.0,
) -> str:
    """
    Transcribe a piano sheet music file to kalimba tab notation.

    Args:
        file_path: Path to a MusicXML (.xml, .mxl, .musicxml), MIDI (.mid, .midi),
                   or PDF (.pdf) file. PDFs require Audiveris (run setup_audiveris.py once).
        chord_gap_s: Notes within this many seconds are grouped as a chord (default 80ms).
        phrase_gap_s: Gap in seconds that marks a new phrase/stanza (default 2s).

    Returns:
        Kalimba tab notation as a string.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    suffix = path.suffix.lower()

    if suffix == ".pdf":
        from src.pdf_converter import convert_pdf_to_musicxml
        print(f"Converting PDF via Audiveris OMR...")
        mxl_path = convert_pdf_to_musicxml(str(path))
        print(f"Converted to: {mxl_path}")
        return _transcribe_musicxml(mxl_path, chord_gap_s, phrase_gap_s)
    elif suffix in (".xml", ".mxl", ".musicxml"):
        return _transcribe_musicxml(path, chord_gap_s, phrase_gap_s)
    elif suffix in (".mid", ".midi"):
        return _transcribe_midi(path, chord_gap_s, phrase_gap_s)
    else:
        raise ValueError(
            f"Unsupported file type '{suffix}'. "
            "Use .pdf, .xml, .mxl, .musicxml, .mid, or .midi"
        )

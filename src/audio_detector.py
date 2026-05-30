import numpy as np
from scipy.io import wavfile
from scipy.signal import stft, find_peaks

KALIMBA_FREQS = {
    "1":   261.63,  # C4
    "2":   293.66,  # D4
    "3":   329.63,  # E4
    "4":   349.23,  # F4
    "5":   392.00,  # G4
    "6":   440.00,  # A4
    "7":   493.88,  # B4
    "1'":  523.25,  # C5
    "2'":  587.33,  # D5
    "3'":  659.25,  # E5
    "4'":  698.46,  # F5
    "5'":  783.99,  # G5
    "6'":  880.00,  # A5
    "7'":  987.77,  # B5
    "1''": 1046.50, # C6
    "2''": 1174.66, # D6
    "3''": 1318.51, # E6
}

SEMITONE = 2 ** (1 / 12)
HALF_SEMITONE = SEMITONE ** 0.5


def freq_to_tab(freq: float) -> str | None:
    best, best_ratio = None, float("inf")
    for tab, f in KALIMBA_FREQS.items():
        ratio = max(freq, f) / min(freq, f)
        if ratio < best_ratio:
            best_ratio = ratio
            best = tab
    return best if best_ratio < HALF_SEMITONE else None


def _is_harmonic(freq: float, fundamentals: list[float], tolerance: float = 0.05) -> bool:
    """Return True if freq is a harmonic (2x, 3x, 4x) of any fundamental."""
    for f in fundamentals:
        for n in range(2, 6):
            harmonic = f * n
            if abs(freq - harmonic) / harmonic < tolerance:
                return True
    return False


def detect_notes(wav_path: str, onset_threshold: float = 0.05, chord_window_ms: float = 60) -> list[list[str]]:
    sample_rate, data = wavfile.read(wav_path)

    if data.dtype == np.int16:
        audio = data.astype(np.float32) / 32768.0
    elif data.dtype == np.int32:
        audio = data.astype(np.float32) / 2147483648.0
    else:
        audio = data.astype(np.float32)

    # STFT with shorter window for better time resolution
    nperseg = 2048
    noverlap = 1536  # 75% overlap → ~23ms hop
    freqs, times, Zxx = stft(audio, fs=sample_rate, nperseg=nperseg, noverlap=noverlap)
    magnitude = np.abs(Zxx)

    # Spectral flux onset detection
    flux = np.sum(np.maximum(np.diff(magnitude, axis=1), 0), axis=0)
    flux_norm = flux / (flux.max() + 1e-8)

    # distance=3 → minimum ~70ms between onsets
    onset_indices, _ = find_peaks(flux_norm, height=onset_threshold, distance=3)

    chord_window = chord_window_ms / 1000.0
    events: list[list[str]] = []
    last_time = -chord_window * 2

    for idx in onset_indices:
        t = times[idx]
        mag_slice = magnitude[:, idx]

        # Focus on kalimba frequency range 200–1400 Hz
        freq_mask = (freqs >= 200) & (freqs <= 1400)
        local_mag = np.zeros_like(mag_slice)
        local_mag[freq_mask] = mag_slice[freq_mask]

        if local_mag.max() == 0:
            continue

        # Find spectral peaks above 20% of local max
        peak_threshold = local_mag[freq_mask].max() * 0.20
        peaks, _ = find_peaks(local_mag, height=peak_threshold, distance=2)
        if len(peaks) == 0:
            continue

        # Sort by magnitude descending
        top_peaks = sorted(peaks, key=lambda p: local_mag[p], reverse=True)

        # Build note list with harmonic suppression
        fundamentals: list[float] = []
        notes: list[str] = []
        for p in top_peaks:
            f = freqs[p]
            if _is_harmonic(f, fundamentals):
                continue
            tab = freq_to_tab(f)
            if tab and tab not in notes:
                notes.append(tab)
                fundamentals.append(f)
            if len(notes) >= 2:  # kalimba rarely plays more than 2 notes at once
                break

        if not notes:
            continue

        if t - last_time < chord_window and events:
            for n in notes:
                if n not in events[-1] and len(events[-1]) < 2:
                    events[-1].append(n)
        else:
            events.append(notes)
            last_time = t

    return events


def format_events(events: list[list[str]]) -> str:
    tokens = []
    for notes in events:
        if len(notes) == 1:
            tokens.append(notes[0])
        else:
            tokens.append("(" + " ".join(notes) + ")")

    lines = []
    i = 0
    while i < len(tokens):
        lines.append(" ".join(tokens[i:i+8]))
        i += 8
    return "\n".join(lines)

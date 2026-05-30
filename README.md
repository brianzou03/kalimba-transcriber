# Kalimba Transcriber

Two tools for generating 17-key kalimba tab notation:

1. **YouTube → Kalimba Tabs** — transcribes falling-notes tutorial videos by detecting when each tine is struck
2. **Piano Sheet Music → Kalimba Tabs** — converts MusicXML or MIDI files to kalimba notation

---

## Kalimba Tab Notation

| Symbol | Meaning | Example |
|--------|---------|---------|
| `1`–`7` | Scale degrees (C4–B4) | `5` = G4 |
| `'` | One octave up | `5'` = G5 |
| `''` | Two octaves up | `1''` = C6 |
| `(notes)` | Chord (played together) | `(6 4)` |
| `-` | Glissando | `1-5` |

Standard 17-key C major layout covers C4 to E6.

---

## Feature 1: YouTube → Kalimba Tabs

Detects note events from falling-notes kalimba tutorial videos by watching for the yellow strike flash on each tine.

### Requirements

- Python 3.11+
- ffmpeg (install via Homebrew: `brew install ffmpeg`)
- yt-dlp, Pillow, numpy (see `requirements.txt`)

### Usage

```bash
python transcriber.py <youtube_url> [options]
```

```bash
# Auto-saves to tabs/<video_title>.txt
python transcriber.py https://youtu.be/hrUnc15BUAU

# Custom output path
python transcriber.py https://youtu.be/hrUnc15BUAU --output tabs/my_song.txt

# Keep downloaded files after transcription
python transcriber.py https://youtu.be/hrUnc15BUAU --keep-files
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--output`, `-o` | stdout | Output file path |
| `--fps` | `10` | Frames per second to extract. Higher = more accurate, slower. |
| `--chord-gap` | `150` | Milliseconds within which notes are grouped as a chord. |
| `--phrase-gap` | `5.0` | Seconds of silence that start a new stanza in the output. |
| `--keep-files` | off | Keep the downloaded video and frames after transcription. |
| `--work-dir` | system temp | Directory for temporary files. |

### How it works

1. Downloads the video with yt-dlp
2. Extracts frames with ffmpeg at the target fps
3. Scans each tine's position at the strike zone (y=468–488) for a yellow flash (R>150, G>100, B<80), which is distinct from the normal pink glow of upcoming notes
4. Groups notes within `chord_gap` ms of each other as chords
5. Inserts blank lines between stanzas where gaps exceed `phrase_gap` seconds

---

## Feature 2: Piano Sheet Music → Kalimba Tabs

Converts piano sheet music to kalimba tab notation. Notes outside the kalimba's range or on accidentals are mapped to the nearest available note.

### Supported Formats

| Format | Extensions | How to get |
|--------|-----------|------------|
| MusicXML | `.xml`, `.mxl`, `.musicxml` | Export from MuseScore, Finale, Sibelius, Noteflight |
| MIDI | `.mid`, `.midi` | Any DAW, MuseScore, or online converters |

> **PDFs are not directly supported.** Open the PDF in [MuseScore](https://musescore.org) (free), then export as MusicXML.

### Setup

```bash
pip install music21 mido
```

### Usage

1. Drop sheet music files into the `sheets/` folder
2. Run the transcriber:

```bash
# List files in sheets/
python sheet_transcriber.py

# Auto-saves to tabs/<filename>.txt
python sheet_transcriber.py sheets/song.xml

# Custom output path
python sheet_transcriber.py sheets/song.xml --output tabs/my_song.txt

# Tune grouping for dense or sparse arrangements
python sheet_transcriber.py sheets/song.mid --chord-gap 0.05 --phrase-gap 1.5
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--output`, `-o` | stdout | Output file path |
| `--chord-gap` | `0.08` | Seconds within which notes are grouped as a chord (80ms). |
| `--phrase-gap` | `2.0` | Seconds of silence that start a new stanza in the output. |

### How it works

1. Parses the MusicXML or MIDI file to extract notes with timestamps
2. Maps each pitch to the nearest kalimba tab (by semitone distance)
3. Groups simultaneous or near-simultaneous notes as chords
4. Formats into tab notation with stanza breaks at long pauses

---

## Installation

```bash
git clone https://github.com/brianzou03/kalimba-transcriber.git
cd kalimba-transcriber
pip install -r requirements.txt
pip install music21 mido  # for sheet music feature
brew install ffmpeg        # for YouTube feature (macOS)
```

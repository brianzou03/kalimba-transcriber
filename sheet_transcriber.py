#!/usr/bin/env python3
"""
Piano Sheet Music → Kalimba Tab Transcriber

Converts MusicXML or MIDI piano sheet music files to 17-key kalimba tab notation.
Drop your sheet files into the sheets/ folder, then run this script.

Supported formats:
    MusicXML: .xml, .mxl, .musicxml  (export from MuseScore, Finale, Sibelius, etc.)
    MIDI:     .mid, .midi

PDFs are not directly supported — open the PDF in MuseScore (free) and export as MusicXML.

Usage:
    python sheet_transcriber.py sheets/song.xml
    python sheet_transcriber.py sheets/song.mid --output tabs/my_song.txt
    python sheet_transcriber.py sheets/song.xml --chord-gap 0.1 --phrase-gap 1.5
"""

import argparse
import sys
from pathlib import Path

TABS_DIR = Path(__file__).parent / "tabs"
SUPPORTED = (".xml", ".mxl", ".musicxml", ".mid", ".midi")


def main():
    parser = argparse.ArgumentParser(
        description="Convert piano sheet music to kalimba tab notation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "file",
        nargs="?",
        help="Sheet music file (.xml, .mxl, .musicxml, .mid, .midi). "
             "If omitted, lists files in the sheets/ folder.",
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file path (default: tabs/<filename>.txt)",
    )
    parser.add_argument(
        "--chord-gap",
        type=float,
        default=0.08,
        help="Seconds within which notes are grouped as a chord (default: 0.08)",
    )
    parser.add_argument(
        "--phrase-gap",
        type=float,
        default=2.0,
        help="Seconds of silence that mark a new phrase/stanza (default: 2.0)",
    )
    args = parser.parse_args()

    sheets_dir = Path(__file__).parent / "sheets"

    if not args.file:
        all_files = sorted(sheets_dir.iterdir()) if sheets_dir.exists() else []
        supported_files = [f for f in all_files if f.suffix.lower() in SUPPORTED]
        pdf_files = [f for f in all_files if f.suffix.lower() == ".pdf"]

        if not supported_files and not pdf_files:
            print(f"No sheet music files found in {sheets_dir}/")
            print("Add .xml, .mxl, .musicxml, .mid, or .midi files and re-run.")
            sys.exit(0)

        if supported_files:
            print(f"Sheet music files in {sheets_dir}/:")
            for f in supported_files:
                print(f"  {f.name}")
            print("\nRun: python sheet_transcriber.py sheets/<filename>")

        if pdf_files:
            print(f"\nPDF files (not directly supported):")
            for f in pdf_files:
                print(f"  {f.name}")
            print("  → Open in MuseScore (free) and export as MusicXML (.musicxml)")

        sys.exit(0)

    file_path = Path(args.file)

    if file_path.suffix.lower() == ".pdf":
        print(f"Error: PDF files cannot be read directly.")
        print(f"To transcribe '{file_path.name}':")
        print(f"  1. Open it in MuseScore (musescore.org — free)")
        print(f"  2. File → Export → MusicXML (.musicxml)")
        print(f"  3. Save the exported file to sheets/")
        print(f"  4. Re-run: python sheet_transcriber.py sheets/{file_path.stem}.musicxml")
        sys.exit(1)

    from src.sheet_transcriber import transcribe_sheet

    print(f"Transcribing: {file_path.name}")
    output = transcribe_sheet(
        str(file_path),
        chord_gap_s=args.chord_gap,
        phrase_gap_s=args.phrase_gap,
    )

    out_path = Path(args.output) if args.output else TABS_DIR / f"{file_path.stem}.txt"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(output, encoding="utf-8")
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()

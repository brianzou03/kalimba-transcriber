#!/usr/bin/env python3
"""
Kalimba Tab Transcriber
Extracts kalimba tab notation from YouTube falling-notes tutorial videos.

Usage:
    python transcriber.py <youtube_url> [options]

    python transcriber.py https://youtu.be/hrUnc15BUAU
    python transcriber.py https://youtu.be/hrUnc15BUAU --output tabs/my_song.txt
    python transcriber.py https://youtu.be/hrUnc15BUAU --chord-gap 150
"""

import argparse
import subprocess
import sys
from pathlib import Path

TABS_DIR = Path(__file__).parent / "tabs"


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe kalimba tabs from a YouTube falling-notes video",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument(
        "--output", "-o",
        help="Output file path (default: tabs/<name>.txt)",
    )
    parser.add_argument(
        "--name", "-n",
        help="Name for the output file (default: fetched from YouTube title)",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=10,
        help="Frames per second to extract (default: 10). Higher = more accurate but slower.",
    )
    parser.add_argument(
        "--chord-gap",
        type=float,
        default=150.0,
        help="Milliseconds within which simultaneous notes are grouped as a chord (default: 150).",
    )
    parser.add_argument(
        "--phrase-gap",
        type=float,
        default=5.0,
        help="Seconds of silence that start a new stanza (blank line) in the output (default: 5.0).",
    )
    parser.add_argument(
        "--line-gap",
        type=float,
        default=2.0,
        help="Seconds of silence that start a new line within a stanza (default: 2.0).",
    )
    parser.add_argument(
        "--keep-files",
        action="store_true",
        help="Keep downloaded video and frames after transcription",
    )
    parser.add_argument(
        "--work-dir",
        help="Directory for temporary files (default: system temp dir)",
    )
    args = parser.parse_args()

    from src.video_processor import VideoProcessor
    from src.visual_detector import detect_notes_visual, format_events

    processor = VideoProcessor(work_dir=args.work_dir)

    try:
        if args.name:
            title = args.name
        else:
            print(f"Fetching title: {args.url}")
            title = processor.get_video_title(args.url)
            print(f"Title: {title}")

        print(f"Downloading video...")
        video_path = processor.download_video(args.url)

        frames_dir = processor.work_dir / "frames"
        frames_dir.mkdir(exist_ok=True)
        print(f"Extracting frames at {args.fps} fps...")
        result = subprocess.run(
            ["ffmpeg", "-i", str(video_path), "-vf", f"fps={args.fps}",
             "-q:v", "2", str(frames_dir / "frame_%05d.jpg"), "-y"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"ffmpeg error: {result.stderr}", file=sys.stderr)
            sys.exit(1)

        frame_count = len(list(frames_dir.glob("*.jpg")))
        print(f"Extracted {frame_count} frames")

        print("Detecting notes...")
        events = detect_notes_visual(str(frames_dir), fps=args.fps, chord_gap_ms=args.chord_gap)
        print(f"Found {len(events)} note events")

        output = format_events(events, phrase_gap_s=args.phrase_gap, line_gap_s=args.line_gap)

        out_path = Path(args.output) if args.output else TABS_DIR / f"{title}.txt"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
        print(f"Saved to {out_path}")

    finally:
        if not args.keep_files:
            processor.cleanup()


if __name__ == "__main__":
    main()

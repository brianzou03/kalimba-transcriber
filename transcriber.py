#!/usr/bin/env python3
"""
Kalimba Tab Transcriber
Extracts kalimba tab notation from YouTube falling-notes tutorial videos.

Usage:
    python transcriber.py <youtube_url> [options]

    python transcriber.py https://youtu.be/hrUnc15BUAU
    python transcriber.py https://youtu.be/hrUnc15BUAU --output tabs.txt
    python transcriber.py https://youtu.be/hrUnc15BUAU --chord-gap 1
"""

import argparse
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe kalimba tabs from a YouTube falling-notes video",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument(
        "--output", "-o",
        help="Output file path (default: print to stdout)",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=4,
        help="Frames per second to extract (default: 4). Higher = more accurate but slower.",
    )
    parser.add_argument(
        "--chord-gap",
        type=int,
        default=0,
        help="Frames within which simultaneous notes are grouped as a chord (default: 0).",
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
        print(f"Downloading: {args.url}")
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
        events = detect_notes_visual(str(frames_dir), chord_gap=args.chord_gap)
        print(f"Found {len(events)} note events")

        output = format_events(events)

        if args.output:
            Path(args.output).write_text(output, encoding="utf-8")
            print(f"Saved to {args.output}")
        else:
            print("\n" + "=" * 50)
            print("KALIMBA TAB TRANSCRIPTION")
            print("=" * 50 + "\n")
            print(output)
            print("\n" + "=" * 50)

    finally:
        if not args.keep_files:
            processor.cleanup()


if __name__ == "__main__":
    main()

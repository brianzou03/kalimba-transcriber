#!/usr/bin/env python3
"""
Kalimba Tab Transcriber
Extracts kalimba tab notation from YouTube videos using Claude vision.

Usage:
    python transcriber.py <youtube_url> [options]

    python transcriber.py https://youtu.be/hrUnc15BUAU
    python transcriber.py https://youtu.be/hrUnc15BUAU --interval 2.0 --output tabs.txt
"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe kalimba tabs from a YouTube video",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument(
        "--interval", "-i",
        type=float,
        default=1.0,
        help="Frame extraction interval in seconds (default: 1.0). "
             "Increase for longer videos to reduce API calls.",
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file path (default: print to stdout)",
    )
    parser.add_argument(
        "--keep-frames",
        action="store_true",
        help="Keep downloaded video and frames after transcription",
    )
    parser.add_argument(
        "--work-dir",
        help="Directory for temporary files (default: system temp dir)",
    )
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable not set.", file=sys.stderr)
        print("Copy .env.example to .env and add your API key.", file=sys.stderr)
        sys.exit(1)

    from src.video_processor import VideoProcessor
    from src.tab_detector import TabDetector
    from src.formatter import format_transcription, print_transcription

    processor = VideoProcessor(work_dir=args.work_dir)

    try:
        print(f"Downloading video: {args.url}")
        video_path, frames_dir = processor.download_and_extract_frames(
            args.url, interval=args.interval
        )
        frame_count = len(list(frames_dir.glob("*.jpg")))
        print(f"Extracted {frame_count} frames (1 per {args.interval}s)")

        detector = TabDetector()
        segments = detector.analyze_frames(frames_dir)

        if not segments:
            print("No kalimba tab notation detected in this video.")
            sys.exit(0)

        print(f"\nFound {len(segments)} unique tab segment(s).")

        if args.output:
            output_path = Path(args.output)
            output_path.write_text(format_transcription(segments), encoding="utf-8")
            print(f"Transcription saved to {output_path}")
        else:
            print_transcription(segments)

    finally:
        if not args.keep_frames:
            processor.cleanup()


if __name__ == "__main__":
    main()

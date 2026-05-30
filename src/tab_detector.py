import base64
import re
from pathlib import Path
from anthropic import Anthropic

SYSTEM_PROMPT = """You are an expert kalimba tab reader. Your job is to extract kalimba tab notation from images.

Kalimba tab notation uses these conventions:
- Numbers 1-7 represent the tines of the kalimba (scale degrees)
- A single quote after a number means higher octave: 1' 2' 3' etc.
- A double quote (two single quotes) after a number means two octaves higher: 1'' 2'' 3'' etc.
- Numbers/notes in parentheses () are played simultaneously (chord): (1' 3') (5 7)
- A hyphen - between notes indicates a glissando
- Notes on the same line are played in sequence
- Blank lines or line breaks separate phrases

Only extract notation that is clearly visible as kalimba tab. If no kalimba tab is visible, respond with exactly: NO_TAB

Extract the notation exactly as shown, preserving the original formatting, primes, parentheses, and line breaks."""

EXTRACTION_PROMPT = """Look at this video frame.

If you can see kalimba tab notation (numbers with optional primes like 1' 2'' 3, notes in parentheses for chords, etc.), extract ALL visible tab text exactly as it appears.

If this frame does NOT contain kalimba tab notation, respond with exactly: NO_TAB

If there is tab notation, respond with ONLY the raw tab text — no explanations, no commentary."""


def _encode_image(path: Path) -> str:
    return base64.standard_b64encode(path.read_bytes()).decode("utf-8")


def _is_tab_content(text: str) -> bool:
    if text.strip() == "NO_TAB":
        return False
    return bool(re.search(r"\d['\"]*", text))


def _normalize(text: str) -> str:
    # Collapse excessive whitespace but preserve line structure
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


class TabDetector:
    def __init__(self, model: str = "claude-sonnet-4-6", batch_size: int = 5):
        self.client = Anthropic()
        self.model = model
        self.batch_size = batch_size

    def analyze_frames(self, frames_dir: Path) -> list[str]:
        frames = sorted(frames_dir.glob("*.jpg"))
        if not frames:
            raise RuntimeError(f"No frames found in {frames_dir}")

        print(f"  Analyzing {len(frames)} frames in batches of {self.batch_size}...")
        seen_content: set[str] = set()
        ordered_segments: list[str] = []

        for i in range(0, len(frames), self.batch_size):
            batch = frames[i : i + self.batch_size]
            batch_results = self._analyze_batch(batch)
            for text in batch_results:
                if text and _is_tab_content(text):
                    normalized = _normalize(text)
                    if normalized not in seen_content:
                        seen_content.add(normalized)
                        ordered_segments.append(normalized)
            print(f"  Processed frames {i+1}–{min(i+len(batch), len(frames))} / {len(frames)}")

        return ordered_segments

    def _analyze_batch(self, frames: list[Path]) -> list[str]:
        results = []
        for frame in frames:
            text = self._analyze_single_frame(frame)
            results.append(text)
        return results

    def _analyze_single_frame(self, frame: Path) -> str:
        image_data = _encode_image(frame)
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_data,
                            },
                        },
                        {"type": "text", "text": EXTRACTION_PROMPT},
                    ],
                }
            ],
        )
        return response.content[0].text.strip()

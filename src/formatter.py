import re


def format_transcription(segments: list[str]) -> str:
    if not segments:
        return ""

    # Join segments, separating with blank line if they don't already end with one
    parts = []
    for seg in segments:
        seg = seg.strip()
        if seg:
            parts.append(seg)

    full_text = "\n\n".join(parts)

    # Normalize quote styles: replace " used as double-prime with ''
    # Some OCR/vision may return curly quotes or straight double quotes
    full_text = re.sub(r'(\d)"(?!["\'])', r"\1''", full_text)

    return full_text


def print_transcription(segments: list[str]) -> None:
    output = format_transcription(segments)
    print("\n" + "=" * 50)
    print("KALIMBA TAB TRANSCRIPTION")
    print("=" * 50 + "\n")
    print(output)
    print("\n" + "=" * 50)

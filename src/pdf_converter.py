"""
PDF sheet music → MusicXML converter using Audiveris OMR.

Audiveris is a free, open-source Optical Music Recognition engine.
On first use, run `python setup_audiveris.py` to install it automatically.
"""

from __future__ import annotations
import subprocess
import tempfile
from pathlib import Path

AUDIVERIS_APP = Path("/Applications/Audiveris.app")
AUDIVERIS_BIN = AUDIVERIS_APP / "Contents" / "MacOS" / "Audiveris"


def is_installed() -> bool:
    return AUDIVERIS_BIN.exists()


def convert_pdf_to_musicxml(pdf_path: str, output_dir: str | None = None) -> Path:
    """
    Convert a PDF of sheet music to MusicXML using Audiveris.

    Returns the path to the generated .mxl file.
    Raises RuntimeError if Audiveris is not installed or conversion fails.
    """
    if not is_installed():
        raise RuntimeError(
            "Audiveris is not installed. Run:\n"
            "    python setup_audiveris.py\n"
            "to install it automatically (one-time setup, ~75MB download)."
        )

    pdf = Path(pdf_path)
    if not pdf.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    # Cache the MXL next to the PDF so Audiveris only runs once per sheet
    if output_dir:
        work_dir = Path(output_dir)
        work_dir.mkdir(parents=True, exist_ok=True)
    else:
        work_dir = pdf.parent / (pdf.stem + "_audiveris")
        work_dir.mkdir(parents=True, exist_ok=True)
        # Return cached result if it exists
        cached = list(work_dir.glob("*.mxl")) + list(work_dir.glob("*.xml"))
        if cached:
            print(f"Using cached MusicXML: {cached[0]}")
            return cached[0]

    result = subprocess.run(
        [str(AUDIVERIS_BIN), "-batch", "-export", "-output", str(work_dir), str(pdf)],
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Audiveris failed:\n{result.stderr}")

    mxl_files = list(work_dir.glob("*.mxl")) + list(work_dir.glob("*.xml"))
    if not mxl_files:
        raise RuntimeError(
            f"Audiveris ran but produced no output in {work_dir}.\n"
            f"stderr: {result.stderr}"
        )

    return mxl_files[0]

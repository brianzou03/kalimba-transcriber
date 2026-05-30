#!/usr/bin/env python3
"""
One-time setup: downloads and installs Audiveris OMR engine.

Audiveris is needed to automatically convert PDF sheet music to MusicXML,
which the kalimba sheet transcriber can then parse.

Run this once:
    python setup_audiveris.py
"""

import subprocess
import sys
import platform
import urllib.request
from pathlib import Path

AUDIVERIS_APP = Path("/Applications/Audiveris.app")
AUDIVERIS_VERSION = "5.10.2"

DOWNLOAD_URLS = {
    "arm64":  f"https://github.com/Audiveris/audiveris/releases/download/{AUDIVERIS_VERSION}/Audiveris-{AUDIVERIS_VERSION}-macosx-arm64.dmg",
    "x86_64": f"https://github.com/Audiveris/audiveris/releases/download/{AUDIVERIS_VERSION}/Audiveris-{AUDIVERIS_VERSION}-macosx-x86_64.dmg",
}


def main():
    if sys.platform != "darwin":
        print("Error: This setup script is for macOS only.")
        print("On Linux, install Audiveris via: sudo apt install audiveris")
        sys.exit(1)

    if AUDIVERIS_APP.exists():
        print(f"Audiveris is already installed at {AUDIVERIS_APP}")
        print("You're all set — PDF transcription is ready to use.")
        sys.exit(0)

    arch = platform.machine()
    url = DOWNLOAD_URLS.get(arch)
    if not url:
        print(f"No Audiveris build for architecture: {arch}")
        sys.exit(1)

    dmg_path = Path("/tmp/audiveris_install.dmg")

    print(f"Downloading Audiveris {AUDIVERIS_VERSION} for macOS ({arch})...")
    print(f"Source: {url}")

    def progress(block, block_size, total):
        done = block * block_size
        if total > 0:
            pct = min(100, done * 100 // total)
            mb = done / 1_048_576
            print(f"\r  {pct}% ({mb:.0f} MB)", end="", flush=True)

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        total = int(resp.headers.get("Content-Length", 0))
        block = 65536
        done = 0
        with open(dmg_path, "wb") as f:
            while True:
                chunk = resp.read(block)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                progress(1, done, total)
    print()

    print("Opening the installer...")
    print()
    print("=" * 60)
    print("INSTALL STEP (one time only):")
    print("  In the window that opens, drag Audiveris to Applications.")
    print("  Then come back here and press Enter.")
    print("=" * 60)
    print()

    subprocess.run(["open", str(dmg_path)])
    input("Press Enter once Audiveris has been dragged to Applications... ")

    if AUDIVERIS_APP.exists():
        print("Audiveris installed successfully!")
        print("PDF sheet music will now be converted automatically.")
    else:
        print("Audiveris not found at /Applications/Audiveris.app")
        print("Make sure you dragged it to the Applications folder and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()

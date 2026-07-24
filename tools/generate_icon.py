#!/usr/bin/env python3
"""Generate platform-specific icons from pytexmk-logo.png."""

import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_DIR.parent
LOGO_PATH = PROJECT_ROOT / "imgs" / "pytexmk-logo.png"
ICO_PATH = TOOLS_DIR / "icon.ico"
ICNS_PATH = TOOLS_DIR / "icon.icns"

# Standard icon sizes for macOS .icns
ICNS_SIZES = (16, 32, 64, 128, 256, 512)


def _read_png_dimensions(data: bytes) -> tuple[int, int]:
    """Read width and height from PNG IHDR chunk."""
    # PNG signature: 8 bytes, then IHDR chunk
    # IHDR: 4 bytes length, 4 bytes 'IHDR', 4 bytes width, 4 bytes height
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Not a valid PNG file")
    width = struct.unpack(">I", data[16:20])[0]
    height = struct.unpack(">I", data[20:24])[0]
    return width, height


def generate_ico() -> Path:
    """Generate ICO file with embedded PNG data.

    The ICO format supports embedding raw PNG data directly in the icon
    entry, which preserves transparency and avoids lossy conversion.
    """
    png_data = LOGO_PATH.read_bytes()
    width, height = _read_png_dimensions(png_data)

    # Clamp to 256 (ICO format maximum)
    w = min(width, 256)
    h = min(height, 256)

    image_offset = 6 + 16  # 6-byte header + 1 directory entry
    image_size = len(png_data)

    # ICO header: reserved(2) + type(2) + count(2)
    header = struct.pack("<HHH", 0, 1, 1)

    # ICO directory entry
    entry = struct.pack(
        "<BBBBHHII",
        w if w < 256 else 0,  # width  (0 means 256)
        h if h < 256 else 0,  # height (0 means 256)
        0,  # color count (0 = no palette, PNG-embedded)
        0,  # reserved
        1,  # planes
        0,  # bpp (0 = PNG data)
        image_size,
        image_offset,
    )

    ICO_PATH.write_bytes(header + entry + png_data)
    return ICO_PATH


def generate_icns() -> Path | None:
    """Generate ICNS file using macOS sips + iconutil.

    Requires macOS; returns None on non-macOS platforms.
    Uses sips to resize the PNG into a temporary .iconset folder,
    then iconutil to convert the iconset into a .icns file.
    """
    if sys.platform != "darwin":
        return None

    # Check required tools
    if not shutil.which("sips"):
        print("  [skip] sips not found on this macOS system")
        return None
    if not shutil.which("iconutil"):
        print("  [skip] iconutil not found on this macOS system")
        return None

    tmp_dir = Path(tempfile.mkdtemp(prefix="pytexmk_iconset_"))
    iconset_dir = tmp_dir / "icon.iconset"
    iconset_dir.mkdir()

    try:
        # Generate each size with sips
        for size in ICNS_SIZES:
            name_1x = f"icon_{size}x{size}.png"
            name_2x = f"icon_{size//2}x{size//2}@2x.png" if size >= 32 else None

            # 1x
            out_1x = iconset_dir / name_1x
            subprocess.run(
                ["sips", "-z", str(size), str(size), str(LOGO_PATH), "--out", str(out_1x)],
                check=True,
                capture_output=True,
                text=True,
            )

            # 2x (retina)
            if name_2x:
                double_size = size
                out_2x = iconset_dir / name_2x
                subprocess.run(
                    ["sips", "-z", str(double_size), str(double_size), str(LOGO_PATH), "--out", str(out_2x)],
                    check=True,
                    capture_output=True,
                    text=True,
                )

        # Convert iconset to .icns
        subprocess.run(
            ["iconutil", "-c", "icns", str(iconset_dir), "-o", str(ICNS_PATH)],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"  [error] macOS icon generation failed: {e.stderr.strip()}")
        return None
    finally:
        # Clean up temporary directory
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return ICNS_PATH


def main() -> None:
    print(f"Source: {LOGO_PATH}")

    if not LOGO_PATH.exists():
        print(f"ERROR: Logo not found at {LOGO_PATH}")
        sys.exit(1)

    print("Generating ICO (Windows)...")
    try:
        ico = generate_ico()
        print(f"  -> {ico} ({ico.stat().st_size} bytes)")
    except Exception as e:
        print(f"  [error] ICO generation failed: {e}")
        sys.exit(1)

    print("Generating ICNS (macOS)...")
    icns = generate_icns()
    if icns:
        print(f"  -> {icns} ({icns.stat().st_size} bytes)")
    else:
        print("  [skip] ICNS generation requires macOS (sips + iconutil)")

    print("Done.")


if __name__ == "__main__":
    main()
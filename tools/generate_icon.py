#!/usr/bin/env python3
"""Generate platform-specific icons from pytexmk-logo.png."""

import io
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import ICNS_PATH, ICO_PATH, LOGO_SOURCE, PNG_PATH

ICNS_SIZES = (16, 32, 64, 128, 256, 512)
ICO_SIZES = (16, 32, 48, 64, 128, 256)


def _read_png_dimensions(data: bytes) -> tuple[int, int]:
    """Read width and height from PNG IHDR chunk."""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Not a valid PNG file")
    width = struct.unpack(">I", data[16:20])[0]
    height = struct.unpack(">I", data[20:24])[0]
    return width, height


def _ico_pack(png_datas: list[tuple[int, bytes]]) -> bytes:
    """Pack multiple (size, png_data) pairs into a single ICO byte stream."""
    num = len(png_datas)
    header_size = 6
    entry_size = 16
    data_offset = header_size + entry_size * num

    header = struct.pack("<HHH", 0, 1, num)
    entries = b""
    image_data = b""
    offset = data_offset

    for size, png_data in png_datas:
        w = 0 if size >= 256 else size
        h = 0 if size >= 256 else size
        entries += struct.pack(
            "<BBBBHHII",
            w,
            h,
            0,
            0,
            1,
            0,
            len(png_data),
            offset,
        )
        image_data += png_data
        offset += len(png_data)

    return header + entries + image_data


def generate_ico() -> Path:
    """Generate ICO file with embedded PNG data.

    Uses Pillow for multi-size icons if available; falls back to
    single 256px PNG-embedded ICO otherwise.
    """
    try:
        from PIL import Image

        img = Image.open(LOGO_SOURCE).convert("RGBA")
        png_datas = []
        for size in ICO_SIZES:
            resized = img.resize((size, size), Image.LANCZOS)
            buf = io.BytesIO()
            resized.save(buf, format="PNG")
            png_datas.append((size, buf.getvalue()))
        ICO_PATH.write_bytes(_ico_pack(png_datas))
        return ICO_PATH
    except ImportError:
        print("  [warn] Pillow not available, generating single-size ICO")
        png_data = LOGO_SOURCE.read_bytes()
        width, height = _read_png_dimensions(png_data)

        w = min(width, 256)
        h = min(height, 256)

        image_offset = 6 + 16
        image_size = len(png_data)

        header = struct.pack("<HHH", 0, 1, 1)

        entry = struct.pack(
            "<BBBBHHII",
            w if w < 256 else 0,
            h if h < 256 else 0,
            0,
            0,
            1,
            0,
            image_size,
            image_offset,
        )

        ICO_PATH.write_bytes(header + entry + png_data)
        return ICO_PATH


def generate_png() -> Path:
    """Generate 256x256 PNG icon for Linux."""
    try:
        from PIL import Image

        img = Image.open(LOGO_SOURCE).convert("RGBA")
        resized = img.resize((256, 256), Image.LANCZOS)
        resized.save(PNG_PATH, format="PNG")
        return PNG_PATH
    except ImportError:
        shutil.copy2(LOGO_SOURCE, PNG_PATH)
        return PNG_PATH


def generate_icns() -> Path | None:
    """Generate ICNS file using macOS sips + iconutil.

    Requires macOS; returns None on non-macOS platforms.
    Uses sips to resize the PNG into a temporary .iconset folder,
    then iconutil to convert the iconset into a .icns file.
    """
    if sys.platform != "darwin":
        return None

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
        for size in ICNS_SIZES:
            name_1x = f"icon_{size}x{size}.png"
            name_2x = f"icon_{size // 2}x{size // 2}@2x.png" if size >= 32 else None

            out_1x = iconset_dir / name_1x
            subprocess.run(
                [
                    "sips",
                    "-z",
                    str(size),
                    str(size),
                    str(LOGO_SOURCE),
                    "--out",
                    str(out_1x),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            if name_2x:
                double_size = size
                out_2x = iconset_dir / name_2x
                subprocess.run(
                    [
                        "sips",
                        "-z",
                        str(double_size),
                        str(double_size),
                        str(LOGO_SOURCE),
                        "--out",
                        str(out_2x),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )

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
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return ICNS_PATH


def main() -> None:
    print(f"Source: {LOGO_SOURCE}")

    if not LOGO_SOURCE.exists():
        print(f"ERROR: Logo not found at {LOGO_SOURCE}")
        sys.exit(1)

    print("Generating PNG (Linux)...")
    try:
        png = generate_png()
        print(f"  -> {png} ({png.stat().st_size} bytes)")
    except Exception as e:
        print(f"  [error] PNG generation failed: {e}")
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

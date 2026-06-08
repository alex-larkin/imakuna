# LLMs: refer to instructions in `Instructions_for_LLMs.md`, located at the root of the current workspace.
# (If you can't find the file, ignore this note.)

# Written by Claude (Opus 4.5) on 13 Jan, 2026, for Alex Larkin
# Config externalized to YAML by Claude (Opus 4.8) on 07 Jun, 2026, for Alex Larkin

"""pdf_combine.py -- combine all PDFs in a folder into one document.

Settings live in pdf_combine.yaml next to this script. See README.md for full
usage, configuration, and limitations.
"""

import os
import yaml
from pypdf import PdfReader, PdfWriter

# Standard page sizes in points (1 pt = 1/72 inch)
PAGE_SIZES = {
    "letter": (612.0, 792.0),
    "a4":     (595.28, 841.89),
    "legal":  (612.0, 1008.0),
    "a3":     (841.89, 1190.55),
}

# ----------------------- CONFIG (YAML-backed) ----------------------------
# Settings come from pdf_combine.yaml; the DEFAULT_* constants below are filled
# from it at import time. Edit the YAML, not the constants. See README.md.

# YAML config filename: same base name as this script, with a .yaml extension.
CONFIG_FILENAME = os.path.splitext(os.path.basename(__file__))[0] + ".yaml"

# Single source of truth for defaults: used to auto-create the config when it is
# missing and to backfill keys a user's config omits. input_folder/middle are
# blank so generated defaults never carry personal paths or filenames.
_DEFAULT_CONFIG_YAML = """\
# pdf_combine.yaml -- settings for pdf_combine.py (auto-created). See README.md.

paths:
  input_folder: ""   # Folder of PDFs to combine (subfolders ignored)

output_filename:
  # Output name: {prefix}{middle}{suffix}.pdf
  prefix: ""
  # middle: null = folder name; "" = omit; "text" = literal text
  middle: ""
  suffix: ""

sorting:
  sort_ascending: true   # true = A-Z, false = Z-A

page_normalization:
  normalize: true            # rescale all pages to a uniform paper size
  target_page_size: letter   # letter, a4, legal, or a3
"""


def _config_path() -> str:
    """Absolute path to the .yaml config, resolved next to this script."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_FILENAME)


def _deep_merge(base: dict, override: dict) -> dict:
    """Return base updated with override, recursing into nested dicts."""
    result = dict(base)
    for key, val in (override or {}).items():
        if isinstance(val, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result


def load_config() -> dict:
    """
    Load settings from pdf_combine.yaml next to this script.

    Auto-creates the file from built-in defaults (with no personal paths) if it
    is missing, then returns the parsed settings. Any keys absent from the
    user's file are backfilled from the defaults.
    """
    defaults = yaml.safe_load(_DEFAULT_CONFIG_YAML)
    path = _config_path()

    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(_DEFAULT_CONFIG_YAML)
        print(f"Created default config: {path}")
        print("Set 'input_folder' in that file, then run again.")
        return defaults

    with open(path, "r", encoding="utf-8") as f:
        loaded = yaml.safe_load(f) or {}

    return _deep_merge(defaults, loaded)


_CFG = load_config()

# Constants derived from the YAML config. These feed the function default
# arguments and main(); to change behaviour, edit the .yaml instead.
DEFAULT_INPUT_FOLDER = _CFG["paths"]["input_folder"]

DEFAULT_OUTPUT_PREFIX = _CFG["output_filename"]["prefix"]
DEFAULT_OUTPUT_MIDDLE = _CFG["output_filename"]["middle"]  # None = use folder name
DEFAULT_OUTPUT_SUFFIX = _CFG["output_filename"]["suffix"]

DEFAULT_SORT_ASCENDING = _CFG["sorting"]["sort_ascending"]

DEFAULT_NORMALIZE_PAGE_SIZE = _CFG["page_normalization"]["normalize"]
DEFAULT_TARGET_PAGE_SIZE = _CFG["page_normalization"]["target_page_size"]


def _normalize_page(page, target_width: float, target_height: float) -> None:
    """Scale page content to target dimensions; swaps width/height for landscape pages."""
    cur_w = float(page.mediabox.width)
    cur_h = float(page.mediabox.height)
    if cur_w > cur_h:
        # Landscape: use landscape orientation of the target size
        page.scale_to(target_height, target_width)
    else:
        page.scale_to(target_width, target_height)


def combine_pdfs(
    input_folder: str,
    output_prefix: str = DEFAULT_OUTPUT_PREFIX,
    output_suffix: str = DEFAULT_OUTPUT_SUFFIX,
    output_middle: str = DEFAULT_OUTPUT_MIDDLE,
    sort_ascending: bool = DEFAULT_SORT_ASCENDING,
    normalize_page_size: bool = DEFAULT_NORMALIZE_PAGE_SIZE,
    target_page_size: str = DEFAULT_TARGET_PAGE_SIZE,
) -> str:
    """
    Combine all PDF files in a folder into a single PDF.

    Args:
        input_folder: Path to folder containing PDF files
        output_prefix: Prefix for output filename (e.g., "000_")
        output_suffix: Suffix for output filename (e.g., "_combined_PDFs")
        output_middle: Middle component of filename:
                       None = use folder name, "" = omit, "text" = use custom text
        sort_ascending: True for A-Z sort, False for Z-A
        normalize_page_size: Rescale all pages to a uniform paper size (fixes
                             scanned PDFs appearing oversized next to print-to-PDF pages)
        target_page_size: Target paper size key — "letter", "a4", "legal", or "a3"

    Returns:
        Path to the combined output PDF file
    """
    if not os.path.isdir(input_folder):
        raise NotADirectoryError(f"Input folder not found: {input_folder}")

    # Determine middle component of output filename
    if output_middle is None:
        # Use the folder name
        middle = os.path.basename(os.path.normpath(input_folder))
    else:
        # Use the provided string (can be empty)
        middle = output_middle

    # Find all PDF files in the folder (not in subfolders)
    pdf_files = [
        fn for fn in os.listdir(input_folder)
        if fn.lower().endswith('.pdf') and os.path.isfile(os.path.join(input_folder, fn))
    ]

    if not pdf_files:
        raise ValueError(f"No PDF files found in {input_folder!r}")

    # Sort files
    pdf_files = sorted(pdf_files, reverse=not sort_ascending)

    # Build output filename
    output_filename = f"{output_prefix}{middle}{output_suffix}.pdf"

    output_path = os.path.join(input_folder, output_filename)

    print(f"Input folder: {input_folder}")
    print(f"Found {len(pdf_files)} PDF file(s) to combine")
    print(f"Output file: {output_filename}")
    print("-" * 50)

    # Create PDF writer
    writer = PdfWriter()

    total_pages = 0

    for idx, filename in enumerate(pdf_files, start=1):
        file_path = os.path.join(input_folder, filename)

        try:
            reader = PdfReader(file_path)
            page_count = len(reader.pages)

            target_w, target_h = PAGE_SIZES[target_page_size.lower()]
            for page in reader.pages:
                if normalize_page_size:
                    _normalize_page(page, target_w, target_h)
                writer.add_page(page)

            total_pages += page_count
            print(f"[{idx}/{len(pdf_files)}] Added: {filename} ({page_count} page(s))")

        except Exception as e:
            print(f"[{idx}/{len(pdf_files)}] ERROR reading {filename}: {e}")
            continue

    if total_pages == 0:
        raise ValueError("No pages were successfully read from input PDFs")

    # Write combined PDF
    print("-" * 50)
    print(f"Writing combined PDF ({total_pages} total pages)...")

    with open(output_path, "wb") as f:
        writer.write(f)

    print(f"Saved: {output_path}")

    return output_path


def main():
    """
    Main entry point. Processes the folder specified in DEFAULT_INPUT_FOLDER.
    """
    input_folder = DEFAULT_INPUT_FOLDER

    if not input_folder:
        print("Error: Please set DEFAULT_INPUT_FOLDER in the USER CONFIG section.")
        print("       This should be a folder containing PDF files to combine.")
        return

    combine_pdfs(
        input_folder=input_folder,
        output_prefix=DEFAULT_OUTPUT_PREFIX,
        output_suffix=DEFAULT_OUTPUT_SUFFIX,
        output_middle=DEFAULT_OUTPUT_MIDDLE,
        sort_ascending=DEFAULT_SORT_ASCENDING,
        normalize_page_size=DEFAULT_NORMALIZE_PAGE_SIZE,
        target_page_size=DEFAULT_TARGET_PAGE_SIZE,
    )


if __name__ == "__main__":
    main()

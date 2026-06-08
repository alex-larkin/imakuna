# LLMs: refer to instructions in `Instructions_for_LLMs.md`, located at the root of the current workspace.
# (If you can't find the file, ignore this note.)

# Written by Claude (Opus 4.5) on 13 Jan, 2026, for Alex Larkin
# Config externalized to YAML by Claude (Opus 4.8) on 07 Jun, 2026, for Alex Larkin

"""pdf_add_page_numbers.py

Add page-number and/or filename footers to existing PDF files (single file or a
whole folder). See README.md for full usage, configuration, and behavior notes.

Created: 2026-01-13
"""

import os
from io import BytesIO
import yaml
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.colors import black

# ----------------------- CONFIG (YAML-backed) ----------------------------
# Settings live in pdf_add_page_numbers.yaml next to this script (gitignored;
# .yaml.template is the shared copy). The constants below are populated from
# that YAML at import time so the function defaults and main() keep working.
# Edit the YAML, not the constants. See README.md for the full reference.

# YAML config filename: same base name as this script, with a .yaml extension.
CONFIG_FILENAME = os.path.splitext(os.path.basename(__file__))[0] + ".yaml"

# Single source of truth for defaults: used to auto-create the config when it is
# missing and to backfill keys a user's config omits. input_path is blank so
# generated defaults never carry personal paths.
_DEFAULT_CONFIG_YAML = """\
# pdf_add_page_numbers.yaml -- settings for pdf_add_page_numbers.py (auto-created defaults)

paths:
  # Single PDF file OR a folder of PDFs to process.
  input_path: ""
  # Output path for single-file mode. Leave blank for auto-naming.
  # Ignored in folder mode (outputs go to a subfolder instead).
  output_path: ""

page_numbers:
  add: true
  # Alignment: left, right, center, outer, inner
  # (outer: odd->right, even->left;  inner: odd->left, even->right)
  align: outer
  # If true, the first page won't show a number.
  skip_first_page: false
  # If true, the first numbered page shows "1"; if false, the actual page number.
  first_page_is_one: true

filename_footer:
  add: true
  align: inner
  include_extension: false

blank_page:
  # Add a blank page when the document has an odd page count.
  add_if_odd: true
  # Footer text for the added blank page. Leave blank for no footer.
  text: "(página en blanco)"

formatting:
  font_name: Helvetica
  font_size: 9
  # Distance from the bottom edge, in millimetres.
  margin_bottom_mm: 10.0
  # Distance from the left/right edge for non-centered text, in millimetres.
  margin_side_mm: 15.0

output_naming:
  suffix: _numbered
  subfolder: numbered_output
"""


def _config_path() -> str:
    """Absolute path to config.yaml, resolved next to this script."""
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
    Load settings from config.yaml next to this script.

    Auto-creates config.yaml from built-in defaults (with no personal paths)
    if it is missing, then returns the parsed settings. Any keys absent from
    the user's file are backfilled from the defaults.
    """
    defaults = yaml.safe_load(_DEFAULT_CONFIG_YAML)
    path = _config_path()

    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(_DEFAULT_CONFIG_YAML)
        print(f"Created default config: {path}")
        print("Set 'input_path' in that file, then run again.")
        return defaults

    with open(path, "r", encoding="utf-8") as f:
        loaded = yaml.safe_load(f) or {}

    return _deep_merge(defaults, loaded)


_CFG = load_config()

# Constants derived from config.yaml. These feed the function default
# arguments and main(); to change behaviour, edit config.yaml instead.
DEFAULT_INPUT_PATH = _CFG["paths"]["input_path"]
DEFAULT_OUTPUT_PATH = _CFG["paths"]["output_path"]

DEFAULT_ADD_PAGE_NUMBERS = _CFG["page_numbers"]["add"]
DEFAULT_PAGE_NUMBER_ALIGN = _CFG["page_numbers"]["align"]
DEFAULT_SKIP_FIRST_PAGE_NUMBER = _CFG["page_numbers"]["skip_first_page"]
DEFAULT_FIRST_PAGE_IS_ONE = _CFG["page_numbers"]["first_page_is_one"]

DEFAULT_ADD_FILENAME = _CFG["filename_footer"]["add"]
DEFAULT_FILENAME_ALIGN = _CFG["filename_footer"]["align"]
DEFAULT_FILENAME_INCLUDE_EXTENSION = _CFG["filename_footer"]["include_extension"]

DEFAULT_ADD_BLANK_IF_ODD = _CFG["blank_page"]["add_if_odd"]
DEFAULT_BLANK_PAGE_TEXT = _CFG["blank_page"]["text"] or ""

DEFAULT_FONT_NAME = _CFG["formatting"]["font_name"]
DEFAULT_FONT_SIZE = _CFG["formatting"]["font_size"]
DEFAULT_MARGIN_BOTTOM_MM = _CFG["formatting"]["margin_bottom_mm"]
DEFAULT_MARGIN_SIDE_MM = _CFG["formatting"]["margin_side_mm"]

DEFAULT_OUTPUT_SUFFIX = _CFG["output_naming"]["suffix"]
DEFAULT_OUTPUT_SUBFOLDER = _CFG["output_naming"]["subfolder"]


def get_alignment_for_page(align: str, page_num: int, is_blank_page: bool = False) -> str:
    """
    Resolve alignment to 'left', 'right', or 'center' based on page number.

    For 'outer' alignment: odd pages -> right, even pages -> left
    For 'inner' alignment: odd pages -> left, even pages -> right

    Args:
        align: One of 'left', 'right', 'center', 'outer', 'inner'
        page_num: The actual page number (1-indexed)
        is_blank_page: If True, this is an added blank page

    Returns:
        One of 'left', 'right', 'center'
    """
    if align in ("left", "right", "center"):
        return align

    is_odd = (page_num % 2) == 1

    if align == "outer":
        return "right" if is_odd else "left"
    elif align == "inner":
        return "left" if is_odd else "right"
    else:
        raise ValueError(f"Unknown alignment: {align!r}. Use 'left', 'right', 'center', 'outer', or 'inner'.")


def create_overlay_page(
    width_pt: float,
    height_pt: float,
    page_num: int,
    total_pages: int,
    filename: str,
    add_page_numbers: bool,
    page_number_align: str,
    skip_first_page_number: bool,
    first_page_is_one: bool,
    add_filename: bool,
    filename_align: str,
    filename_include_extension: bool,
    font_name: str,
    font_size: int,
    margin_bottom_mm: float,
    margin_side_mm: float,
    is_blank_page: bool = False,
    blank_page_text: str = ""
) -> BytesIO:
    """
    Create a single-page PDF overlay with footer elements.

    Returns:
        BytesIO buffer containing a single-page PDF
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(width_pt, height_pt))

    margin_bottom_pt = margin_bottom_mm * mm
    margin_side_pt = margin_side_mm * mm

    c.setFont(font_name, font_size)
    c.setFillColor(black)

    # Handle blank page specially
    if is_blank_page:
        if blank_page_text:
            # Center the blank page text
            c.drawCentredString(width_pt / 2, margin_bottom_pt, blank_page_text)
        c.showPage()
        c.save()
        buffer.seek(0)
        return buffer

    # Check for alignment conflicts
    if add_page_numbers and add_filename:
        resolved_pn_align = get_alignment_for_page(page_number_align, page_num)
        resolved_fn_align = get_alignment_for_page(filename_align, page_num)
        if resolved_pn_align == resolved_fn_align:
            print(f"  Warning: Page {page_num} - page number and filename both aligned to '{resolved_pn_align}'")

    # Calculate display page number
    display_num = None
    if add_page_numbers:
        should_show = not (skip_first_page_number and page_num == 1)
        if should_show:
            if first_page_is_one:
                # If skipping first page, page 2 displays as "1", etc.
                if skip_first_page_number:
                    display_num = page_num - 1
                else:
                    display_num = page_num
            else:
                # Always show actual page number
                display_num = page_num

    # Draw page number
    if display_num is not None:
        resolved_align = get_alignment_for_page(page_number_align, page_num)
        text = str(display_num)

        if resolved_align == "center":
            c.drawCentredString(width_pt / 2, margin_bottom_pt, text)
        elif resolved_align == "left":
            c.drawString(margin_side_pt, margin_bottom_pt, text)
        elif resolved_align == "right":
            c.drawRightString(width_pt - margin_side_pt, margin_bottom_pt, text)

    # Draw filename
    if add_filename:
        if filename_include_extension:
            display_filename = filename
        else:
            display_filename = os.path.splitext(filename)[0]

        resolved_align = get_alignment_for_page(filename_align, page_num)

        if resolved_align == "center":
            c.drawCentredString(width_pt / 2, margin_bottom_pt, display_filename)
        elif resolved_align == "left":
            c.drawString(margin_side_pt, margin_bottom_pt, display_filename)
        elif resolved_align == "right":
            c.drawRightString(width_pt - margin_side_pt, margin_bottom_pt, display_filename)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


def add_footers_to_pdf(
    input_path: str,
    output_path: str = None,
    add_page_numbers: bool = DEFAULT_ADD_PAGE_NUMBERS,
    page_number_align: str = DEFAULT_PAGE_NUMBER_ALIGN,
    skip_first_page_number: bool = DEFAULT_SKIP_FIRST_PAGE_NUMBER,
    first_page_is_one: bool = DEFAULT_FIRST_PAGE_IS_ONE,
    add_filename: bool = DEFAULT_ADD_FILENAME,
    filename_align: str = DEFAULT_FILENAME_ALIGN,
    filename_include_extension: bool = DEFAULT_FILENAME_INCLUDE_EXTENSION,
    add_blank_if_odd: bool = DEFAULT_ADD_BLANK_IF_ODD,
    blank_page_text: str = DEFAULT_BLANK_PAGE_TEXT,
    font_name: str = DEFAULT_FONT_NAME,
    font_size: int = DEFAULT_FONT_SIZE,
    margin_bottom_mm: float = DEFAULT_MARGIN_BOTTOM_MM,
    margin_side_mm: float = DEFAULT_MARGIN_SIDE_MM,
    output_suffix: str = DEFAULT_OUTPUT_SUFFIX
) -> str:
    """
    Add page numbers and/or filename footer to an existing PDF.

    Args:
        input_path: Path to the input PDF file
        output_path: Path for output PDF (if None, auto-generates with suffix)
        add_page_numbers: Whether to add page numbers
        page_number_align: Alignment for page numbers ('left', 'right', 'center', 'outer', 'inner')
        skip_first_page_number: If True, first page won't show a number
        first_page_is_one: If True and skip_first_page_number, page 2 shows "1"
        add_filename: Whether to add filename to footer
        filename_align: Alignment for filename ('left', 'right', 'center', 'outer', 'inner')
        filename_include_extension: Whether to include file extension in footer
        add_blank_if_odd: Whether to add a blank page if document has odd page count
        blank_page_text: Text for blank page footer (empty string = no footer)
        font_name: Font name for footer text
        font_size: Font size in points
        margin_bottom_mm: Distance from bottom of page in mm
        margin_side_mm: Distance from side edges in mm (for left/right aligned text)
        output_suffix: Suffix to add to output filename

    Returns:
        Path to the output PDF file
    """
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # Generate output path if not specified
    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}{output_suffix}{ext}"

    # Get original filename for footer
    original_filename = os.path.basename(input_path)

    print(f"Processing: {original_filename}")

    # Read the input PDF
    reader = PdfReader(input_path)
    writer = PdfWriter()

    total_pages = len(reader.pages)
    needs_blank_page = add_blank_if_odd and (total_pages % 2) == 1

    # Process each page
    for page_num, page in enumerate(reader.pages, start=1):
        # Get page dimensions
        media_box = page.mediabox
        width_pt = float(media_box.width)
        height_pt = float(media_box.height)

        # Create overlay
        overlay_buffer = create_overlay_page(
            width_pt=width_pt,
            height_pt=height_pt,
            page_num=page_num,
            total_pages=total_pages,
            filename=original_filename,
            add_page_numbers=add_page_numbers,
            page_number_align=page_number_align,
            skip_first_page_number=skip_first_page_number,
            first_page_is_one=first_page_is_one,
            add_filename=add_filename,
            filename_align=filename_align,
            filename_include_extension=filename_include_extension,
            font_name=font_name,
            font_size=font_size,
            margin_bottom_mm=margin_bottom_mm,
            margin_side_mm=margin_side_mm
        )

        # Merge overlay onto original page
        overlay_reader = PdfReader(overlay_buffer)
        page.merge_page(overlay_reader.pages[0])
        writer.add_page(page)

        print(f"  Page {page_num}/{total_pages} complete")

    # Add blank page if needed
    if needs_blank_page:
        # Use dimensions from the last page
        last_page = reader.pages[-1]
        media_box = last_page.mediabox
        width_pt = float(media_box.width)
        height_pt = float(media_box.height)

        blank_page_num = total_pages + 1

        blank_buffer = create_overlay_page(
            width_pt=width_pt,
            height_pt=height_pt,
            page_num=blank_page_num,
            total_pages=total_pages + 1,
            filename=original_filename,
            add_page_numbers=False,  # No page number on blank page
            page_number_align=page_number_align,
            skip_first_page_number=skip_first_page_number,
            first_page_is_one=first_page_is_one,
            add_filename=False,  # No filename on blank page
            filename_align=filename_align,
            filename_include_extension=filename_include_extension,
            font_name=font_name,
            font_size=font_size,
            margin_bottom_mm=margin_bottom_mm,
            margin_side_mm=margin_side_mm,
            is_blank_page=True,
            blank_page_text=blank_page_text  # Leave empty for no footer on blank page
        )

        blank_reader = PdfReader(blank_buffer)
        writer.add_page(blank_reader.pages[0])
        print(f"  Added blank page ({blank_page_num})")

    # Write output
    with open(output_path, "wb") as f:
        writer.write(f)

    print(f"Saved: {output_path}")
    return output_path


def process_folder(
    input_folder: str,
    output_subfolder: str = DEFAULT_OUTPUT_SUBFOLDER,
    add_page_numbers: bool = DEFAULT_ADD_PAGE_NUMBERS,
    page_number_align: str = DEFAULT_PAGE_NUMBER_ALIGN,
    skip_first_page_number: bool = DEFAULT_SKIP_FIRST_PAGE_NUMBER,
    first_page_is_one: bool = DEFAULT_FIRST_PAGE_IS_ONE,
    add_filename: bool = DEFAULT_ADD_FILENAME,
    filename_align: str = DEFAULT_FILENAME_ALIGN,
    filename_include_extension: bool = DEFAULT_FILENAME_INCLUDE_EXTENSION,
    add_blank_if_odd: bool = DEFAULT_ADD_BLANK_IF_ODD,
    blank_page_text: str = DEFAULT_BLANK_PAGE_TEXT,
    font_name: str = DEFAULT_FONT_NAME,
    font_size: int = DEFAULT_FONT_SIZE,
    margin_bottom_mm: float = DEFAULT_MARGIN_BOTTOM_MM,
    margin_side_mm: float = DEFAULT_MARGIN_SIDE_MM,
    output_suffix: str = DEFAULT_OUTPUT_SUFFIX
) -> list:
    """
    Process all PDF files in a folder.

    Args:
        input_folder: Path to folder containing PDF files
        output_subfolder: Name of subfolder for output files
        (other args same as add_footers_to_pdf)

    Returns:
        List of output file paths
    """
    if not os.path.isdir(input_folder):
        raise NotADirectoryError(f"Input folder not found: {input_folder}")

    # Create output folder
    output_folder = os.path.join(input_folder, output_subfolder)
    os.makedirs(output_folder, exist_ok=True)

    # Find all PDF files
    pdf_files = sorted(
        fn for fn in os.listdir(input_folder)
        if fn.lower().endswith('.pdf') and os.path.isfile(os.path.join(input_folder, fn))
    )

    if not pdf_files:
        raise ValueError(f"No PDF files found in {input_folder!r}")

    print(f"Found {len(pdf_files)} PDF file(s) in {input_folder}")
    print(f"Output folder: {output_folder}")
    print("-" * 50)

    output_paths = []

    for idx, filename in enumerate(pdf_files, start=1):
        print(f"\n[{idx}/{len(pdf_files)}] {filename}")

        input_path = os.path.join(input_folder, filename)

        # Generate output filename with suffix
        base, ext = os.path.splitext(filename)
        output_filename = f"{base}{output_suffix}{ext}"
        output_path = os.path.join(output_folder, output_filename)

        result_path = add_footers_to_pdf(
            input_path=input_path,
            output_path=output_path,
            add_page_numbers=add_page_numbers,
            page_number_align=page_number_align,
            skip_first_page_number=skip_first_page_number,
            first_page_is_one=first_page_is_one,
            add_filename=add_filename,
            filename_align=filename_align,
            filename_include_extension=filename_include_extension,
            add_blank_if_odd=add_blank_if_odd,
            blank_page_text=blank_page_text,
            font_name=font_name,
            font_size=font_size,
            margin_bottom_mm=margin_bottom_mm,
            margin_side_mm=margin_side_mm,
            output_suffix=""  # Already applied to output_path
        )
        output_paths.append(result_path)

    print("\n" + "=" * 50)
    print(f"Completed processing {len(output_paths)} file(s)")

    return output_paths


def main():
    """
    Main entry point. Determines whether input is a file or folder
    and processes accordingly.
    """
    input_path = DEFAULT_INPUT_PATH

    if not input_path:
        print("Error: Please set DEFAULT_INPUT_PATH in the USER CONFIG section.")
        print("       This can be a single PDF file or a folder containing PDFs.")
        return

    if os.path.isfile(input_path):
        # Single file mode
        add_footers_to_pdf(
            input_path=input_path,
            output_path=DEFAULT_OUTPUT_PATH if DEFAULT_OUTPUT_PATH else None,
            add_page_numbers=DEFAULT_ADD_PAGE_NUMBERS,
            page_number_align=DEFAULT_PAGE_NUMBER_ALIGN,
            skip_first_page_number=DEFAULT_SKIP_FIRST_PAGE_NUMBER,
            first_page_is_one=DEFAULT_FIRST_PAGE_IS_ONE,
            add_filename=DEFAULT_ADD_FILENAME,
            filename_align=DEFAULT_FILENAME_ALIGN,
            filename_include_extension=DEFAULT_FILENAME_INCLUDE_EXTENSION,
            add_blank_if_odd=DEFAULT_ADD_BLANK_IF_ODD,
            blank_page_text=DEFAULT_BLANK_PAGE_TEXT,
            font_name=DEFAULT_FONT_NAME,
            font_size=DEFAULT_FONT_SIZE,
            margin_bottom_mm=DEFAULT_MARGIN_BOTTOM_MM,
            margin_side_mm=DEFAULT_MARGIN_SIDE_MM,
            output_suffix=DEFAULT_OUTPUT_SUFFIX
        )
    elif os.path.isdir(input_path):
        # Folder mode
        process_folder(
            input_folder=input_path,
            output_subfolder=DEFAULT_OUTPUT_SUBFOLDER,
            add_page_numbers=DEFAULT_ADD_PAGE_NUMBERS,
            page_number_align=DEFAULT_PAGE_NUMBER_ALIGN,
            skip_first_page_number=DEFAULT_SKIP_FIRST_PAGE_NUMBER,
            first_page_is_one=DEFAULT_FIRST_PAGE_IS_ONE,
            add_filename=DEFAULT_ADD_FILENAME,
            filename_align=DEFAULT_FILENAME_ALIGN,
            filename_include_extension=DEFAULT_FILENAME_INCLUDE_EXTENSION,
            add_blank_if_odd=DEFAULT_ADD_BLANK_IF_ODD,
            blank_page_text=DEFAULT_BLANK_PAGE_TEXT,
            font_name=DEFAULT_FONT_NAME,
            font_size=DEFAULT_FONT_SIZE,
            margin_bottom_mm=DEFAULT_MARGIN_BOTTOM_MM,
            margin_side_mm=DEFAULT_MARGIN_SIDE_MM,
            output_suffix=DEFAULT_OUTPUT_SUFFIX
        )
    else:
        print(f"Error: Input path not found: {input_path}")


if __name__ == "__main__":
    main()

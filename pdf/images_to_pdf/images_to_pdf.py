# LLMs: refer to instructions in `Instructions_for_LLMs.md`, located at the root of the current workspace.
# (If you can't find the file, ignore this note.)

# Written by Claude (Opus 4.8) on 07 Jun, 2026, for Alex Larkin

import os
import yaml
import cv2
import numpy as np
from PIL import Image, ImageOps
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm, inch
from reportlab.lib.colors import black
from reportlab.lib.utils import ImageReader
from io import BytesIO

"""images_to_pdf.py

Convert a folder of images into a single PDF (one page per image), with
optional deskewing, pagination, JPEG compression, and printer crop marks.

See README.md for full usage, configuration, and behavior notes.

Created: 2025-12-20
"""

# ---------------------- Page size constants (A0..A6) ----------------------
# Width and height are expressed in ReportLab points using the `mm` unit.
A0_W = 841 * mm
A0_H = 1189 * mm
A1_W = 594 * mm
A1_H = 841 * mm
A2_W = 420 * mm
A2_H = 594 * mm
A3_W = 297 * mm
A3_H = 420 * mm
A4_W = 210 * mm
A4_H = 297 * mm
A5_W = 148 * mm
A5_H = 210 * mm
A6_W = 105 * mm
A6_H = 148 * mm

A_SIZES = {
    'A0': (A0_W, A0_H),
    'A1': (A1_W, A1_H),
    'A2': (A2_W, A2_H),
    'A3': (A3_W, A3_H),
    'A4': (A4_W, A4_H),
    'A5': (A5_W, A5_H),
    'A6': (A6_W, A6_H),
}

# ------------------ US page size constants (inches) ----------------------
# Common North American paper sizes, expressed in ReportLab points using the
# `inch` unit. Dimensions are (width, height) in portrait orientation.
LETTER_W = 8.5 * inch       # 8.5 x 11   in
LETTER_H = 11 * inch
LEGAL_W = 8.5 * inch        # 8.5 x 14   in
LEGAL_H = 14 * inch
TABLOID_W = 11 * inch       # 11 x 17    in (also called Ledger in landscape)
TABLOID_H = 17 * inch
EXECUTIVE_W = 7.25 * inch   # 7.25 x 10.5 in
EXECUTIVE_H = 10.5 * inch
STATEMENT_W = 5.5 * inch    # 5.5 x 8.5  in (Half Letter)
STATEMENT_H = 8.5 * inch
JUNIOR_LEGAL_W = 5 * inch   # 5 x 8      in
JUNIOR_LEGAL_H = 8 * inch

US_SIZES = {
    'LETTER': (LETTER_W, LETTER_H),
    'LEGAL': (LEGAL_W, LEGAL_H),
    'TABLOID': (TABLOID_W, TABLOID_H),
    'EXECUTIVE': (EXECUTIVE_W, EXECUTIVE_H),
    'STATEMENT': (STATEMENT_W, STATEMENT_H),
    'JUNIOR_LEGAL': (JUNIOR_LEGAL_W, JUNIOR_LEGAL_H),
}

# All named page sizes in one lookup (A-series + US).
PAGE_SIZES = dict(A_SIZES)
PAGE_SIZES.update(US_SIZES)
# Friendly aliases for sizes that go by more than one name.
PAGE_SIZES['LEDGER'] = (TABLOID_W, TABLOID_H)
PAGE_SIZES['HALF_LETTER'] = (STATEMENT_W, STATEMENT_H)


def get_page_size_by_name(name: str):
    """Return (width_pt, height_pt) for a given page size name.

    Accepts A-series names (e.g. 'A4') and US names (e.g. 'LETTER', 'LEGAL').
    Raises ValueError for unknown names.
    """
    if not isinstance(name, str):
        raise ValueError('page size name must be a string like "A4" or "LETTER"')
    key = name.strip().upper()
    if key not in PAGE_SIZES:
        raise ValueError(f'Unsupported page size: {name!r}. Use one of: {list(PAGE_SIZES.keys())}')
    return PAGE_SIZES[key]


def mm_to_pt(mm_value: float) -> float:
    """Convert millimetres to PostScript points (1 in = 25.4 mm, 72 pt/in)."""
    return float(mm_value) * 72.0 / 25.4


def pt_to_mm(pt_value: float) -> float:
    """Convert PostScript points to millimetres."""
    return float(pt_value) * 25.4 / 72.0


# --------------------------- USER CONFIG ---------------------------------
# Settings live in images_to_pdf.yaml next to this script (git-ignored,
# auto-created on first run). See README.md for details.

# Config file sits beside this script regardless of the current working dir.
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "images_to_pdf.yaml")

# Built-in defaults: used to auto-generate a fresh config and as fallbacks for
# any keys missing from the user's file. Kept free of personal info.
_DEFAULT_CONFIG = {
    "paths": {
        "input_folder": "./input",
        "output_pdf": "./output/output.pdf",
    },
    "page": {
        "size": "A4",        # 'A4', 'A5', 'A3', etc. (A0..A6)
        "margin_cm": 0.75,   # Margin around image in cm
        "bleed_mm": 3.0,     # Bleed in millimetres (used if crop_bleed is true)
    },
    "options": {
        "paginate": False,           # Add page numbers at bottom center
        "deskew": False,             # Deskew each image before adding to PDF
        "crop_bleed": True,          # Draw crop marks + bleed
        "detect_orientation": False, # Match each page's orientation to its image
    },
    "image": {
        "target_dpi": 250,   # Target DPI for images without DPI info
        "jpeg_quality": 85,  # JPEG compression quality (1-100)
    },
}

# YAML written verbatim when auto-creating the config, so the generated file
# keeps explanatory comments rather than being a bare value dump.
_DEFAULT_CONFIG_YAML = """\
# Configuration for images_to_pdf.py
# Edit these values to control a run. Paths may be relative (./folder) or
# absolute. This file is git-ignored: keep personal paths here, not in the .py.

paths:
  input_folder: ./input          # Folder of source images (png/jpg/jpeg/tiff/bmp)
  output_pdf: ./output/output.pdf # Where the combined PDF is written

page:
  size: A4          # ISO A-series name: A0, A1, A2, A3, A4, A5, A6
  margin_cm: 0.75   # Margin around the image, in centimetres
  bleed_mm: 3.0     # Bleed in millimetres (used only if options.crop_bleed)

options:
  paginate: false           # Draw a centered page number near the bottom
  deskew: false             # Auto-straighten each image before placing it
  crop_bleed: true          # Draw hairline crop marks around the trim edges
  detect_orientation: false # Make a page landscape when its image is wider than tall
                            # (near-square images, within 2%, stay portrait)

image:
  target_dpi: 250   # Assumed DPI for images that carry no DPI metadata
  jpeg_quality: 85  # JPEG compression quality, 1 (smallest) to 100 (best)
"""


def load_config(config_path: str = CONFIG_PATH) -> dict:
    """Load settings from the YAML config, auto-creating it if missing.

    Returns a nested dict mirroring _DEFAULT_CONFIG; keys absent from the file
    fall back to the built-in defaults.
    """
    if not os.path.exists(config_path):
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(_DEFAULT_CONFIG_YAML)
        print(f"Created default config: {config_path}\n"
              f"Edit it to set your input/output paths, then run again.")

    with open(config_path, "r", encoding="utf-8") as f:
        loaded = yaml.safe_load(f) or {}

    # Merge loaded values over defaults, one section at a time.
    cfg = {section: dict(values) for section, values in _DEFAULT_CONFIG.items()}
    for section, values in loaded.items():
        if section in cfg and isinstance(values, dict):
            cfg[section].update(values)
        else:
            cfg[section] = values
    return cfg


# Load once at import so the function defaults below reflect the user's config.
_CFG = load_config()

DEFAULT_INPUT_FOLDER = _CFG["paths"]["input_folder"]
DEFAULT_OUTPUT_PDF = _CFG["paths"]["output_pdf"]
DEFAULT_PAGE_SIZE = _CFG["page"]["size"]        # e.g. 'A4', or a (w_pt, h_pt) tuple
DEFAULT_PAGINATE = _CFG["options"]["paginate"]  # Add page numbers at bottom center
DEFAULT_DESKEW = _CFG["options"]["deskew"]      # Deskew each image before adding
DEFAULT_TARGET_DPI = _CFG["image"]["target_dpi"]    # DPI for images without DPI info
DEFAULT_MARGIN_CM = _CFG["page"]["margin_cm"]       # Margin around image in cm
DEFAULT_JPEG_QUALITY = _CFG["image"]["jpeg_quality"]  # JPEG quality (1-100)
DEFAULT_CROP_BLEED = _CFG["options"]["crop_bleed"]    # Draw crop marks + bleed
DEFAULT_BLEED_MM = _CFG["page"]["bleed_mm"]           # Bleed in millimetres
DEFAULT_DETECT_ORIENTATION = _CFG["options"]["detect_orientation"]  # Per-page orientation


def deskew_image(pil_img, delta=1, limit=5):
    """
    Detects the skew angle via Hough lines and rotates the image to deskew.
    Returns a new PIL Image.
    """
    # Convert to grayscale numpy array
    gray = np.array(pil_img.convert('L'))

    # Binarize (invert for Hough)
    _, bw = cv2.threshold(gray, 0, 255,
                          cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Detect lines
    lines = cv2.HoughLines(bw, 1, np.pi/180, threshold=200)
    if lines is None:
        return pil_img

    # Collect angles within limit
    angles = []
    for rho, theta in lines[:, 0]:
        angle_deg = (theta - np.pi/2) * (180/np.pi)
        if abs(angle_deg) < limit:
            angles.append(angle_deg)
    if not angles:
        return pil_img

    # Median angle
    skew = np.median(angles)

    # Rotate original image by negative skew
    return pil_img.rotate(-skew, resample=Image.BICUBIC, expand=False)

def images_to_pdf(
    input_folder: str,
    output_pdf: str,
    paginate: bool = DEFAULT_PAGINATE,
    deskew: bool = DEFAULT_DESKEW,
    target_dpi: int = DEFAULT_TARGET_DPI,
    page_size = DEFAULT_PAGE_SIZE,  # Accept either a string like 'A4' or a (w_pt, h_pt) tuple
    margin_cm: float = DEFAULT_MARGIN_CM,                   # Default margin in cm
    jpeg_quality: int = DEFAULT_JPEG_QUALITY,                   # JPEG compression quality (1-100)
    crop_bleed: bool = DEFAULT_CROP_BLEED,                      # Whether to draw crop marks + bleed
    bleed_mm: float = DEFAULT_BLEED_MM,                          # Bleed in millimetres
    detect_orientation: bool = DEFAULT_DETECT_ORIENTATION        # Match page orientation to each image
):
    # Resolve page_size if given as a name. These are the base dimensions; when
    # detect_orientation is on, each page may swap them to match its image.
    if isinstance(page_size, str):
        width_pt, height_pt = get_page_size_by_name(page_size)
    else:
        width_pt, height_pt = page_size
    margin_pt = margin_cm * 10 * mm  # 1 cm = 10 mm

    # Validate the output path before doing any work. ReportLab only tries to
    # open the file at the very end (c.save), so a bad path otherwise wastes the
    # whole render and surfaces a misleading "Permission denied" on Windows when
    # the path is actually a folder.
    if os.path.isdir(output_pdf):
        raise ValueError(
            f"output_pdf must be a file path ending in .pdf, not a folder: {output_pdf!r}. Edit the `output_pdf` variable in the .yaml file."
        )
    if not output_pdf.lower().endswith(".pdf"):
        raise ValueError(
            f"output_pdf must end in .pdf (or .PDF): {output_pdf!r}. Edit the `output_pdf` variable in the .yaml file."
        )
    out_dir = os.path.dirname(output_pdf)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)  # Create the destination folder if needed

    # Gather and sort images
    files = sorted(fn for fn in os.listdir(input_folder)
                   if fn.lower().endswith(('.png','jpg','jpeg','tiff','bmp')))
    if not files:
        raise ValueError(f"No images in {input_folder!r}")

    c = canvas.Canvas(output_pdf, pagesize=(width_pt, height_pt))

    for idx, fn in enumerate(files, start=1):
        path = os.path.join(input_folder, fn)
        img = Image.open(path)

        # Honor any EXIF orientation flag so detection and placement match what
        # a viewer shows (phone photos are often stored rotated). This bakes the
        # rotation into the pixels, after which img.size is the as-seen size.
        img = ImageOps.exif_transpose(img)

        # Ensure transparent images are composited onto white so they
        # print white (not black) when flattened. Handle RGBA/LA and
        # paletted images with a transparency entry.
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and 'transparency' in img.info):
            rgba = img.convert("RGBA")
            alpha = rgba.split()[-1]
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(rgba, mask=alpha)
            img = bg
        else:
            img = img.convert("RGB")

        # Optional deskew
        if deskew:
            print(f"Deskewing page {idx}: {fn} ...")
            img = deskew_image(img)
            print(f"Deskewed page {idx}: {fn}")

        px_w, px_h = img.size
        img_dpi = img.info.get('dpi', (target_dpi,))[0]

        # Choose this page's dimensions. With detect_orientation on, a page goes
        # landscape only when the image is more than 2% wider than tall; anything
        # squarer than that (including portrait) stays vertical. sorted() makes
        # this robust no matter which way the base size tuple was given.
        if detect_orientation:
            short_side, long_side = sorted((width_pt, height_pt))
            if px_w > px_h * 1.02:
                page_w, page_h = long_side, short_side  # landscape
            else:
                page_w, page_h = short_side, long_side  # portrait / near-square
        else:
            page_w, page_h = width_pt, height_pt
        c.setPageSize((page_w, page_h))

        # Calculate available area for image (subtract margins)
        avail_w = page_w - 2 * margin_pt
        avail_h = page_h - 2 * margin_pt

        # Calculate image size in points at its DPI
        img_w_pt = (px_w / img_dpi) * 72
        img_h_pt = (px_h / img_dpi) * 72

        # Scale image to fit within available area, preserving aspect ratio
        scale = min(avail_w / img_w_pt, avail_h / img_h_pt, 1.0)
        disp_w = img_w_pt * scale
        disp_h = img_h_pt * scale

        # Center image within margins
        x = margin_pt + (avail_w - disp_w) / 2
        y = margin_pt + (avail_h - disp_h) / 2

        # Compress image to JPEG in memory with user-set quality
        img_buffer = BytesIO()
        img.save(img_buffer, format='JPEG', quality=jpeg_quality)
        img_buffer.seek(0)
        img_reader = ImageReader(img_buffer)

        c.drawImage(img_reader, x, y, disp_w, disp_h)

        # Optional: draw bleed area and crop marks relative to the image (trim) edges
        if crop_bleed:
             # Measurements: bleed, small gap from image edge, and crop mark length
             bleed_pt = mm_to_pt(bleed_mm)
             gap_pt = mm_to_pt(0.5)
             mark_len_pt = mm_to_pt(5.0)

             trim_left = x
             trim_right = x + disp_w
             trim_bottom = y
             trim_top = y + disp_h

             # Style: 100% black, thin hairline ~0.25-0.5 pt
             stroke_w = 0.35
             c.setStrokeColor(black)
             c.setLineWidth(stroke_w)

             # Top-left corner (L-shape outside trim)
             c.line(trim_left - gap_pt - mark_len_pt, trim_top + gap_pt,
                 trim_left - gap_pt, trim_top + gap_pt)
             c.line(trim_left - gap_pt, trim_top + gap_pt,
                 trim_left - gap_pt, trim_top + gap_pt + mark_len_pt)

             # Top-right
             c.line(trim_right + gap_pt, trim_top + gap_pt,
                 trim_right + gap_pt + mark_len_pt, trim_top + gap_pt)
             c.line(trim_right + gap_pt, trim_top + gap_pt,
                 trim_right + gap_pt, trim_top + gap_pt + mark_len_pt)

             # Bottom-left
             c.line(trim_left - gap_pt - mark_len_pt, trim_bottom - gap_pt,
                 trim_left - gap_pt, trim_bottom - gap_pt)
             c.line(trim_left - gap_pt, trim_bottom - gap_pt - mark_len_pt,
                 trim_left - gap_pt, trim_bottom - gap_pt)

             # Bottom-right
             c.line(trim_right + gap_pt, trim_bottom - gap_pt,
                 trim_right + gap_pt + mark_len_pt, trim_bottom - gap_pt)
             c.line(trim_right + gap_pt, trim_bottom - gap_pt - mark_len_pt,
                 trim_right + gap_pt, trim_bottom - gap_pt)

        if paginate:
            c.setFont("Helvetica", 9)
            c.setFillColor(black)
            c.drawCentredString(page_w/2, 10 * mm, str(idx))

        c.showPage()
        print(f"Completed page {idx}: {fn}")

    print("Finalizing PDF file, please wait. This may take several minutes, depending on the size of the file.")
    c.save()
    print(f"PDF saved to: {output_pdf}")

if __name__ == "__main__":
    images_to_pdf(
        input_folder=DEFAULT_INPUT_FOLDER,
        output_pdf=DEFAULT_OUTPUT_PDF,
        paginate=DEFAULT_PAGINATE,
        deskew=DEFAULT_DESKEW,
        target_dpi=DEFAULT_TARGET_DPI,
        page_size=DEFAULT_PAGE_SIZE,
        margin_cm=DEFAULT_MARGIN_CM,
        jpeg_quality=DEFAULT_JPEG_QUALITY,
        crop_bleed=DEFAULT_CROP_BLEED,
        bleed_mm=DEFAULT_BLEED_MM,
        detect_orientation=DEFAULT_DETECT_ORIENTATION,
    )
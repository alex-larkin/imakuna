# images_to_pdf.py

_Note: Written by Claude (Opus 4.8) on 07 Jun, 2026, for Alex Larkin_

## Overview

**images_to_pdf.py** converts a folder of images into a single PDF. Each image
becomes one page, sized and centered on an ISO A-series page (A0-A6) or a common
US page (Letter, Legal, etc.), with optional deskewing, page numbering, JPEG
compression, and printer crop marks with bleed. (The deskewing feature has not
yet been tested.)

It is aimed at print-ready output: images are placed at their real-world size
(based on DPI), centered within configurable margins, and never enlarged past
100% so they stay sharp.

## What it does, step by step

For every image in the input folder (sorted by filename), the script:

1. **Flattens transparency** onto a white background, so transparent PNGs print
   white instead of black.
2. **Optionally deskews** the image by detecting near-horizontal lines (Hough
   transform) and rotating by the median skew angle. (Feature not yet tested.)
3. **Sizes the image** in PostScript points using its DPI metadata (falling back
   to `target_dpi` when the image carries no DPI info).
4. **Scales to fit** the available area (page minus margins), preserving aspect
   ratio and never scaling above 100%.
5. **Centers** the image horizontally and vertically within the margins.
6. **Compresses** the image to JPEG in memory at the configured quality, then
   draws it onto the page.
7. **Optionally draws crop marks** (hairline L-shapes just outside each trim
   corner) and **page numbers** (centered near the bottom).

When all pages are drawn, the combined PDF is saved to the output path.

## Requirements

- Python 3
- Packages: `pyyaml`, `opencv-python` (`cv2`), `numpy`, `Pillow` (`PIL`),
  `reportlab`

```powershell
pip install pyyaml opencv-python numpy Pillow reportlab
```

## Setup and use

1. **First run** auto-creates a config file, `images_to_pdf.yaml`, next to the
   script (using safe, non-personal defaults) and then exits with a message.
   You can also rename `images_to_pdf.yaml.template` to `images_to_pdf.yaml`
   manually.
2. **Edit `images_to_pdf.yaml`** to point at your input folder and output path,
   and to adjust any options (see below).
3. **Run the script:**

   ```powershell
   python images_to_pdf.py
   ```

   The PDF is written to the `output_pdf` path from your config.

> `images_to_pdf.yaml` is git-ignored so your personal paths are never
> committed. Share `images_to_pdf.yaml.template` instead. Any keys missing from
> your `.yaml` fall back to built-in defaults, so an older config keeps working
> after new settings are added.

### Calling from another script

`images_to_pdf(...)` can also be imported and called directly, passing explicit
values to override the config defaults:

```python
from images_to_pdf import images_to_pdf

images_to_pdf(
    input_folder="./scans",
    output_pdf="./out/book.pdf",
    page_size="A4",
    deskew=True,
    crop_bleed=True,
)
```

## Configuration reference

All settings live in `images_to_pdf.yaml`:

| Section   | Key            | Type    | Default              | Meaning |
|-----------|----------------|---------|----------------------|---------|
| `paths`   | `input_folder` | string  | `./input`            | Folder of source images (`png`, `jpg`, `jpeg`, `tiff`, `bmp`). |
| `paths`   | `output_pdf`   | string  | `./output/output.pdf`| Where the combined PDF is written. |
| `page`    | `size`         | string  | `A4`                 | Page name (case-insensitive): ISO A-series `A0`-`A6`, or US `LETTER`, `LEGAL`, `TABLOID` (alias `LEDGER`), `EXECUTIVE`, `STATEMENT` (alias `HALF_LETTER`), `JUNIOR_LEGAL`. |
| `page`    | `margin_cm`    | number  | `0.75`               | Margin around the image, in centimetres. |
| `page`    | `bleed_mm`     | number  | `3.0`                | Bleed in millimetres (used only when `crop_bleed` is true). |
| `options` | `paginate`     | boolean | `false`              | Draw a centered page number near the bottom. |
| `options` | `deskew`       | boolean | `false`              | Auto-straighten each image before placing it. |
| `options` | `crop_bleed`   | boolean | `true`               | Draw hairline crop marks around the trim edges. |
| `image`   | `target_dpi`   | integer | `250`                | Assumed DPI for images with no DPI metadata. |
| `image`   | `jpeg_quality` | integer | `85`                 | JPEG compression quality, 1 (smallest) to 100 (best). |

Paths may be relative (`./folder`) or absolute.

### Page sizes

All names are case-insensitive and given in portrait orientation. ISO A-series
sizes (`A0`-`A6`) are defined in millimetres; US sizes in inches:

| Name | Size | Aliases |
|------|------|---------|
| `A0` | 841 x 1189 mm | |
| `A1` | 594 x 841 mm | |
| `A2` | 420 x 594 mm | |
| `A3` | 297 x 420 mm | |
| `A4` | 210 x 297 mm | |
| `A5` | 148 x 210 mm | |
| `A6` | 105 x 148 mm | |
| `LETTER` | 8.5 x 11 in | |
| `LEGAL` | 8.5 x 14 in | |
| `TABLOID` | 11 x 17 in | `LEDGER` |
| `EXECUTIVE` | 7.25 x 10.5 in | |
| `STATEMENT` | 5.5 x 8.5 in | `HALF_LETTER` |
| `JUNIOR_LEGAL` | 5 x 8 in | |

## Notes on behavior

- **Centering:** when an image (at its DPI) does not fill the available page
  area, it is centered both horizontally and vertically within the margins.
- **Scaling:** images larger than the available area are scaled down to fit;
  smaller images are left at their natural size (never enlarged).
- **Pagination:** when `paginate` is enabled, a centered page number is drawn
  about 10 mm from the bottom of each page.
- **Crop marks:** when `crop_bleed` is enabled, thin (~0.35 pt) black L-shaped
  marks are drawn just outside each corner of the image's trim box.

## Files

- `images_to_pdf.py` - the script.
- `images_to_pdf.yaml` - your local config (git-ignored, auto-created).
- `images_to_pdf.yaml.template` - shareable config template (committed).

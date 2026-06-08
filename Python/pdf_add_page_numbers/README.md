# pdf_add_page_numbers.py

_Note: Written by Claude (Opus 4.8) on 07 Jun, 2026, for Alex Larkin_

## Overview

**pdf_add_page_numbers.py** adds page-number and/or filename footers to existing
PDF files. It can process a single PDF or every PDF in a folder. The original
pages are left untouched -- the footer text is drawn on a transparent overlay
that is merged onto each page, so existing content is never re-rendered or
degraded.

Features:

- **Page numbers** with flexible alignment (left, right, center, outer, inner).
- **Filename footer** with its own flexible alignment.
- **Skip the first page** when numbering (e.g. for a cover or title page).
- **Start numbering at "1"** on the first numbered page, or keep the document's
  actual page numbers.
- **Add a blank page** when the document has an odd page count (handy for
  duplex/booklet printing), with optional footer text.
- Configurable **font, font size, and margins**.

## How it works, step by step

For each page of the input PDF the script:

1. **Reads the page size** (from its media box) so the overlay matches exactly.
2. **Builds a single-page overlay** in memory (via ReportLab) containing the page
   number and/or filename, positioned according to the resolved alignment and
   margins.
3. **Resolves alignment per page** for `outer`/`inner` modes -- `outer` puts text
   on the right for odd pages and the left for even pages; `inner` does the
   reverse. This keeps footers on the correct edge for double-sided printing.
4. **Merges the overlay** onto the original page (via pypdf) and writes the result
   to the output PDF.

If `add_if_odd` is enabled and the document has an odd number of pages, a final
blank page (optionally carrying a centered footer such as "(blank page)")
is appended so the total page count is even.

When page number and filename footers resolve to the same edge on a given page,
the script prints a warning so you can adjust their alignments.

## Requirements

- Python 3
- Packages: `pyyaml`, `pypdf`, `reportlab`

```powershell
pip install pyyaml pypdf reportlab
```

## Setup and use

1. **First run** auto-creates a config file, `pdf_add_page_numbers.yaml`, next to
   the script (using safe, non-personal defaults) and then exits with a message. 
   You can also take `pdf_combine.yaml.template`, remove the `.template` extension, 
   and edit it. 
2. Be sure to **Edit `pdf_add_page_numbers.yaml`** to set `input_path` (a single PDF file or
   a folder of PDFs) and adjust any options (see below).
3. **Run the script:**

   ```powershell
   python pdf_add_page_numbers.py
   ```

   - If `input_path` is a **file**, the output goes to `output_path` (or, if that
     is blank, alongside the input with the `_numbered` suffix).
   - If `input_path` is a **folder**, every `.pdf` in it is processed and the
     results are written to a `numbered_output` subfolder (each with the
     `_numbered` suffix). `output_path` is ignored in folder mode.

> `pdf_add_page_numbers.yaml` should be git-ignored so your personal paths aren't
> committed. Share `pdf_add_page_numbers.yaml.template` instead. Any keys missing
> from your `.yaml` fall back to built-in defaults, so an older config keeps
> working after new settings are added.

### Calling from another script

The two main functions can be imported and called directly, passing explicit
values to override the config defaults:

```python
from pdf_add_page_numbers import add_footers_to_pdf, process_folder

# Single file
add_footers_to_pdf(
    input_path="./report.pdf",
    page_number_align="outer",
    add_filename=False,
)

# Whole folder
process_folder(
    input_folder="./reports",
    output_subfolder="numbered_output",
)
```

## Configuration reference

All settings live in `pdf_add_page_numbers.yaml`:

| Section            | Key                 | Type    | Default              | Meaning |
|--------------------|---------------------|---------|----------------------|---------|
| `paths`            | `input_path`        | string  | `""`                 | Single PDF file **or** a folder of PDFs to process. Must be set before running. |
| `paths`            | `output_path`       | string  | `""`                 | Output path for single-file mode. Blank = auto-name with the suffix. Ignored in folder mode. |
| `page_numbers`     | `add`               | boolean | `true`               | Whether to draw page numbers. |
| `page_numbers`     | `align`             | string  | `outer`              | `left`, `right`, `center`, `outer`, or `inner` (see below). |
| `page_numbers`     | `skip_first_page`   | boolean | `false`              | If true, the first page shows no number. |
| `page_numbers`     | `first_page_is_one` | boolean | `true`               | If true, the first numbered page shows "1"; if false, the document's actual page number. |
| `filename_footer`  | `add`               | boolean | `true`               | Whether to draw the filename in the footer. |
| `filename_footer`  | `align`             | string  | `inner`              | `left`, `right`, `center`, `outer`, or `inner`. |
| `filename_footer`  | `include_extension` | boolean | `false`              | Include the `.pdf` extension in the footer text. |
| `blank_page`       | `add_if_odd`        | boolean | `true`               | Append a blank page when the document has an odd page count. |
| `blank_page`       | `text`              | string  | `(página en blanco)` | Centered footer for the added blank page. Blank = no footer. |
| `formatting`       | `font_name`         | string  | `Helvetica`          | Font for footer text (a standard PDF font). |
| `formatting`       | `font_size`         | integer | `9`                  | Font size in points. |
| `formatting`       | `margin_bottom_mm`  | number  | `10.0`               | Distance of footer text from the bottom edge, in millimetres. |
| `formatting`       | `margin_side_mm`    | number  | `15.0`               | Distance from the left/right edge for non-centered text, in millimetres. |
| `output_naming`    | `suffix`            | string  | `_numbered`          | Suffix added to output filenames. |
| `output_naming`    | `subfolder`         | string  | `numbered_output`    | Subfolder name for folder-mode output. |

Paths may be relative (`./folder`) or absolute.

### Alignment modes

`align` accepts five values. `left`, `right`, and `center` are fixed on every
page. The two "smart" modes alternate by page parity so footers land on the
correct edge for double-sided (duplex) printing:

| Mode     | Odd pages | Even pages |
|----------|-----------|------------|
| `left`   | left      | left       |
| `right`  | right     | right      |
| `center` | center    | center     |
| `outer`  | right     | left       |
| `inner`  | left      | right      |

A common pairing is page numbers `outer` and filename `inner`, so the two never
collide on the same edge.

## Notes on behavior

- **Start numbering:** with `skip_first_page: true` and `first_page_is_one:
  true`, the cover page is unnumbered and the second page displays "1".
- **Blank page:** the appended blank page never carries a page number or
  filename -- only the optional `blank_page.text`.
- **Alignment collisions:** if the page number and filename resolve to the same
  edge on a page, the script prints a warning (it still draws both, overlapping).

## Files

- `pdf_add_page_numbers.py` - the script.
- `pdf_add_page_numbers.yaml` - your local config (git-ignored, auto-created).
- `pdf_add_page_numbers.yaml.template` - shareable config template (committed).

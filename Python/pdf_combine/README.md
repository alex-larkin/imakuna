# pdf_combine

_Note: Written by Claude (Opus 4.8) on 07 Jun, 2026, for Alex Larkin_

Combine every PDF in a folder into a single PDF document.

## What it does

`pdf_combine.py` reads all of the `.pdf` files sitting directly inside one
folder (files in subfolders are ignored), concatenates them in alphabetical
order, and writes the result back into that same folder as a new PDF.

Key behaviors:

- **Ordering** — files are merged alphabetically by filename. You can flip this
  to reverse (Z-A) order via the config.
- **Page-size normalization** — optionally rescales every page to a uniform
  paper size (letter, A4, legal, or A3). This fixes a common problem where
  scanned PDFs (which encode their pixel dimensions as PDF "points") show up
  hugely oversized next to ordinary print-to-PDF pages. Landscape pages are
  detected and kept landscape.
- **Configurable output name** — the output filename is built from three parts:

  ```
  {prefix}{middle}{suffix}.pdf
  ```

  The `middle` part is flexible:

  | `middle` value | Result                                    |
  | -------------- | ----------------------------------------- |
  | `null`         | use the input folder's name automatically |
  | `""` (empty)   | omit the middle entirely                  |
  | `"some text"`  | use that literal text                     |

  Example: with `prefix: "000_"`, `middle: "MyFolder"`,
  `suffix: "_combined_PDFs"`, the output is `000_MyFolder_combined_PDFs.pdf`.

## Requirements

- Python 3
- [`pypdf`](https://pypi.org/project/pypdf/) and
  [`PyYAML`](https://pypi.org/project/PyYAML/):

  ```
  pip install pypdf pyyaml
  ```

## Setup

Settings live in `pdf_combine.yaml`, which sits next to the script. This file is
git-ignored because it holds machine-specific paths; the committed
`pdf_combine.yaml.template` is the shared copy.

You can get a config file two ways:

1. **Take `pdf_combine.yaml.template` and remove the `.template` extension** and edit it, **or**
2. **Let the script create it:** just run the script once. If `pdf_combine.yaml`
   is missing, it is auto-created from built-in defaults (with no personal
   paths), and the script tells you to set `input_folder` and run again.

## Usage

1. Set `input_folder` in `pdf_combine.yaml` to the folder of PDFs you want to
   combine.
2. Adjust the other settings as desired (see below).
3. Run it:

   ```
   python pdf_combine.py
   ```

The combined PDF is written into the input folder, and progress is printed to
the console (one line per file added, plus a final summary).

### Calling it from another script

`combine_pdfs()` can be imported and called directly with explicit arguments,
which override the YAML defaults:

```python
from pdf_combine import combine_pdfs

combine_pdfs(
    r"C:\docs\pdfs",          # r"..." = raw string; required for Windows paths
    output_prefix="01_",
    sort_ascending=False,
    normalize_page_size=True,
    target_page_size="letter",
)
```

## Configuration reference

All settings live in `pdf_combine.yaml`:

```yaml
paths:
  # Folder containing the PDFs to combine (PDFs in subfolders are ignored).
  # Single-quote the value so backslashes in Windows paths are taken literally.
  input_folder: 'C:\Users\you\Documents\Scans'

output_filename:
  # Output name is built as: {prefix}{middle}{suffix}.pdf
  prefix: ""
  # middle: null = use folder name; "" = omit; "text" = literal text
  middle: ""
  suffix: ""

sorting:
  # true  -> combine input files A-Z; false -> Z-A.
  sort_ascending: true

page_normalization:
  # Rescale every page to a uniform paper size (see "What it does" above).
  normalize: true
  # Target paper size: letter, a4, legal, or a3.
  target_page_size: letter
```

| Key                                  | Type    | Meaning                                                            |
| ------------------------------------ | ------- | ----------------------------------------------------------------- |
| `paths.input_folder`                 | string  | Folder of PDFs to combine. Subfolders are ignored.                |
| `output_filename.prefix`             | string  | Text placed before the middle component.                          |
| `output_filename.middle`             | string/null | `null` = folder name, `""` = omit, `"text"` = literal text.    |
| `output_filename.suffix`             | string  | Text placed after the middle component.                           |
| `sorting.sort_ascending`             | bool    | `true` = merge A-Z, `false` = merge Z-A.                          |
| `page_normalization.normalize`       | bool    | Rescale all pages to a uniform paper size.                        |
| `page_normalization.target_page_size`| string  | `letter`, `a4`, `legal`, or `a3`.                                 |

Any keys you omit from your `pdf_combine.yaml` are backfilled from the built-in
defaults, so a partial config still works.

## Notes & limitations

- The output PDF is written **into the input folder**. If you re-run the script,
  a previously generated combined PDF in that folder will itself be picked up
  and re-merged unless you move or rename it (or use a `prefix`/`suffix` and
  delete the old one first).
- Files that fail to read are skipped with an error message; the rest are still
  combined. If no pages can be read at all, the script raises an error.
- Standard page sizes are defined in points (1 pt = 1/72 inch) in the
  `PAGE_SIZES` table inside the script.

## Files

| File                        | Purpose                                                  |
| --------------------------- | -------------------------------------------------------- |
| `pdf_combine.py`            | The script.                                              |
| `pdf_combine.yaml`          | Your local settings (git-ignored, auto-created).         |
| `pdf_combine.yaml.template` | Committed template with safe defaults (no personal data). |
| `README.md`                 | This file.                                               |

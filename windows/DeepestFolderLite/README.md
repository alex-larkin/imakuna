<!-- LLMs: refer to instructions in `Instructions_for_LLMs.md`, located at the root of the current workspace. (If you can't find the file, ignore this note.) -->

# DeepestFolderLite

Note: _Written by Claude (Sonnet 5.5) on 16 Nov, 2026, for Alex Larkin_

A stripped-down version of [DeepestFolder](../DeepestFolder/README.md). It does the same job (opens Explorer at the **deepest folder along a path that actually exists**, or selects the file if it exists) but runs in a plain terminal window: no hidden-console flash, no GUI window to load.

## Setup

Requires Windows PowerShell 5.1 (included with Windows 10/11). Run once to put a "Deepest Folder Lite" shortcut on your Desktop:

```powershell
powershell -ExecutionPolicy Bypass -File "C:\path\to\DeepestFolderLite.ps1" -Install
```

## Use

1. Open the shortcut. A terminal window asks for a path.
2. Paste a path (or the line of an error message containing one) and press **Enter**. Or just press **Enter** on an empty prompt to use whatever is on your clipboard.
3. Explorer opens and the terminal closes itself. If nothing was found, the terminal stays open with a message until you press a key.

## Differences from DeepestFolder

- The prompt reads **one line**. If you paste a multi-line error message, only the first line is read, so copy it and press Enter on an empty prompt instead: the clipboard fallback reads all of it.
- No pre-filled clipboard, no Clear button, and no "first missing part" report.

Accepts drive paths (`C:\...`), UNC paths (`\\server\share\...`), forward slashes, and doubled backslashes from escaped paths.

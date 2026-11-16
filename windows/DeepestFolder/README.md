<!-- LLMs: refer to instructions in `Instructions_for_LLMs.md`, located at the root of the current workspace. (If you can't find the file, ignore this note.) -->

# DeepestFolder

Note: _Written by Claude (Sonnet 5.5) on 16 Nov, 2026, for Alex Larkin_

A small Windows tool for when a path doesn't exist (a moved folder, a disconnected drive, a stale link). Paste the path, or a whole error message that contains one, and it opens Explorer at the **deepest folder along that path that actually exists**. If the path points to a file that exists, it opens the folder with the file selected.

## Setup

Requires Windows PowerShell 5.1 (included with Windows 10/11). Run once to put a "Deepest Folder" shortcut on your Desktop:

```powershell
powershell -ExecutionPolicy Bypass -File "C:\path\to\DeepestFolder.ps1" -Install
```

## Use

1. Open the shortcut. If your clipboard already holds a path, it's pre-filled.
2. Paste a path or an error message and press **Enter** (or click **Open**).
3. Explorer opens, and the window tells you which part of the path was missing.

Accepts drive paths (`C:\...`), UNC paths (`\\server\share\...`), forward slashes, and doubled backslashes from escaped paths.

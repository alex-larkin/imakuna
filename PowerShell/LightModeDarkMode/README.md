# LightModeDarkModeToggle

_Note: Written by Claude (claude-sonnet-4-6) on 26 May, 2026, for Alex Larkin_

Toggles Windows 11 between Light Mode and Dark Mode for both apps and the system UI. Optionally applies a preset accent color to the taskbar and title bar in either mode. Changes take effect immediately — no sign-out or restart required.

---

## Requirements

- Windows 11
- PowerShell 5.1+
- [`powershell-yaml`](https://github.com/cloudbase/powershell-yaml) module

Install the module once with:

```powershell
Install-Module powershell-yaml -Scope CurrentUser
```

---

## Setup

### 1. Config file

On first run, the script auto-creates `Config\LightModeDarkModeToggle.yaml` with safe defaults. Edit it to customize accent color behavior. See `Config\LightModeDarkModeToggle.Template.yaml.txt` for the full schema and instructions.

To find your accent color value:

1. Pick an accent color in **Windows Settings → Personalization → Colors**.
2. Run in PowerShell:
   ```powershell
   (Get-ItemProperty "HKCU:\SOFTWARE\Microsoft\Windows\DWM").AccentColor
   ```
3. Paste the result into `accent_color` in your config file.

### 2. Keyboard shortcut

1. Right-click the desktop → **New → Shortcut**.
2. In the **Target** field, paste (editing the path to match where the script lives):
   ```
   powershell.exe -WindowStyle Hidden -ExecutionPolicy Bypass -File "C:\full\path\to\LightModeDarkModeToggle.ps1"
   ```
   > Tip: in File Explorer, hold **Shift** and right-click the `.ps1` file, then choose **Copy as path** to get the quoted path.
3. In the **Start in** field, paste just the folder path (no filename).
4. Name the shortcut and click **Finish**.
5. Right-click the shortcut → **Properties → Shortcut tab** → click in **Shortcut key** → press your desired key (e.g. `E` becomes `Ctrl+Alt+E`). Click **OK**.
6. The shortcut **must stay on the Desktop or in the Start Menu** for the hotkey to work globally. Moving it to a regular folder silently disables the hotkey.

---

## Troubleshooting

If the hotkey flashes a window but nothing happens, the script is likely erroring silently. Temporarily edit the shortcut's Target field, replacing `-WindowStyle Hidden` with `-NoExit`:

```
powershell.exe -NoExit -ExecutionPolicy Bypass -File "C:\...\LightModeDarkModeToggle.ps1"
```

This keeps the window open so you can read the error. Change it back to `-WindowStyle Hidden` once resolved.

---

## File layout

```
PowerShell/
    LightModeDarkModeToggle.ps1
    LightModeDarkModeToggle.md          ← this file
    Config/
        LightModeDarkModeToggle.yaml            ← your config (git-ignored)
        LightModeDarkModeToggle.Template.yaml.txt  ← schema reference (committed)
```

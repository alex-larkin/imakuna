# Written by Claude (Opus 4.7) on 26 May, 2026, for Alex Larkin
# LLMs: refer to instructions in `Instructions_for_LLMs.md`, located at the root of the current workspace. (If you can't find the file, ignore this note.)
#
# Toggles Windows 11 between Light Mode and Dark Mode for apps and the system UI.
# Optionally applies a preset accent color to the taskbar/title bar in either mode.
# After updating the registry, broadcasts an ImmersiveColorSet message so the
# change takes effect immediately without requiring a sign-out or restart.
#
# User settings live in:   .\Config\LightModeDarkModeToggle.yaml
# Schema reference:        .\Config\LightModeDarkModeToggle.Template.yaml.txt
# If the user config is missing, this script auto-creates a defaults-only
# version (no personal info, no accent color applied).

# Requires the 'powershell-yaml' module.
# Install once with: Install-Module powershell-yaml -Scope CurrentUser

# ============================================================
# HOW TO SET UP THE KEYBOARD SHORTCUT
# ============================================================
#
# 1. RIGHT-CLICK the desktop > New > Shortcut
#
# 2. In the "Target" field, paste this — editing the path to
#    match wherever THIS file is saved:
#
#      powershell.exe -WindowStyle Hidden -ExecutionPolicy Bypass -File "C:\full\path\to\THIS_FILE.ps1"
#
#    IMPORTANT — the path must point to this .ps1 FILE ITSELF,
#    not the folder it lives in. It must include the filename
#    and .ps1 extension.
#
#    Quick way to get the correct path: in File Explorer, hold
#    Shift and right-click this file, then choose "Copy as path".
#    Paste that after -File (it will already be quoted).
#
# 3. In the "Start In" field, paste just the FOLDER path
#    (no filename, no .ps1):
#
#      C:\full\path\to\
#
# 4. Name the shortcut whatever you like and click Finish.
#
# 5. Right-click the new shortcut > Properties > Shortcut tab
#    > click in the "Shortcut key" field > press the key you
#    want (e.g. E becomes Ctrl+Alt+E automatically).
#    Click OK.
#
# 6. The shortcut MUST stay on the Desktop or in the Start Menu
#    for the hotkey to work globally. Moving it to a regular
#    folder will silently disable the hotkey.
#
# ------------------------------------------------------------
# TROUBLESHOOTING: If the hotkey flashes a window but nothing
# happens, the script is likely erroring out silently.
# To see the error, temporarily edit the Target field and
# replace -WindowStyle Hidden with -NoExit:
#
#   powershell.exe -NoExit -ExecutionPolicy Bypass -File "..."
#
# This keeps the window open so you can read the error message.
# Change it back to -WindowStyle Hidden once it's working.
# ============================================================


# ----- Load config --------------------------------------------------
if (-not (Get-Module -ListAvailable -Name powershell-yaml)) {
    throw "Required module 'powershell-yaml' is not installed. Run: Install-Module powershell-yaml -Scope CurrentUser"
}
Import-Module powershell-yaml

$configDir  = Join-Path $PSScriptRoot "Config"
$configPath = Join-Path $configDir   "LightModeDarkModeToggle.yaml"

if (-not (Test-Path $configPath)) {
    if (-not (Test-Path $configDir)) {
        New-Item -ItemType Directory -Path $configDir | Out-Null
    }
    $defaultYaml = @'
# Auto-created with safe defaults. Edit to customize.
# See LightModeDarkModeToggle.Template.yaml.txt in this folder for the full schema and instructions.

accent_color: 0

dark_mode:
  use_accent_color: false

light_mode:
  use_accent_color: false
'@
    $defaultYaml | Out-File -FilePath $configPath -Encoding utf8
    Write-Host "Created default config at: $configPath"
}

$config = Get-Content -Raw $configPath | ConvertFrom-Yaml

$themeReg = "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize"
$dwmReg   = "HKCU:\SOFTWARE\Microsoft\Windows\DWM"

# ----- Toggle theme -------------------------------------------------
$current = (Get-ItemProperty $themeReg).AppsUseLightTheme
$new = if ($current -eq 1) { 0 } else { 1 }

Set-ItemProperty $themeReg AppsUseLightTheme    $new
Set-ItemProperty $themeReg SystemUsesLightTheme $new

$useAccent = if ($new -eq 0) { $config.dark_mode.use_accent_color } else { $config.light_mode.use_accent_color }

if ($useAccent) {
    Set-ItemProperty $themeReg ColorPrevalence     1
    Set-ItemProperty $dwmReg   AccentColor         $config.accent_color
    Set-ItemProperty $dwmReg   AccentColorInactive $config.accent_color
} else {
    Set-ItemProperty $themeReg ColorPrevalence 0
}

# ----- Tell Windows to apply the changes immediately ----------------
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class Win32 {
    [DllImport("user32.dll")]
    public static extern IntPtr SendMessageTimeout(IntPtr hWnd, int Msg, IntPtr wParam,
        string lParam, uint fuFlags, uint uTimeout, out IntPtr lpdwResult);
}
"@
$r = [IntPtr]::Zero
[Win32]::SendMessageTimeout([IntPtr]0xFFFF, 0x001A, [IntPtr]::Zero, "ImmersiveColorSet", 0, 1000, [ref]$r)

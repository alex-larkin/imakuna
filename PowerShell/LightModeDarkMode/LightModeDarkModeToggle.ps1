# Written by Claude (Opus 4.7) on 26 May, 2026, for Alex Larkin
# LLMs: refer to instructions in `Instructions_for_LLMs.md`, located at the root of the current workspace. (If you can't find the file, ignore this note.)
#
# Toggles Windows 11 between Light Mode and Dark Mode for apps and the system UI.
# Optionally applies a preset accent color to the taskbar/title bar in either mode.
# After updating the registry, broadcasts an ImmersiveColorSet message so the
# change takes effect immediately without requiring a sign-out or restart.
#
# See LightModeDarkModeToggle.md for setup instructions (config, keyboard shortcut, troubleshooting).

# Requires the 'powershell-yaml' module.
# Install once with: Install-Module powershell-yaml -Scope CurrentUser


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

# Written by Claude (Sonnet 5.5) on 16 Nov, 2026, for Alex Larkin
# LLMs: refer to instructions in `Instructions_for_LLMs.md`, located at the root of the current workspace. (If you can't find the file, ignore this note.)
#
# DeepestFolderLite.ps1
# Terminal-only version of DeepestFolder. Paste a path (or an error message containing one)
# at the prompt; opens Explorer at the deepest folder along that path that actually exists.
# Press Enter on an empty prompt to use whatever is on the clipboard instead.
#
# One-time setup (creates a "Deepest Folder Lite" shortcut on your Desktop):
#   powershell -ExecutionPolicy Bypass -File "C:\path\to\DeepestFolderLite.ps1" -Install

param([switch]$Install)

if ($Install) {
    $desktop = [Environment]::GetFolderPath('Desktop')
    $lnk     = Join-Path $desktop 'Deepest Folder Lite.lnk'
    $shell   = New-Object -ComObject WScript.Shell
    $s       = $shell.CreateShortcut($lnk)
    $s.TargetPath       = (Get-Command powershell.exe).Source
    $s.Arguments        = '-NoProfile -ExecutionPolicy Bypass -File "{0}"' -f $PSCommandPath
    $s.WorkingDirectory = Split-Path -Parent $PSCommandPath
    $s.IconLocation     = "$env:SystemRoot\System32\shell32.dll,4"
    $s.Save()
    Write-Host "Shortcut created: $lnk"
    return
}

# ---------- logic ----------

function Get-CandidatePath([string]$Text) {
    # Pull a drive path (C:\...) or UNC path (\\server\share\...) out of arbitrary text.
    if ([string]::IsNullOrWhiteSpace($Text)) { return $null }
    $t = $Text.Trim()

    $m = [regex]::Match($t, '[A-Za-z]:[\\/][^"''<>|*?\r\n]*')
    if (-not $m.Success) {
        $m = [regex]::Match($t, '\\\\[^\\/\s"''<>|*?\r\n]+[\\/][^"''<>|*?\r\n]*')
    }
    if (-not $m.Success) { return $null }

    $p = $m.Value.Trim().TrimEnd('.', ',', ';', ')', ' ')
    $p = $p -replace '/', '\'

    # Collapse doubled backslashes (from escaped paths) but keep a leading UNC "\\"
    $prefix = ''
    if ($p.StartsWith('\\')) { $prefix = '\\'; $p = $p.Substring(2) }
    $p = $p -replace '\\{2,}', '\'
    $p = $prefix + $p

    if ($p.Length -gt 3) { $p = $p.TrimEnd('\') }
    return $p
}

function Test-Exists([string]$Path, [string]$Type) {
    try { return (Test-Path -LiteralPath $Path -PathType $Type -ErrorAction Stop) }
    catch { return $false }
}

function Find-Deepest([string]$Path) {
    if (Test-Exists $Path 'Leaf') {
        return @{ Kind = 'File'; Path = $Path; Missing = '' }
    }
    $cur = $Path
    while ($cur) {
        if (Test-Exists $cur 'Container') {
            $missing = ''
            if ($Path.Length -gt $cur.Length) { $missing = $Path.Substring($cur.Length).TrimStart('\') }
            return @{ Kind = 'Folder'; Path = $cur; Missing = $missing }
        }
        # .NET instead of Split-Path: in Windows PowerShell 5.1, -LiteralPath and -Parent
        # are in different parameter sets, so that combination always throws.
        # GetDirectoryName returns $null at a root (C:\ or \\server\share), ending the loop.
        try   { $parent = [System.IO.Path]::GetDirectoryName($cur) }
        catch { break }
        if ([string]::IsNullOrEmpty($parent) -or $parent -eq $cur) { break }
        $cur = $parent
    }
    return $null
}

function Stop-WithMessage([string]$Message) {
    # Only used on failure: keep the window open so the message can be read.
    Write-Host $Message -ForegroundColor Red
    Write-Host 'Press any key to close...'
    [void][System.Console]::ReadKey($true)
    exit 1
}

# ---------- run ----------

$text = Read-Host 'Paste a path (Enter = use clipboard)'
if ([string]::IsNullOrWhiteSpace($text)) { $text = Get-Clipboard -Raw }

$path = Get-CandidatePath $text
if (-not $path) {
    Stop-WithMessage 'No path found in that text. Expected something like C:\folder\file.ext'
}

$r = Find-Deepest $path
if (-not $r) {
    Stop-WithMessage "Nothing along that path exists (is the drive connected?):`n$path"
}

# Success: open Explorer and let the window close right away.
if ($r.Kind -eq 'File') {
    Start-Process explorer.exe -ArgumentList ('/select,"{0}"' -f $r.Path)
}
else {
    Start-Process explorer.exe -ArgumentList ('"{0}"' -f $r.Path)
}

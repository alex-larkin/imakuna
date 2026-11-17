# DeepestFolder.ps1
# Paste a path (or a whole error message containing one); opens Explorer at the
# deepest folder along that path that actually exists.
#
# One-time setup (creates a "Deepest Folder" shortcut on your Desktop):
#   powershell -ExecutionPolicy Bypass -File "C:\path\to\DeepestFolder.ps1" -Install

param([switch]$Install)

if ($Install) {
    $desktop = [Environment]::GetFolderPath('Desktop')
    $lnk     = Join-Path $desktop 'Deepest Folder.lnk'
    $shell   = New-Object -ComObject WScript.Shell
    $s       = $shell.CreateShortcut($lnk)
    $s.TargetPath       = (Get-Command powershell.exe).Source
    $s.Arguments        = '-NoProfile -ExecutionPolicy Bypass -STA -WindowStyle Hidden -File "{0}"' -f $PSCommandPath
    $s.WorkingDirectory = Split-Path -Parent $PSCommandPath
    $s.IconLocation     = "$env:SystemRoot\System32\shell32.dll,4"
    $s.Save()
    Write-Host "Shortcut created: $lnk"
    return
}

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

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

function Invoke-Lookup {
    $path = Get-CandidatePath $txt.Text
    if (-not $path) {
        $status.ForeColor = [System.Drawing.Color]::Firebrick
        $status.Text = 'No path found in that text. Expected something like C:\folder\file.ext'
        return
    }

    $r = Find-Deepest $path
    if (-not $r) {
        $status.ForeColor = [System.Drawing.Color]::Firebrick
        $status.Text = "Nothing along that path exists (is the drive connected?):`r`n$path"
        return
    }

    if ($r.Kind -eq 'File') {
        Start-Process explorer.exe -ArgumentList ('/select,"{0}"' -f $r.Path)
        $status.ForeColor = [System.Drawing.Color]::DarkGreen
        $status.Text = "That file exists. Opened its folder with it selected."
    }
    else {
        Start-Process explorer.exe -ArgumentList ('"{0}"' -f $r.Path)
        if ($r.Missing) {
            $status.ForeColor = [System.Drawing.Color]::DarkGreen
            $status.Text = "Opened: $($r.Path)`r`nFirst missing part: $($r.Missing)"
        } else {
            $status.ForeColor = [System.Drawing.Color]::DarkGreen
            $status.Text = "That folder exists. Opened: $($r.Path)"
        }
    }
}

# ---------- UI ----------

[System.Windows.Forms.Application]::EnableVisualStyles()

$form = New-Object System.Windows.Forms.Form
$form.Text            = 'Deepest Folder'
$form.StartPosition   = 'CenterScreen'
$form.ClientSize      = New-Object System.Drawing.Size(640, 260)
$form.MinimumSize     = New-Object System.Drawing.Size(480, 240)
$form.Font            = New-Object System.Drawing.Font('Segoe UI', 10)

$label = New-Object System.Windows.Forms.Label
$label.Text     = 'Paste a path (or an error message containing one):'
$label.Location = New-Object System.Drawing.Point(12, 12)
$label.AutoSize = $true
$form.Controls.Add($label)

$txt = New-Object System.Windows.Forms.TextBox
$txt.Multiline  = $true
$txt.WordWrap   = $true
$txt.ScrollBars = 'Vertical'
$txt.Location   = New-Object System.Drawing.Point(12, 40)
$txt.Size       = New-Object System.Drawing.Size(616, 90)
$txt.Anchor     = 'Top, Left, Right'
$form.Controls.Add($txt)

$btnOpen = New-Object System.Windows.Forms.Button
$btnOpen.Text     = 'Open'
$btnOpen.Location = New-Object System.Drawing.Point(12, 142)
$btnOpen.Size     = New-Object System.Drawing.Size(100, 32)
$btnOpen.Add_Click({
    try { Invoke-Lookup }
    catch {
        $status.ForeColor = [System.Drawing.Color]::Firebrick
        $status.Text = "Error: $($_.Exception.Message)"
    }
})
$form.Controls.Add($btnOpen)
$form.AcceptButton = $btnOpen    # Enter key = Open

$btnClear = New-Object System.Windows.Forms.Button
$btnClear.Text     = 'Clear'
$btnClear.Location = New-Object System.Drawing.Point(122, 142)
$btnClear.Size     = New-Object System.Drawing.Size(100, 32)
$btnClear.Add_Click({
    $txt.Clear()
    $status.Text = ''
    $txt.Focus() | Out-Null
})
$form.Controls.Add($btnClear)

$status = New-Object System.Windows.Forms.Label
$status.Location = New-Object System.Drawing.Point(12, 186)
$status.Size     = New-Object System.Drawing.Size(616, 64)
$status.Anchor   = 'Top, Left, Right, Bottom'
$form.Controls.Add($status)

# If the clipboard already holds something path-like, pre-fill it.
$form.Add_Shown({
    try {
        if ([System.Windows.Forms.Clipboard]::ContainsText()) {
            $clip = [System.Windows.Forms.Clipboard]::GetText()
            if (Get-CandidatePath $clip) { $txt.Text = $clip }
        }
    } catch { }
    $txt.Focus() | Out-Null
    $txt.SelectAll()
})

[void]$form.ShowDialog()

# Written by Claude Sonnet 5.5 on 30 Sep, 2026, for Alex Larkin.
# Revised version of the original Convert-PubFileToPDF.ps1, adding: progress output, one-line orange notice for existing PDFs,
# read-only opening, and a per-file watchdog that kills a stuck Publisher and carries on.
<#
.SYNOPSIS
	Converts Microsoft Publisher .pub files to PDF format.

.DESCRIPTION
	This script automates the conversion of Microsoft Publisher (.pub) files to PDF format using the Microsoft Office Interop Publisher library.
	It processes all files matching the specified filter, skipping any file whose PDF already exists (one orange line each).
	Each file is given -TimeoutSeconds to open and export. If Publisher hangs (for example on a hidden dialog), the script kills that
	Publisher process, deletes any partial PDF, records the file as timed out, starts a fresh Publisher and continues with the next file.
	Files are opened read-only, so the .pub files are never modified.

.PARAMETER Filter
	Specifies the file filter to select Publisher files for conversion.
	This can be a specific file name (e.g., "document.pub") or a wildcard pattern (e.g., "*.pub").

.PARAMETER Recurse
	If specified, searches for Publisher files recursively in all subdirectories that match the filter. If omitted, only the current directory is searched.

.PARAMETER TimeoutSeconds
	Maximum time allowed for one file (open + export + close) before Publisher is killed and the file is skipped. Default: 120.

.EXAMPLE
	Convert-PubFileToPDF.ps1 -Filter "C:\Documents\MyFile.pub"
	Converts the specified Publisher file to PDF format.

.EXAMPLE
	Convert-PubFileToPDF.ps1 -Filter "*.pub" -Recurse -TimeoutSeconds 60
	Converts all Publisher files in the current directory and all subdirectories, giving each file at most 60 seconds.
#>
[CmdletBinding()]
param
(
	[ValidateNotNullOrEmpty()]
	[string]
	$Filter,

	[switch]
	$Recurse,

	[ValidateRange(5, 3600)]
	[int]
	$TimeoutSeconds = 120
)

if (-not $PSBoundParameters.ContainsKey('Filter')) {
	Write-Error "The -Filter parameter is required."
	exit 1
}

if (-not ($Filter -like "*.pub")) {
	Write-Error "The filter must specify .pub files (e.g., '*.pub' or 'file.pub').";
	exit 1;
}

# Prints one line in orange (256-colour ANSI 208) when the host supports it, otherwise in DarkYellow.
function Write-Orange {
	param([string]$Text)
	$esc = [char]27;
	$vt = $false;
	try { $vt = [bool]$Host.UI.SupportsVirtualTerminal -and -not [Console]::IsOutputRedirected } catch { }
	if ($vt) {
		Write-Host "$esc[38;5;208m$Text$esc[0m";
	} else {
		Write-Host $Text -ForegroundColor DarkYellow;
	}
}

# Starts Publisher and works out which MSPUB process is ours, so the watchdog never kills a Publisher window you have open.
# ProcessId is $null if Publisher attached to an already-running instance; the watchdog then cannot kill it.
function New-PublisherSession {
	$before = @(Get-Process MSPUB -ErrorAction SilentlyContinue | ForEach-Object { $_.Id });
	$comApp = New-Object -ComObject Publisher.Application;
	$newPid = $null;
	for ($i = 0; $i -lt 20 -and -not $newPid; $i++) {
		$newPid = Get-Process MSPUB -ErrorAction SilentlyContinue |
			Where-Object { $before -notcontains $_.Id } |
			Select-Object -First 1 -ExpandProperty Id;
		if (-not $newPid) { Start-Sleep -Milliseconds 250 }
	}
	if (-not $newPid) {
		Write-Warning "Could not identify the new Publisher process (an instance was already running?). The timeout cannot kill it, so a hung file would block the run.";
	}
	return [pscustomobject]@{ App = $comApp; ProcessId = $newPid };
}

$app = $null;
$watch = $null;
$watchShell = $null;
$watchHandle = $null;

try {
	$files = @(Get-ChildItem $Filter -File -Recurse:$Recurse | Where-Object { $_.Extension -eq ".pub" });
	if ($files.Count -eq 0) {
		Write-Error "No Publisher files found for the filter: $Filter";
		exit 1;
	}

	Write-Output "Found $($files.Count) Publisher files. Running...";

	Add-type -AssemblyName Office;
	Add-type -AssemblyName Microsoft.Office.Interop.Publisher;
	try {
		$session = New-PublisherSession;
		$app = $session.App;
	} catch {
		Write-Error "Microsoft Publisher is not installed or accessible.";
		exit 1;
	}

	# Watchdog: a background thread that only kills our MSPUB process when one file exceeds the timeout.
	# It never touches the COM objects; the blocked call on the main thread then throws and is handled below.
	$watch = [hashtable]::Synchronized(@{ ProcessId = $null; StartedAt = $null; Killed = $false; Stop = $false; Timeout = $TimeoutSeconds });
	$watchShell = [powershell]::Create();
	[void]$watchShell.AddScript({
		param($w)
		while (-not $w.Stop) {
			$started = $w.StartedAt;
			if ($w.ProcessId -and $started -and ((Get-Date) - $started).TotalSeconds -gt $w.Timeout) {
				$w.Killed = $true;
				Stop-Process -Id $w.ProcessId -Force -ErrorAction SilentlyContinue;
				$w.StartedAt = $null;
			}
			Start-Sleep -Milliseconds 500;
		}
	}).AddArgument($watch);
	$watchHandle = $watchShell.BeginInvoke();

	$successCount = 0;
	$skipCount = 0;
	$failCount = 0;
	$timedOut = @();
	$index = 0;

	foreach ($file in $files) {
		$index++;
		$fileFullName = $file.FullName;
		$pdfFilePath = [System.IO.Path]::ChangeExtension($fileFullName, '.pdf')
		if (Test-Path -LiteralPath $pdfFilePath) {
			Write-Orange "[$index/$($files.Count)] Skipped, PDF already exists: $pdfFilePath";
			$skipCount++;
			Continue;
		}

		Write-Output "[$index/$($files.Count)] Converting $fileFullName ...";

		$doc = $null;
		$problem = $null;
		$watch.Killed = $false;
		$watch.ProcessId = $session.ProcessId;
		$watch.StartedAt = Get-Date;
		try {
			# Open read-only and keep it out of the recent-files list
			$doc = $app.Open($fileFullName, $true, $false);
			if (-not $doc) { throw "Publisher returned no document." }

			$doc.ExportAsFixedFormat([Microsoft.Office.Interop.Publisher.PbFixedFormatType]::pbFixedFormatTypePDF, $pdfFilePath);
			if (-not (Test-Path -LiteralPath $pdfFilePath)) { throw "No PDF was produced." }
		} catch {
			$problem = $_;
		}
		try { if ($doc) { $doc.Close() } } catch { }
		$watch.StartedAt = $null;

		if ($watch.Killed) {
			Write-Warning "Timed out after $TimeoutSeconds seconds, Publisher was killed: $fileFullName";
			# We checked the PDF did not exist before starting, so anything there now is a partial file.
			Remove-Item -LiteralPath $pdfFilePath -Force -ErrorAction SilentlyContinue;
			$timedOut += $fileFullName;
			$failCount++;
			$session = New-PublisherSession;
			$app = $session.App;
		} elseif ($problem) {
			Write-Error "Failed on $fileFullName : $problem";
			$failCount++;
		} else {
			Write-Output "Exported to $pdfFilePath.";
			$successCount++;
		}
	}

	#Log output
	Write-Output "Converted $successCount files, skipped $skipCount existing PDFs, $failCount failed.";
	if ($timedOut.Count -gt 0) {
		Write-Output "Timed out (open these by hand to see what Publisher complains about):";
		$timedOut | ForEach-Object { Write-Output "  $_" };
	}
}catch{
	Write-Error $_;
}finally {
	if ($watch) { $watch.Stop = $true; }
	if ($watchShell) {
		try { [void]$watchShell.EndInvoke($watchHandle) } catch { }
		$watchShell.Dispose();
	}
	if ($app) {
		#Quit Publisher
		try { $app.Quit() } catch { }
	}
}

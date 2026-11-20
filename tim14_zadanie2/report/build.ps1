# Build report_tim14_2.pdf from LaTeX (requires pdflatex / MiKTeX or TeX Live)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$pdflatex = Get-Command pdflatex -ErrorAction SilentlyContinue
if (-not $pdflatex) {
    Write-Host "pdflatex not found. Install MiKTeX:"
    Write-Host "  winget install -e --id MiKTeX.MiKTeX"
    Write-Host "Then reopen the terminal and re-run: .\build.ps1"
    exit 1
}

pdflatex -interaction=nonstopmode -halt-on-error report_tim14_2.tex
pdflatex -interaction=nonstopmode -halt-on-error report_tim14_2.tex

# Copy final PDF next to README / submission root
Copy-Item -Force report_tim14_2.pdf ..\report_tim14_2.pdf
Write-Host "OK -> report\report_tim14_2.pdf and ..\report_tim14_2.pdf"

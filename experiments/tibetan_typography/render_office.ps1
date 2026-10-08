$ErrorActionPreference = 'Stop'
$auditOutput = Join-Path $PSScriptRoot 'output'
$auditWord = $null
$auditPowerPoint = $null
try {
    $auditWord = New-Object -ComObject Word.Application
    $auditWord.Visible = $false
    $auditWord.DisplayAlerts = 0
    foreach ($auditName in @('current_app', 'tibetan_corrected')) {
        $auditDocument = $null
        try {
            $auditDocPath = Join-Path $auditOutput "$auditName.docx"
            $auditPdfPath = Join-Path $auditOutput "$auditName.docx.pdf"
            $auditDocument = $auditWord.Documents.Open($auditDocPath, $false, $true, $false)
            $auditDocument.ExportAsFixedFormat($auditPdfPath, 17)
            Write-Output "Rendered $auditPdfPath"
        } finally {
            if ($null -ne $auditDocument) { $auditDocument.Close(0) }
        }
    }
} finally {
    if ($null -ne $auditWord) { $auditWord.Quit() }
}
try {
    $auditPowerPoint = New-Object -ComObject PowerPoint.Application
    foreach ($auditName in @('current_app', 'tibetan_corrected')) {
        $auditDeck = $null
        try {
            $auditDeckPath = Join-Path $auditOutput "$auditName.pptx"
            $auditPdfPath = Join-Path $auditOutput "$auditName.pptx.pdf"
            # ReadOnly=true, Untitled=false, WithWindow=false.
            $auditDeck = $auditPowerPoint.Presentations.Open($auditDeckPath, -1, 0, 0)
            $auditDeck.SaveAs($auditPdfPath, 32)
            Write-Output "Rendered $auditPdfPath"
        } finally {
            if ($null -ne $auditDeck) { $auditDeck.Close() }
        }
    }
} finally {
    if ($null -ne $auditPowerPoint) { $auditPowerPoint.Quit() }
}

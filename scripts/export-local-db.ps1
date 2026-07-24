# Exporta la DB local Almas a un dump listo para restaurar en el VPS.
# Uso (PowerShell, desde la raíz del repo o cualquier cwd):
#   .\scripts\export-local-db.ps1
#   .\scripts\export-local-db.ps1 -HostName localhost -Port 5432 -User postgres -Database almas -OutFile .\almas_local.dump

param(
  [string]$HostName = "localhost",
  [int]$Port = 5432,
  [string]$User = "postgres",
  [string]$Database = "almas",
  [string]$OutFile = "almas_local.dump"
)

$ErrorActionPreference = "Stop"

$pgDump = Get-Command pg_dump -ErrorAction SilentlyContinue
if (-not $pgDump) {
  Write-Error "pg_dump no está en el PATH. Agregá la carpeta bin de PostgreSQL o usá la ruta completa."
}

Write-Host "Chequeá antes: SELECT version_num FROM alembic_version; (debe ser 001 o 002)."
Write-Host "Dump: $User@$HostName:$Port/$Database -> $OutFile"

if (-not $env:PGPASSWORD) {
  $secure = Read-Host "Password Postgres ($User)" -AsSecureString
  $BSTR = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
  $env:PGPASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
}

& pg_dump -h $HostName -p $Port -U $User -d $Database -Fc -f $OutFile
if ($LASTEXITCODE -ne 0) {
  Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
  exit $LASTEXITCODE
}

Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
Write-Host "OK: $OutFile"
Write-Host "Subí al VPS: scp $OutFile root@TU_VPS:/docker/app-almas/"
Write-Host "Seguí docs/vps-deploy.md sección 3."

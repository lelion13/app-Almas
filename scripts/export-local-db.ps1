# Exporta la DB local Almas a un dump listo para restaurar en el VPS.
# Uso (PowerShell, desde la raíz del repo):
#   .\scripts\export-local-db.ps1
#   .\scripts\export-local-db.ps1 -User postgres -Database almas

param(
  [string]$HostName = "localhost",
  [int]$Port = 5432,
  [string]$User = "postgres",
  [string]$Database = "almas",
  [string]$OutFile = "almas_local.dump",
  [string]$PgDumpPath = ""
)

$ErrorActionPreference = "Stop"

function Find-PgDump {
  param([string]$Explicit)

  if ($Explicit) {
    if (-not (Test-Path $Explicit)) {
      throw "No existe pg_dump en: $Explicit"
    }
    return (Resolve-Path $Explicit).Path
  }

  $fromPath = Get-Command pg_dump -ErrorAction SilentlyContinue
  if ($fromPath) {
    return $fromPath.Source
  }

  $candidates = @(
    "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe",
    "C:\Program Files\PostgreSQL\17\bin\pg_dump.exe",
    "C:\Program Files\PostgreSQL\16\bin\pg_dump.exe",
    "C:\Program Files\PostgreSQL\15\bin\pg_dump.exe"
  )

  foreach ($c in $candidates) {
    if (Test-Path $c) {
      return $c
    }
  }

  $found = Get-ChildItem "C:\Program Files\PostgreSQL" -Recurse -Filter "pg_dump.exe" -ErrorAction SilentlyContinue |
    Select-Object -First 1 -ExpandProperty FullName
  if ($found) {
    return $found
  }

  throw "pg_dump no está en el PATH ni en Program Files\PostgreSQL. Pasá -PgDumpPath 'C:\...\bin\pg_dump.exe'"
}

$pgDumpExe = Find-PgDump -Explicit $PgDumpPath

Write-Host "Usando: $pgDumpExe"
Write-Host "Chequeá antes: SELECT version_num FROM alembic_version; (debe ser 001 o 002)."
Write-Host "Dump: ${User}@${HostName}:${Port}/${Database} -> ${OutFile}"

if (-not $env:PGPASSWORD) {
  $secure = Read-Host "Password Postgres ($User)" -AsSecureString
  $BSTR = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
  $env:PGPASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
}

& $pgDumpExe -h $HostName -p $Port -U $User -d $Database -Fc -f $OutFile
$code = $LASTEXITCODE
Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue

if ($code -ne 0) {
  exit $code
}

Write-Host "OK: $OutFile"
Write-Host "Subí al VPS: scp $OutFile root@TU_VPS:/docker/app-almas/"
Write-Host "Seguí docs/vps-deploy.md sección 3."

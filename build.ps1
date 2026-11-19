$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

python -m pip install --disable-pip-version-check pyinstaller | Out-Null
python tools/make_icon.py
python -m PyInstaller --noconfirm --clean --onefile --console --noupx `
    --name HannibalVN `
    --icon assets/hannibal.ico `
    --version-file version_info.txt `
    --paths src `
    --distpath dist `
    --workpath build `
    src/main.py

if (Test-Path "dist\HannibalVN.exe") {
    Copy-Item -Path "README.txt" -Destination "dist\README.txt" -Force
    Write-Host "Сборка готова: dist\HannibalVN.exe"
    & "dist\HannibalVN.exe" --version
} else {
    throw "Сборка не удалась"
}

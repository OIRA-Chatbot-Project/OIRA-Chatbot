Write-Host "================================" -ForegroundColor Cyan
Write-Host "   OIRA Chatbot Startup" -ForegroundColor Cyan
Write-Host "================================`n" -ForegroundColor Cyan

# Check directories
if (!(Test-Path "backend")) {
    Write-Host "❌ Backend directory not found" -ForegroundColor Red
    exit 1
}

if (!(Test-Path "frontend")) {
    Write-Host "❌ Frontend directory not found" -ForegroundColor Red
    exit 1
}

# -----------------------
# Start Backend
# -----------------------
Write-Host "Starting Backend Server..." -ForegroundColor Cyan
Set-Location backend

if (Test-Path ".venv") {
    Write-Host "✓ Found Python virtual environment" -ForegroundColor Green

    if (Test-Path ".venv\Scripts\Activate.ps1") {
        . .\.venv\Scripts\Activate.ps1
    }
    elseif (Test-Path ".venv\Scripts\activate.bat") {
        cmd /c ".venv\Scripts\activate.bat"
    }
    else {
        Write-Host "⚠ Could not find activate script inside .venv" -ForegroundColor Yellow
    }
}
else {
    Write-Host "⚠ No virtual environment found. Using system Python." -ForegroundColor Yellow
}

# Install deps if fastapi missing
python -c "import fastapi" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
    pip install -r requirements.txt
}

Write-Host "✓ Starting FastAPI backend on http://localhost:8000" -ForegroundColor Green
$backendProcess = Start-Process -FilePath "python" -ArgumentList "main.py" `
    -RedirectStandardOutput "..\backend.log" `
    -RedirectStandardError "..\backend.log" `
    -NoNewWindow -PassThru

Set-Location ..

Start-Sleep -Seconds 3

if ($backendProcess.HasExited) {
    Write-Host "❌ Backend failed to start. Check backend.log for details." -ForegroundColor Red
    Get-Content backend.log
    exit 1
}

# -----------------------
# Start Frontend
# -----------------------
Write-Host "`nStarting Frontend Server..." -ForegroundColor Cyan
Set-Location frontend

if (!(Test-Path "node_modules")) {
    Write-Host "Installing Node.js dependencies..." -ForegroundColor Yellow
    npm install
}

Write-Host "✓ Starting Next.js frontend on http://localhost:3000" -ForegroundColor Green
$frontendProcess = Start-Process -FilePath "npm" -ArgumentList "run dev" `
    -RedirectStandardOutput "..\frontend.log" `
    -RedirectStandardError "..\frontend.log" `
    -NoNewWindow -PassThru

Set-Location ..

Start-Sleep -Seconds 5

Write-Host "`n================================" -ForegroundColor Green
Write-Host "   🎉 Both servers are running!" -ForegroundColor Green
Write-Host "================================`n" -ForegroundColor Green

Write-Host "📡 Backend API:  http://localhost:8000"
Write-Host "🌐 Frontend UI:  http://localhost:3000"
Write-Host "📚 API Docs:     http://localhost:8000/docs`n"
Write-Host "Press Ctrl+C to stop both servers`n" -ForegroundColor Yellow

Write-Host "Logs are being written to:"
Write-Host "  - backend.log"
Write-Host "  - frontend.log`n"

# Wait until user stops it
try {
    while ($true) {
        Start-Sleep -Seconds 2
        if ($backendProcess.HasExited -or $frontendProcess.HasExited) {
            Write-Host "⚠ One of the servers stopped unexpectedly." -ForegroundColor Yellow
            break
        }
    }
}
finally {
    Write-Host "`nShutting down servers..." -ForegroundColor Yellow

    if (!$backendProcess.HasExited) { Stop-Process -Id $backendProcess.Id -Force }
    if (!$frontendProcess.HasExited) { Stop-Process -Id $frontendProcess.Id -Force }
}

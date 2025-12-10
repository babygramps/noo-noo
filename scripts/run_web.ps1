# PowerShell script to run the web interface on Windows
# Starts both the FastAPI backend and Next.js frontend

$ErrorActionPreference = "Stop"

# Get the project root directory
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ProjectRoot

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "EPDM Vacuum Fixture - Web Interface" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Project root: $ProjectRoot"
Write-Host ""

# Check if virtual environment exists
if (-not (Test-Path "venv")) {
    Write-Host "ERROR: Python virtual environment not found!" -ForegroundColor Red
    Write-Host "Please run: python -m venv venv && .\venv\Scripts\Activate.ps1 && pip install -r requirements.txt"
    exit 1
}

# Check if Node.js is installed
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Node.js is not installed!" -ForegroundColor Red
    Write-Host "Please install Node.js 18+ (https://nodejs.org)"
    exit 1
}

# Check if web dependencies are installed
if (-not (Test-Path "web/node_modules")) {
    Write-Host "Installing web dependencies..."
    Set-Location web
    npm install
    Set-Location ..
}

# Activate virtual environment
Write-Host "Activating Python virtual environment..."
& ".\venv\Scripts\Activate.ps1"

# Add src to PYTHONPATH
$env:PYTHONPATH = "$ProjectRoot\src;$env:PYTHONPATH"

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Starting services..." -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Start FastAPI backend in a new window
Write-Host "Starting FastAPI backend on port 8000..."
$backendProcess = Start-Process -FilePath "python" `
    -ArgumentList "-m", "uvicorn", "epdm_vacuum.api_main:app", "--host", "0.0.0.0", "--port", "8000" `
    -WorkingDirectory $ProjectRoot `
    -PassThru `
    -WindowStyle Normal

Start-Sleep -Seconds 2

# Check if backend is running
if ($backendProcess.HasExited) {
    Write-Host "ERROR: Backend failed to start!" -ForegroundColor Red
    exit 1
}

Write-Host "Backend started (PID: $($backendProcess.Id))" -ForegroundColor Green

# Start Next.js frontend in a new window
Write-Host "Starting Next.js frontend on port 3000..."
Set-Location web

if ((Test-Path ".next") -and (Test-Path ".next/BUILD_ID")) {
    Write-Host "Using production build..."
    $frontendProcess = Start-Process -FilePath "npm" `
        -ArgumentList "run", "start" `
        -PassThru `
        -WindowStyle Normal
} else {
    Write-Host "No production build found, using development mode..."
    $frontendProcess = Start-Process -FilePath "npm" `
        -ArgumentList "run", "dev" `
        -PassThru `
        -WindowStyle Normal
}

Set-Location ..

Start-Sleep -Seconds 3

# Get local IP
$LocalIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notlike "*Loopback*" -and $_.PrefixOrigin -eq "Dhcp" } | Select-Object -First 1).IPAddress
if (-not $LocalIP) { $LocalIP = "localhost" }

Write-Host ""
Write-Host "======================================" -ForegroundColor Green
Write-Host "Web interface ready!" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Local:    http://localhost:3000" -ForegroundColor White
Write-Host "  Network:  http://${LocalIP}:3000" -ForegroundColor White
Write-Host ""
Write-Host "  API:      http://${LocalIP}:8000" -ForegroundColor White
Write-Host "  API Docs: http://${LocalIP}:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop (or close windows manually)" -ForegroundColor Yellow
Write-Host "======================================" -ForegroundColor Green
Write-Host ""

# Wait for user to stop
try {
    Write-Host "Services running. Press Ctrl+C to stop..."
    while ($true) {
        Start-Sleep -Seconds 1
        
        # Check if processes are still running
        if ($backendProcess.HasExited -and $frontendProcess.HasExited) {
            Write-Host "All services stopped."
            break
        }
    }
} finally {
    # Cleanup
    Write-Host ""
    Write-Host "Shutting down..."
    
    if (-not $backendProcess.HasExited) {
        Stop-Process -Id $backendProcess.Id -Force -ErrorAction SilentlyContinue
    }
    if (-not $frontendProcess.HasExited) {
        Stop-Process -Id $frontendProcess.Id -Force -ErrorAction SilentlyContinue
    }
    
    Write-Host "Cleanup complete."
}



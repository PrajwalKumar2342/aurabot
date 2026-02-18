# Setup script for Screen Memory Assistant (Windows PowerShell)

Write-Host "Setting up Screen Memory Assistant..." -ForegroundColor Green

# Check Go installation
try {
    $goVersion = go version
    Write-Host "✓ Go installed: $goVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Go is not installed. Please install Go 1.21+ from https://go.dev/dl/" -ForegroundColor Red
    exit 1
}

# Download dependencies
Write-Host "Downloading Go dependencies..." -ForegroundColor Cyan
go mod download

# Check if LM Studio is running
Write-Host ""
Write-Host "Checking LM Studio..." -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "http://localhost:1234/v1/models" -Method GET -TimeoutSec 2 -ErrorAction SilentlyContinue
    Write-Host "✓ LM Studio is running" -ForegroundColor Green
} catch {
    Write-Host "⚠️ LM Studio not detected at http://localhost:1234" -ForegroundColor Yellow
    Write-Host "   Please start LM Studio and load a vision model"
}

# Check if Mem0 is running
Write-Host ""
Write-Host "Checking Mem0..." -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -Method GET -TimeoutSec 2 -ErrorAction SilentlyContinue
    Write-Host "✓ Mem0 is running" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Mem0 not detected at http://localhost:8000" -ForegroundColor Yellow
    Write-Host "   Install: pip install mem0ai"
    Write-Host "   Start: mem0 server"
}

Write-Host ""
Write-Host "Setup complete! Run with: go run ." -ForegroundColor Green

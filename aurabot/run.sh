#!/bin/bash
# Complete run script for AuraBot with permission handling

set -e

cd "$(dirname "$0")"

echo "========================================"
echo "    AURABOT - Screen Memory Assistant"
echo "========================================"
echo

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    if [ $2 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $1"
    else
        echo -e "${RED}✗${NC} $1"
    fi
}

# Check and request screen recording permission
check_screen_permission() {
    if screencapture -x /tmp/sc_test.png 2>/dev/null; then
        rm -f /tmp/sc_test.png
        return 0
    fi
    return 1
}

# Main check
echo "Checking prerequisites..."
echo

# 1. Check LM Studio
echo -n "1. LM Studio (port 1234): "
if curl -s http://localhost:1234/v1/models > /dev/null 2>&1; then
    print_status "Running" 0
    LMSTUDIO_OK=1
else
    print_status "Not running" 1
    echo
    echo "Please start LM Studio:"
    echo "  1. Open LM Studio"
    echo "  2. Load LFM2-350M-Q8_0.gguf"
    echo "  3. Start the API server (Developer tab)"
    echo
    exit 1
fi

# 2. Check screen recording permission
echo -n "2. Screen Recording: "
if check_screen_permission; then
    print_status "Permitted" 0
    PERMISSION_OK=1
else
    print_status "Permission Required" 1
    echo
    echo "${YELLOW}Screen Recording Permission Required!${NC}"
    echo
    echo "To grant permission:"
    echo "  1. Opening System Settings..."
    open 'x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture' 2>/dev/null || true
    echo
    echo "  2. Find 'Terminal' in the list"
    echo "  3. Toggle the switch ON"
    echo "  4. Return here and run this script again"
    echo
    read -p "Press Enter after granting permission..."
    
    # Check again
    if check_screen_permission; then
        echo -e "${GREEN}Permission granted!${NC}"
    else
        echo -e "${RED}Permission still not granted. Please try again.${NC}"
        exit 1
    fi
fi

echo

# Start services
echo "Starting services..."
echo

# Kill existing processes
pkill -f "mem0_server_split" 2>/dev/null || true
pkill -f "go run \\." 2>/dev/null || true
sleep 2

# Start Mem0 Server
echo -n "Starting Mem0 Server... "
cd python/src
python3 mem0_server_split.py > /tmp/mem0.log 2>&1 &
sleep 3

if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}OK${NC} (port 8000)"
else
    echo -e "${RED}FAILED${NC}"
    cat /tmp/mem0.log | tail -10
    exit 1
fi

# Start Go App
echo -n "Starting Go App... "
export PATH=$PATH:/opt/homebrew/go/bin:/usr/local/go/bin:$HOME/go/bin
cd ../go
go run . > /tmp/goapp.log 2>&1 &
sleep 5

if ps aux | grep "go run \\." | grep -v grep > /dev/null; then
    echo -e "${GREEN}OK${NC} (screen capture active)"
else
    echo -e "${RED}FAILED${NC}"
    cat /tmp/goapp.log | tail -10
    exit 1
fi

echo
echo "========================================"
echo -e "${GREEN}    ALL SERVICES RUNNING!${NC}"
echo "========================================"
echo
echo "Services:"
echo "  • LM Studio:      http://localhost:1234"
echo "  • Mem0 Server:    http://localhost:8000"
echo "  • Go App:         Screen capture every 30s"
echo "  • Extension API:  http://localhost:7345"
echo
echo "Logs:"
echo "  • Mem0:   tail -f /tmp/mem0.log"
echo "  • Go App: tail -f /tmp/goapp.log"
echo
echo "Press Ctrl+C to stop all services"
echo

# Wait for interrupt
trap 'echo; echo "Stopping services..."; pkill -f "mem0_server_split"; pkill -f "go run \\."; echo "Done!"; exit 0' INT

while true; do
    sleep 1
done

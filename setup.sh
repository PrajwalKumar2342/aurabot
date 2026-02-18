#!/bin/bash

# Setup script for Screen Memory Assistant

echo "Setting up Screen Memory Assistant..."

# Check Go installation
if ! command -v go &> /dev/null; then
    echo "❌ Go is not installed. Please install Go 1.21+ from https://go.dev/dl/"
    exit 1
fi

GO_VERSION=$(go version | awk '{print $3}')
echo "✓ Go installed: $GO_VERSION"

# Download dependencies
echo "Downloading Go dependencies..."
go mod download

# Check if LM Studio is running
echo ""
echo "Checking LM Studio..."
if curl -s http://localhost:1234/v1/models > /dev/null 2>&1; then
    echo "✓ LM Studio is running"
else
    echo "⚠️  LM Studio not detected at http://localhost:1234"
    echo "   Please start LM Studio and load a vision model"
fi

# Check if Mem0 is running
echo ""
echo "Checking Mem0..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✓ Mem0 is running"
else
    echo "⚠️  Mem0 not detected at http://localhost:8000"
    echo "   Install: pip install mem0ai"
    echo "   Start: mem0 server"
fi

echo ""
echo "Setup complete! Run with: go run ."

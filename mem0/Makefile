# Screen Memory Assistant Makefile

.PHONY: build test clean run deps install

BINARY_NAME=screen-memory-assistant
BUILD_DIR=build

# Build the application
build:
	mkdir -p $(BUILD_DIR)
	go build -o $(BUILD_DIR)/$(BINARY_NAME) .

# Build for macOS
build-macos:
	mkdir -p $(BUILD_DIR)
	GOOS=darwin GOARCH=amd64 go build -o $(BUILD_DIR)/$(BINARY_NAME)-macos-amd64 .
	GOOS=darwin GOARCH=arm64 go build -o $(BUILD_DIR)/$(BINARY_NAME)-macos-arm64 .

# Build for Windows
build-windows:
	mkdir -p $(BUILD_DIR)
	GOOS=windows GOARCH=amd64 go build -o $(BUILD_DIR)/$(BINARY_NAME)-windows.exe .

# Run tests
test:
	go test -v ./...

# Run tests with coverage
test-coverage:
	go test -cover ./...

# Clean build artifacts
clean:
	rm -rf $(BUILD_DIR)

# Run the application
run:
	go run .

# Download dependencies
deps:
	go mod download
	go mod tidy

# Install locally
install:
	go install .

# Development mode with verbose logging
dev:
	go run . -verbose

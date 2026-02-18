.PHONY: build build-macos build-windows build-linux run dev test test-coverage clean

BINARY_NAME=screen-memory-supermemory
CHAT_BINARY=chat

# Default build for current platform
build:
	go build -o $(BINARY_NAME) .
	go build -o $(CHAT_BINARY) ./cmd/chat

# Build for macOS
build-macos:
	GOOS=darwin GOARCH=amd64 go build -o $(BINARY_NAME)-macos-amd64 .
	GOOS=darwin GOARCH=arm64 go build -o $(BINARY_NAME)-macos-arm64 .
	GOOS=darwin GOARCH=amd64 go build -o $(CHAT_BINARY)-macos-amd64 ./cmd/chat
	GOOS=darwin GOARCH=arm64 go build -o $(CHAT_BINARY)-macos-arm64 ./cmd/chat

# Build for Windows
build-windows:
	GOOS=windows GOARCH=amd64 go build -o $(BINARY_NAME).exe .
	GOOS=windows GOARCH=amd64 go build -o $(CHAT_BINARY).exe ./cmd/chat

# Build for Linux
build-linux:
	GOOS=linux GOARCH=amd64 go build -o $(BINARY_NAME)-linux-amd64 .
	GOOS=linux GOARCH=amd64 go build -o $(CHAT_BINARY)-linux-amd64 ./cmd/chat

# Run the service
run:
	go run .

# Run with verbose logging
dev:
	go run . -verbose

# Run tests
test:
	go test -v ./...

# Run tests with coverage
test-coverage:
	go test -coverprofile=coverage.out ./...
	go tool cover -html=coverage.out -o coverage.html

# Clean build artifacts
clean:
	rm -f $(BINARY_NAME) $(BINARY_NAME)-* $(CHAT_BINARY) $(CHAT_BINARY)-* *.exe
	rm -f coverage.out coverage.html

# Install dependencies
deps:
	go mod download
	go mod tidy

# Format code
fmt:
	go fmt ./...

# Run linter
lint:
	golangci-lint run

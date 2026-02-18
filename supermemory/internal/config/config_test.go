package config

import (
	"os"
	"testing"
)

func TestLoad(t *testing.T) {
	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load() failed: %v", err)
	}

	// Check default values
	if cfg.Capture.IntervalSeconds != 30 {
		t.Errorf("Expected IntervalSeconds=30, got %d", cfg.Capture.IntervalSeconds)
	}

	if cfg.Memory.BaseURL != "http://localhost:8000" {
		t.Errorf("Expected BaseURL=http://localhost:8000, got %s", cfg.Memory.BaseURL)
	}
}

func TestLoadWithEnvVars(t *testing.T) {
	// Set environment variables
	os.Setenv("SUPERMEMORY_URL", "http://test:9000")
	os.Setenv("SUPERMEMORY_API_KEY", "test-key")
	defer func() {
		os.Unsetenv("SUPERMEMORY_URL")
		os.Unsetenv("SUPERMEMORY_API_KEY")
	}()

	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load() failed: %v", err)
	}

	if cfg.Memory.BaseURL != "http://test:9000" {
		t.Errorf("Expected BaseURL=http://test:9000, got %s", cfg.Memory.BaseURL)
	}

	if cfg.Memory.APIKey != "test-key" {
		t.Errorf("Expected APIKey=test-key, got %s", cfg.Memory.APIKey)
	}
}

func TestSave(t *testing.T) {
	cfg := &Config{
		Capture: CaptureConfig{
			IntervalSeconds: 60,
			Quality:         80,
		},
		Memory: MemoryConfig{
			APIKey:         "test-key",
			BaseURL:        "http://localhost:8000",
			UserID:         "test_user",
			CollectionName: "test_collection",
		},
	}

	tmpFile := "test_config.yaml"
	defer os.Remove(tmpFile)

	err := cfg.Save(tmpFile)
	if err != nil {
		t.Fatalf("Save() failed: %v", err)
	}

	// Check file exists
	if _, err := os.Stat(tmpFile); os.IsNotExist(err) {
		t.Error("Config file was not created")
	}
}

package service

import (
	"testing"

	"screen-memory-supermemory/internal/config"
)

func TestNew(t *testing.T) {
	cfg := &config.Config{
		Capture: config.CaptureConfig{
			IntervalSeconds: 30,
			Quality:         60,
			Enabled:         true,
		},
		LLM: config.LLMConfig{
			BaseURL:     "http://localhost:1234/v1",
			Model:       "test-model",
			MaxTokens:   512,
			Temperature: 0.7,
		},
		Memory: config.MemoryConfig{
			APIKey:         "test-key",
			BaseURL:        "http://localhost:8000",
			UserID:         "test_user",
			CollectionName: "test_collection",
		},
		App: config.AppConfig{
			Verbose:          false,
			ProcessOnCapture: true,
			MemoryWindow:     10,
		},
	}

	svc, err := New(cfg)
	if err != nil {
		t.Fatalf("New() failed: %v", err)
	}

	if svc == nil {
		t.Fatal("New() returned nil service")
	}

	if svc.config != cfg {
		t.Error("Service config mismatch")
	}

	if svc.capturer == nil {
		t.Error("Service capturer is nil")
	}

	if svc.llm == nil {
		t.Error("Service llm is nil")
	}

	if svc.memory == nil {
		t.Error("Service memory is nil")
	}
}

func TestGetStatus(t *testing.T) {
	cfg := &config.Config{
		Capture: config.CaptureConfig{
			IntervalSeconds: 30,
			Quality:         60,
			Enabled:         true,
		},
		Memory: config.MemoryConfig{
			APIKey:         "test-key",
			BaseURL:        "http://localhost:8000",
			UserID:         "test_user",
			CollectionName: "test_collection",
		},
		App: config.AppConfig{
			Verbose:          false,
			ProcessOnCapture: true,
			MemoryWindow:     10,
		},
	}

	svc, err := New(cfg)
	if err != nil {
		t.Fatalf("New() failed: %v", err)
	}

	status := svc.GetStatus()

	if status["running"] != false {
		t.Errorf("Expected running=false, got %v", status["running"])
	}

	if status["platform"] == "" {
		t.Error("Platform should not be empty")
	}

	configMap, ok := status["config"].(map[string]interface{})
	if !ok {
		t.Fatal("Config not found in status")
	}

	if configMap["capture_interval"] != 30 {
		t.Errorf("Expected capture_interval=30, got %v", configMap["capture_interval"])
	}
}

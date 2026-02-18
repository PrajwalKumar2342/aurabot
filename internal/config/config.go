package config

import (
	"fmt"
	"os"

	"gopkg.in/yaml.v3"
)

// Config holds all application configuration
type Config struct {
	Capture CaptureConfig `yaml:"capture"`
	LLM     LLMConfig     `yaml:"llm"`
	Memory  MemoryConfig  `yaml:"memory"`
	App     AppConfig     `yaml:"app"`
}

// CaptureConfig holds screen capture settings
type CaptureConfig struct {
	IntervalSeconds int  `yaml:"interval_seconds"`
	Quality         int  `yaml:"quality"`
	Enabled         bool `yaml:"enabled"`
}

// LLMConfig holds LLM API settings
type LLMConfig struct {
	BaseURL        string  `yaml:"base_url"`
	Model          string  `yaml:"model"`
	MaxTokens      int     `yaml:"max_tokens"`
	Temperature    float32 `yaml:"temperature"`
	TimeoutSeconds int     `yaml:"timeout_seconds"`
}

// MemoryConfig holds Mem0 settings
type MemoryConfig struct {
	APIKey         string `yaml:"api_key"`
	BaseURL        string `yaml:"base_url"`
	UserID         string `yaml:"user_id"`
	CollectionName string `yaml:"collection_name"`
}

// AppConfig holds general app settings
type AppConfig struct {
	Verbose          bool `yaml:"verbose"`
	ProcessOnCapture bool `yaml:"process_on_capture"`
	MemoryWindow     int  `yaml:"memory_window"`
}

// Load reads config from file or creates default
func Load() (*Config, error) {
	cfg := &Config{
		Capture: CaptureConfig{
			IntervalSeconds: 30,
			Quality:         85,
			Enabled:         true,
		},
		LLM: LLMConfig{
			BaseURL:        "http://localhost:1234/v1",
			Model:          "local-model",
			MaxTokens:      512,
			Temperature:    0.7,
			TimeoutSeconds: 30,
		},
		Memory: MemoryConfig{
			APIKey:         "",
			BaseURL:        "http://localhost:8000",
			UserID:         "default_user",
			CollectionName: "screen_memories",
		},
		App: AppConfig{
			Verbose:          false,
			ProcessOnCapture: true,
			MemoryWindow:     10,
		},
	}

	// Try to load from file
	if _, err := os.Stat("config.yaml"); err == nil {
		data, err := os.ReadFile("config.yaml")
		if err != nil {
			return nil, fmt.Errorf("reading config file: %w", err)
		}
		if err := yaml.Unmarshal(data, cfg); err != nil {
			return nil, fmt.Errorf("parsing config file: %w", err)
		}
	}

	// Override with environment variables
	if val := os.Getenv("LM_STUDIO_URL"); val != "" {
		cfg.LLM.BaseURL = val
	}
	if val := os.Getenv("MEM0_URL"); val != "" {
		cfg.Memory.BaseURL = val
	}
	if val := os.Getenv("MEM0_API_KEY"); val != "" {
		cfg.Memory.APIKey = val
	}

	return cfg, nil
}

// Save writes current config to file
func (c *Config) Save(path string) error {
	data, err := yaml.Marshal(c)
	if err != nil {
		return err
	}
	return os.WriteFile(path, data, 0644)
}

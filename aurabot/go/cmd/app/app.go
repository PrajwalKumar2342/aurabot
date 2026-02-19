package main

import (
	"context"
	"fmt"
	"time"

	"screen-memory-assistant/internal/config"
	"screen-memory-assistant/internal/service"
)

// App struct
type App struct {
	ctx     context.Context
	service *service.Service
	config  *config.Config
}

// NewApp creates a new App application struct
func NewApp() *App {
	return &App{}
}

// Startup is called when the app starts
func (a *App) Startup(ctx context.Context) {
	a.ctx = ctx

	// Load configuration
	cfg, err := config.Load()
	if err != nil {
		fmt.Printf("Failed to load config: %v\n", err)
		return
	}
	a.config = cfg

	// Create service instance
	svc, err := service.New(cfg)
	if err != nil {
		fmt.Printf("Failed to create service: %v\n", err)
		return
	}
	a.service = svc

	// Start service in background
	go func() {
		serviceCtx, cancel := context.WithCancel(context.Background())
		defer cancel()
		if err := svc.Run(serviceCtx); err != nil {
			fmt.Printf("Service error: %v\n", err)
		}
	}()
}

// Shutdown is called when the app shuts down
func (a *App) Shutdown(ctx context.Context) {
	// Cleanup if needed
}

// GetStatus returns the current service status
func (a *App) GetStatus() map[string]interface{} {
	if a.service == nil {
		return map[string]interface{}{
			"running":   false,
			"platform":  "unknown",
			"lastState": "Service not initialized",
		}
	}
	return a.service.GetStatus()
}

// Chat sends a message and returns the response
func (a *App) Chat(message string) (string, error) {
	if a.service == nil {
		return "", fmt.Errorf("service not initialized")
	}

	ctx, cancel := context.WithTimeout(a.ctx, 30*time.Second)
	defer cancel()

	return a.service.Chat(ctx, message)
}

// GetConfig returns the current configuration
func (a *App) GetConfig() map[string]interface{} {
	if a.config == nil {
		return map[string]interface{}{}
	}

	return map[string]interface{}{
		"capture": map[string]interface{}{
			"intervalSeconds": a.config.Capture.IntervalSeconds,
			"quality":         a.config.Capture.Quality,
			"maxWidth":        a.config.Capture.MaxWidth,
			"maxHeight":       a.config.Capture.MaxHeight,
			"enabled":         a.config.Capture.Enabled,
		},
		"llm": map[string]interface{}{
			"baseUrl":        a.config.LLM.BaseURL,
			"model":          a.config.LLM.Model,
			"maxTokens":      a.config.LLM.MaxTokens,
			"temperature":    a.config.LLM.Temperature,
			"timeoutSeconds": a.config.LLM.TimeoutSeconds,
		},
		"memory": map[string]interface{}{
			"baseUrl":        a.config.Memory.BaseURL,
			"userId":         a.config.Memory.UserID,
			"collectionName": a.config.Memory.CollectionName,
		},
		"app": map[string]interface{}{
			"verbose":          a.config.App.Verbose,
			"processOnCapture": a.config.App.ProcessOnCapture,
			"memoryWindow":     a.config.App.MemoryWindow,
		},
	}
}

// UpdateConfig updates configuration values
func (a *App) UpdateConfig(updates map[string]interface{}) error {
	if a.config == nil {
		return fmt.Errorf("config not initialized")
	}

	// Update capture settings
	if capture, ok := updates["capture"].(map[string]interface{}); ok {
		if v, ok := capture["intervalSeconds"].(float64); ok {
			a.config.Capture.IntervalSeconds = int(v)
		}
		if v, ok := capture["quality"].(float64); ok {
			a.config.Capture.Quality = int(v)
		}
		if v, ok := capture["enabled"].(bool); ok {
			a.config.Capture.Enabled = v
		}
	}

	// Save config to file
	return a.config.Save("config.yaml")
}

// GetMemories returns recent memories (placeholder - would need mem0 client)
func (a *App) GetMemories(limit int) []map[string]interface{} {
	// This would require direct mem0 client access
	// For now, return mock data
	return []map[string]interface{}{
		{
			"id":        "1",
			"content":   "User was working on code editor, typing Go code",
			"timestamp": time.Now().Add(-5 * time.Minute).Format(time.RFC3339),
			"metadata": map[string]string{
				"context": "Coding session",
			},
		},
	}
}

// ToggleCapture enables/disables screen capture
func (a *App) ToggleCapture(enabled bool) bool {
	if a.config == nil {
		return false
	}
	a.config.Capture.Enabled = enabled
	return a.config.Capture.Enabled
}

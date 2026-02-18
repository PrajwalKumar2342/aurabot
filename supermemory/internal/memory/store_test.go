package memory

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"screen-memory-supermemory/internal/config"
)

func TestNewStore(t *testing.T) {
	cfg := &config.MemoryConfig{
		APIKey:         "test-key",
		BaseURL:        "http://localhost:8000",
		UserID:         "test_user",
		CollectionName: "test_collection",
	}

	store := NewStore(cfg)
	if store == nil {
		t.Fatal("NewStore() returned nil")
	}

	if store.config != cfg {
		t.Error("Store config mismatch")
	}

	if store.httpClient == nil {
		t.Error("Store httpClient is nil")
	}

	if store.httpClient.Timeout != 10*time.Second {
		t.Errorf("Expected timeout 10s, got %v", store.httpClient.Timeout)
	}
}

func TestAddMemory(t *testing.T) {
	// Create test server
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "POST" {
			t.Errorf("Expected POST, got %s", r.Method)
		}

		if r.URL.Path != "/v1/memories/" {
			t.Errorf("Expected path /v1/memories/, got %s", r.URL.Path)
		}

		// Check authorization header
		authHeader := r.Header.Get("Authorization")
		if authHeader != "Bearer test-key" {
			t.Errorf("Expected Authorization header, got %s", authHeader)
		}

		// Parse request body
		var payload map[string]interface{}
		if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
			t.Fatalf("Failed to decode request: %v", err)
		}

		if payload["content"] != "Test memory content" {
			t.Errorf("Expected content 'Test memory content', got %v", payload["content"])
		}

		// Return success response
		w.WriteHeader(http.StatusCreated)
		json.NewEncoder(w).Encode(map[string]string{
			"id": "test-memory-id",
		})
	}))
	defer server.Close()

	cfg := &config.MemoryConfig{
		APIKey:         "test-key",
		BaseURL:        server.URL,
		UserID:         "test_user",
		CollectionName: "test_collection",
	}

	store := NewStore(cfg)
	metadata := Metadata{
		Timestamp:   time.Now().Format(time.RFC3339),
		Context:     "test",
		Activities:  []string{"testing"},
		KeyElements: []string{"test"},
		UserIntent:  "testing",
		DisplayNum:  0,
	}

	memory, err := store.Add("Test memory content", metadata)
	if err != nil {
		t.Fatalf("Add() failed: %v", err)
	}

	if memory.Content != "Test memory content" {
		t.Errorf("Expected content 'Test memory content', got %s", memory.Content)
	}
}

func TestSearchMemories(t *testing.T) {
	// Create test server
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "POST" {
			t.Errorf("Expected POST, got %s", r.Method)
		}

		if r.URL.Path != "/v1/memories/search/" {
			t.Errorf("Expected path /v1/memories/search/, got %s", r.URL.Path)
		}

		// Return search results
		response := map[string]interface{}{
			"results": []map[string]interface{}{
				{
					"id":     "mem-1",
					"memory": "Test memory 1",
					"score":  0.95,
				},
				{
					"id":     "mem-2",
					"memory": "Test memory 2",
					"score":  0.85,
				},
			},
		}
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(response)
	}))
	defer server.Close()

	cfg := &config.MemoryConfig{
		APIKey:         "test-key",
		BaseURL:        server.URL,
		UserID:         "test_user",
		CollectionName: "test_collection",
	}

	store := NewStore(cfg)
	results, err := store.Search("test query", 10)
	if err != nil {
		t.Fatalf("Search() failed: %v", err)
	}

	if len(results) != 2 {
		t.Errorf("Expected 2 results, got %d", len(results))
	}

	if results[0].Memory.Content != "Test memory 1" {
		t.Errorf("Expected first result 'Test memory 1', got %s", results[0].Memory.Content)
	}
}

func TestCheckHealth(t *testing.T) {
	// Create test server
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/health" {
			t.Errorf("Expected path /health, got %s", r.URL.Path)
		}
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
	}))
	defer server.Close()

	cfg := &config.MemoryConfig{
		APIKey:         "test-key",
		BaseURL:        server.URL,
		UserID:         "test_user",
		CollectionName: "test_collection",
	}

	store := NewStore(cfg)
	err := store.CheckHealth()
	if err != nil {
		t.Fatalf("CheckHealth() failed: %v", err)
	}
}

func TestCheckHealthFailure(t *testing.T) {
	// Create test server that returns error
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusServiceUnavailable)
	}))
	defer server.Close()

	cfg := &config.MemoryConfig{
		APIKey:         "test-key",
		BaseURL:        server.URL,
		UserID:         "test_user",
		CollectionName: "test_collection",
	}

	store := NewStore(cfg)
	err := store.CheckHealth()
	if err == nil {
		t.Error("CheckHealth() should have failed")
	}
}

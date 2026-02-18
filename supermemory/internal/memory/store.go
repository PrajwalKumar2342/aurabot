package memory

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"time"

	"screen-memory-supermemory/internal/config"
)

// Memory represents a stored memory
type Memory struct {
	ID        string    `json:"id"`
	Content   string    `json:"content"`
	UserID    string    `json:"user_id"`
	Metadata  Metadata  `json:"metadata"`
	CreatedAt time.Time `json:"created_at"`
}

// Metadata contains additional context about the memory
type Metadata struct {
	Timestamp   string   `json:"timestamp"`
	Context     string   `json:"context"`
	Activities  []string `json:"activities"`
	KeyElements []string `json:"key_elements"`
	UserIntent  string   `json:"user_intent"`
	DisplayNum  int      `json:"display_num"`
}

// SearchResult represents a memory search result
type SearchResult struct {
	Memory   Memory  `json:"memory"`
	Score    float64 `json:"score"`
	Distance float64 `json:"distance"`
}

// parseTime parses an ISO8601 time string, returning zero time on error
func parseTime(s string) time.Time {
	t, _ := time.Parse(time.RFC3339, s)
	return t
}

// Store handles Supermemory operations
type Store struct {
	config     *config.MemoryConfig
	httpClient *http.Client
}

// NewStore creates a new memory store
func NewStore(cfg *config.MemoryConfig) *Store {
	return &Store{
		config: cfg,
		httpClient: &http.Client{
			Timeout: 10 * time.Second,
		},
	}
}

// Add stores a new memory
func (s *Store) Add(content string, metadata Metadata) (*Memory, error) {
	url := fmt.Sprintf("%s/v1/memories/", s.config.BaseURL)

	memory := &Memory{
		Content:   content,
		UserID:    s.config.UserID,
		Metadata:  metadata,
		CreatedAt: time.Now(),
	}

	payload := map[string]interface{}{
		"content":       content,
		"container_tag": s.config.CollectionName,
		"metadata":      metadata,
	}

	jsonData, err := json.Marshal(payload)
	if err != nil {
		return nil, fmt.Errorf("marshaling memory: %w", err)
	}

	req, err := http.NewRequest("POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("creating request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	if s.config.APIKey != "" {
		req.Header.Set("Authorization", "Bearer "+s.config.APIKey)
	}

	resp, err := s.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("sending request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusCreated {
		return nil, fmt.Errorf("unexpected status: %d", resp.StatusCode)
	}

	// Parse response to get the ID
	var result struct {
		ID string `json:"id"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&result); err == nil && result.ID != "" {
		memory.ID = result.ID
	}

	return memory, nil
}

// Search retrieves relevant memories based on query
func (s *Store) Search(query string, limit int) ([]SearchResult, error) {
	url := fmt.Sprintf("%s/v1/memories/search/", s.config.BaseURL)

	if limit <= 0 {
		limit = 10
	}

	payload := map[string]interface{}{
		"q":             query,
		"container_tag": s.config.CollectionName,
		"limit":         limit,
	}

	jsonData, err := json.Marshal(payload)
	if err != nil {
		return nil, fmt.Errorf("marshaling search: %w", err)
	}

	req, err := http.NewRequest("POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("creating request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	if s.config.APIKey != "" {
		req.Header.Set("Authorization", "Bearer "+s.config.APIKey)
	}

	resp, err := s.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("sending request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("unexpected status: %d", resp.StatusCode)
	}

	var result struct {
		Results []struct {
			Content   string    `json:"memory"`  // Python sends "memory" field
			ID        string    `json:"id"`
			UserID    string    `json:"user_id"`
			Score     float64   `json:"score"`
			Distance  float64   `json:"distance"`
			Metadata  Metadata  `json:"metadata"`
			CreatedAt string    `json:"created_at"`
		} `json:"results"`
	}

	bodyBytes, _ := io.ReadAll(resp.Body)
	log.Printf("[DEBUG] Raw response: %.500s", string(bodyBytes))
	
	if err := json.Unmarshal(bodyBytes, &result); err != nil {
		return nil, fmt.Errorf("decoding response: %w", err)
	}

	var searchResults []SearchResult
	for _, r := range result.Results {
		searchResults = append(searchResults, SearchResult{
			Memory: Memory{
				ID:        r.ID,
				Content:   r.Content,
				UserID:    r.UserID,
				Metadata:  r.Metadata,
				CreatedAt: parseTime(r.CreatedAt),
			},
			Score:    r.Score,
			Distance: r.Distance,
		})
	}

	return searchResults, nil
}

// GetRecent retrieves the most recent memories
func (s *Store) GetRecent(limit int) ([]Memory, error) {
	// Supermemory doesn't have a direct "get recent" endpoint
	// We'll use search with an empty query to get recent memories
	url := fmt.Sprintf("%s/v1/memories/", s.config.BaseURL)

	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("creating request: %w", err)
	}

	// Add query parameters
	q := req.URL.Query()
	q.Add("container_tag", s.config.CollectionName)
	q.Add("limit", fmt.Sprintf("%d", limit))
	req.URL.RawQuery = q.Encode()

	if s.config.APIKey != "" {
		req.Header.Set("Authorization", "Bearer "+s.config.APIKey)
	}

	resp, err := s.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("sending request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("unexpected status: %d", resp.StatusCode)
	}

	var memories []Memory
	if err := json.NewDecoder(resp.Body).Decode(&memories); err != nil {
		return nil, fmt.Errorf("decoding response: %w", err)
	}

	return memories, nil
}

// Delete removes a memory by ID
func (s *Store) Delete(memoryID string) error {
	url := fmt.Sprintf("%s/v1/memories/%s", s.config.BaseURL, memoryID)

	req, err := http.NewRequest("DELETE", url, nil)
	if err != nil {
		return fmt.Errorf("creating request: %w", err)
	}

	if s.config.APIKey != "" {
		req.Header.Set("Authorization", "Bearer "+s.config.APIKey)
	}

	resp, err := s.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("sending request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusNoContent {
		return fmt.Errorf("unexpected status: %d", resp.StatusCode)
	}

	return nil
}

// CheckHealth verifies the Supermemory endpoint is available
func (s *Store) CheckHealth() error {
	url := fmt.Sprintf("%s/health", s.config.BaseURL)

	resp, err := s.httpClient.Get(url)
	if err != nil {
		return fmt.Errorf("health check failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("health check returned: %d", resp.StatusCode)
	}

	return nil
}

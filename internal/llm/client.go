package llm

import (
	"context"
	"encoding/base64"
	"fmt"
	"time"

	"github.com/sashabaranov/go-openai"
	"screen-memory-assistant/internal/config"
)

// Client wraps the OpenAI-compatible LLM API
type Client struct {
	client *openai.Client
	config *config.LLMConfig
}

// VisionMessage represents a message with image content
type VisionMessage struct {
	Role        string
	Text        string
	ImageBase64 string
}

// AnalysisResult contains the LLM's understanding of a screen
type AnalysisResult struct {
	Summary     string   `json:"summary"`
	Context     string   `json:"context"`
	Activities  []string `json:"activities"`
	KeyElements []string `json:"key_elements"`
	UserIntent  string   `json:"user_intent"`
}

// NewClient creates a new LLM client
func NewClient(cfg *config.LLMConfig) *Client {
	config := openai.DefaultConfig("")
	config.BaseURL = cfg.BaseURL

	return &Client{
		client: openai.NewClientWithConfig(config),
		config: cfg,
	}
}

// AnalyzeScreen sends a screen capture to the LLM for analysis
func (c *Client) AnalyzeScreen(ctx context.Context, imageData []byte, previousContext string) (*AnalysisResult, error) {
	ctx, cancel := context.WithTimeout(ctx, time.Duration(c.config.TimeoutSeconds)*time.Second)
	defer cancel()

	base64Image := base64.StdEncoding.EncodeToString(imageData)
	dataURL := fmt.Sprintf("data:image/jpeg;base64,%s", base64Image)

	// Build system prompt
	systemPrompt := `You are a personal AI assistant observing the user's screen. Analyze what you see and provide:
1. A brief summary of what's on screen
2. The context (work, entertainment, communication, etc.)
3. Activities the user might be doing
4. Key UI elements visible
5. What the user likely intends to do

Respond in this exact JSON format:
{
  "summary": "brief description",
  "context": "work/entertainment/social/etc",
  "activities": ["activity1", "activity2"],
  "key_elements": ["element1", "element2"],
  "user_intent": "what user is trying to accomplish"
}`

	// Add previous context if available
	userPrompt := "Analyze this screenshot:"
	if previousContext != "" {
		userPrompt = fmt.Sprintf("Previous context: %s\n\nAnalyze this new screenshot:", previousContext)
	}

	req := openai.ChatCompletionRequest{
		Model: c.config.Model,
		Messages: []openai.ChatCompletionMessage{
			{
				Role:    openai.ChatMessageRoleSystem,
				Content: systemPrompt,
			},
			{
				Role: openai.ChatMessageRoleUser,
				MultiContent: []openai.ChatMessagePart{
					{
						Type: openai.ChatMessagePartTypeText,
						Text: userPrompt,
					},
					{
						Type: openai.ChatMessagePartTypeImageURL,
						ImageURL: &openai.ChatMessageImageURL{
							URL:    dataURL,
							Detail: openai.ImageURLDetailLow, // Use low detail for speed
						},
					},
				},
			},
		},
		MaxTokens:   c.config.MaxTokens,
		Temperature: c.config.Temperature,
	}

	resp, err := c.client.CreateChatCompletion(ctx, req)
	if err != nil {
		return nil, fmt.Errorf("LLM API error: %w", err)
	}

	if len(resp.Choices) == 0 {
		return nil, fmt.Errorf("no response from LLM")
	}

	// Parse the response
	return c.parseResponse(resp.Choices[0].Message.Content), nil
}

// GenerateResponse generates a conversational response based on context
func (c *Client) GenerateResponse(ctx context.Context, prompt string, memories []string) (string, error) {
	ctx, cancel := context.WithTimeout(ctx, time.Duration(c.config.TimeoutSeconds)*time.Second)
	defer cancel()

	systemPrompt := "You are a helpful AI assistant that knows the user well through their screen activity history. Be concise and contextually aware."

	// Include memories as context
	userPrompt := prompt
	if len(memories) > 0 {
		memoryContext := "Based on your activity history:\n"
		for _, m := range memories {
			memoryContext += "- " + m + "\n"
		}
		userPrompt = memoryContext + "\nUser: " + prompt
	}

	req := openai.ChatCompletionRequest{
		Model: c.config.Model,
		Messages: []openai.ChatCompletionMessage{
			{
				Role:    openai.ChatMessageRoleSystem,
				Content: systemPrompt,
			},
			{
				Role:    openai.ChatMessageRoleUser,
				Content: userPrompt,
			},
		},
		MaxTokens:   c.config.MaxTokens,
		Temperature: c.config.Temperature,
	}

	resp, err := c.client.CreateChatCompletion(ctx, req)
	if err != nil {
		return "", fmt.Errorf("LLM API error: %w", err)
	}

	if len(resp.Choices) == 0 {
		return "", fmt.Errorf("no response from LLM")
	}

	return resp.Choices[0].Message.Content, nil
}

// parseResponse extracts structured data from LLM text response
func (c *Client) parseResponse(content string) *AnalysisResult {
	// Simple parsing - in production, use proper JSON parsing
	result := &AnalysisResult{
		Summary:     content,
		Context:     "unknown",
		Activities:  []string{},
		KeyElements: []string{},
		UserIntent:  "unknown",
	}

	// Try to extract structured fields if JSON-like
	// For now, use the full content as summary
	if len(content) > 500 {
		result.Summary = content[:500] + "..."
	}

	return result
}

// CheckHealth verifies the LLM endpoint is available
func (c *Client) CheckHealth(ctx context.Context) error {
	ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	req := openai.ChatCompletionRequest{
		Model: c.config.Model,
		Messages: []openai.ChatCompletionMessage{
			{
				Role:    openai.ChatMessageRoleUser,
				Content: "Hi",
			},
		},
		MaxTokens: 5,
	}

	_, err := c.client.CreateChatCompletion(ctx, req)
	return err
}

package capture

import (
	"bytes"
	"fmt"
	"image"
	"image/jpeg"
	"runtime"
	"time"

	"github.com/kbinani/screenshot"
	"screen-memory-assistant/internal/config"
)

// Capture represents a screen capture with metadata
type Capture struct {
	Timestamp  time.Time
	Image      image.Image
	Compressed []byte
	DisplayNum int
}

// Capturer handles screen capture operations
type Capturer struct {
	config *config.CaptureConfig
}

// New creates a new screen capturer
func New(cfg *config.CaptureConfig) *Capturer {
	return &Capturer{
		config: cfg,
	}
}

// CaptureScreen captures all displays and returns them
func (c *Capturer) CaptureScreen() ([]*Capture, error) {
	n := screenshot.NumActiveDisplays()
	if n == 0 {
		return nil, fmt.Errorf("no active displays found")
	}

	var captures []*Capture
	now := time.Now()

	for i := 0; i < n; i++ {
		bounds := screenshot.GetDisplayBounds(i)
		img, err := screenshot.CaptureRect(bounds)
		if err != nil {
			return nil, fmt.Errorf("capturing display %d: %w", i, err)
		}

		// Compress full image
		compressed, err := c.compress(img)
		if err != nil {
			return nil, fmt.Errorf("compressing display %d: %w", i, err)
		}

		captures = append(captures, &Capture{
			Timestamp:  now,
			Image:      img,
			Compressed: compressed,
			DisplayNum: i,
		})
	}

	return captures, nil
}

// CapturePrimary captures only the primary display
func (c *Capturer) CapturePrimary() (*Capture, error) {
	n := screenshot.NumActiveDisplays()
	if n == 0 {
		return nil, fmt.Errorf("no active displays found")
	}

	bounds := screenshot.GetDisplayBounds(0)
	img, err := screenshot.CaptureRect(bounds)
	if err != nil {
		return nil, fmt.Errorf("capturing primary display: %w", err)
	}

	// Compress full image
	compressed, err := c.compress(img)
	if err != nil {
		return nil, fmt.Errorf("compressing: %w", err)
	}

	return &Capture{
		Timestamp:  time.Now(),
		Image:      img,
		Compressed: compressed,
		DisplayNum: 0,
	}, nil
}

// compress converts image to JPEG
func (c *Capturer) compress(img image.Image) ([]byte, error) {
	var buf bytes.Buffer

	quality := c.config.Quality
	if quality <= 0 || quality > 100 {
		quality = 85
	}

	opts := &jpeg.Options{Quality: quality}
	if err := jpeg.Encode(&buf, img, opts); err != nil {
		return nil, err
	}

	return buf.Bytes(), nil
}

// GetPlatform returns the current platform name
func GetPlatform() string {
	return runtime.GOOS
}

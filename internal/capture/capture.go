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

		// Resize if needed
		resizedImg := c.resize(img)

		// Compress
		compressed, err := c.compress(resizedImg)
		if err != nil {
			return nil, fmt.Errorf("compressing display %d: %w", i, err)
		}

		captures = append(captures, &Capture{
			Timestamp:  now,
			Image:      resizedImg,
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

	// Resize if needed
	resizedImg := c.resize(img)

	// Compress
	compressed, err := c.compress(resizedImg)
	if err != nil {
		return nil, fmt.Errorf("compressing: %w", err)
	}

	return &Capture{
		Timestamp:  time.Now(),
		Image:      resizedImg,
		Compressed: compressed,
		DisplayNum: 0,
	}, nil
}

// resize scales down the image if it exceeds max width
func (c *Capturer) resize(img image.Image) image.Image {
	if c.config.MaxWidth <= 0 {
		return img
	}

	bounds := img.Bounds()
	width := bounds.Dx()

	if width <= c.config.MaxWidth {
		return img
	}

	ratio := float64(c.config.MaxWidth) / float64(width)
	height := int(float64(bounds.Dy()) * ratio)

	return resizeImage(img, c.config.MaxWidth, height)
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

// resizeImage uses simple nearest neighbor for performance
func resizeImage(src image.Image, newWidth, newHeight int) image.Image {
	bounds := src.Bounds()
	oldWidth := bounds.Dx()
	oldHeight := bounds.Dy()

	dst := image.NewRGBA(image.Rect(0, 0, newWidth, newHeight))

	xRatio := float64(oldWidth) / float64(newWidth)
	yRatio := float64(oldHeight) / float64(newHeight)

	for y := 0; y < newHeight; y++ {
		for x := 0; x < newWidth; x++ {
			srcX := int(float64(x) * xRatio)
			srcY := int(float64(y) * yRatio)
			dst.Set(x, y, src.At(bounds.Min.X+srcX, bounds.Min.Y+srcY))
		}
	}

	return dst
}

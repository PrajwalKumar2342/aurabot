package capture

import (
	"image"
	"image/color"
	"testing"

	"screen-memory-assistant/internal/config"
)

func TestCapturer_resize(t *testing.T) {
	tests := []struct {
		name      string
		maxWidth  int
		imgWidth  int
		imgHeight int
		wantWidth int
	}{
		{
			name:      "no resize needed",
			maxWidth:  1024,
			imgWidth:  800,
			imgHeight: 600,
			wantWidth: 800,
		},
		{
			name:      "resize large image",
			maxWidth:  512,
			imgWidth:  1920,
			imgHeight: 1080,
			wantWidth: 512,
		},
		{
			name:      "max width 0 - no resize",
			maxWidth:  0,
			imgWidth:  800,
			imgHeight: 600,
			wantWidth: 800,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			c := New(&config.CaptureConfig{MaxWidth: tt.maxWidth})

			// Create test image
			img := image.NewRGBA(image.Rect(0, 0, tt.imgWidth, tt.imgHeight))

			result := c.resize(img)
			gotWidth := result.Bounds().Dx()

			if gotWidth != tt.wantWidth {
				t.Errorf("resize() width = %d, want %d", gotWidth, tt.wantWidth)
			}
		})
	}
}

func TestCapturer_compress(t *testing.T) {
	c := New(&config.CaptureConfig{Quality: 85})

	// Create a test image
	img := image.NewRGBA(image.Rect(0, 0, 100, 100))
	// Fill with some color
	for x := 0; x < 100; x++ {
		for y := 0; y < 100; y++ {
			img.Set(x, y, color.RGBA{100, 150, 200, 255})
		}
	}

	data, err := c.compress(img)
	if err != nil {
		t.Fatalf("compress failed: %v", err)
	}

	if len(data) == 0 {
		t.Error("compressed data is empty")
	}

	// JPEG data should start with 0xFF 0xD8
	if data[0] != 0xFF || data[1] != 0xD8 {
		t.Error("compressed data is not valid JPEG")
	}
}

func TestResizeImage(t *testing.T) {
	src := image.NewRGBA(image.Rect(0, 0, 400, 300))

	dst := resizeImage(src, 200, 150)

	if dst.Bounds().Dx() != 200 {
		t.Errorf("width = %d, want 200", dst.Bounds().Dx())
	}
	if dst.Bounds().Dy() != 150 {
		t.Errorf("height = %d, want 150", dst.Bounds().Dy())
	}
}

func TestGetPlatform(t *testing.T) {
	platform := GetPlatform()
	if platform == "" {
		t.Error("GetPlatform() returned empty string")
	}

	// Should be one of known platforms
	validPlatforms := map[string]bool{
		"darwin":  true,
		"windows": true,
		"linux":   true,
	}

	if !validPlatforms[platform] {
		t.Errorf("GetPlatform() returned unknown platform: %s", platform)
	}
}

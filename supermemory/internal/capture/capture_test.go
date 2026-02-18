package capture

import (
	"image"
	"testing"

	"screen-memory-supermemory/internal/config"
)

func TestNew(t *testing.T) {
	cfg := &config.CaptureConfig{
		IntervalSeconds: 30,
		Quality:         60,
		MaxWidth:        1280,
		MaxHeight:       720,
		Enabled:         true,
	}

	capturer := New(cfg)
	if capturer == nil {
		t.Fatal("New() returned nil")
	}

	if capturer.config != cfg {
		t.Error("Capturer config mismatch")
	}
}

func TestGetPlatform(t *testing.T) {
	platform := GetPlatform()
	if platform == "" {
		t.Error("GetPlatform() returned empty string")
	}

	// Should be one of the known platforms
	validPlatforms := map[string]bool{
		"windows": true,
		"darwin":  true,
		"linux":   true,
	}

	if !validPlatforms[platform] {
		t.Errorf("GetPlatform() returned unknown platform: %s", platform)
	}
}

func TestResizeImage(t *testing.T) {
	// Create a test image
	img := image.NewRGBA(image.Rect(0, 0, 1920, 1080))

	// Test resize down
	resized := resizeImage(img, 1280, 720)
	bounds := resized.Bounds()

	if bounds.Dx() > 1280 {
		t.Errorf("Width %d exceeds max 1280", bounds.Dx())
	}

	if bounds.Dy() > 720 {
		t.Errorf("Height %d exceeds max 720", bounds.Dy())
	}

	// Test no resize needed
	smallImg := image.NewRGBA(image.Rect(0, 0, 640, 480))
	notResized := resizeImage(smallImg, 1280, 720)

	if notResized != smallImg {
		t.Error("Image was resized when it shouldn't have been")
	}

	// Test zero dimensions (should return original)
	original := resizeImage(img, 0, 0)
	if original != img {
		t.Error("Image should be returned unchanged when max dimensions are 0")
	}
}

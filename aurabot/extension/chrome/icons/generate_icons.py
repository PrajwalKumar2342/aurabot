#!/usr/bin/env python3
"""Generate PNG icons for Chrome extension from SVG."""

import sys
import os

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("Pillow not installed. Installing...")
    os.system(f"{sys.executable} -m pip install Pillow")
    from PIL import Image, ImageDraw


def create_icon(size, output_path):
    """Create a simple icon with gradient background."""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Background gradient simulation (purple)
    padding = size // 8
    draw.rounded_rectangle(
        [padding, padding, size - padding, size - padding],
        radius=size // 8,
        fill=(99, 102, 241, 255)  # Indigo-500
    )
    
    # Draw stacked layers (simplified memory stack icon)
    line_color = (255, 255, 255, 255)
    line_width = max(1, size // 16)
    center_y = size // 2
    spacing = size // 8
    
    # Three horizontal lines (stacked)
    for i in range(3):
        y = center_y - spacing + (i * spacing)
        x_start = size // 4
        x_end = size - size // 4
        # Offset each layer slightly
        offset = (1 - i) * (size // 20)
        draw.line(
            [(x_start + offset, y), (x_end + offset, y)],
            fill=line_color,
            width=line_width
        )
    
    img.save(output_path, 'PNG')
    print(f"Created {output_path} ({size}x{size})")


def main():
    """Generate all required icon sizes."""
    sizes = [16, 48, 128]
    
    for size in sizes:
        output_path = f"icon{size}.png"
        create_icon(size, output_path)
    
    print("\nAll icons generated successfully!")
    print("You can now load the extension in Chrome.")


if __name__ == "__main__":
    main()

# Examples

This directory contains example files for the mockup generator.

## Directory Structure

```
examples/
├── designs/        # Put your design images here (PNG with transparency)
├── mockups/        # Put your mockup templates here (with colored boxes)
├── output/         # Generated mockups will be saved here
└── parameters.json # Generated positioning parameters
```

## Quick Test

1. Add some mockup templates with red (#FF0000) placeholder boxes to `mockups/`
2. Add your design images to `designs/`
3. Run:

```bash
# Calculate positions
mockup-generator calculate --hex-color "#FF0000" --input examples/mockups/ --output examples/parameters.json

# Generate mockups
mockup-generator generate --params examples/parameters.json --designs examples/designs/ --mockups examples/mockups/ --output examples/output/
```

## Creating Mockup Templates

1. Find or create a product image (t-shirt, mug, etc.)
2. Add a solid color box where the design should appear
3. The box color should be unique (not present elsewhere in the image)
4. Save as PNG

**Tip:** Use bright red (#FF0000) or magenta (#FF00FF) as they're easy to detect and rarely appear in product photos.

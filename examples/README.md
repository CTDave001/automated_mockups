# Examples

Working sample files, so you can see real output before preparing anything of your own.

## What's here

```
examples/
├── mockups/
│   ├── tshirt_front.png   # square print area, no tilt
│   └── tote_bag.png       # wide print area, tilted 12 degrees
├── designs/
│   ├── circles.png        # transparent PNG
│   └── wordmark.png       # transparent PNG
├── parameters.json        # produced by `calculate`, committed for reference
└── demo.png               # the image used in the top-level README
```

`output/` is git-ignored; it's created when you run the commands below.

## Run it

From the repository root:

```bash
# 1. Find the placeholder boxes
mockup-generator calculate --hex-color "#FF0000" --input examples/mockups/ --output examples/parameters.json

# 2. Render every design onto every template
mockup-generator generate --params examples/parameters.json --designs examples/designs/ \
  --mockups examples/mockups/ --output examples/output/ --alignment center
```

You'll get four files in `examples/output/` — two designs times two templates.

The two templates are deliberately different: `tshirt_front.png` has a square, upright print area, while `tote_bag.png` has a wide one tilted 12 degrees. Compare the two outputs to see the tilt being tracked.

## Creating your own templates

1. Find or create a product image (t-shirt, mug, tote, etc.)
2. Draw a solid colour box covering the area the design should fill
3. Draw it at the angle the product sits at — the tilt is recovered automatically
4. Use a colour that appears nowhere else in the image
5. Save as PNG

**Tip:** bright red (`#FF0000`) or magenta (`#FF00FF`) work well; they're easy to detect and rarely occur in product photography.

**Note:** the marker is erased before your design is composited, using a colour sampled from just around the box. On a flat-coloured garment that's exact. Over a busy or heavily textured photo, pass `--placeholder-fill` with an explicit colour instead.

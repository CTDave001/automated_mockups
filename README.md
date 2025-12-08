# Automated Mockup Generator

[![PyPI version](https://badge.fury.io/py/mockup-generator.svg)](https://badge.fury.io/py/mockup-generator)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/CTDave001/automated_mockups/actions/workflows/ci.yml/badge.svg)](https://github.com/CTDave001/automated_mockups/actions/workflows/ci.yml)

**Automatically generate hundreds of product mockups in seconds.** Perfect for e-commerce, print-on-demand, and marketing teams.

![Mockup Generator Demo](https://raw.githubusercontent.com/CTDave001/automated_mockups/main/examples/demo.gif)

## Features

- **Batch Processing** - Generate all design x mockup combinations automatically
- **Smart Detection** - Automatically detects placeholder boxes by color
- **Rotation Support** - Handles angled/rotated design placements
- **Flexible Alignment** - 9 alignment options (top-left to bottom-right)
- **Multiple Formats** - PNG, JPEG, WebP output support
- **Parallel Processing** - Fast generation with multi-threading
- **CLI & Python API** - Use from command line or integrate into your workflow

## Quick Start

### Installation

```bash
pip install mockup-generator
```

Or install from source:

```bash
git clone https://github.com/CTDave001/automated_mockups.git
cd automated_mockups
pip install -e .
```

### Basic Usage

#### Step 1: Prepare Your Mockup Templates

Create mockup templates with a **colored placeholder box** where designs should be placed:

```
mockups/
  ├── tshirt_front.png    # Has a red (#FF0000) box where design goes
  ├── tshirt_back.png
  └── hoodie_front.png
```

#### Step 2: Calculate Placeholder Positions

```bash
mockup-generator calculate --hex-color "#FF0000" --input mockups/ --output params.json
```

This analyzes your mockups and saves the position, size, and rotation of each placeholder.

#### Step 3: Generate Mockups

```bash
mockup-generator generate \
  --params params.json \
  --designs designs/ \
  --mockups mockups/ \
  --output output/
```

That's it! Your `output/` folder now contains all combinations.

## Python API

```python
from mockup_generator import MockupCalculator, MockupGenerator, Color

# Step 1: Calculate placeholder positions
calculator = MockupCalculator(Color.from_hex("#FF0000"))
params = calculator.process_directory("mockups/")
calculator.save_parameters(params, "params.json")

# Step 2: Generate mockups
generator = MockupGenerator(params)
results = generator.generate_all(
    design_dir="designs/",
    mockup_dir="mockups/",
    output_dir="output/"
)

print(f"Generated {len([r for r in results if r.success])} mockups!")
```

## CLI Reference

### Calculate Command

Analyzes mockup templates to find placeholder boxes.

```bash
mockup-generator calculate [OPTIONS]

Options:
  --color R G B        Target color as RGB (e.g., --color 255 0 0)
  --hex-color HEX      Target color as hex (e.g., --hex-color "#FF0000")
  -i, --input DIR      Input directory with mockup templates (required)
  -o, --output FILE    Output JSON file (default: parameters.json)
  --tolerance N        Color matching tolerance 0-255 (default: 30)
  --recursive          Process subdirectories
  -v, --verbose        Show detailed output
```

### Generate Command

Creates mockups from designs and templates.

```bash
mockup-generator generate [OPTIONS]

Options:
  -p, --params FILE    Parameters JSON file (required)
  -d, --designs DIR    Directory with design images (required)
  -m, --mockups DIR    Directory with mockup templates (required)
  -o, --output DIR     Output directory (required)
  --alignment ALIGN    Design alignment: top_left, top_center, top_right,
                       center_left, center, center_right, bottom_left,
                       bottom_center, bottom_right (default: top_center)
  --scale-mode MODE    Scaling: fit, fill, stretch, none (default: fit)
  --format FORMAT      Output format: PNG, JPEG, WEBP (default: PNG)
  --quality N          JPEG quality 1-100 (default: 95)
  --pattern PATTERN    Output naming pattern (default: {design}_{mockup})
  --no-parallel        Disable parallel processing
  --workers N          Number of parallel workers (default: 4)
```

## Configuration Options

### Alignment Modes

| Alignment | Description |
|-----------|-------------|
| `top_left` | Design aligned to top-left of placeholder |
| `top_center` | Design centered horizontally, aligned to top |
| `top_right` | Design aligned to top-right |
| `center_left` | Design centered vertically, aligned to left |
| `center` | Design centered both ways |
| `center_right` | Design centered vertically, aligned to right |
| `bottom_left` | Design aligned to bottom-left |
| `bottom_center` | Design centered horizontally, aligned to bottom |
| `bottom_right` | Design aligned to bottom-right |

### Scale Modes

| Mode | Description |
|------|-------------|
| `fit` | Scale to fit within placeholder, maintaining aspect ratio |
| `fill` | Scale to fill placeholder completely (may crop) |
| `stretch` | Stretch to exact placeholder size (ignores aspect ratio) |
| `none` | Use original design size |

## Use Cases

- **Print-on-Demand** - Generate product previews for your POD store
- **E-commerce** - Create product images for multiple colors/variants
- **Marketing** - Quickly visualize designs on merchandise
- **Design Agencies** - Present client designs on realistic mockups
- **Social Media** - Generate promotional images at scale

## Project Structure

```
automated_mockups/
├── mockup_generator/
│   ├── __init__.py       # Package exports
│   ├── calculator.py     # Box position detection
│   ├── generator.py      # Mockup generation
│   ├── cli.py           # Command-line interface
│   └── utils.py         # Utilities and helpers
├── examples/
│   ├── designs/         # Sample design files
│   ├── mockups/         # Sample mockup templates
│   └── output/          # Generated mockups
├── tests/               # Unit tests
├── pyproject.toml       # Package configuration
└── README.md
```

## Requirements

- Python 3.8+
- NumPy
- Pillow
- scikit-image
- OpenCV (cv2)

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [Pillow](https://pillow.readthedocs.io/) for image processing
- Color detection powered by [scikit-image](https://scikit-image.org/)

---

**Star this repo** if you find it useful! Questions? Open an [issue](https://github.com/CTDave001/automated_mockups/issues).

"""Tests for the MockupCalculator class."""

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from mockup_generator import MockupCalculator, Color, BoxParameters


@pytest.fixture
def sample_image_with_box(tmp_path):
    """Create a sample image with a red box for testing."""
    # Create a white image with a red box
    img = Image.new("RGB", (500, 500), color=(255, 255, 255))
    pixels = img.load()

    # Draw a red box (100x150 at position 150,100)
    for x in range(150, 250):
        for y in range(100, 250):
            pixels[x, y] = (255, 0, 0)

    # Save to temp path
    image_path = tmp_path / "test_mockup.png"
    img.save(image_path)
    return image_path


@pytest.fixture
def calculator():
    """Create a calculator with red as target color."""
    return MockupCalculator(Color(255, 0, 0), color_tolerance=30)


class TestMockupCalculator:
    """Tests for the MockupCalculator class."""

    def test_calculator_initialization(self):
        """Test calculator initialization."""
        calc = MockupCalculator(Color(255, 0, 0))
        assert calc.target_color.r == 255
        assert calc.color_tolerance == 30  # default

    def test_calculate_parameters(self, calculator, sample_image_with_box):
        """Test calculating parameters from an image."""
        params = calculator.calculate_parameters(sample_image_with_box)

        assert params is not None
        assert params.filename == "test_mockup.png"
        assert params.width == 100  # 250 - 150
        assert params.height == 150  # 250 - 100

    def test_calculate_parameters_no_box(self, calculator, tmp_path):
        """Test with an image that has no matching box."""
        # Create a white image (no red box)
        img = Image.new("RGB", (200, 200), color=(255, 255, 255))
        image_path = tmp_path / "no_box.png"
        img.save(image_path)

        params = calculator.calculate_parameters(image_path)
        assert params is None

    def test_calculate_parameters_missing_file(self, calculator):
        """Test with a non-existent file."""
        params = calculator.calculate_parameters("/nonexistent/file.png")
        assert params is None

    def test_process_directory(self, calculator, sample_image_with_box):
        """Test processing a directory of images."""
        directory = sample_image_with_box.parent
        results = calculator.process_directory(directory)

        assert len(results) == 1
        assert "test_mockup.png" in results

    def test_save_and_load_parameters(self, calculator, sample_image_with_box, tmp_path):
        """Test saving and loading parameters."""
        # Calculate parameters
        params = calculator.calculate_parameters(sample_image_with_box)
        parameters = {params.filename: params}

        # Save
        output_path = tmp_path / "params.json"
        calculator.save_parameters(parameters, output_path)

        # Verify file exists and is valid JSON
        assert output_path.exists()
        with open(output_path) as f:
            data = json.load(f)
        assert "test_mockup.png" in data

        # Load
        loaded = calculator.load_parameters(output_path)
        assert len(loaded) == 1
        assert loaded["test_mockup.png"].width == params.width


class TestBoxParameters:
    """Tests for the BoxParameters dataclass."""

    def test_to_dict(self):
        """Test converting parameters to dictionary."""
        params = BoxParameters(
            filename="test.png",
            bbox=(10, 20, 110, 120),
            width=100,
            height=100,
            rotation=0.0,
            center=(70, 60)
        )
        d = params.to_dict()

        assert d["filename"] == "test.png"
        assert d["width"] == 100
        assert d["bbox"] == (10, 20, 110, 120)

    def test_from_dict(self):
        """Test creating parameters from dictionary."""
        data = {
            "filename": "test.png",
            "bbox": [10, 20, 110, 120],
            "width": 100,
            "height": 100,
            "rotation": 5.5,
            "center": [70, 60]
        }
        params = BoxParameters.from_dict(data)

        assert params.filename == "test.png"
        assert params.rotation == 5.5
        assert params.bbox == (10, 20, 110, 120)

"""Tests for utility functions and classes."""

import pytest
from mockup_generator.utils import Color, ImageFormat


class TestColor:
    """Tests for the Color class."""

    def test_color_creation(self):
        """Test creating a color with RGB values."""
        color = Color(255, 128, 0)
        assert color.r == 255
        assert color.g == 128
        assert color.b == 0

    def test_color_validation(self):
        """Test that invalid color values raise errors."""
        with pytest.raises(ValueError):
            Color(256, 0, 0)  # r too high

        with pytest.raises(ValueError):
            Color(0, -1, 0)  # g negative

    def test_color_from_hex(self):
        """Test creating color from hex string."""
        # With hash
        color = Color.from_hex("#FF0000")
        assert color.r == 255
        assert color.g == 0
        assert color.b == 0

        # Without hash
        color = Color.from_hex("00FF00")
        assert color.r == 0
        assert color.g == 255
        assert color.b == 0

        # Lowercase
        color = Color.from_hex("#0000ff")
        assert color.b == 255

    def test_color_from_hex_shorthand(self):
        """Test creating color from 3-character hex."""
        color = Color.from_hex("#F00")
        assert color.r == 255
        assert color.g == 0
        assert color.b == 0

    def test_color_from_hex_invalid(self):
        """Test that invalid hex strings raise errors."""
        with pytest.raises(ValueError):
            Color.from_hex("invalid")

        with pytest.raises(ValueError):
            Color.from_hex("#GGGGGG")

    def test_color_to_rgb(self):
        """Test converting color to RGB tuple."""
        color = Color(100, 150, 200)
        assert color.to_rgb() == (100, 150, 200)

    def test_color_to_hex(self):
        """Test converting color to hex string."""
        color = Color(255, 0, 128)
        assert color.to_hex() == "#FF0080"


class TestImageFormat:
    """Tests for the ImageFormat enum."""

    def test_supported_extensions(self):
        """Test getting supported file extensions."""
        extensions = ImageFormat.supported_extensions()
        assert ".png" in extensions
        assert ".jpg" in extensions
        assert ".jpeg" in extensions

    def test_glob_patterns(self):
        """Test getting glob patterns."""
        patterns = ImageFormat.glob_patterns()
        assert "*.png" in patterns
        assert "*.PNG" in patterns

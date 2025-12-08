"""
Utility classes and functions for the mockup generator.
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Tuple, Union, List
import re
import logging

logger = logging.getLogger(__name__)


class ImageFormat(Enum):
    """Supported image formats."""
    PNG = "png"
    JPG = "jpg"
    JPEG = "jpeg"
    WEBP = "webp"
    TIFF = "tiff"
    BMP = "bmp"

    @classmethod
    def supported_extensions(cls) -> Tuple[str, ...]:
        """Return tuple of supported file extensions."""
        return tuple(f".{fmt.value}" for fmt in cls)

    @classmethod
    def glob_patterns(cls) -> List[str]:
        """Return glob patterns for all supported formats."""
        patterns = []
        for fmt in cls:
            patterns.extend([f"*.{fmt.value}", f"*.{fmt.value.upper()}"])
        return patterns


@dataclass
class Color:
    """
    Represents a color with RGB values.

    Can be initialized from:
    - RGB tuple: Color(255, 0, 0)
    - Hex string: Color.from_hex("#FF0000") or Color.from_hex("FF0000")
    """
    r: int
    g: int
    b: int

    def __post_init__(self):
        """Validate color values are in valid range."""
        for channel, value in [("r", self.r), ("g", self.g), ("b", self.b)]:
            if not 0 <= value <= 255:
                raise ValueError(f"Color channel '{channel}' must be 0-255, got {value}")

    @classmethod
    def from_hex(cls, hex_color: str) -> "Color":
        """
        Create a Color from a hex string.

        Args:
            hex_color: Hex color string (e.g., "#FF0000", "FF0000", "#f00")

        Returns:
            Color instance

        Raises:
            ValueError: If hex string is invalid
        """
        # Remove # prefix if present
        hex_color = hex_color.lstrip("#")

        # Handle shorthand hex (e.g., "F00" -> "FF0000")
        if len(hex_color) == 3:
            hex_color = "".join(c * 2 for c in hex_color)

        if len(hex_color) != 6:
            raise ValueError(f"Invalid hex color: {hex_color}. Expected 6 characters.")

        if not re.match(r'^[0-9A-Fa-f]{6}$', hex_color):
            raise ValueError(f"Invalid hex color: {hex_color}. Contains invalid characters.")

        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)

        return cls(r, g, b)

    def to_rgb(self) -> Tuple[int, int, int]:
        """Return color as RGB tuple."""
        return (self.r, self.g, self.b)

    def to_hex(self) -> str:
        """Return color as hex string (with # prefix)."""
        return f"#{self.r:02X}{self.g:02X}{self.b:02X}"

    def __str__(self) -> str:
        return f"Color({self.r}, {self.g}, {self.b})"


def validate_directory(path: Union[str, Path], must_exist: bool = True) -> Path:
    """
    Validate and return a Path object for a directory.

    Args:
        path: Directory path as string or Path
        must_exist: If True, raise error if directory doesn't exist

    Returns:
        Validated Path object

    Raises:
        ValueError: If path is invalid
        FileNotFoundError: If must_exist=True and directory doesn't exist
    """
    path = Path(path)

    if must_exist and not path.exists():
        raise FileNotFoundError(f"Directory not found: {path}")

    if path.exists() and not path.is_dir():
        raise ValueError(f"Path is not a directory: {path}")

    return path


def get_image_files(directory: Path) -> List[Path]:
    """
    Get all supported image files from a directory.

    Args:
        directory: Directory to scan for images

    Returns:
        List of Path objects for image files, sorted alphabetically
    """
    images = []
    for pattern in ImageFormat.glob_patterns():
        images.extend(directory.glob(pattern))

    # Remove duplicates and sort
    return sorted(set(images))


def setup_logging(
    level: int = logging.INFO,
    format_string: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
) -> None:
    """
    Configure logging for the package.

    Args:
        level: Logging level (e.g., logging.DEBUG, logging.INFO)
        format_string: Log message format
    """
    logging.basicConfig(
        level=level,
        format=format_string,
        handlers=[logging.StreamHandler()]
    )

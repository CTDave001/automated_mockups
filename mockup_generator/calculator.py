"""
Box position calculator for mockup templates.

This module analyzes mockup template images to extract positioning parameters
for design placement based on colored placeholder boxes.
"""

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from skimage import measure

from .geometry import extent_to_pixel_count, min_area_rect
from .utils import Color, ImageFormat, get_image_files, validate_directory

logger = logging.getLogger(__name__)


@dataclass
class BoxParameters:
    """
    Parameters describing a detected placeholder box in a mockup template.

    The box is modelled as a rotated rectangle: ``width``, ``height`` and
    ``rotation`` describe the box in its own frame, and ``center`` locates it
    on the template. ``bbox`` is the axis-aligned bounding box, retained for
    inspection and debugging.

    Attributes:
        filename: Name of the source mockup file
        bbox: Axis-aligned bounds as (min_row, min_col, max_row, max_col)
        width: Width of the box along its own axis, in pixels
        height: Height of the box along its own axis, in pixels
        rotation: Tilt in degrees, normalized to (-45, 45]. Positive values
            tilt clockwise on screen.
        center: Center point of the box as (x, y)
    """

    filename: str
    bbox: tuple[int, int, int, int]
    width: int
    height: int
    rotation: float
    center: tuple[int, int]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BoxParameters":
        """Create from dictionary."""
        return cls(
            filename=data["filename"],
            bbox=tuple(data["bbox"]),
            width=data["width"],
            height=data["height"],
            rotation=data["rotation"],
            center=tuple(data["center"]),
        )


class MockupCalculator:
    """
    Analyzes mockup templates to extract design placement parameters.

    This class processes mockup images containing colored placeholder boxes
    and extracts their position, dimensions, and rotation for use in
    automated mockup generation.

    Example:
        >>> calculator = MockupCalculator(Color(255, 0, 0))
        >>> params = calculator.process_directory("templates/")
        >>> calculator.save_parameters(params, "parameters.json")
    """

    def __init__(
        self, target_color: Color, color_tolerance: int = 30, min_region_area: int = 100
    ) -> None:
        """
        Initialize the mockup calculator.

        Args:
            target_color: The color of placeholder boxes to detect
            color_tolerance: Tolerance for color matching (0-255)
            min_region_area: Minimum pixel area for valid regions
        """
        self.target_color = target_color
        self.color_tolerance = color_tolerance
        self.min_region_area = min_region_area

        logger.info(f"Initialized calculator with target color: {target_color}")

    def _create_color_mask(self, image: np.ndarray) -> np.ndarray:
        """
        Create a binary mask for pixels matching the target color.

        Args:
            image: RGB image as numpy array

        Returns:
            Binary mask where True indicates matching pixels
        """
        r, g, b = self.target_color.to_rgb()

        color_distance = np.sqrt(
            (image[:, :, 0].astype(float) - r) ** 2
            + (image[:, :, 1].astype(float) - g) ** 2
            + (image[:, :, 2].astype(float) - b) ** 2
        )

        mask: np.ndarray = color_distance <= self.color_tolerance
        return mask

    def _find_largest_region(self, mask: np.ndarray) -> Any | None:
        """
        Find the largest connected region in a binary mask.

        Args:
            mask: Binary mask image

        Returns:
            RegionProperties for largest region, or None if no valid region found
        """
        labeled = measure.label(mask)
        regions = measure.regionprops(labeled)

        valid_regions = [r for r in regions if r.area >= self.min_region_area]
        if not valid_regions:
            return None

        return max(valid_regions, key=lambda r: r.area)

    def calculate_parameters(self, image_path: str | Path) -> BoxParameters | None:
        """
        Calculate box parameters from a single mockup template image.

        Args:
            image_path: Path to the mockup template image

        Returns:
            BoxParameters if a valid box is found, None otherwise
        """
        image_path = Path(image_path)

        if not image_path.exists():
            logger.error(f"Image not found: {image_path}")
            return None

        try:
            with Image.open(image_path) as img:
                image_array = np.array(img.convert("RGB"))

            logger.debug(f"Processing image: {image_path.name} ({image_array.shape})")

            mask = self._create_color_mask(image_array)
            region = self._find_largest_region(mask)

            if region is None:
                logger.warning(f"No valid region found in {image_path.name}")
                return None

            rect = min_area_rect(region.coords)
            if rect is None:
                logger.warning(f"Region in {image_path.name} is degenerate; skipping")
                return None

            (center_x, center_y), (extent_w, extent_h), rotation = rect

            params = BoxParameters(
                filename=image_path.name,
                bbox=tuple(int(v) for v in region.bbox),  # type: ignore[arg-type]
                width=extent_to_pixel_count(extent_w),
                height=extent_to_pixel_count(extent_h),
                rotation=rotation,
                center=(int(round(center_x)), int(round(center_y))),
            )

            logger.info(
                f"Detected box in {image_path.name}: "
                f"{params.width}x{params.height}px, rotation={rotation:.1f}deg"
            )

            return params

        except Exception as e:
            logger.error(f"Error processing {image_path.name}: {e}")
            return None

    def process_directory(
        self, directory: str | Path, recursive: bool = False
    ) -> dict[str, BoxParameters]:
        """
        Process all mockup templates in a directory.

        Args:
            directory: Path to directory containing mockup templates
            recursive: If True, also process subdirectories

        Returns:
            Dictionary mapping filenames to BoxParameters
        """
        directory = validate_directory(directory)
        results: dict[str, BoxParameters] = {}

        images: list[Path]
        if recursive:
            found: list[Path] = []
            for ext in ImageFormat.supported_extensions():
                found.extend(directory.rglob(f"*{ext}"))
                found.extend(directory.rglob(f"*{ext.upper()}"))
            images = sorted(set(found))
        else:
            images = get_image_files(directory)

        logger.info(f"Found {len(images)} images in {directory}")

        for image_path in images:
            params = self.calculate_parameters(image_path)
            if params:
                results[params.filename] = params

        logger.info(f"Successfully processed {len(results)}/{len(images)} images")

        return results

    @staticmethod
    def save_parameters(
        parameters: dict[str, BoxParameters], output_path: str | Path, indent: int = 2
    ) -> None:
        """
        Save calculated parameters to a JSON file.

        Args:
            parameters: Dictionary of BoxParameters
            output_path: Path for output JSON file
            indent: JSON indentation level
        """
        output_path = Path(output_path)
        data = {name: params.to_dict() for name, params in parameters.items()}

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent)

        logger.info(f"Saved parameters to {output_path}")

    @staticmethod
    def load_parameters(input_path: str | Path) -> dict[str, BoxParameters]:
        """
        Load parameters from a JSON file.

        Args:
            input_path: Path to JSON parameters file

        Returns:
            Dictionary mapping filenames to BoxParameters
        """
        input_path = Path(input_path)

        with open(input_path, encoding="utf-8") as f:
            data = json.load(f)

        parameters = {name: BoxParameters.from_dict(params) for name, params in data.items()}

        logger.info(f"Loaded {len(parameters)} parameter sets from {input_path}")

        return parameters

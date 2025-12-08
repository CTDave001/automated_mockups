"""
Box position calculator for mockup templates.

This module analyzes mockup template images to extract positioning parameters
for design placement based on colored placeholder boxes.
"""

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple
import json
import logging

import numpy as np
from PIL import Image
from skimage import measure
from skimage.color import rgb2gray

from .utils import Color, validate_directory, get_image_files, ImageFormat

logger = logging.getLogger(__name__)


@dataclass
class BoxParameters:
    """
    Parameters describing a detected placeholder box in a mockup template.

    Attributes:
        filename: Name of the source mockup file
        bbox: Bounding box as (min_row, min_col, max_row, max_col)
        width: Width of the detected box in pixels
        height: Height of the detected box in pixels
        rotation: Rotation angle in degrees (counter-clockwise)
        center: Center point of the box as (x, y)
    """
    filename: str
    bbox: Tuple[int, int, int, int]
    width: int
    height: int
    rotation: float
    center: Tuple[int, int]

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "BoxParameters":
        """Create from dictionary."""
        return cls(
            filename=data["filename"],
            bbox=tuple(data["bbox"]),
            width=data["width"],
            height=data["height"],
            rotation=data["rotation"],
            center=tuple(data["center"])
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
        self,
        target_color: Color,
        color_tolerance: int = 30,
        min_region_area: int = 100
    ):
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

        # Calculate distance from target color for each pixel
        color_distance = np.sqrt(
            (image[:, :, 0].astype(float) - r) ** 2 +
            (image[:, :, 1].astype(float) - g) ** 2 +
            (image[:, :, 2].astype(float) - b) ** 2
        )

        # Create mask for pixels within tolerance
        mask = color_distance <= self.color_tolerance

        return mask

    def _find_largest_region(
        self,
        mask: np.ndarray
    ) -> Optional[measure._regionprops.RegionProperties]:
        """
        Find the largest connected region in a binary mask.

        Args:
            mask: Binary mask image

        Returns:
            RegionProperties for largest region, or None if no valid region found
        """
        # Label connected components
        labeled = measure.label(mask)
        regions = measure.regionprops(labeled)

        if not regions:
            return None

        # Filter by minimum area and find largest
        valid_regions = [r for r in regions if r.area >= self.min_region_area]

        if not valid_regions:
            return None

        return max(valid_regions, key=lambda r: r.area)

    def calculate_parameters(self, image_path: Union[str, Path]) -> Optional[BoxParameters]:
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
            # Load and convert image
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode != "RGB":
                    img = img.convert("RGB")
                image_array = np.array(img)

            logger.debug(f"Processing image: {image_path.name} ({image_array.shape})")

            # Create mask and find region
            mask = self._create_color_mask(image_array)
            region = self._find_largest_region(mask)

            if region is None:
                logger.warning(f"No valid region found in {image_path.name}")
                return None

            # Extract parameters
            min_row, min_col, max_row, max_col = region.bbox
            height = max_row - min_row
            width = max_col - min_col

            # Calculate rotation angle from region orientation
            # orientation is in radians, convert to degrees
            rotation = np.degrees(region.orientation)

            # Calculate center point
            center_y, center_x = region.centroid
            center = (int(center_x), int(center_y))

            params = BoxParameters(
                filename=image_path.name,
                bbox=(min_row, min_col, max_row, max_col),
                width=width,
                height=height,
                rotation=rotation,
                center=center
            )

            logger.info(
                f"Detected box in {image_path.name}: "
                f"{width}x{height}px, rotation={rotation:.1f}deg"
            )

            return params

        except Exception as e:
            logger.error(f"Error processing {image_path.name}: {e}")
            return None

    def process_directory(
        self,
        directory: Union[str, Path],
        recursive: bool = False
    ) -> Dict[str, BoxParameters]:
        """
        Process all mockup templates in a directory.

        Args:
            directory: Path to directory containing mockup templates
            recursive: If True, also process subdirectories

        Returns:
            Dictionary mapping filenames to BoxParameters
        """
        directory = validate_directory(directory)
        results: Dict[str, BoxParameters] = {}

        # Get all image files
        if recursive:
            images = []
            for ext in ImageFormat.supported_extensions():
                images.extend(directory.rglob(f"*{ext}"))
                images.extend(directory.rglob(f"*{ext.upper()}"))
        else:
            images = get_image_files(directory)

        logger.info(f"Found {len(images)} images in {directory}")

        # Process each image
        for image_path in images:
            params = self.calculate_parameters(image_path)
            if params:
                results[params.filename] = params

        logger.info(f"Successfully processed {len(results)}/{len(images)} images")

        return results

    @staticmethod
    def save_parameters(
        parameters: Dict[str, BoxParameters],
        output_path: Union[str, Path],
        indent: int = 2
    ) -> None:
        """
        Save calculated parameters to a JSON file.

        Args:
            parameters: Dictionary of BoxParameters
            output_path: Path for output JSON file
            indent: JSON indentation level
        """
        output_path = Path(output_path)

        # Convert to serializable format
        data = {name: params.to_dict() for name, params in parameters.items()}

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent)

        logger.info(f"Saved parameters to {output_path}")

    @staticmethod
    def load_parameters(input_path: Union[str, Path]) -> Dict[str, BoxParameters]:
        """
        Load parameters from a JSON file.

        Args:
            input_path: Path to JSON parameters file

        Returns:
            Dictionary mapping filenames to BoxParameters
        """
        input_path = Path(input_path)

        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        parameters = {
            name: BoxParameters.from_dict(params)
            for name, params in data.items()
        }

        logger.info(f"Loaded {len(parameters)} parameter sets from {input_path}")

        return parameters

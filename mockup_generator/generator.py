"""
Mockup generator module.

This module combines design images with mockup templates to create
final product mockups using pre-calculated positioning parameters.
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Union, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

import numpy as np
from PIL import Image

from .calculator import BoxParameters, MockupCalculator
from .utils import validate_directory, get_image_files

logger = logging.getLogger(__name__)


class Alignment(Enum):
    """Design alignment options within the placeholder box."""
    TOP_LEFT = "top_left"
    TOP_CENTER = "top_center"
    TOP_RIGHT = "top_right"
    CENTER_LEFT = "center_left"
    CENTER = "center"
    CENTER_RIGHT = "center_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_CENTER = "bottom_center"
    BOTTOM_RIGHT = "bottom_right"


class ScaleMode(Enum):
    """How to scale the design to fit the placeholder."""
    FIT = "fit"  # Scale to fit within bounds, maintaining aspect ratio
    FILL = "fill"  # Scale to fill bounds, may crop
    STRETCH = "stretch"  # Stretch to exact bounds, ignoring aspect ratio
    NONE = "none"  # No scaling, use original size


@dataclass
class GenerationResult:
    """Result of generating a single mockup."""
    success: bool
    output_path: Optional[Path]
    design_name: str
    mockup_name: str
    error: Optional[str] = None


class MockupGenerator:
    """
    Generates product mockups by combining designs with templates.

    This class takes design images and mockup templates, using pre-calculated
    positioning parameters to create final composite mockups.

    Example:
        >>> params = MockupCalculator.load_parameters("parameters.json")
        >>> generator = MockupGenerator(params)
        >>> results = generator.generate_all(
        ...     design_dir="designs/",
        ...     mockup_dir="mockups/",
        ...     output_dir="output/"
        ... )
    """

    def __init__(
        self,
        parameters: Dict[str, BoxParameters],
        alignment: Alignment = Alignment.TOP_CENTER,
        scale_mode: ScaleMode = ScaleMode.FIT,
        output_quality: int = 95,
        output_format: str = "PNG"
    ):
        """
        Initialize the mockup generator.

        Args:
            parameters: Dictionary mapping mockup filenames to BoxParameters
            alignment: How to align the design within the placeholder
            scale_mode: How to scale designs to fit placeholders
            output_quality: JPEG quality (1-100) if saving as JPEG
            output_format: Output image format (PNG, JPEG, etc.)
        """
        self.parameters = parameters
        self.alignment = alignment
        self.scale_mode = scale_mode
        self.output_quality = output_quality
        self.output_format = output_format.upper()

        logger.info(f"Initialized generator with {len(parameters)} mockup templates")

    def _calculate_scaled_size(
        self,
        design_size: tuple,
        target_size: tuple
    ) -> tuple:
        """
        Calculate the scaled size for a design based on scale mode.

        Args:
            design_size: Original (width, height) of the design
            target_size: Target (width, height) of the placeholder

        Returns:
            New (width, height) for the scaled design
        """
        design_w, design_h = design_size
        target_w, target_h = target_size

        if self.scale_mode == ScaleMode.STRETCH:
            return target_size

        if self.scale_mode == ScaleMode.NONE:
            return design_size

        # Calculate scale factors
        scale_x = target_w / design_w
        scale_y = target_h / design_h

        if self.scale_mode == ScaleMode.FIT:
            scale = min(scale_x, scale_y)
        else:  # FILL
            scale = max(scale_x, scale_y)

        new_w = int(design_w * scale)
        new_h = int(design_h * scale)

        return (new_w, new_h)

    def _calculate_position(
        self,
        design_size: tuple,
        params: BoxParameters
    ) -> tuple:
        """
        Calculate the paste position based on alignment.

        Args:
            design_size: (width, height) of the scaled design
            params: Box parameters for the mockup

        Returns:
            (x, y) position for pasting the design
        """
        design_w, design_h = design_size
        box_w, box_h = params.width, params.height
        min_row, min_col, _, _ = params.bbox

        # Calculate offsets based on alignment
        if "left" in self.alignment.value:
            x_offset = 0
        elif "right" in self.alignment.value:
            x_offset = box_w - design_w
        else:  # center
            x_offset = (box_w - design_w) // 2

        if "top" in self.alignment.value:
            y_offset = 0
        elif "bottom" in self.alignment.value:
            y_offset = box_h - design_h
        else:  # center
            y_offset = (box_h - design_h) // 2

        # Add box position offset
        x = min_col + x_offset
        y = min_row + y_offset

        return (x, y)

    def _rotate_design(
        self,
        design: Image.Image,
        angle: float
    ) -> Image.Image:
        """
        Rotate the design image.

        Args:
            design: PIL Image to rotate
            angle: Rotation angle in degrees

        Returns:
            Rotated PIL Image with transparency preserved
        """
        if abs(angle) < 0.1:  # Skip rotation for very small angles
            return design

        # Ensure RGBA mode for transparency
        if design.mode != "RGBA":
            design = design.convert("RGBA")

        # Rotate with expansion to prevent cropping
        rotated = design.rotate(
            angle,
            expand=True,
            resample=Image.Resampling.BICUBIC,
            fillcolor=(0, 0, 0, 0)
        )

        return rotated

    def generate_mockup(
        self,
        design_path: Union[str, Path],
        mockup_path: Union[str, Path],
        output_path: Union[str, Path]
    ) -> GenerationResult:
        """
        Generate a single mockup by combining a design with a template.

        Args:
            design_path: Path to the design image
            mockup_path: Path to the mockup template
            output_path: Path for the output image

        Returns:
            GenerationResult with success status and details
        """
        design_path = Path(design_path)
        mockup_path = Path(mockup_path)
        output_path = Path(output_path)

        # Get parameters for this mockup
        if mockup_path.name not in self.parameters:
            return GenerationResult(
                success=False,
                output_path=None,
                design_name=design_path.name,
                mockup_name=mockup_path.name,
                error=f"No parameters found for mockup: {mockup_path.name}"
            )

        params = self.parameters[mockup_path.name]

        try:
            # Load images
            design = Image.open(design_path)
            mockup = Image.open(mockup_path)

            # Convert design to RGBA for transparency support
            if design.mode != "RGBA":
                design = design.convert("RGBA")

            # Convert mockup to RGBA
            if mockup.mode != "RGBA":
                mockup = mockup.convert("RGBA")

            # Calculate scaled size
            target_size = (params.width, params.height)
            new_size = self._calculate_scaled_size(design.size, target_size)

            # Resize design
            design = design.resize(new_size, Image.Resampling.LANCZOS)

            # Rotate design to match mockup angle
            design = self._rotate_design(design, params.rotation)

            # Calculate paste position
            position = self._calculate_position(design.size, params)

            # Create output image (copy of mockup)
            output = mockup.copy()

            # Paste design onto mockup
            output.paste(design, position, design)

            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Save output
            if self.output_format == "JPEG":
                # Convert to RGB for JPEG (no alpha channel)
                output = output.convert("RGB")
                output.save(output_path, format="JPEG", quality=self.output_quality)
            else:
                output.save(output_path, format=self.output_format)

            logger.debug(f"Generated: {output_path.name}")

            return GenerationResult(
                success=True,
                output_path=output_path,
                design_name=design_path.name,
                mockup_name=mockup_path.name
            )

        except Exception as e:
            logger.error(f"Error generating mockup: {e}")
            return GenerationResult(
                success=False,
                output_path=None,
                design_name=design_path.name,
                mockup_name=mockup_path.name,
                error=str(e)
            )

    def generate_all(
        self,
        design_dir: Union[str, Path],
        mockup_dir: Union[str, Path],
        output_dir: Union[str, Path],
        naming_pattern: str = "{design}_{mockup}",
        parallel: bool = True,
        max_workers: int = 4,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[GenerationResult]:
        """
        Generate all combinations of designs and mockups.

        Args:
            design_dir: Directory containing design images
            mockup_dir: Directory containing mockup templates
            output_dir: Directory for output images
            naming_pattern: Pattern for output filenames
                           ({design} and {mockup} are replaced with source names)
            parallel: If True, process mockups in parallel
            max_workers: Number of parallel workers
            progress_callback: Optional callback(completed, total) for progress updates

        Returns:
            List of GenerationResult for all generated mockups
        """
        design_dir = validate_directory(design_dir)
        mockup_dir = validate_directory(mockup_dir)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Get all design and mockup files
        designs = get_image_files(design_dir)
        mockups = [
            f for f in get_image_files(mockup_dir)
            if f.name in self.parameters
        ]

        logger.info(f"Generating {len(designs)} designs x {len(mockups)} mockups")

        # Prepare generation tasks
        tasks = []
        for design_path in designs:
            for mockup_path in mockups:
                design_stem = design_path.stem
                mockup_stem = mockup_path.stem

                output_name = naming_pattern.format(
                    design=design_stem,
                    mockup=mockup_stem
                )
                output_ext = f".{self.output_format.lower()}"
                output_path = output_dir / f"{output_name}{output_ext}"

                tasks.append((design_path, mockup_path, output_path))

        total = len(tasks)
        results = []
        completed = 0

        if parallel and len(tasks) > 1:
            # Parallel processing
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(self.generate_mockup, *task): task
                    for task in tasks
                }

                for future in as_completed(futures):
                    result = future.result()
                    results.append(result)
                    completed += 1

                    if progress_callback:
                        progress_callback(completed, total)
        else:
            # Sequential processing
            for task in tasks:
                result = self.generate_mockup(*task)
                results.append(result)
                completed += 1

                if progress_callback:
                    progress_callback(completed, total)

        # Log summary
        successful = sum(1 for r in results if r.success)
        logger.info(f"Generation complete: {successful}/{total} successful")

        if successful < total:
            failed = [r for r in results if not r.success]
            for r in failed[:5]:  # Show first 5 failures
                logger.warning(f"Failed: {r.design_name} + {r.mockup_name}: {r.error}")

        return results

"""
Mockup generator module.

This module combines design images with mockup templates to create
final product mockups using pre-calculated positioning parameters.
"""

import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from .calculator import BoxParameters
from .geometry import rect_corners
from .utils import get_image_files, validate_directory

logger = logging.getLogger(__name__)

# Below this, a rotation is visually indistinguishable from none and only costs
# a resample pass.
_ROTATION_EPSILON_DEG = 0.01

# The marker is erased very slightly proud of the detected box so that the
# anti-aliased pixels at its edge go too.
_COVER_OVERSCAN = 1.04

# Ring, as a multiple of the box, sampled to guess what the marker is sitting on.
_SURROUND_INNER = 1.10
_SURROUND_OUTER = 1.45


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
    output_path: Path | None
    design_name: str
    mockup_name: str
    error: str | None = None


class MockupGenerator:
    """
    Generates product mockups by combining designs with templates.

    Placement happens in the placeholder box's own frame: the design is scaled
    and aligned against an upright box, and only then is the whole composition
    rotated to match the box's tilt and centred on it. Doing it in that order
    keeps alignment meaningful for tilted boxes.

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
        parameters: dict[str, BoxParameters],
        alignment: Alignment = Alignment.TOP_CENTER,
        scale_mode: ScaleMode = ScaleMode.FIT,
        output_quality: int = 95,
        output_format: str = "PNG",
        cover_placeholder: bool = True,
        placeholder_fill: tuple[int, int, int] | None = None,
    ) -> None:
        """
        Initialize the mockup generator.

        Args:
            parameters: Dictionary mapping mockup filenames to BoxParameters
            alignment: How to align the design within the placeholder
            scale_mode: How to scale designs to fit placeholders
            output_quality: JPEG quality (1-100) if saving as JPEG
            output_format: Output image format (PNG, JPEG, etc.)
            cover_placeholder: Erase the marker box before compositing. Designs
                are usually transparent PNGs, so without this the marker shows
                through wherever the design does not paint.
            placeholder_fill: Colour to erase the marker with. When None, the
                colour is sampled from the template around each box, which is
                what lets one batch span differently coloured products.
        """
        self.parameters = parameters
        self.alignment = alignment
        self.scale_mode = scale_mode
        self.output_quality = output_quality
        self.output_format = output_format.upper()
        self.cover_placeholder = cover_placeholder
        self.placeholder_fill = placeholder_fill

        logger.info(f"Initialized generator with {len(parameters)} mockup templates")

    def _placeholder_polygon(
        self, params: BoxParameters, scale: float = 1.0
    ) -> list[tuple[float, float]]:
        """Corners of the placeholder box, optionally grown about its centre."""
        return rect_corners(
            (float(params.center[0]), float(params.center[1])),
            (params.width * scale, params.height * scale),
            params.rotation,
        )

    def _sample_surrounding_color(
        self, template: Image.Image, params: BoxParameters
    ) -> tuple[int, int, int] | None:
        """
        Estimate what the marker is painted on top of.

        Samples a ring around the box and takes the median, so a stray
        neighbouring colour cannot drag the result the way a mean would.

        Returns:
            An (r, g, b) tuple, or None if the ring falls outside the image.
        """
        inner = Image.new("L", template.size, 0)
        ImageDraw.Draw(inner).polygon(self._placeholder_polygon(params, _SURROUND_INNER), fill=255)

        outer = Image.new("L", template.size, 0)
        ImageDraw.Draw(outer).polygon(self._placeholder_polygon(params, _SURROUND_OUTER), fill=255)

        ring = (np.array(outer) > 0) & (np.array(inner) == 0)
        if not ring.any():
            return None

        pixels = np.array(template.convert("RGB"))[ring]
        median = np.median(pixels, axis=0)
        return (int(median[0]), int(median[1]), int(median[2]))

    def _erase_placeholder(self, output: Image.Image, params: BoxParameters) -> None:
        """Paint over the marker box so it cannot show through the design."""
        fill = self.placeholder_fill or self._sample_surrounding_color(output, params)
        if fill is None:
            logger.warning("Could not determine a placeholder fill colour; leaving marker in place")
            return

        ImageDraw.Draw(output).polygon(
            self._placeholder_polygon(params, _COVER_OVERSCAN), fill=(*fill, 255)
        )

    def _calculate_scaled_size(
        self, design_size: tuple[int, int], target_size: tuple[int, int]
    ) -> tuple[int, int]:
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

        scale_x = target_w / design_w
        scale_y = target_h / design_h

        if self.scale_mode == ScaleMode.FIT:
            scale = min(scale_x, scale_y)
        else:  # FILL
            scale = max(scale_x, scale_y)

        return (max(1, int(design_w * scale)), max(1, int(design_h * scale)))

    def _calculate_alignment_offset(
        self, design_size: tuple[int, int], box_size: tuple[int, int]
    ) -> tuple[int, int]:
        """
        Calculate where to place the design inside the upright placeholder box.

        Args:
            design_size: (width, height) of the scaled design
            box_size: (width, height) of the placeholder box

        Returns:
            (x, y) offset within the box
        """
        design_w, design_h = design_size
        box_w, box_h = box_size
        value = self.alignment.value

        if "left" in value:
            x_offset = 0
        elif "right" in value:
            x_offset = box_w - design_w
        else:
            x_offset = (box_w - design_w) // 2

        if "top" in value:
            y_offset = 0
        elif "bottom" in value:
            y_offset = box_h - design_h
        else:
            y_offset = (box_h - design_h) // 2

        return (x_offset, y_offset)

    def _compose_box(self, design: Image.Image, params: BoxParameters) -> Image.Image:
        """
        Scale and align the design onto a transparent canvas the size of the box.

        Anything overflowing the box is clipped, which is what gives FILL its
        crop-to-box behaviour.

        Args:
            design: The design image, in RGBA
            params: Box parameters for the target mockup

        Returns:
            An RGBA canvas exactly the size of the placeholder box
        """
        box_size = (params.width, params.height)

        scaled = design.resize(
            self._calculate_scaled_size(design.size, box_size), Image.Resampling.LANCZOS
        )

        canvas = Image.new("RGBA", box_size, (0, 0, 0, 0))
        canvas.paste(scaled, self._calculate_alignment_offset(scaled.size, box_size), scaled)
        return canvas

    def generate_mockup(
        self,
        design_path: str | Path,
        mockup_path: str | Path,
        output_path: str | Path,
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

        if mockup_path.name not in self.parameters:
            return GenerationResult(
                success=False,
                output_path=None,
                design_name=design_path.name,
                mockup_name=mockup_path.name,
                error=f"No parameters found for mockup: {mockup_path.name}",
            )

        params = self.parameters[mockup_path.name]

        try:
            with Image.open(design_path) as design_src, Image.open(mockup_path) as mockup_src:
                design = design_src.convert("RGBA")
                output = mockup_src.convert("RGBA")

            if self.cover_placeholder:
                self._erase_placeholder(output, params)

            placed = self._compose_box(design, params)

            # The box frame is upright; rotate it into the template's frame.
            # `rotation` tilts clockwise on screen, while PIL rotates
            # counter-clockwise, hence the negation.
            if abs(params.rotation) >= _ROTATION_EPSILON_DEG:
                placed = placed.rotate(
                    -params.rotation,
                    expand=True,
                    resample=Image.Resampling.BICUBIC,
                    fillcolor=(0, 0, 0, 0),
                )

            center_x, center_y = params.center
            position = (
                int(round(center_x - placed.width / 2)),
                int(round(center_y - placed.height / 2)),
            )
            output.paste(placed, position, placed)

            output_path.parent.mkdir(parents=True, exist_ok=True)

            if self.output_format in ("JPEG", "JPG"):
                output.convert("RGB").save(output_path, format="JPEG", quality=self.output_quality)
            else:
                output.save(output_path, format=self.output_format)

            logger.debug(f"Generated: {output_path.name}")

            return GenerationResult(
                success=True,
                output_path=output_path,
                design_name=design_path.name,
                mockup_name=mockup_path.name,
            )

        except Exception as e:
            logger.error(f"Error generating mockup: {e}")
            return GenerationResult(
                success=False,
                output_path=None,
                design_name=design_path.name,
                mockup_name=mockup_path.name,
                error=str(e),
            )

    def generate_all(
        self,
        design_dir: str | Path,
        mockup_dir: str | Path,
        output_dir: str | Path,
        naming_pattern: str = "{design}_{mockup}",
        parallel: bool = True,
        max_workers: int = 4,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[GenerationResult]:
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

        designs = get_image_files(design_dir)
        mockups = [f for f in get_image_files(mockup_dir) if f.name in self.parameters]

        logger.info(f"Generating {len(designs)} designs x {len(mockups)} mockups")

        extension = (
            ".jpg" if self.output_format in ("JPEG", "JPG") else f".{self.output_format.lower()}"
        )

        tasks = []
        for design_path in designs:
            for mockup_path in mockups:
                output_name = naming_pattern.format(
                    design=design_path.stem, mockup=mockup_path.stem
                )
                tasks.append((design_path, mockup_path, output_dir / f"{output_name}{extension}"))

        total = len(tasks)
        results: list[GenerationResult] = []
        completed = 0

        if parallel and len(tasks) > 1:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(self.generate_mockup, *task) for task in tasks]

                for future in as_completed(futures):
                    results.append(future.result())
                    completed += 1
                    if progress_callback:
                        progress_callback(completed, total)
        else:
            for task in tasks:
                results.append(self.generate_mockup(*task))
                completed += 1
                if progress_callback:
                    progress_callback(completed, total)

        successful = sum(1 for r in results if r.success)
        logger.info(f"Generation complete: {successful}/{total} successful")

        if successful < total:
            for r in [r for r in results if not r.success][:5]:
                logger.warning(f"Failed: {r.design_name} + {r.mockup_name}: {r.error}")

        return results

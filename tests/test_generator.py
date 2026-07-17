"""
Tests for the MockupGenerator class.

The central test here is end-to-end: render a design into a placeholder and
assert the ink lands where the placeholder actually was. That property is what
catches placement regressions, which unit-testing the maths alone will not.
"""

import numpy as np
import pytest
from PIL import Image

from mockup_generator import Color, MockupCalculator, MockupGenerator
from mockup_generator.generator import Alignment, GenerationResult, ScaleMode

CANVAS = (600, 600)
RED = (255, 0, 0)
BLUE = (0, 0, 255)


def write_mockup(path, box_w, box_h, tilt_deg=0.0):
    """Write a white template carrying one red placeholder box, optionally tilted."""
    template = Image.new("RGB", CANVAS, (255, 255, 255))
    box = Image.new("RGBA", (box_w, box_h), RED + (255,))

    if tilt_deg:
        box = box.rotate(
            tilt_deg, expand=True, resample=Image.Resampling.NEAREST, fillcolor=(0, 0, 0, 0)
        )

    template.paste(box, (CANVAS[0] // 2 - box.width // 2, CANVAS[1] // 2 - box.height // 2), box)
    template.save(path)
    return path


def write_design(path, width=64, height=64, color=BLUE):
    """Write a solid design so its footprint is unambiguous in the output."""
    Image.new("RGB", (width, height), color).save(path)
    return path


def mask_of(image_array, channel):
    """Boolean mask of pixels dominated by the given channel."""
    others = [c for c in (0, 1, 2) if c != channel]
    return (image_array[:, :, channel] > 200) & np.all(image_array[:, :, others] < 80, axis=-1)


def iou(mask_a, mask_b):
    union = np.logical_or(mask_a, mask_b).sum()
    return float(np.logical_and(mask_a, mask_b).sum() / union) if union else 0.0


@pytest.fixture
def calculator():
    return MockupCalculator(Color(*RED), color_tolerance=30)


class TestPlacementAccuracy:
    """The design must land on the placeholder it was aimed at."""

    @pytest.mark.parametrize(
        "box_w,box_h,tilt",
        [
            (100, 150, 0),  # tall  - the only shape the original suite covered
            (150, 100, 0),  # wide  - previously rotated 90 degrees
            (200, 60, 0),  # wider - previously rotated 90 degrees
            (120, 120, 0),  # square - previously rotated 45 degrees
            (150, 100, 20),  # genuinely tilted
            (150, 100, -30),  # tilted the other way
        ],
    )
    def test_design_covers_the_placeholder(self, calculator, tmp_path, box_w, box_h, tilt):
        mockup = write_mockup(tmp_path / "m.png", box_w, box_h, tilt)
        design = write_design(tmp_path / "d.png")

        placeholder = mask_of(np.array(Image.open(mockup).convert("RGB")), channel=0)

        params = calculator.calculate_parameters(mockup)
        assert params is not None

        generator = MockupGenerator(
            {params.filename: params}, scale_mode=ScaleMode.STRETCH, alignment=Alignment.CENTER
        )
        result = generator.generate_mockup(design, mockup, tmp_path / "out.png")
        assert result.success, result.error

        painted = mask_of(np.array(Image.open(result.output_path).convert("RGB")), channel=2)

        # Anti-aliasing along the rotated edges costs a little overlap, so this
        # is deliberately short of 1.0 while still far above what a wrongly
        # rotated placement could reach.
        assert iou(placeholder, painted) > 0.9

    def test_no_red_placeholder_remains_visible(self, calculator, tmp_path):
        """A correctly placed design should cover the marker it was aimed at."""
        mockup = write_mockup(tmp_path / "m.png", 120, 120, 0)
        design = write_design(tmp_path / "d.png")

        params = calculator.calculate_parameters(mockup)
        generator = MockupGenerator({params.filename: params}, scale_mode=ScaleMode.STRETCH)
        result = generator.generate_mockup(design, mockup, tmp_path / "out.png")

        remaining = mask_of(np.array(Image.open(result.output_path).convert("RGB")), channel=0)
        assert remaining.sum() < 0.02 * (120 * 120)


class TestPlaceholderCovering:
    """
    The marker must not survive into the output.

    Designs are typically transparent PNGs, so simply pasting over the marker
    leaves it showing through everywhere the design does not paint.
    """

    def write_transparent_design(self, path, size=200):
        """A design that paints only a small dot, leaving most of the box bare."""
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        img.paste(Image.new("RGBA", (20, 20), BLUE + (255,)), (size // 2, size // 2))
        img.save(path)
        return path

    def test_transparent_design_leaves_no_marker(self, calculator, tmp_path):
        mockup = write_mockup(tmp_path / "m.png", 200, 200, 0)
        design = self.write_transparent_design(tmp_path / "d.png")

        params = calculator.calculate_parameters(mockup)
        generator = MockupGenerator({params.filename: params}, scale_mode=ScaleMode.NONE)
        result = generator.generate_mockup(design, mockup, tmp_path / "out.png")
        assert result.success, result.error

        remaining = mask_of(np.array(Image.open(result.output_path).convert("RGB")), channel=0)
        assert remaining.sum() == 0

    def test_marker_is_erased_on_a_tilted_box(self, calculator, tmp_path):
        mockup = write_mockup(tmp_path / "m.png", 200, 120, 25)
        design = self.write_transparent_design(tmp_path / "d.png")

        params = calculator.calculate_parameters(mockup)
        generator = MockupGenerator({params.filename: params}, scale_mode=ScaleMode.NONE)
        result = generator.generate_mockup(design, mockup, tmp_path / "out.png")

        remaining = mask_of(np.array(Image.open(result.output_path).convert("RGB")), channel=0)
        assert remaining.sum() == 0

    def test_fill_colour_is_sampled_from_the_template(self, calculator, tmp_path):
        """A box sitting on a coloured garment should be erased to that colour."""
        garment = (30, 160, 90)
        template = Image.new("RGB", CANVAS, garment)
        template.paste(Image.new("RGB", (150, 150), RED), (225, 225))
        template.save(tmp_path / "m.png")

        design = self.write_transparent_design(tmp_path / "d.png")
        params = calculator.calculate_parameters(tmp_path / "m.png")

        generator = MockupGenerator({params.filename: params}, scale_mode=ScaleMode.NONE)
        result = generator.generate_mockup(design, tmp_path / "m.png", tmp_path / "out.png")

        out = np.array(Image.open(result.output_path).convert("RGB"))
        # Where the marker used to be, we should now find the garment colour.
        assert tuple(out[230, 230]) == garment

    def test_explicit_fill_overrides_sampling(self, calculator, tmp_path):
        mockup = write_mockup(tmp_path / "m.png", 200, 200, 0)
        design = self.write_transparent_design(tmp_path / "d.png")

        params = calculator.calculate_parameters(mockup)
        generator = MockupGenerator(
            {params.filename: params}, scale_mode=ScaleMode.NONE, placeholder_fill=(10, 20, 30)
        )
        result = generator.generate_mockup(design, mockup, tmp_path / "out.png")

        out = np.array(Image.open(result.output_path).convert("RGB"))
        # Sample inside the box but clear of the design's dot.
        assert tuple(out[220, 220]) == (10, 20, 30)

    def test_opt_out_keeps_the_marker(self, calculator, tmp_path):
        mockup = write_mockup(tmp_path / "m.png", 200, 200, 0)
        design = self.write_transparent_design(tmp_path / "d.png")

        params = calculator.calculate_parameters(mockup)
        generator = MockupGenerator(
            {params.filename: params}, scale_mode=ScaleMode.NONE, cover_placeholder=False
        )
        result = generator.generate_mockup(design, mockup, tmp_path / "out.png")

        remaining = mask_of(np.array(Image.open(result.output_path).convert("RGB")), channel=0)
        assert remaining.sum() > 0

    def test_covering_does_not_bleed_outside_the_box(self, calculator, tmp_path):
        """Erasing must stay local; the rest of the template is untouched."""
        mockup = write_mockup(tmp_path / "m.png", 200, 200, 0)
        design = self.write_transparent_design(tmp_path / "d.png")
        before = np.array(Image.open(mockup).convert("RGB"))

        params = calculator.calculate_parameters(mockup)
        generator = MockupGenerator({params.filename: params}, scale_mode=ScaleMode.NONE)
        result = generator.generate_mockup(design, mockup, tmp_path / "out.png")
        after = np.array(Image.open(result.output_path).convert("RGB"))

        # A generous margin outside the box must be pixel-identical.
        min_r, min_c, max_r, max_c = params.bbox
        margin = 20
        untouched = np.ones(before.shape[:2], dtype=bool)
        untouched[min_r - margin : max_r + margin, min_c - margin : max_c + margin] = False

        assert np.array_equal(before[untouched], after[untouched])


class TestScaleModes:
    """Tests for how designs are fitted to the box."""

    @pytest.fixture
    def square_params(self, calculator, tmp_path):
        mockup = write_mockup(tmp_path / "sq.png", 200, 200, 0)
        return mockup, calculator.calculate_parameters(mockup)

    def test_stretch_fills_the_whole_box(self, square_params, tmp_path):
        mockup, params = square_params
        design = write_design(tmp_path / "d.png", 40, 80)

        generator = MockupGenerator({params.filename: params}, scale_mode=ScaleMode.STRETCH)
        result = generator.generate_mockup(design, mockup, tmp_path / "out.png")

        painted = mask_of(np.array(Image.open(result.output_path).convert("RGB")), channel=2)
        assert painted.sum() == pytest.approx(200 * 200, rel=0.05)

    def test_fit_preserves_aspect_ratio(self, square_params, tmp_path):
        mockup, params = square_params
        design = write_design(tmp_path / "d.png", 40, 80)  # 1:2

        generator = MockupGenerator({params.filename: params}, scale_mode=ScaleMode.FIT)
        result = generator.generate_mockup(design, mockup, tmp_path / "out.png")

        painted = mask_of(np.array(Image.open(result.output_path).convert("RGB")), channel=2)
        rows = np.where(painted.any(axis=1))[0]
        cols = np.where(painted.any(axis=0))[0]
        height = rows[-1] - rows[0] + 1
        width = cols[-1] - cols[0] + 1

        assert height == pytest.approx(200, abs=2)
        assert width == pytest.approx(100, abs=2)

    def test_fill_covers_box_and_crops_overflow(self, square_params, tmp_path):
        mockup, params = square_params
        design = write_design(tmp_path / "d.png", 40, 80)

        generator = MockupGenerator({params.filename: params}, scale_mode=ScaleMode.FILL)
        result = generator.generate_mockup(design, mockup, tmp_path / "out.png")

        painted = mask_of(np.array(Image.open(result.output_path).convert("RGB")), channel=2)
        # FILL must cover the box completely and must not spill outside it.
        assert painted.sum() == pytest.approx(200 * 200, rel=0.05)


class TestAlignment:
    """Alignment is applied within the box, before any rotation."""

    @pytest.fixture
    def wide_box(self, calculator, tmp_path):
        mockup = write_mockup(tmp_path / "wide.png", 200, 200, 0)
        return mockup, calculator.calculate_parameters(mockup)

    @pytest.mark.parametrize(
        "alignment,expect_left,expect_top",
        [
            (Alignment.TOP_LEFT, True, True),
            (Alignment.TOP_RIGHT, False, True),
            (Alignment.BOTTOM_LEFT, True, False),
            (Alignment.BOTTOM_RIGHT, False, False),
        ],
    )
    def test_corners(self, wide_box, tmp_path, alignment, expect_left, expect_top):
        mockup, params = wide_box
        design = write_design(tmp_path / "d.png", 50, 50)

        generator = MockupGenerator(
            {params.filename: params}, alignment=alignment, scale_mode=ScaleMode.NONE
        )
        result = generator.generate_mockup(design, mockup, tmp_path / "out.png")

        painted = mask_of(np.array(Image.open(result.output_path).convert("RGB")), channel=2)
        rows = np.where(painted.any(axis=1))[0]
        cols = np.where(painted.any(axis=0))[0]
        box_min_row, box_min_col, box_max_row, box_max_col = params.bbox

        if expect_left:
            assert cols[0] == pytest.approx(box_min_col, abs=3)
        else:
            assert cols[-1] == pytest.approx(box_max_col - 1, abs=3)

        if expect_top:
            assert rows[0] == pytest.approx(box_min_row, abs=3)
        else:
            assert rows[-1] == pytest.approx(box_max_row - 1, abs=3)


class TestGenerateAll:
    """Tests for batch generation."""

    def test_generates_every_combination(self, calculator, tmp_path):
        mockup_dir = tmp_path / "mockups"
        design_dir = tmp_path / "designs"
        out_dir = tmp_path / "out"
        mockup_dir.mkdir()
        design_dir.mkdir()

        write_mockup(mockup_dir / "a.png", 120, 120)
        write_mockup(mockup_dir / "b.png", 150, 100)
        write_design(design_dir / "one.png")
        write_design(design_dir / "two.png")

        params = calculator.process_directory(mockup_dir)
        generator = MockupGenerator(params)
        results = generator.generate_all(design_dir, mockup_dir, out_dir)

        assert len(results) == 4
        assert all(r.success for r in results)
        assert len(list(out_dir.glob("*.png"))) == 4

    def test_parallel_and_sequential_agree(self, calculator, tmp_path):
        mockup_dir = tmp_path / "mockups"
        design_dir = tmp_path / "designs"
        mockup_dir.mkdir()
        design_dir.mkdir()

        write_mockup(mockup_dir / "a.png", 120, 120)
        write_design(design_dir / "one.png")

        params = calculator.process_directory(mockup_dir)
        generator = MockupGenerator(params)

        par = generator.generate_all(design_dir, mockup_dir, tmp_path / "p", parallel=True)
        seq = generator.generate_all(design_dir, mockup_dir, tmp_path / "s", parallel=False)

        assert [r.success for r in par] == [r.success for r in seq]
        assert np.array_equal(
            np.array(Image.open(tmp_path / "p" / "one_a.png")),
            np.array(Image.open(tmp_path / "s" / "one_a.png")),
        )

    def test_progress_callback_reports_completion(self, calculator, tmp_path):
        mockup_dir = tmp_path / "mockups"
        design_dir = tmp_path / "designs"
        mockup_dir.mkdir()
        design_dir.mkdir()

        write_mockup(mockup_dir / "a.png", 120, 120)
        write_design(design_dir / "one.png")
        write_design(design_dir / "two.png")

        params = calculator.process_directory(mockup_dir)
        generator = MockupGenerator(params)

        seen = []
        generator.generate_all(
            design_dir,
            mockup_dir,
            tmp_path / "o",
            progress_callback=lambda c, t: seen.append((c, t)),
        )

        assert seen[-1] == (2, 2)

    def test_jpeg_output_uses_jpg_extension(self, calculator, tmp_path):
        mockup_dir = tmp_path / "mockups"
        design_dir = tmp_path / "designs"
        mockup_dir.mkdir()
        design_dir.mkdir()

        write_mockup(mockup_dir / "a.png", 120, 120)
        write_design(design_dir / "one.png")

        params = calculator.process_directory(mockup_dir)
        generator = MockupGenerator(params, output_format="JPEG")
        results = generator.generate_all(design_dir, mockup_dir, tmp_path / "o")

        assert all(r.success for r in results), [r.error for r in results]
        assert (tmp_path / "o" / "one_a.jpg").exists()


class TestFailureHandling:
    """Tests for graceful degradation."""

    def test_unknown_mockup_reports_error(self, tmp_path):
        design = write_design(tmp_path / "d.png")
        mockup = write_mockup(tmp_path / "m.png", 100, 100)

        generator = MockupGenerator({})
        result = generator.generate_mockup(design, mockup, tmp_path / "out.png")

        assert isinstance(result, GenerationResult)
        assert not result.success
        assert "No parameters found" in result.error

    def test_missing_design_reports_error(self, calculator, tmp_path):
        mockup = write_mockup(tmp_path / "m.png", 100, 100)
        params = calculator.calculate_parameters(mockup)

        generator = MockupGenerator({params.filename: params})
        result = generator.generate_mockup(tmp_path / "nope.png", mockup, tmp_path / "out.png")

        assert not result.success
        assert result.error

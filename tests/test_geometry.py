"""Tests for the rotated-rectangle geometry helpers."""

import numpy as np
import pytest

from mockup_generator.geometry import (
    extent_to_pixel_count,
    min_area_rect,
    normalize_rect,
    rect_corners,
)


def filled_rect_coords(width: int, height: int, angle_deg: float = 0.0, center: float = 300.0):
    """Build (row, col) coords for a filled rectangle tilted by angle_deg."""
    ys, xs = np.mgrid[0:height, 0:width]
    points = np.column_stack([xs.ravel(), ys.ravel()]).astype(float)
    points -= points.mean(axis=0)

    theta = np.radians(angle_deg)
    rotation = np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
    points = points @ rotation.T + center

    return np.column_stack([points[:, 1], points[:, 0]])


class TestNormalizeRect:
    """Tests for canonical rotated-rectangle form."""

    def test_leaves_small_tilts_alone(self):
        assert normalize_rect(100, 50, 20.0) == (100, 50, 20.0)

    def test_ninety_degrees_is_axis_aligned_with_swapped_sides(self):
        # A 50x100 box tilted 90 degrees is a 100x50 box tilted not at all.
        width, height, angle = normalize_rect(50, 100, 90.0)
        assert (width, height) == (100, 50)
        assert angle == pytest.approx(0.0)

    def test_result_is_always_within_canonical_range(self):
        for angle in range(-360, 361, 7):
            _, _, normalized = normalize_rect(80, 40, float(angle))
            assert -45.0 < normalized <= 45.0


class TestExtentToPixelCount:
    """A run of N pixels spans N-1 units between its outer centres."""

    def test_round_trips_pixel_counts(self):
        assert extent_to_pixel_count(99.0) == 100
        assert extent_to_pixel_count(0.0) == 1


class TestMinAreaRect:
    """Tests for minimum-area rectangle recovery."""

    def test_returns_none_for_degenerate_input(self):
        assert min_area_rect(np.array([[0, 0], [1, 1]])) is None

    def test_returns_none_for_collinear_points(self):
        collinear = np.array([[0, i] for i in range(10)])
        assert min_area_rect(collinear) is None

    @pytest.mark.parametrize(
        "width,height",
        [(100, 150), (150, 100), (200, 60), (120, 120)],
    )
    def test_axis_aligned_boxes_report_no_tilt(self, width, height):
        """
        Regression: an untilted box must report 0 degrees regardless of shape.

        The previous implementation used region orientation, which reported 90
        degrees for any wide box and -45 for a square, silently rotating every
        design placed into one.
        """
        _, (w, h), angle = min_area_rect(filled_rect_coords(width, height))

        assert angle == pytest.approx(0.0, abs=0.5)
        assert extent_to_pixel_count(w) == pytest.approx(width, abs=1)
        assert extent_to_pixel_count(h) == pytest.approx(height, abs=1)

    @pytest.mark.parametrize("tilt", [-40, -20, -5, 5, 20, 30, 40])
    def test_recovers_true_tilt(self, tilt):
        _, (w, h), angle = min_area_rect(filled_rect_coords(150, 100, tilt))

        assert angle == pytest.approx(tilt, abs=1.0)
        assert extent_to_pixel_count(w) == pytest.approx(150, abs=2)
        assert extent_to_pixel_count(h) == pytest.approx(100, abs=2)

    def test_recovers_center(self):
        (cx, cy), _, _ = min_area_rect(filled_rect_coords(150, 100, 25.0, center=300.0))

        assert cx == pytest.approx(300.0, abs=1.0)
        assert cy == pytest.approx(300.0, abs=1.0)

    def test_area_is_minimal_versus_axis_aligned_bounds(self):
        """A tilted box's min-area rect must beat its axis-aligned bounds."""
        coords = filled_rect_coords(200, 60, 30.0)
        _, (w, h), _ = min_area_rect(coords)

        aabb_area = np.ptp(coords[:, 0]) * np.ptp(coords[:, 1])
        assert w * h < aabb_area


class TestRectCorners:
    """Tests for corner reconstruction."""

    def test_untilted_corners(self):
        corners = rect_corners((100.0, 100.0), (40.0, 20.0), 0.0)
        xs = sorted({round(x) for x, _ in corners})
        ys = sorted({round(y) for _, y in corners})

        assert xs == [80, 120]
        assert ys == [90, 110]

    def test_corners_round_trip_through_min_area_rect(self):
        corners = np.array(rect_corners((300.0, 300.0), (150.0, 100.0), 20.0))
        coords = np.column_stack([corners[:, 1], corners[:, 0]])

        _, (w, h), angle = min_area_rect(coords)

        assert angle == pytest.approx(20.0, abs=0.5)
        assert sorted([round(w), round(h)]) == [100, 150]

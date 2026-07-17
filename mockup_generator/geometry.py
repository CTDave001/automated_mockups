"""
Geometric primitives for locating placeholder boxes.

The key routine here is :func:`min_area_rect`, which recovers the true
minimum-area rectangle enclosing a set of pixels. This is what lets the
calculator report the *tilt* of a placeholder box rather than a property of
its equivalent ellipse.
"""

import numpy as np
from scipy.spatial import ConvexHull, QhullError

# A rectangle is fully described by its centre, its side lengths, and its tilt.
RotatedRect = tuple[tuple[float, float], tuple[float, float], float]


def normalize_rect(width: float, height: float, angle_deg: float) -> tuple[float, float, float]:
    """
    Put a rotated rectangle into canonical form.

    A rectangle of size ``(w, h)`` tilted by ``a`` describes exactly the same
    region as one of size ``(h, w)`` tilted by ``a + 90``. This picks the
    representation with the smallest tilt, so an axis-aligned box reports 0
    degrees instead of an arbitrary multiple of 90.

    Args:
        width: Rectangle width along its own local x-axis
        height: Rectangle height along its own local y-axis
        angle_deg: Tilt in degrees

    Returns:
        ``(width, height, angle)`` with angle in the range (-45, 45]
    """
    while angle_deg <= -45.0:
        angle_deg += 90.0
        width, height = height, width
    while angle_deg > 45.0:
        angle_deg -= 90.0
        width, height = height, width
    return width, height, angle_deg


def _rotation_matrix(theta: float) -> np.ndarray:
    """Return the 2x2 matrix rotating a point by ``theta`` radians."""
    cos_t, sin_t = np.cos(theta), np.sin(theta)
    return np.array([[cos_t, -sin_t], [sin_t, cos_t]])


def min_area_rect(coords: np.ndarray) -> RotatedRect | None:
    """
    Find the minimum-area rectangle enclosing a set of pixels.

    Uses rotating calipers over the convex hull. The minimum-area enclosing
    rectangle always has one side collinear with a hull edge, so testing every
    hull edge is exhaustive rather than approximate.

    Args:
        coords: Array of shape (N, 2) holding ``(row, col)`` pixel coordinates,
            matching the layout of ``skimage`` region ``coords``.

    Returns:
        ``((center_x, center_y), (width, height), angle_degrees)`` with the
        angle normalized to (-45, 45], or None if the points are degenerate
        (fewer than 3 points, or exactly collinear).
    """
    if coords.shape[0] < 3:
        return None

    # Work in (x, y) so that angles read naturally against image axes.
    points = np.column_stack([coords[:, 1], coords[:, 0]]).astype(np.float64)

    try:
        hull: np.ndarray = points[ConvexHull(points).vertices]
    except (QhullError, ValueError):
        # Collinear or otherwise degenerate input has no 2D hull.
        return None

    best_area: float | None = None
    best: RotatedRect | None = None

    for i in range(len(hull)):
        edge = hull[(i + 1) % len(hull)] - hull[i]
        if not edge.any():
            continue

        theta = float(np.arctan2(edge[1], edge[0]))

        # Rotate the hull so this edge lies on the x-axis; the enclosing box is
        # then just an axis-aligned bounding box, which is trivial to measure.
        aligned = hull @ _rotation_matrix(-theta).T
        mins = aligned.min(axis=0)
        maxs = aligned.max(axis=0)
        width, height = maxs - mins
        area = float(width * height)

        if best_area is None or area < best_area:
            best_area = area
            center = _rotation_matrix(theta) @ ((mins + maxs) / 2.0)
            best = (
                (float(center[0]), float(center[1])),
                (float(width), float(height)),
                float(np.degrees(theta)),
            )

    if best is None:
        return None

    center_xy, (width, height), angle = best
    width, height, angle = normalize_rect(width, height, angle)
    return center_xy, (width, height), angle


def extent_to_pixel_count(extent: float) -> int:
    """
    Convert a span measured between pixel centres into a pixel count.

    A run of N pixels spans N-1 units from first centre to last centre, so the
    inverse adds one back. Keeps reported sizes consistent with the pixel
    dimensions a user actually drew.
    """
    return int(round(extent)) + 1


def rect_corners(
    center: tuple[float, float], size: tuple[float, float], angle_deg: float
) -> list[tuple[float, float]]:
    """
    Return the four corners of a rotated rectangle, for tests and debugging.

    Args:
        center: ``(x, y)`` centre of the rectangle
        size: ``(width, height)`` of the rectangle
        angle_deg: Tilt in degrees

    Returns:
        Four ``(x, y)`` corners in order.
    """
    half_w, half_h = size[0] / 2.0, size[1] / 2.0
    local = np.array([(-half_w, -half_h), (half_w, -half_h), (half_w, half_h), (-half_w, half_h)])
    rotated = local @ _rotation_matrix(np.radians(angle_deg)).T + np.asarray(center)
    return [(float(x), float(y)) for x, y in rotated]

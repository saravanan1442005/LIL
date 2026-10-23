"""Geometric utility functions for virtual tripwire line crossing and zone polygon detection.
Used by the tracking and event generation engine.
"""
from typing import List, Tuple, Optional


def ccw(A: Tuple[float, float], B: Tuple[float, float], C: Tuple[float, float]) -> bool:
    """Check if three points are listed in counterclockwise order."""
    return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])


def segments_intersect(
    A: Tuple[float, float], B: Tuple[float, float],
    C: Tuple[float, float], D: Tuple[float, float]
) -> bool:
    """Return True if line segment AB intersects line segment CD."""
    return (ccw(A, C, D) != ccw(B, C, D)) and (ccw(A, B, C) != ccw(A, B, D))


def get_crossing_direction(
    prev_pos: Tuple[float, float],
    curr_pos: Tuple[float, float],
    line_start: Tuple[float, float],
    line_end: Tuple[float, float]
) -> str:
    """Determine crossing direction relative to directed tripwire line (line_start -> line_end).
    Returns 'ENTRY' if crossed from right-to-left of line, 'EXIT' if crossed from left-to-right.
    """
    # Vector along tripwire: L = line_end - line_start
    lx = line_end[0] - line_start[0]
    ly = line_end[1] - line_start[1]

    # Motion vector: M = curr_pos - prev_pos
    mx = curr_pos[0] - prev_pos[0]
    my = curr_pos[1] - prev_pos[1]

    # 2D cross product: L x M = lx * my - ly * mx
    cross_product = lx * my - ly * mx
    if cross_product > 0:
        return "ENTRY"
    elif cross_product < 0:
        return "EXIT"
    return "CROSS"


def check_line_crossing(
    prev_point: Tuple[float, float],
    curr_point: Tuple[float, float],
    tripwire_coords: List[List[float]]
) -> Optional[str]:
    """Check if object moving from prev_point to curr_point crossed the tripwire.
    tripwire_coords is [[x1, y1], [x2, y2]].
    Returns 'ENTRY', 'EXIT', or None.
    """
    if not tripwire_coords or len(tripwire_coords) < 2:
        return None

    p1 = (float(prev_point[0]), float(prev_point[1]))
    p2 = (float(curr_point[0]), float(curr_point[1]))
    l1 = (float(tripwire_coords[0][0]), float(tripwire_coords[0][1]))
    l2 = (float(tripwire_coords[1][0]), float(tripwire_coords[1][1]))

    if segments_intersect(p1, p2, l1, l2):
        return get_crossing_direction(p1, p2, l1, l2)
    return None


def point_in_polygon(point: Tuple[float, float], polygon: List[List[float]]) -> bool:
    """Ray casting algorithm to determine if a 2D point is inside a polygon."""
    if not polygon or len(polygon) < 3:
        return False

    x, y = point[0], point[1]
    inside = False
    n = len(polygon)
    p1x, p1y = polygon[0][0], polygon[0][1]

    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n][0], polygon[i % n][1]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y

    return inside

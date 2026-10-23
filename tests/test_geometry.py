"""Unit tests for virtual tripwire line crossing and polygon containment logic."""
from services.geometry import (
    segments_intersect, get_crossing_direction, check_line_crossing, point_in_polygon
)


def test_line_intersection():
    # Crossing lines
    assert segments_intersect((0, 0), (10, 10), (0, 10), (10, 0)) is True
    # Parallel lines
    assert segments_intersect((0, 0), (10, 0), (0, 5), (10, 5)) is False
    # Disjoint segments
    assert segments_intersect((0, 0), (2, 2), (5, 5), (10, 10)) is False


def test_tripwire_crossing_direction():
    tripwire = [[0.0, 10.0], [10.0, 10.0]]  # Horizontal tripwire at y=10, directed from x=0 to x=10

    # Moving downward across line: (5, 5) -> (5, 15)
    # L = (10, 0), M = (0, 10) -> L x M = 10*10 - 0 = 100 > 0 -> ENTRY
    crossing_down = check_line_crossing((5.0, 5.0), (5.0, 15.0), tripwire)
    assert crossing_down == "ENTRY"

    # Moving upward across line: (5, 15) -> (5, 5)
    # L = (10, 0), M = (0, -10) -> L x M = -100 < 0 -> EXIT
    crossing_up = check_line_crossing((5.0, 15.0), (5.0, 5.0), tripwire)
    assert crossing_up == "EXIT"

    # Moving without crossing line: (5, 2) -> (5, 8)
    no_crossing = check_line_crossing((5.0, 2.0), (5.0, 8.0), tripwire)
    assert no_crossing is None


def test_point_in_polygon():
    square = [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]]

    # Inside
    assert point_in_polygon((5.0, 5.0), square) is True
    # Outside
    assert point_in_polygon((15.0, 5.0), square) is False
    assert point_in_polygon((-1.0, 5.0), square) is False

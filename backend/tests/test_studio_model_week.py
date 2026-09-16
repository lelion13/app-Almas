from datetime import time

from app.services.studio_service import tile_open_window


def test_tile_open_window_splits_by_duration():
    tiles = tile_open_window(time(8, 0), time(10, 0), 60)
    assert tiles == [(time(8, 0), time(9, 0)), (time(9, 0), time(10, 0))]


def test_tile_open_window_drops_partial_remainder():
    tiles = tile_open_window(time(8, 0), time(9, 30), 60)
    assert tiles == [(time(8, 0), time(9, 0))]
